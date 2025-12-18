"""Policy Engine for Rules of Engagement (RoE) and concurrency control."""

from __future__ import annotations

import ipaddress
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

import yaml
from pydantic import BaseModel, Field


class RateLimitPolicy(BaseModel):
    """Rate limiting configuration."""

    requests_per_second: float = Field(default=1.0, ge=0.1, le=100.0)
    burst_size: int = Field(default=5, ge=1, le=100)


class ConcurrencyPolicy(BaseModel):
    """Concurrency control configuration."""

    max_parallel_jobs: int = Field(default=5, ge=1, le=50)
    max_parallel_tools: int = Field(default=3, ge=1, le=20)
    max_parallel_tools_per_job: int = Field(default=2, ge=1, le=10)


class NetworkPolicy(BaseModel):
    """Network access control configuration."""

    allowlist: list[str] = Field(default_factory=list)  # CIDR ranges allowed
    denylist: list[str] = Field(default_factory=list)  # CIDR ranges denied
    require_explicit_approval: bool = Field(default=True)


class ToolPolicy(BaseModel):
    """Tool-specific policies."""

    high_risk_tools: list[str] = Field(
        default_factory=lambda: [
            "metasploit",
            "sqlmap",
            "hydra",
            "medusa",
            "patator",
            "thc-hydra",
        ]
    )
    require_approval_for_high_risk: bool = Field(default=True)
    disabled_tools: list[str] = Field(default_factory=list)


class RulesOfEngagement(BaseModel):
    """Complete Rules of Engagement configuration."""

    rate_limit: RateLimitPolicy = Field(default_factory=RateLimitPolicy)
    concurrency: ConcurrencyPolicy = Field(default_factory=ConcurrencyPolicy)
    network: NetworkPolicy = Field(default_factory=NetworkPolicy)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    audit_all_actions: bool = Field(default=True)
    require_legal_consent: bool = Field(default=True)


@dataclass
class RateLimitState:
    """State for rate limiting using token bucket algorithm."""

    tokens: float
    last_update: float


