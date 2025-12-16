"""SQLAlchemy database models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..models import AssetType, IOCType, JobStatus, Severity, TargetScope, TargetType, ToolStatus
from .base import Base


# Helper function for UUID columns that works with both SQLite and PostgreSQL
def uuid_column():
    """Create a UUID column that works with SQLite and PostgreSQL."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TargetModel(Base):
    """Database model for Target."""

    __tablename__ = "targets"

    id: Mapped[UUID] = uuid_column()
    value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    scope: Mapped[TargetScope] = mapped_column(Enum(TargetScope), nullable=False, default=TargetScope.REQUIRES_APPROVAL)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class ScanJobModel(Base):
    """Database model for ScanJob."""

    __tablename__ = "scan_jobs"

    id: Mapped[UUID] = uuid_column()
    target_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)
    tools: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class ToolRunModel(Base):
    """Database model for ToolRun."""

    __tablename__ = "tool_runs"

    id: Mapped[UUID] = uuid_column()
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    command_line: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ToolStatus] = mapped_column(Enum(ToolStatus), nullable=False, default=ToolStatus.PENDING, index=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    stdout_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stderr_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    environment: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EvidenceModel(Base):
    """Database model for Evidence."""

    __tablename__ = "evidence"

    id: Mapped[UUID] = uuid_column()
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    command_line: Mapped[str] = mapped_column(Text, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    collected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FindingModel(Base):
    """Database model for Finding."""

    __tablename__ = "findings"

    id: Mapped[UUID] = uuid_column()
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    target_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    affected_asset: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    affected_component: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    evidence_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    references: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    cvss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exploitability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_finding_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    false_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AssetModel(Base):
    """Database model for Asset."""

    __tablename__ = "assets"

    id: Mapped[UUID] = uuid_column()
    target_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    job_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)

    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    service_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    parent_asset_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class IOCModel(Base):
    """Database model for IOC."""

    __tablename__ = "iocs"

    id: Mapped[UUID] = uuid_column()
    finding_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    job_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)

    ioc_type: Mapped[IOCType] = mapped_column(Enum(IOCType), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")

    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    categories: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    threat_actor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    campaign: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    malware_family: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    references: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    mitre_attack: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    false_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
