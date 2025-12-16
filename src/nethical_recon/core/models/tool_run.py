"""ToolRun model for tracking individual tool executions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """Status of a tool run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolRun(BaseModel):
    """Individual tool execution within a scan job.

    Tracks the execution of a specific security tool, including
    command line, output, and provenance information.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this tool run")
    job_id: UUID = Field(..., description="Reference to parent scan job")
    tool_name: str = Field(..., description="Name of the tool executed")
    tool_version: Optional[str] = Field(None, description="Version of the tool")
    
    # Execution details
    command_line: str = Field(..., description="Exact command line executed")
    status: ToolStatus = Field(default=ToolStatus.PENDING, description="Current status")
    exit_code: Optional[int] = Field(None, description="Process exit code")
    
    # Output and evidence
    stdout_path: Optional[str] = Field(None, description="Path to stdout output file")
    stderr_path: Optional[str] = Field(None, description="Path to stderr output file")
    output_file: Optional[str] = Field(None, description="Path to tool output file")
    output_hash: Optional[str] = Field(None, description="SHA256 hash of output file")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Run creation time (UTC)")
    started_at: Optional[datetime] = Field(None, description="Run start time (UTC)")
    completed_at: Optional[datetime] = Field(None, description="Run completion time (UTC)")
    duration_seconds: Optional[float] = Field(None, description="Execution duration in seconds")
    
    # Results
    findings_count: int = Field(default=0, description="Number of findings from this run")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Metadata
    environment: dict = Field(default_factory=dict, description="Environment variables and context")
    
    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "tool_name": "nmap",
                "tool_version": "7.94",
                "command_line": "nmap -sV -p- example.com",
                "status": "completed",
                "exit_code": 0,
                "findings_count": 5,
            }
        }
