"""Policy engine for Rules of Engagement (RoE) enforcement."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RoEConfig:
    """Rules of Engagement configuration."""

    # Rate limiting
    max_requests_per_second: float = 10.0
    max_concurrent_tools: int = 5
    max_concurrent_jobs: int = 10

    # Network restrictions
    allowed_networks: list[str] = field(default_factory=list)  # CIDR ranges
    denied_networks: list[str] = field(default_factory=list)  # CIDR ranges

    # Tool restrictions
    high_risk_tools: list[str] = field(
        default_factory=lambda: [
            "metasploit",
            "sqlmap",
            "hydra",
            "john",
            "hashcat",
        ]
    )
    allowed_tools: list[str] = field(
        default_factory=lambda: [
            "nmap",
            "nikto",
            "dirb",
            "sublist3r",
            "whatweb",
            "dnsenum",
            "theHarvester",
        ]
    )
    require_explicit_auth_for_high_risk: bool = True

    # Scan limits
    max_scan_duration_seconds: int = 3600  # 1 hour
    max_ports_to_scan: int = 1000
    max_threads: int = 10

    # Logging and audit
    log_all_commands: bool = True
    require_justification: bool = False

    @classmethod
    def from_env(cls) -> RoEConfig:
        """Load configuration from environment variables."""
        return cls(
            max_requests_per_second=float(os.getenv("ROE_MAX_REQUESTS_PER_SEC", "10.0")),
            max_concurrent_tools=int(os.getenv("ROE_MAX_CONCURRENT_TOOLS", "5")),
            max_concurrent_jobs=int(os.getenv("ROE_MAX_CONCURRENT_JOBS", "10")),
            max_scan_duration_seconds=int(os.getenv("ROE_MAX_SCAN_DURATION", "3600")),
            max_ports_to_scan=int(os.getenv("ROE_MAX_PORTS", "1000")),
            max_threads=int(os.getenv("ROE_MAX_THREADS", "10")),
            require_explicit_auth_for_high_risk=os.getenv("ROE_REQUIRE_EXPLICIT_AUTH", "true").lower() == "true",
        )


class PolicyEngine:
    """
    Policy engine for enforcing Rules of Engagement (RoE).

    Ensures all scans comply with defined security and operational policies.
    """

    def __init__(self, config: RoEConfig | None = None):
        """
        Initialize policy engine.

        Args:
            config: RoE configuration, defaults to environment-based config
        """
        self.config = config or RoEConfig.from_env()
        self._active_tools = 0
        self._active_jobs = 0
        logger.info("Policy engine initialized with RoE configuration")

    def can_run_tool(self, tool_name: str, explicit_auth: bool = False) -> bool:
        """
        Check if a tool can be run according to policy.

        Args:
            tool_name: Name of the tool
            explicit_auth: Whether explicit authorization was provided

        Returns:
            True if tool can be run, False otherwise
        """
        # Check if tool is in allowed list
        if self.config.allowed_tools and tool_name not in self.config.allowed_tools:
            logger.warning(f"Tool {tool_name} not in allowed tools list")
            return False

        # Check if tool is high-risk
        if tool_name in self.config.high_risk_tools:
            if self.config.require_explicit_auth_for_high_risk and not explicit_auth:
                logger.warning(f"High-risk tool {tool_name} requires explicit authorization")
                return False

        # Check concurrency limits
        if self._active_tools >= self.config.max_concurrent_tools:
            logger.warning(f"Max concurrent tools limit reached ({self.config.max_concurrent_tools})")
            return False

        logger.info(f"Tool {tool_name} authorized to run")
        return True

    def can_start_job(self) -> bool:
        """
        Check if a new job can be started according to policy.

        Returns:
            True if job can be started, False otherwise
        """
        if self._active_jobs >= self.config.max_concurrent_jobs:
            logger.warning(f"Max concurrent jobs limit reached ({self.config.max_concurrent_jobs})")
            return False

        logger.info("Job authorized to start")
        return True

    def is_network_allowed(self, target: str) -> bool:
        """
        Check if a target network is allowed by policy.

        Args:
            target: Target IP, CIDR, or domain

        Returns:
            True if network is allowed, False otherwise
        """
        import ipaddress

        # If no allowed networks specified, allow all except denied
        if not self.config.allowed_networks:
            # Check denied networks
            if self.config.denied_networks:
                try:
                    target_ip = ipaddress.ip_address(target)
                    for denied_net in self.config.denied_networks:
                        if target_ip in ipaddress.ip_network(denied_net, strict=False):
                            logger.warning(f"Target {target} is in denied network {denied_net}")
                            return False
                except ValueError:
                    # Not an IP address, assume allowed (domain name)
                    pass
            return True

        # Check if target is in allowed networks
        try:
            target_ip = ipaddress.ip_address(target)
            for allowed_net in self.config.allowed_networks:
                if target_ip in ipaddress.ip_network(allowed_net, strict=False):
                    logger.info(f"Target {target} is in allowed network {allowed_net}")
                    return True
            logger.warning(f"Target {target} is not in any allowed network")
            return False
        except ValueError:
            # Not an IP address, assume allowed (domain name)
            logger.info(f"Target {target} is a domain name, allowing")
            return True

    def validate_scan_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate scan configuration against policy.

        Args:
            config: Scan configuration dictionary

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check port count
        if "ports" in config:
            port_count = len(config["ports"]) if isinstance(config["ports"], list) else 0
            if port_count > self.config.max_ports_to_scan:
                errors.append(
                    f"Port count {port_count} exceeds maximum {self.config.max_ports_to_scan}"
                )

        # Check thread count
        if "threads" in config:
            threads = config["threads"]
            if threads > self.config.max_threads:
                errors.append(f"Thread count {threads} exceeds maximum {self.config.max_threads}")

        # Check timeout
        if "timeout" in config:
            timeout = config["timeout"]
            if timeout > self.config.max_scan_duration_seconds:
                errors.append(
                    f"Timeout {timeout}s exceeds maximum {self.config.max_scan_duration_seconds}s"
                )

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Scan configuration validated successfully")
        else:
            logger.warning(f"Scan configuration validation failed: {errors}")

        return is_valid, errors

    def increment_active_tools(self) -> None:
        """Increment the active tools counter."""
        self._active_tools += 1
        logger.debug(f"Active tools: {self._active_tools}")

    def decrement_active_tools(self) -> None:
        """Decrement the active tools counter."""
        self._active_tools = max(0, self._active_tools - 1)
        logger.debug(f"Active tools: {self._active_tools}")

    def increment_active_jobs(self) -> None:
        """Increment the active jobs counter."""
        self._active_jobs += 1
        logger.debug(f"Active jobs: {self._active_jobs}")

    def decrement_active_jobs(self) -> None:
        """Decrement the active jobs counter."""
        self._active_jobs = max(0, self._active_jobs - 1)
        logger.debug(f"Active jobs: {self._active_jobs}")

    def get_status(self) -> dict[str, Any]:
        """
        Get current policy engine status.

        Returns:
            Dictionary with status information
        """
        return {
            "active_tools": self._active_tools,
            "max_concurrent_tools": self.config.max_concurrent_tools,
            "active_jobs": self._active_jobs,
            "max_concurrent_jobs": self.config.max_concurrent_jobs,
            "max_requests_per_second": self.config.max_requests_per_second,
        }
