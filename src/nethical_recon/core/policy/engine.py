"""Policy engine for Rules of Engagement enforcement."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .. models import Target

logger = logging.getLogger(__name__)


class RulesOfEngagement:
    """
    Rules of Engagement configuration. 
    
    Defines what is allowed/forbidden during security assessments.
    """

    def __init__(
        self,
        allowed_ports: list[int] | None = None,
        forbidden_ports: list[int] | None = None,
        allowed_networks: list[str] | None = None,
        forbidden_networks:  list[str] | None = None,
        rate_limit_requests_per_second: int = 10,
        max_parallel_scans: int = 3,
        allowed_tools: list[str] | None = None,
        forbidden_tools:  list[str] | None = None,
        time_windows: list[dict[str, Any]] | None = None,
    ):
        """Initialize Rules of Engagement."""
        self.allowed_ports = allowed_ports or []
        self.forbidden_ports = forbidden_ports or [22, 23, 3389]  # SSH, Telnet, RDP by default
        self.allowed_networks = allowed_networks or []
        self.forbidden_networks = forbidden_networks or []
        self.rate_limit_requests_per_second = rate_limit_requests_per_second
        self.max_parallel_scans = max_parallel_scans
        self.allowed_tools = allowed_tools or []
        self.forbidden_tools = forbidden_tools or []
        self.time_windows = time_windows or []


class PolicyViolation(Exception):
    """Exception raised when a policy is violated."""

    pass


class PolicyEngine:
    """
    Engine for enforcing Rules of Engagement.
    
    Validates that scan requests comply with defined policies.
    """

    def __init__(self, roe: RulesOfEngagement | None = None):
        """Initialize policy engine."""
        self.roe = roe or RulesOfEngagement()
        self.logger = logging.getLogger(__name__)

    def validate_scan_request(
        self,
        target: Target,
        tool:  str,
        ports: list[int] | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        Validate a scan request against RoE. 
        
        Args:
            target: Target to scan
            tool: Tool to use
            ports: Ports to scan (if applicable)
            **kwargs: Additional parameters
            
        Returns:
            True if allowed
            
        Raises:
            PolicyViolation: If request violates policy
        """
        # Check tool restrictions
        if self.roe.forbidden_tools and tool in self. roe.forbidden_tools:
            raise PolicyViolation(f"Tool '{tool}' is forbidden by policy")

        if self.roe.allowed_tools and tool not in self.roe.allowed_tools:
            raise PolicyViolation(f"Tool '{tool}' is not in allowed tools list")

        # Check port restrictions
        if ports:
            for port in ports:
                if self.roe.forbidden_ports and port in self.roe.forbidden_ports:
                    raise PolicyViolation(f"Port {port} is forbidden by policy")

                if self.roe.allowed_ports and port not in self. roe.allowed_ports:
                    raise PolicyViolation(f"Port {port} is not in allowed ports list")

        # Check time windows
        if self.roe.time_windows:
            current_time = datetime.now()
            allowed = False
            for window in self.roe.time_windows:
                start = datetime.fromisoformat(window["start"])
                end = datetime.fromisoformat(window["end"])
                if start <= current_time <= end: 
                    allowed = True
                    break

            if not allowed:
                raise PolicyViolation("Current time is outside allowed scanning windows")

        return True

    @classmethod
    def from_config(cls, config_path: str | Path) -> PolicyEngine:
        """
        Load policy engine from configuration file.
        
        Args:
            config_path: Path to config file (JSON or YAML)
            
        Returns:
            Configured PolicyEngine instance
        """
        config_path = Path(config_path)

        with open(config_path) as f:
            if config_path.suffix in [". yaml", ".yml"]:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError as e:
                    raise ImportError("PyYAML required for YAML configuration files") from e
            else: 
                data = json.load(f)

        roe = RulesOfEngagement(**data. get("rules_of_engagement", {}))
        return cls(roe=roe)
