"""Tests for core domain models."""

from __future__ import annotations

import pytest
from uuid import UUID

from nethical_recon.core.models import (
    Asset,
    AssetType,
    Evidence,
    Finding,
    IOC,
    IOCType,
    JobStatus,
    ScanJob,
    Severity,
    Target,
    TargetScope,
    TargetType,
    ToolRun,
    ToolStatus,
)


class TestTarget:
    """Tests for Target model."""

    def test_create_target(self):
        """Test creating a target."""
        target = Target(
            value="example.com",
            target_type=TargetType.DOMAIN,
            scope=TargetScope.IN_SCOPE,
            description="Test target",
            tags=["test", "example"],
        )

        assert target.value == "example.com"
        assert target.target_type == TargetType.DOMAIN
        assert target.scope == TargetScope.IN_SCOPE
        assert isinstance(target.id, UUID)
        assert "test" in target.tags

    def test_target_defaults(self):
        """Test target default values."""
        target = Target(value="192.168.1.1", target_type=TargetType.IP)

        assert target.scope == TargetScope.REQUIRES_APPROVAL
        assert target.tags == []
        assert target.description is None


class TestScanJob:
    """Tests for ScanJob model."""

    def test_create_scan_job(self):
        """Test creating a scan job."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)
        job = ScanJob(
            target_id=target.id,
            name="Test Scan",
            description="Testing scan job",
            tools=["nmap", "nikto"],
        )

        assert job.name == "Test Scan"
        assert job.target_id == target.id
        assert job.status == JobStatus.PENDING
        assert "nmap" in job.tools
        assert job.total_runs == 0

    def test_job_status_enum(self):
        """Test job status values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"


class TestToolRun:
    """Tests for ToolRun model."""

    def test_create_tool_run(self):
        """Test creating a tool run."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)
        job = ScanJob(target_id=target.id, name="Test")

        run = ToolRun(
            job_id=job.id,
            tool_name="nmap",
            tool_version="7.94",
            command_line="nmap -sV example.com",
        )

        assert run.tool_name == "nmap"
        assert run.tool_version == "7.94"
        assert run.status == ToolStatus.PENDING
        assert run.findings_count == 0


class TestEvidence:
    """Tests for Evidence model."""

    def test_create_evidence(self):
        """Test creating evidence."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)
        job = ScanJob(target_id=target.id, name="Test")
        run = ToolRun(job_id=job.id, tool_name="nmap", command_line="nmap example.com")

        evidence = Evidence(
            run_id=run.id,
            job_id=job.id,
            content_type="nmap_xml",
            file_path="/tmp/scan.xml",
            file_size=1024,
            file_hash="abc123",
            tool_name="nmap",
            command_line="nmap example.com",
        )

        assert evidence.run_id == run.id
        assert evidence.content_type == "nmap_xml"
        assert evidence.file_hash == "abc123"
        assert evidence.verified is False


class TestFinding:
    """Tests for Finding model."""

    def test_create_finding(self):
        """Test creating a finding."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)
        job = ScanJob(target_id=target.id, name="Test")
        run = ToolRun(job_id=job.id, tool_name="nmap", command_line="nmap example.com")

        finding = Finding(
            run_id=run.id,
            job_id=job.id,
            target_id=target.id,
            title="Open SSH Port",
            description="SSH service detected",
            severity=Severity.INFO,
            confidence=0.95,
            category="exposure",
            tool_name="nmap",
        )

        assert finding.title == "Open SSH Port"
        assert finding.severity == Severity.INFO
        assert finding.confidence == 0.95
        assert finding.false_positive is False

    def test_severity_enum(self):
        """Test severity values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"


class TestAsset:
    """Tests for Asset model."""

    def test_create_host_asset(self):
        """Test creating a host asset."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)

        asset = Asset(
            target_id=target.id,
            asset_type=AssetType.HOST,
            value="192.168.1.1",
            ip_address="192.168.1.1",
            hostname="web-server.example.com",
        )

        assert asset.asset_type == AssetType.HOST
        assert asset.ip_address == "192.168.1.1"
        assert asset.status == "active"

    def test_create_service_asset(self):
        """Test creating a service asset."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)

        asset = Asset(
            target_id=target.id,
            asset_type=AssetType.SERVICE,
            value="192.168.1.1:22",
            ip_address="192.168.1.1",
            port=22,
            protocol="tcp",
            service_name="ssh",
            service_version="OpenSSH 8.2",
        )

        assert asset.asset_type == AssetType.SERVICE
        assert asset.port == 22
        assert asset.service_name == "ssh"


class TestIOC:
    """Tests for IOC model."""

    def test_create_ioc(self):
        """Test creating an IOC."""
        ioc = IOC(
            ioc_type=IOCType.IP,
            value="192.0.2.1",
            description="Suspicious IP",
            confidence=0.8,
            severity="high",
            source="network_scan",
        )

        assert ioc.ioc_type == IOCType.IP
        assert ioc.value == "192.0.2.1"
        assert ioc.confidence == 0.8
        assert ioc.active is True
        assert ioc.false_positive is False
