"""Tests for scheduler module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from nethical_recon.scheduler import ScanScheduler


class TestScanScheduler:
    """Tests for scan scheduler."""

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_scheduler_initialization(self, mock_init_db):
        """Test scheduler initialization."""
        scheduler = ScanScheduler()
        assert scheduler.scheduler is not None
        assert scheduler.db is not None

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_scheduler_start(self, mock_init_db):
        """Test starting the scheduler."""
        scheduler = ScanScheduler()
        scheduler.start()
        assert scheduler.scheduler.running is True
        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_scheduler_shutdown(self, mock_init_db):
        """Test shutting down the scheduler."""
        scheduler = ScanScheduler()
        scheduler.start()
        assert scheduler.scheduler.running is True
        scheduler.shutdown(wait=False)
        assert scheduler.scheduler.running is False

    @patch("nethical_recon.scheduler.scheduler.init_database")
    @patch("nethical_recon.scheduler.scheduler.run_scan_job")
    def test_schedule_periodic_scan(self, mock_run_scan_job, mock_init_db):
        """Test scheduling a periodic scan."""
        scheduler = ScanScheduler()
        scheduler.start()

        # Mock database operations
        mock_session = MagicMock()
        mock_init_db.return_value.session.return_value.__enter__.return_value = mock_session

        job_id = scheduler.schedule_periodic_scan(
            target="example.com",
            tools=["nmap", "nikto"],
            interval_hours=6,
            name="Test periodic scan",
        )

        assert job_id is not None
        assert len(scheduler.list_jobs()) == 1

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    @patch("nethical_recon.scheduler.scheduler.run_scan_job")
    def test_schedule_cron_scan(self, mock_run_scan_job, mock_init_db):
        """Test scheduling a cron scan."""
        scheduler = ScanScheduler()
        scheduler.start()

        # Mock database operations
        mock_session = MagicMock()
        mock_init_db.return_value.session.return_value.__enter__.return_value = mock_session

        job_id = scheduler.schedule_cron_scan(
            target="example.com",
            tools=["nmap"],
            cron_expression="0 2 * * *",  # Daily at 2 AM
            name="Test cron scan",
        )

        assert job_id is not None
        assert len(scheduler.list_jobs()) == 1

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_schedule_cron_scan_invalid_expression(self, mock_init_db):
        """Test scheduling a cron scan with invalid expression."""
        scheduler = ScanScheduler()
        scheduler.start()

        with pytest.raises(ValueError):
            scheduler.schedule_cron_scan(
                target="example.com",
                tools=["nmap"],
                cron_expression="invalid",
            )

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_schedule_baseline_update(self, mock_init_db):
        """Test scheduling baseline updates."""
        scheduler = ScanScheduler()
        scheduler.start()

        job_id = scheduler.schedule_baseline_update(interval_hours=24)

        assert job_id == "baseline_update"
        assert len(scheduler.list_jobs()) == 1

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    @patch("nethical_recon.scheduler.scheduler.run_scan_job")
    def test_remove_job(self, mock_run_scan_job, mock_init_db):
        """Test removing a scheduled job."""
        scheduler = ScanScheduler()
        scheduler.start()

        # Mock database operations
        mock_session = MagicMock()
        mock_init_db.return_value.session.return_value.__enter__.return_value = mock_session

        job_id = scheduler.schedule_periodic_scan(
            target="example.com",
            tools=["nmap"],
            interval_hours=6,
        )

        assert len(scheduler.list_jobs()) == 1

        success = scheduler.remove_job(job_id)
        assert success is True
        assert len(scheduler.list_jobs()) == 0

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    def test_remove_nonexistent_job(self, mock_init_db):
        """Test removing a job that doesn't exist."""
        scheduler = ScanScheduler()
        scheduler.start()

        success = scheduler.remove_job("nonexistent-job")
        assert success is False

        scheduler.shutdown(wait=False)

    @patch("nethical_recon.scheduler.scheduler.init_database")
    @patch("nethical_recon.scheduler.scheduler.run_scan_job")
    def test_list_jobs(self, mock_run_scan_job, mock_init_db):
        """Test listing scheduled jobs."""
        scheduler = ScanScheduler()
        scheduler.start()

        # Mock database operations
        mock_session = MagicMock()
        mock_init_db.return_value.session.return_value.__enter__.return_value = mock_session

        # Schedule multiple jobs
        scheduler.schedule_periodic_scan(
            target="example1.com",
            tools=["nmap"],
            interval_hours=6,
        )
        scheduler.schedule_periodic_scan(
            target="example2.com",
            tools=["nikto"],
            interval_hours=12,
        )

        jobs = scheduler.list_jobs()
        assert len(jobs) == 2
        assert all("id" in job for job in jobs)
        assert all("name" in job for job in jobs)
        assert all("next_run" in job for job in jobs)
        assert all("trigger" in job for job in jobs)

        scheduler.shutdown(wait=False)
