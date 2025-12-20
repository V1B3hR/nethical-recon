"""Policy engine for enforcing Rules of Engagement."""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import ValidationError

from .models import RulesOfEngagement

logger = logging.getLogger(__name__)


class PolicyViolation(Exception):
    """Raised when a policy is violated."""

    pass


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        """Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Burst size (max tokens)
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
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            now = time.time()
            # Add tokens based on time passed
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Try to take tokens
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
    """Engine for enforcing Rules of Engagement."""

    def __init__(self, roe: RulesOfEngagement | None = None):
        """Initialize policy engine.

        Args:
            roe: Rules of Engagement configuration
        """
        self.roe = roe or RulesOfEngagement()
        self.rate_limiter: RateLimiter | None = None
        self.active_jobs: set[str] = set()
        self.active_tools: set[str] = set()
        self.lock = Lock()

        # Initialize rate limiter
        if self.roe.rate_limit.enabled:
            self.rate_limiter = RateLimiter(
                rate=self.roe.rate_limit.requests_per_second,
                burst=self.roe.rate_limit.burst_size,
            )

        # Track tool execution counts per target
        self.tool_counts: dict[str, int] = defaultdict(int)

    @classmethod
    def from_file(cls, path: str | Path) -> PolicyEngine:
        """Load policy engine from YAML/JSON file.

        Args:
            path: Path to configuration file

        Returns:
            Configured policy engine
        """
        import json

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")

        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML configuration files")
            else:
                data = json.load(f)

        try:
            roe = RulesOfEngagement(**data)
            return cls(roe)
        except ValidationError as e:
            raise ValueError(f"Invalid policy configuration: {e}") from e

    def check_target_allowed(self, target: str) -> tuple[bool, str]:
        """Check if a target is allowed to be scanned.

        Args:
            target: Target IP, domain, or CIDR

        Returns:
            Tuple of (allowed, reason)
        """
        # Try to parse as IP address
        try:
            ip = ipaddress.ip_address(target)
            target_network = ipaddress.ip_network(f"{ip}/32", strict=False)
        except ValueError:
            # Not an IP, might be a domain - allow if no network restrictions
            if not self.roe.network.allowed_networks and not self.roe.network.denied_networks:
                return True, "No network restrictions"
            return True, "Domain target, network policies not applicable"

        # Check denied networks first
        for denied in self.roe.network.denied_networks:
            denied_net = ipaddress.ip_network(denied, strict=False)
            if target_network.subnet_of(denied_net) or target_network.overlaps(denied_net):
                return False, f"Target in denied network: {denied}"

        # If allowed networks are specified, target must be in one
        if self.roe.network.allowed_networks:
            for allowed in self.roe.network.allowed_networks:
                allowed_net = ipaddress.ip_network(allowed, strict=False)
                if target_network.subnet_of(allowed_net) or target_network.overlaps(allowed_net):
                    return True, f"Target in allowed network: {allowed}"
            return False, "Target not in any allowed network"

        # No restrictions
        return True, "No network restrictions"

    def check_tool_allowed(self, tool_name: str) -> tuple[bool, str]:
        """Check if a tool is allowed to run.

        Args:
            tool_name: Name of the tool

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.roe.is_tool_allowed(tool_name):
            if tool_name in self.roe.high_risk_tools:
                return False, f"High-risk tool '{tool_name}' not explicitly enabled in policy"
            return False, f"Tool '{tool_name}' is disabled in policy"

        policy = self.roe.get_tool_policy(tool_name)
        if policy.requires_approval:
            return False, f"Tool '{tool_name}' requires explicit approval"

        return True, "Tool allowed"

    def check_concurrency_limits(self, job_id: str | None = None, tool_id: str | None = None) -> tuple[bool, str]:
        """Check if concurrency limits allow starting new job/tool.

        Args:
            job_id: Job ID to start (optional)
            tool_id: Tool ID to start (optional)

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.roe.concurrency.enabled:
            return True, "Concurrency limits disabled"

        with self.lock:
            if job_id and len(self.active_jobs) >= self.roe.concurrency.max_parallel_jobs:
                return False, f"Max parallel jobs limit reached: {self.roe.concurrency.max_parallel_jobs}"

            if tool_id and len(self.active_tools) >= self.roe.concurrency.max_parallel_tools:
                return False, f"Max parallel tools limit reached: {self.roe.concurrency.max_parallel_tools}"

        return True, "Within concurrency limits"

    def acquire_rate_limit(self, tokens: int = 1) -> tuple[bool, float]:
        """Try to acquire rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Tuple of (acquired, wait_time)
        """
        if not self.roe.rate_limit.enabled or not self.rate_limiter:
            return True, 0.0

        if self.rate_limiter.acquire(tokens):
            return True, 0.0

        wait_time = self.rate_limiter.wait_time(tokens)
        return False, wait_time

    def register_job_start(self, job_id: str) -> None:
        """Register that a job has started.

        Args:
            job_id: Job ID
        """
        with self.lock:
            self.active_jobs.add(job_id)
            logger.info(f"Job {job_id} started. Active jobs: {len(self.active_jobs)}")

    def register_job_end(self, job_id: str) -> None:
        """Register that a job has ended.

        Args:
            job_id: Job ID
        """
        with self.lock:
            self.active_jobs.discard(job_id)
            logger.info(f"Job {job_id} ended. Active jobs: {len(self.active_jobs)}")

    def register_tool_start(self, tool_id: str, tool_name: str) -> None:
        """Register that a tool has started.

        Args:
            tool_id: Tool run ID
            tool_name: Tool name
        """
        with self.lock:
            self.active_tools.add(tool_id)
            self.tool_counts[tool_name] += 1
            logger.info(f"Tool {tool_name} ({tool_id}) started. Active tools: {len(self.active_tools)}")

    def register_tool_end(self, tool_id: str) -> None:
        """Register that a tool has ended.

        Args:
            tool_id: Tool run ID
        """
        with self.lock:
            self.active_tools.discard(tool_id)
            logger.info(f"Tool {tool_id} ended. Active tools: {len(self.active_tools)}")

    def validate_job(self, target: str, tools: list[str]) -> dict[str, Any]:
        """Validate a job before execution.

        Args:
            target: Target to scan
            tools: List of tools to use

        Returns:
            Validation result with status and messages

        Raises:
            PolicyViolation: If validation fails
        """
        result: dict[str, Any] = {
            "allowed": True,
            "target_allowed": True,
            "tools_allowed": {},
            "warnings": [],
            "errors": [],
        }

        # Check target
        target_allowed, target_reason = self.check_target_allowed(target)
        result["target_allowed"] = target_allowed
        result["target_reason"] = target_reason

        if not target_allowed:
            result["allowed"] = False
            result["errors"].append(f"Target not allowed: {target_reason}")

        # Check tools
        for tool in tools:
            tool_allowed, tool_reason = self.check_tool_allowed(tool)
            result["tools_allowed"][tool] = {
                "allowed": tool_allowed,
                "reason": tool_reason,
            }

            if not tool_allowed:
                result["allowed"] = False
                result["errors"].append(f"Tool '{tool}' not allowed: {tool_reason}")

            # Add warnings for high-risk tools
            policy = self.roe.get_tool_policy(tool)
            if policy.risk_level.value in ["high", "critical"]:
                result["warnings"].append(f"Tool '{tool}' has {policy.risk_level.value} risk level")

        # Check concurrency
        concurrency_ok, concurrency_reason = self.check_concurrency_limits()
        if not concurrency_ok:
            result["allowed"] = False
            result["errors"].append(f"Concurrency limit: {concurrency_reason}")

        if not result["allowed"]:
            raise PolicyViolation("; ".join(result["errors"]))

        return result
