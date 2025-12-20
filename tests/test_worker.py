"""Tests for worker tasks (mock-based tests)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nethical_recon.core.models import (
    JobStatus,
    ToolStatus,
    ScanJob,
    Target,
    TargetScope,
    TargetType,
    ToolRun,
)


class TestWorkerComponents:
    """Test worker components."""

    def test_get_tool_version_nmap(self):
        """Test getting nmap version."""
        from nethical_recon.worker.tasks import _get_tool_version

        version = _get_tool_version("nmap")
        assert isinstance(version, str)
        # Version should be "unknown" if nmap not installed
        assert len(version) > 0

    def test_get_tool_version_unknown(self):
        """Test getting version of unknown tool."""
        from nethical_recon.worker.tasks import _get_tool_version

        version = _get_tool_version("nonexistent-tool")
        assert version == "unknown"


class TestScheduler:
    """Test scheduler functionality."""

    def test_scheduler_initialization(self):
        """Test scheduler can be initialized."""
        from nethical_recon.worker.scheduler import ScanScheduler

        scheduler = ScanScheduler()
        assert scheduler is not None
        assert scheduler.scheduler is not None

    @patch("nethical_recon.worker.scheduler.init_database")
    def test_get_scheduler_singleton(self, mock_db):
        """Test scheduler singleton pattern."""
        from nethical_recon.worker.scheduler import get_scheduler, _scheduler

        # Reset singleton
        import nethical_recon.worker.scheduler as sched_module

        sched_module._scheduler = None

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2

    def test_scheduler_list_jobs_empty(self):
        """Test listing scheduled jobs when empty."""
        from nethical_recon.worker.scheduler import ScanScheduler

        scheduler = ScanScheduler()
        jobs = scheduler.list_scheduled_jobs()
        assert isinstance(jobs, list)

