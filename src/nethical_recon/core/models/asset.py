"""Asset model for discovered infrastructure and services."""

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
    SUBDOMAIN = "subdomain"
    EMAIL = "email"
    CERTIFICATE = "certificate"


class Asset(BaseModel):
    """Discovered asset during reconnaissance.

    Represents infrastructure elements discovered during scanning,
    such as hosts, services, URLs, etc.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    target_id: UUID = Field(..., description="Reference to the parent target")
    job_id: Optional[UUID] = Field(None, description="Job that discovered this asset")
    
    # Asset identification
    asset_type: AssetType = Field(..., description="Type of asset")
    value: str = Field(..., description="Asset value (IP, domain, URL, etc.)")
    
    # Host information (for HOST type)
    ip_address: Optional[str] = Field(None, description="IP address")
    hostname: Optional[str] = Field(None, description="Hostname")
    
    # Service information (for SERVICE type)
    port: Optional[int] = Field(None, description="Port number")
    protocol: Optional[str] = Field(None, description="Protocol (tcp/udp)")
    service_name: Optional[str] = Field(None, description="Service name")
    service_version: Optional[str] = Field(None, description="Service version")
    
    # Additional details
    status: str = Field(default="active", description="Asset status (active, inactive, unknown)")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    # Timestamps
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="First discovery time (UTC)")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last seen time (UTC)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation time (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time (UTC)")
    
    # Metadata
    metadata: dict = Field(default_factory=dict, description="Additional asset metadata")
    
    # Relationships
    parent_asset_id: Optional[UUID] = Field(None, description="Parent asset (e.g., host for a service)")
    
    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "target_id": "123e4567-e89b-12d3-a456-426614174000",
                "asset_type": "service",
                "value": "192.168.1.100:22",
                "ip_address": "192.168.1.100",
                "port": 22,
                "protocol": "tcp",
                "service_name": "ssh",
                "service_version": "OpenSSH 8.2",
                "status": "active",
                "tags": ["ssh", "remote-access"],
            }
        }
