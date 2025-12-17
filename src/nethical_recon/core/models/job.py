"""ScanJob model for orchestrating reconnaissance scans."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a scan job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanJob(BaseModel):
    """Scan job that orchestrates multiple tool runs against targets.

    Represents a complete reconnaissance operation that may include
    multiple tools running against one or more targets.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the job")
    target_id: UUID = Field(..., description="Reference to the target being scanned")
    name: str = Field(..., description="Human-readable name for this job")
    description: Optional[str] = Field(None, description="Detailed description of the job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    tools: list[str] = Field(default_factory=list, description="List of tools to run in this job")
    config: dict = Field(default_factory=dict, description="Job-specific configuration")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time (UTC)")
    started_at: Optional[datetime] = Field(None, description="Job start time (UTC)")
    completed_at: Optional[datetime] = Field(None, description="Job completion time (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time (UTC)")

    # Results metadata
    total_runs: int = Field(default=0, description="Total number of tool runs")
    successful_runs: int = Field(default=0, description="Number of successful tool runs")
    failed_runs: int = Field(default=0, description="Number of failed tool runs")
    findings_count: int = Field(default=0, description="Total findings discovered")

    # Operator info
    operator: Optional[str] = Field(None, description="User or system that initiated the job")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "target_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Full recon scan",
                "description": "Complete reconnaissance of target domain",
                "status": "pending",
                "tools": ["nmap", "nikto", "sublist3r"],
                "operator": "security_team",
            }
        }
