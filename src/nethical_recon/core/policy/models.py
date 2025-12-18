"""Policy models for Rules of Engagement (RoE)."""

from __future__ import annotations

import ipaddress
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    """Risk level of operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitPolicy(BaseModel):
    """Rate limiting policy for network operations."""

    enabled: bool = Field(default=True, description="Enable rate limiting")
    requests_per_second: float = Field(default=10.0, description="Max requests per second", gt=0)
    burst_size: int = Field(default=20, description="Max burst size", gt=0)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "enabled": True,
                "requests_per_second": 10.0,
                "burst_size": 20,
            }
        }


class ConcurrencyPolicy(BaseModel):
    """Concurrency control policy."""

    enabled: bool = Field(default=True, description="Enable concurrency limits")
    max_parallel_scans: int = Field(default=5, description="Max parallel scan jobs", gt=0)
    max_parallel_tools: int = Field(default=3, description="Max parallel tools per job", gt=0)
    max_workers: int = Field(default=4, description="Max worker processes", gt=0)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "enabled": True,
                "max_parallel_scans": 5,
                "max_parallel_tools": 3,
                "max_workers": 4,
            }
        }


class NetworkPolicy(BaseModel):
    """Network access policy."""

    enabled: bool = Field(default=True, description="Enable network restrictions")
    allow_networks: list[str] = Field(
        default_factory=list,
        description="Allowed CIDR networks (empty = allow all)",
    )
    deny_networks: list[str] = Field(
        default_factory=lambda: [
            "10.0.0.0/8",  # Private
            "172.16.0.0/12",  # Private
            "192.168.0.0/16",  # Private
            "127.0.0.0/8",  # Loopback
            "169.254.0.0/16",  # Link-local
        ],
        description="Denied CIDR networks",
    )
    require_explicit_consent: bool = Field(
        default=True,
        description="Require explicit user consent before scanning",
    )

    @field_validator("allow_networks", "deny_networks")
    @classmethod
    def validate_networks(cls, v: list[str]) -> list[str]:
        """Validate network CIDR notation."""
        validated = []
        for network in v:
            try:
                ipaddress.ip_network(network)
                validated.append(network)
            except ValueError as e:
                raise ValueError(f"Invalid CIDR network '{network}': {e}") from e
        return validated

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "enabled": True,
                "allow_networks": ["192.0.2.0/24"],
                "deny_networks": ["10.0.0.0/8"],
                "require_explicit_consent": True,
            }
        }


class ToolPolicy(BaseModel):
    """Tool execution policy."""

    enabled: bool = Field(default=True, description="Enable tool restrictions")
    high_risk_tools: list[str] = Field(
        default_factory=lambda: [
            "metasploit",
            "sqlmap",
            "hydra",
            "john",
            "hashcat",
        ],
        description="High-risk tools requiring explicit approval",
    )
    require_approval_for_high_risk: bool = Field(
        default=True,
        description="Require approval for high-risk tools",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Explicitly allowed tools (empty = all allowed)",
    )
    timeout_seconds: int = Field(
        default=3600,
        description="Default timeout for tool execution (seconds)",
        gt=0,
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "enabled": True,
                "high_risk_tools": ["metasploit", "sqlmap"],
                "require_approval_for_high_risk": True,
                "timeout_seconds": 3600,
            }
        }


class Policy(BaseModel):
    """Complete Rules of Engagement (RoE) policy."""

    name: str = Field(default="default", description="Policy name")
    description: str | None = Field(None, description="Policy description")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Default risk level")
    rate_limit: RateLimitPolicy = Field(default_factory=RateLimitPolicy)
    concurrency: ConcurrencyPolicy = Field(default_factory=ConcurrencyPolicy)
    network: NetworkPolicy = Field(default_factory=NetworkPolicy)
    tool: ToolPolicy = Field(default_factory=ToolPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "production",
                "description": "Production environment policy",
                "risk_level": "low",
                "rate_limit": {"enabled": True, "requests_per_second": 5.0},
                "concurrency": {"max_parallel_scans": 3},
            }
        }


def create_default_policy() -> Policy:
    """Create a safe default policy."""
    return Policy(
        name="default",
        description="Safe default policy for authorized scanning",
        risk_level=RiskLevel.LOW,
    )


def create_aggressive_policy() -> Policy:
    """Create an aggressive policy for authorized penetration testing."""
    return Policy(
        name="aggressive",
        description="Aggressive policy for authorized penetration testing",
        risk_level=RiskLevel.HIGH,
        rate_limit=RateLimitPolicy(
            enabled=True,
            requests_per_second=50.0,
            burst_size=100,
        ),
        concurrency=ConcurrencyPolicy(
            enabled=True,
            max_parallel_scans=10,
            max_parallel_tools=5,
            max_workers=8,
        ),
        network=NetworkPolicy(
            enabled=True,
            allow_networks=[],  # Allow all
            deny_networks=[],  # No denials
            require_explicit_consent=True,
        ),
        tool=ToolPolicy(
            enabled=True,
            require_approval_for_high_risk=True,
            timeout_seconds=7200,
        ),
    )
