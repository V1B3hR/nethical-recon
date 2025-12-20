"""Policy models for Rules of Engagement."""

from __future__ import annotations

import ipaddress
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    """Risk level for tools and operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitPolicy(BaseModel):
    """Rate limiting policy for requests."""

    requests_per_second: float = Field(default=1.0, ge=0.1, le=1000.0, description="Max requests per second")
    burst_size: int = Field(default=5, ge=1, le=100, description="Burst size for rate limiter")
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")


class ConcurrencyPolicy(BaseModel):
    """Concurrency control policy."""

    max_parallel_tools: int = Field(default=3, ge=1, le=50, description="Max parallel tool executions")
    max_parallel_jobs: int = Field(default=5, ge=1, le=100, description="Max parallel scan jobs")
    enabled: bool = Field(default=True, description="Whether concurrency limits are enabled")


class NetworkPolicy(BaseModel):
    """Network targeting policy."""

    allowed_networks: list[str] = Field(
        default_factory=list, description="CIDR networks that are allowed to be scanned"
    )
    denied_networks: list[str] = Field(
        default_factory=list, description="CIDR networks that are explicitly denied"
    )
    require_explicit_approval: bool = Field(
        default=False, description="Whether all targets require explicit approval"
    )

    @field_validator("allowed_networks", "denied_networks")
    @classmethod
    def validate_networks(cls, v: list[str]) -> list[str]:
        """Validate that all network entries are valid CIDR notation."""
        validated = []
        for network in v:
            try:
                # This will raise ValueError if invalid
                ipaddress.ip_network(network, strict=False)
                validated.append(network)
            except ValueError as e:
                raise ValueError(f"Invalid network CIDR '{network}': {e}") from e
        return validated


class ToolPolicy(BaseModel):
    """Policy for individual tools."""

    tool_name: str = Field(..., description="Name of the tool")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Risk level of the tool")
    requires_approval: bool = Field(default=False, description="Whether tool requires explicit approval")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    max_duration_seconds: int | None = Field(default=None, ge=1, description="Max execution time in seconds")
    custom_args: dict[str, Any] = Field(default_factory=dict, description="Custom tool-specific arguments")


class RulesOfEngagement(BaseModel):
    """Complete Rules of Engagement configuration."""

    name: str = Field(default="default", description="Name of the RoE profile")
    description: str | None = Field(default=None, description="Description of this RoE profile")

    # Rate limiting
    rate_limit: RateLimitPolicy = Field(default_factory=RateLimitPolicy)

    # Concurrency
    concurrency: ConcurrencyPolicy = Field(default_factory=ConcurrencyPolicy)

    # Network policies
    network: NetworkPolicy = Field(default_factory=NetworkPolicy)

    # Tool-specific policies
    tool_policies: dict[str, ToolPolicy] = Field(default_factory=dict, description="Tool-specific policies")

    # High-risk tools that require explicit enabling
    high_risk_tools: list[str] = Field(
        default_factory=lambda: ["sqlmap", "metasploit", "hydra", "john"],
        description="Tools considered high-risk",
    )

    # Global flags
    authorized_only: bool = Field(default=True, description="Only scan authorized targets")
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed to run."""
        # Check if it's a high-risk tool without explicit policy
        if tool_name in self.high_risk_tools:
            if tool_name not in self.tool_policies:
                return False
            return self.tool_policies[tool_name].enabled

        # Check if there's a specific policy
        if tool_name in self.tool_policies:
            return self.tool_policies[tool_name].enabled

        # Default: allow
        return True

    def get_tool_policy(self, tool_name: str) -> ToolPolicy:
        """Get policy for a specific tool, or create default."""
        if tool_name in self.tool_policies:
            return self.tool_policies[tool_name]

        # Determine risk level
        risk_level = RiskLevel.HIGH if tool_name in self.high_risk_tools else RiskLevel.MEDIUM

        return ToolPolicy(
            tool_name=tool_name,
            risk_level=risk_level,
            requires_approval=tool_name in self.high_risk_tools,
        )
