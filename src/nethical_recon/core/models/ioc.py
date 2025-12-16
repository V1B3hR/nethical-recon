"""IOC (Indicator of Compromise) model for threat intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IOCType(str, Enum):
    """Type of Indicator of Compromise."""

    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    EMAIL = "email"
    FILE_HASH = "file_hash"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    CVE = "cve"
    PROCESS = "process"
    REGISTRY = "registry"
    MUTEX = "mutex"


class IOC(BaseModel):
    """Indicator of Compromise for threat intelligence.

    Represents potential indicators of malicious activity or compromise
    discovered during reconnaissance.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    finding_id: Optional[UUID] = Field(None, description="Related finding if applicable")
    job_id: Optional[UUID] = Field(None, description="Job that discovered this IOC")
    
    # IOC details
    ioc_type: IOCType = Field(..., description="Type of IOC")
    value: str = Field(..., description="IOC value")
    
    # Context
    description: Optional[str] = Field(None, description="Description of the IOC")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    severity: str = Field(default="unknown", description="Severity if known")
    
    # Classification
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    categories: list[str] = Field(default_factory=list, description="Threat categories")
    
    # Threat intelligence
    threat_actor: Optional[str] = Field(None, description="Associated threat actor")
    campaign: Optional[str] = Field(None, description="Associated campaign")
    malware_family: Optional[str] = Field(None, description="Associated malware family")
    
    # External references
    references: list[str] = Field(default_factory=list, description="External references and URLs")
    mitre_attack: list[str] = Field(default_factory=list, description="MITRE ATT&CK techniques")
    
    # Source information
    source: str = Field(..., description="Source of the IOC (tool, feed, manual)")
    source_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in source")
    
    # Timestamps
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="First seen time (UTC)")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last seen time (UTC)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation time (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time (UTC)")
    
    # Status
    active: bool = Field(default=True, description="Whether IOC is still active")
    false_positive: bool = Field(default=False, description="Marked as false positive")
    
    # Additional context
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "ioc_type": "ip",
                "value": "192.0.2.1",
                "description": "Suspicious IP address communicating with internal network",
                "confidence": 0.8,
                "severity": "high",
                "tags": ["command-and-control", "suspicious"],
                "categories": ["network", "c2"],
                "source": "network_scan",
                "mitre_attack": ["T1071.001"],
            }
        }
