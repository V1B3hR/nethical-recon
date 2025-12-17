"""Asset model - represents discovered infrastructure assets."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Type of asset."""

    HOST = "host"
    SERVICE = "service"
    URL = "url"
    DOMAIN = "domain"
    EMAIL = "email"


class Asset(BaseModel):
    """
    Represents a discovered asset during reconnaissance.

    Assets are infrastructure elements discovered during scans:
    hosts, services, URLs, domains, email addresses, etc.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique asset identifier")
    job_id: UUID = Field(..., description="Job that discovered this asset")
    type: AssetType = Field(..., description="Type of asset")
    value: str = Field(..., description="Asset value (IP, domain, URL, etc.)")
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Asset description")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp (UTC)")
    last_seen_at: datetime = Field(default_factory=datetime.utcnow, description="Last seen timestamp (UTC)")

    # Asset-specific fields
    ip_address: Optional[str] = Field(None, description="IP address (for HOST type)")
    hostname: Optional[str] = Field(None, description="Hostname")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port number (for SERVICE type)")
    protocol: Optional[str] = Field(None, description="Protocol")
    service_name: Optional[str] = Field(None, description="Service name")
    service_version: Optional[str] = Field(None, description="Service version")
    os_name: Optional[str] = Field(None, description="Operating system name")
    os_version: Optional[str] = Field(None, description="Operating system version")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "service",
                "value": "example.com:443",
                "name": "HTTPS Service",
                "ip_address": "192.0.2.1",
                "hostname": "example.com",
                "port": 443,
                "protocol": "tcp",
                "service_name": "https",
                "service_version": "nginx/1.18.0",
                "tags": ["web", "production"],
            }
        }
