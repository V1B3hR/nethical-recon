"""Tests for storage layer."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from nethical_recon.core.models import JobStatus, ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import DatabaseManager
from nethical_recon.core.storage.models import ScanJobModel, TargetModel


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db_url = f"sqlite:///{db_path}"
        manager = DatabaseManager(db_url)
        manager.create_tables()

        yield manager

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_create_tables(self, temp_db):
        """Test creating database tables."""
        # Tables should be created without error
        assert temp_db.engine is not None

    def test_insert_target(self, temp_db):
        """Test inserting a target into database."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN, scope=TargetScope.IN_SCOPE)

        with temp_db.get_session() as session:
            db_target = TargetModel(
                id=target.id,
                value=target.value,
                target_type=target.target_type,
                scope=target.scope,
                tags=[],
            )
            session.add(db_target)

        # Verify the target was inserted
        with temp_db.get_session() as session:
            retrieved = session.query(TargetModel).filter_by(id=target.id).first()
            assert retrieved is not None
            assert retrieved.value == "example.com"
            assert retrieved.target_type == TargetType.DOMAIN

    def test_insert_scan_job(self, temp_db):
        """Test inserting a scan job."""
        target = Target(value="example.com", target_type=TargetType.DOMAIN)
        job = ScanJob(target_id=target.id, name="Test Scan", tools=["nmap"])

        with temp_db.get_session() as session:
            # Insert target first
            db_target = TargetModel(
                id=target.id, value=target.value, target_type=target.target_type, scope=target.scope, tags=[]
            )
            session.add(db_target)

            # Insert job
            db_job = ScanJobModel(
                id=job.id,
                target_id=job.target_id,
                name=job.name,
                status=job.status,
                tools=job.tools,
                config={},
            )
            session.add(db_job)

        # Verify the job was inserted
        with temp_db.get_session() as session:
            retrieved = session.query(ScanJobModel).filter_by(id=job.id).first()
            assert retrieved is not None
            assert retrieved.name == "Test Scan"
            assert retrieved.status == JobStatus.PENDING
            assert "nmap" in retrieved.tools
