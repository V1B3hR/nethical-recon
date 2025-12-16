"""Target model for reconnaissance operations."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TargetType(str, Enum):
    """Type of target."""

    DOMAIN = "domain"
    IP = "ip"
    CIDR = "cidr"
    URL = "url"


class TargetScope(str, Enum):
    """Scope of authorization for target."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    REQUIRES_APPROVAL = "requires_approval"


class Target(BaseModel):
    """Target for security reconnaissance.

    Represents a target system, network, or domain to be scanned.
    Includes scope information for authorization tracking.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the target")
    value: str = Field(..., description="Target value (domain, IP, CIDR, or URL)")
    target_type: TargetType = Field(..., description="Type of target")
    scope: TargetScope = Field(
        default=TargetScope.REQUIRES_APPROVAL, description="Authorization scope for this target"
    )
    description: Optional[str] = Field(None, description="Human-readable description")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp (UTC)")

    @field_validator("value")
    @classmethod
    def validate_target_value(cls, v: str, info) -> str:
        """Validate target value based on type."""
        # Basic validation - more comprehensive validation can be added
        if not v or not v.strip():
            raise ValueError("Target value cannot be empty")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Ensure tags are non-empty strings."""
        return [tag.strip() for tag in v if tag and tag.strip()]

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "value": "example.com",
                "target_type": "domain",
                "scope": "in_scope",
                "description": "Main target domain",
                "tags": ["web", "high-priority"],
            }
        }
