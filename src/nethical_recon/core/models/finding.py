"""Finding model for normalized security findings."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level for findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    """Normalized security finding from any tool.

    All tool outputs are normalized into this unified format to enable
    consistent analysis, correlation, and reporting.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    run_id: UUID = Field(..., description="Reference to tool run that discovered this finding")
    job_id: UUID = Field(..., description="Reference to parent scan job")
    target_id: UUID = Field(..., description="Reference to the scanned target")
    
    # Finding details
    title: str = Field(..., description="Short, descriptive title")
    description: str = Field(..., description="Detailed description of the finding")
    severity: Severity = Field(..., description="Severity level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    
    # Classification
    category: str = Field(..., description="Category (e.g., 'vulnerability', 'misconfiguration', 'exposure')")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    
    # Technical details
    affected_asset: Optional[str] = Field(None, description="Affected asset (IP, domain, URL)")
    affected_component: Optional[str] = Field(None, description="Specific component affected")
    port: Optional[int] = Field(None, description="Network port if applicable")
    protocol: Optional[str] = Field(None, description="Protocol if applicable")
    
    # Evidence and references
    evidence_ids: list[UUID] = Field(default_factory=list, description="References to evidence records")
    references: list[str] = Field(default_factory=list, description="External references (CVE, CWE, URLs)")
    
    # Risk assessment
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="CVSS score if applicable")
    exploitability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Exploitability score")
    impact: Optional[float] = Field(None, ge=0.0, le=1.0, description="Impact score")
    
    # Remediation
    remediation: Optional[str] = Field(None, description="Remediation guidance")
    
    # Tool info
    tool_name: str = Field(..., description="Tool that discovered this finding")
    tool_finding_id: Optional[str] = Field(None, description="Original finding ID from the tool")
    
    # Timestamps
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="When finding was discovered (UTC)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When record was created (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update (UTC)")
    
    # Status
    false_positive: bool = Field(default=False, description="Marked as false positive")
    verified: bool = Field(default=False, description="Manually verified")
    
    # Additional context
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "run_id": "123e4567-e89b-12d3-a456-426614174000",
                "job_id": "987e6543-e21b-12d3-a456-426614174000",
                "target_id": "456e7890-e12b-12d3-a456-426614174000",
                "title": "Open SSH Port",
                "description": "SSH service detected on port 22",
                "severity": "info",
                "confidence": 0.95,
                "category": "exposure",
                "tags": ["network", "ssh"],
                "affected_asset": "192.168.1.100",
                "port": 22,
                "protocol": "tcp",
                "tool_name": "nmap",
            }
        }