class PolicyEngine:
    """Engine for enforcing Rules of Engagement and concurrency policies."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize the policy engine.

        Args:
            config_path: Optional path to RoE configuration file (YAML)
        """
        self._lock = Lock()
        self._active_jobs: set[str] = set()
        self._active_tools: set[str] = set()
        self._rate_limit_state: dict[str, RateLimitState] = {}

        # Load configuration
        if config_path:
            self.config = self._load_config(config_path)
        else:
            # Use default configuration
            self.config = RulesOfEngagement()

    def _load_config(self, config_path: str | Path) -> RulesOfEngagement:
        """Load RoE configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return RulesOfEngagement(**data)

    def can_start_job(self, job_id: str) -> tuple[bool, str]:
        """Check if a new job can be started.

        Args:
            job_id: Unique job identifier

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            if job_id in self._active_jobs:
                return False, "Job is already running"

            if len(self._active_jobs) >= self.config.concurrency.max_parallel_jobs:
                return False, f"Maximum parallel jobs limit reached ({self.config.concurrency.max_parallel_jobs})"

            return True, "OK"

    def start_job(self, job_id: str) -> None:
        """Register a job as started."""
        with self._lock:
            self._active_jobs.add(job_id)

    def finish_job(self, job_id: str) -> None:
        """Register a job as finished."""
        with self._lock:
            self._active_jobs.discard(job_id)

    def can_start_tool(self, tool_name: str, job_id: str | None = None) -> tuple[bool, str]:
        """Check if a tool can be started.

        Args:
            tool_name: Name of the tool
            job_id: Optional job ID for per-job limits

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            # Check if tool is disabled
            if tool_name in self.config.tools.disabled_tools:
                return False, f"Tool '{tool_name}' is disabled by policy"

            # Check if tool is high-risk and requires approval
            if (
                self.config.tools.require_approval_for_high_risk
                and tool_name in self.config.tools.high_risk_tools
            ):
                # In production, this would check for explicit approval flag
                approval_env = os.environ.get(f"NETHICAL_APPROVE_{tool_name.upper()}", "false")
                if approval_env.lower() != "true":
                    return False, f"High-risk tool '{tool_name}' requires explicit approval"

            # Check global tool concurrency
            active_tool_count = len([t for t in self._active_tools])
            if active_tool_count >= self.config.concurrency.max_parallel_tools:
                return False, f"Maximum parallel tools limit reached ({self.config.concurrency.max_parallel_tools})"

            # Check per-job tool concurrency if job_id provided
            if job_id:
                job_tool_count = len([t for t in self._active_tools if t.startswith(f"{job_id}:")])
                if job_tool_count >= self.config.concurrency.max_parallel_tools_per_job:
                    return (
                        False,
                        f"Maximum tools per job limit reached ({self.config.concurrency.max_parallel_tools_per_job})",
                    )

            return True, "OK"

    def start_tool(self, tool_name: str, job_id: str | None = None) -> None:
        """Register a tool as started."""
        with self._lock:
            key = f"{job_id}:{tool_name}" if job_id else tool_name
            self._active_tools.add(key)

    def finish_tool(self, tool_name: str, job_id: str | None = None) -> None:
        """Register a tool as finished."""
        with self._lock:
            key = f"{job_id}:{tool_name}" if job_id else tool_name
            self._active_tools.discard(key)

    def is_target_allowed(self, target: str) -> tuple[bool, str]:
        """Check if a target is allowed by network policy.

        Args:
            target: Target IP, domain, or CIDR

        Returns:
            Tuple of (allowed, reason)
        """
        # If no allowlist is configured and require_explicit_approval is False, allow all
        if not self.config.network.allowlist and not self.config.network.require_explicit_approval:
            return self._check_denylist(target)

        # If allowlist is configured, target must be in allowlist
        if self.config.network.allowlist:
            try:
                target_ip = ipaddress.ip_address(target)
                for allowed_cidr in self.config.network.allowlist:
                    network = ipaddress.ip_network(allowed_cidr, strict=False)
                    if target_ip in network:
                        return self._check_denylist(target)
                return False, f"Target {target} is not in allowlist"
            except ValueError:
                # Not an IP address, check if domain matches
                if target in self.config.network.allowlist:
                    return self._check_denylist(target)
                return False, f"Target {target} is not in allowlist"

        return False, "Target not explicitly allowed by policy"

    def _check_denylist(self, target: str) -> tuple[bool, str]:
        """Check if target is in denylist."""
        if not self.config.network.denylist:
            return True, "OK"

        try:
            target_ip = ipaddress.ip_address(target)
            for denied_cidr in self.config.network.denylist:
                network = ipaddress.ip_network(denied_cidr, strict=False)
                if target_ip in network:
                    return False, f"Target {target} is in denylist"
        except ValueError:
            # Not an IP address, check if domain matches
            if target in self.config.network.denylist:
                return False, f"Target {target} is in denylist"

        return True, "OK"

    def check_rate_limit(self, resource_id: str = "global") -> tuple[bool, str]:
        """Check if rate limit allows the action using token bucket algorithm.

        Args:
            resource_id: Resource identifier (default: "global")

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            # Initialize state with full bucket if not exists
            if resource_id not in self._rate_limit_state:
                self._rate_limit_state[resource_id] = RateLimitState(
                    tokens=float(self.config.rate_limit.burst_size),
                    last_update=time.time()
                )
            
            state = self._rate_limit_state[resource_id]
            now = time.time()
            elapsed = now - state.last_update

            # Add tokens based on elapsed time
            tokens_to_add = elapsed * self.config.rate_limit.requests_per_second
            state.tokens = min(state.tokens + tokens_to_add, self.config.rate_limit.burst_size)
            state.last_update = now

            # Check if we have tokens available
            if state.tokens >= 1.0:
                state.tokens -= 1.0
                return True, "OK"
            else:
                wait_time = (1.0 - state.tokens) / self.config.rate_limit.requests_per_second
                return False, f"Rate limit exceeded. Wait {wait_time:.2f} seconds"

    def get_stats(self) -> dict[str, Any]:
        """Get current policy engine statistics."""
        with self._lock:
            return {
                "active_jobs": len(self._active_jobs),
                "active_tools": len(self._active_tools),
                "max_parallel_jobs": self.config.concurrency.max_parallel_jobs,
                "max_parallel_tools": self.config.concurrency.max_parallel_tools,
                "rate_limit_rps": self.config.rate_limit.requests_per_second,
            }


# Global policy engine instance
_policy_engine: PolicyEngine | None = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the global policy engine instance."""
    global _policy_engine
    if _policy_engine is None:
        config_path = os.environ.get("NETHICAL_POLICY_CONFIG")
        _policy_engine = PolicyEngine(config_path=config_path)
    return _policy_engine
