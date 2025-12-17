"""Target model - represents scan targets."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
import ipaddress


class TargetType(str, Enum):
    """Type of target."""

    DOMAIN = "domain"
    IP = "ip"
    CIDR = "cidr"
    URL = "url"


class TargetScope(str, Enum):
    """Scope of the target for engagement."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


class Target(BaseModel):
    """
    Represents a target for reconnaissance.

    A target can be a domain, IP address, CIDR range, or URL.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique target identifier")
    value: str = Field(..., description="Target value (domain, IP, CIDR, or URL)")
    type: TargetType = Field(..., description="Type of target")
    scope: TargetScope = Field(default=TargetScope.UNKNOWN, description="Engagement scope")
    description: Optional[str] = Field(None, description="Target description")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp (UTC)")

    @field_validator("value")
    @classmethod
    def validate_target_value(cls, v: str, info) -> str:
        """Validate target value based on type."""
        target_type = info.data.get("type")

        if target_type == TargetType.IP:
            try:
                ipaddress.ip_address(v)
            except ValueError as e:
                raise ValueError(f"Invalid IP address: {v}") from e

        elif target_type == TargetType.CIDR:
            try:
                ipaddress.ip_network(v, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid CIDR notation: {v}") from e

        elif target_type == TargetType.URL:
            if not v.startswith(("http://", "https://")):
                raise ValueError(f"URL must start with http:// or https://: {v}")

        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "value": "example.com",
                "type": "domain",
                "scope": "in_scope",
                "description": "Primary target domain",
                "tags": ["web", "production"],
            }
        }
