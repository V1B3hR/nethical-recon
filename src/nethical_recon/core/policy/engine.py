"""Policy enforcement engine."""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from .models import Policy, RiskLevel


class PolicyViolationError(Exception):
    """Raised when a policy is violated."""

    pass


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        """Initialize rate limiter.

        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate


class PolicyEngine:
    """Policy enforcement engine for Rules of Engagement."""

    def __init__(self, policy: Policy | None = None):
        """Initialize policy engine.

        Args:
            policy: Policy to enforce (uses default if None)
        """
        from .models import create_default_policy

        self.policy = policy or create_default_policy()
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._active_scans: set[str] = set()
        self._active_tools: dict[str, int] = defaultdict(int)
        self._lock = Lock()
        
        # Pre-compute lowercase high-risk tools set for efficient lookup
        self._high_risk_tools_lower = frozenset(
            tool.lower() for tool in self.policy.tool.high_risk_tools
        )

    def validate_target(self, target: str) -> bool:
        """Validate if target is allowed by network policy.

        Args:
            target: Target IP or hostname

        Returns:
            True if target is allowed

        Raises:
            PolicyViolationError: If target is not allowed
        """
        if not self.policy.network.enabled:
            return True

        # Try to parse as IP address
        try:
            target_ip = ipaddress.ip_address(target)
        except ValueError:
            # Not an IP, assume hostname is OK (will be resolved later)
            return True

        # Check deny list first
        for network_str in self.policy.network.deny_networks:
            network = ipaddress.ip_network(network_str)
            if target_ip in network:
                raise PolicyViolationError(f"Target {target} is in denied network {network_str}")

        # Check allow list if specified
        if self.policy.network.allow_networks:
            allowed = False
            for network_str in self.policy.network.allow_networks:
                network = ipaddress.ip_network(network_str)
                if target_ip in network:
                    allowed = True
                    break
            if not allowed:
                raise PolicyViolationError(f"Target {target} is not in any allowed network")

        return True

    def validate_tool(self, tool_name: str) -> bool:
        """Validate if tool is allowed by tool policy.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is allowed

        Raises:
            PolicyViolationError: If tool is not allowed
        """
        if not self.policy.tool.enabled:
            return True

        # Check if tool is in allowed list (if specified)
        if self.policy.tool.allowed_tools and tool_name not in self.policy.tool.allowed_tools:
            raise PolicyViolationError(f"Tool {tool_name} is not in allowed tools list")

        # Check if tool is high-risk and requires approval
        if (
            self.policy.tool.require_approval_for_high_risk
            and tool_name.lower() in self._high_risk_tools_lower
        ):
            raise PolicyViolationError(f"High-risk tool {tool_name} requires explicit approval")

        return True

    def acquire_scan_slot(self, job_id: str) -> bool:
        """Try to acquire a scan slot.

        Args:
            job_id: Job identifier

        Returns:
            True if slot acquired

        Raises:
            PolicyViolationError: If max parallel scans exceeded
        """
        if not self.policy.concurrency.enabled:
            return True

        with self._lock:
            if len(self._active_scans) >= self.policy.concurrency.max_parallel_scans:
                raise PolicyViolationError(
                    f"Max parallel scans ({self.policy.concurrency.max_parallel_scans}) exceeded"
                )
            self._active_scans.add(job_id)
            return True

    def release_scan_slot(self, job_id: str) -> None:
        """Release a scan slot.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            self._active_scans.discard(job_id)

    def acquire_tool_slot(self, job_id: str) -> bool:
        """Try to acquire a tool slot for a job.

        Args:
            job_id: Job identifier

        Returns:
            True if slot acquired

        Raises:
            PolicyViolationError: If max parallel tools exceeded
        """
        if not self.policy.concurrency.enabled:
            return True

        with self._lock:
            current = self._active_tools[job_id]
            if current >= self.policy.concurrency.max_parallel_tools:
                raise PolicyViolationError(
                    f"Max parallel tools ({self.policy.concurrency.max_parallel_tools}) exceeded for job {job_id}"
                )
            self._active_tools[job_id] += 1
            return True

    def release_tool_slot(self, job_id: str) -> None:
        """Release a tool slot for a job.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            if job_id in self._active_tools:
                self._active_tools[job_id] -= 1
                if self._active_tools[job_id] <= 0:
                    del self._active_tools[job_id]

    def acquire_rate_limit(self, key: str = "default") -> bool:
        """Try to acquire rate limit token.

        Args:
            key: Rate limit key (for different limiters)

        Returns:
            True if token acquired

        Raises:
            PolicyViolationError: If rate limit would be exceeded
        """
        if not self.policy.rate_limit.enabled:
            return True

        # Get or create rate limiter for this key
        if key not in self._rate_limiters:
            self._rate_limiters[key] = RateLimiter(
                rate=self.policy.rate_limit.requests_per_second,
                burst=self.policy.rate_limit.burst_size,
            )

        limiter = self._rate_limiters[key]
        if not limiter.acquire():
            wait_time = limiter.wait_time()
            raise PolicyViolationError(f"Rate limit exceeded. Wait {wait_time:.2f} seconds")

        return True

    def get_tool_timeout(self) -> int:
        """Get tool timeout from policy.

        Returns:
            Timeout in seconds
        """
        return self.policy.tool.timeout_seconds

    def check_consent_required(self) -> bool:
        """Check if explicit consent is required.

        Returns:
            True if consent required
        """
        return self.policy.network.require_explicit_consent

    def get_stats(self) -> dict[str, Any]:
        """Get current policy engine statistics.

        Returns:
            Statistics dictionary
        """
        with self._lock:
            return {
                "active_scans": len(self._active_scans),
                "active_tools_by_job": dict(self._active_tools),
                "total_active_tools": sum(self._active_tools.values()),
                "max_parallel_scans": self.policy.concurrency.max_parallel_scans,
                "max_parallel_tools": self.policy.concurrency.max_parallel_tools,
                "rate_limit_enabled": self.policy.rate_limit.enabled,
                "requests_per_second": self.policy.rate_limit.requests_per_second,
            }
