"""Evidence model for tracking provenance and auditability."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Evidence collected during reconnaissance operations.

    Provides provenance tracking and auditability for all collected data.
    Each piece of evidence is linked to its source (tool run) and includes
    cryptographic hashes for integrity verification.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    run_id: UUID = Field(..., description="Reference to the tool run that produced this evidence")
    job_id: UUID = Field(..., description="Reference to parent scan job")
    
    # Evidence content
    content_type: str = Field(..., description="Type of evidence (e.g., 'nmap_xml', 'raw_output', 'screenshot')")
    file_path: str = Field(..., description="Path to the evidence file")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_hash: str = Field(..., description="SHA256 hash of the file for integrity")
    
    # Provenance
    tool_name: str = Field(..., description="Tool that generated this evidence")
    tool_version: Optional[str] = Field(None, description="Version of the tool")
    command_line: str = Field(..., description="Exact command that produced this evidence")
    
    # Timestamps (all UTC)
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When evidence was collected")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When evidence record was created")
    
    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    description: Optional[str] = Field(None, description="Human-readable description")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    # Chain of custody
    collected_by: Optional[str] = Field(None, description="Operator who collected the evidence")
    verified: bool = Field(default=False, description="Whether hash has been verified")
    
    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "run_id": "123e4567-e89b-12d3-a456-426614174000",
                "job_id": "987e6543-e21b-12d3-a456-426614174000",
                "content_type": "nmap_xml",
                "file_path": "/evidence/scan_20231216_120000.xml",
                "file_size": 45678,
                "file_hash": "a1b2c3d4e5f6...",
                "tool_name": "nmap",
                "tool_version": "7.94",
                "command_line": "nmap -sV -oX output.xml example.com",
                "tags": ["network-scan", "port-discovery"],
            }
        }
