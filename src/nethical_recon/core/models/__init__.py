"""Domain models for Nethical Recon.

This module contains Pydantic v2 models representing the core domain:
- Target: scan targets
- ScanJob: orchestration metadata
- ToolRun: tool execution records
- Evidence: output artifacts with provenance
- Finding: normalized security findings
- Asset: discovered infrastructure
- IOC: indicators of compromise
"""

from __future__ import annotations

from .target import Target, TargetType, TargetScope
from .scan_job import ScanJob, JobStatus
from .tool_run import ToolRun, ToolStatus
from .evidence import Evidence, EvidenceType
from .finding import Finding, Severity, Confidence
from .asset import Asset, AssetType
from .ioc import IOC, IOCType

__all__ = [
    # Target
    "Target",
    "TargetType",
    "TargetScope",
    # ScanJob
    "ScanJob",
    "JobStatus",
    # ToolRun
    "ToolRun",
    "ToolStatus",
    # Evidence
    "Evidence",
    "EvidenceType",
    # Finding
    "Finding",
    "Severity",
    "Confidence",
    # Asset
    "Asset",
    "AssetType",
    # IOC
    "IOC",
    "IOCType",
]
