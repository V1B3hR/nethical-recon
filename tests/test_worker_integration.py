"""Integration tests for worker module (without Redis dependency)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.worker.policy import PolicyEngine
from nethical_recon.worker.scheduler import ScanScheduler


class TestWorkerIntegration:
    """Test worker integration without Redis."""

    def test_policy_engine_initialization(self):
        """Test that policy engine initializes correctly."""
        policy = PolicyEngine()
        assert policy.config is not None
        assert policy.config.rate_limit is not None
        assert policy.config.concurrency is not None

    def test_job_lifecycle_with_policy(self):
        """Test job lifecycle with policy enforcement."""
        policy = PolicyEngine()
        job_id = str(uuid4())

        # Job should be able to start
        can_start, reason = policy.can_start_job(job_id)
        assert can_start is True

        # Register job as started
        policy.start_job(job_id)

        # Same job cannot start twice
        can_start, reason = policy.can_start_job(job_id)
        assert can_start is False
        assert "already running" in reason.lower()

        # Finish job
        policy.finish_job(job_id)

        # Now can start again
        can_start, reason = policy.can_start_job(job_id)
        assert can_start is True

    def test_tool_lifecycle_with_policy(self):
        """Test tool lifecycle with policy enforcement."""
        policy = PolicyEngine()
        job_id = str(uuid4())

        # Tool should be able to start
        can_start, reason = policy.can_start_tool("nmap", job_id)
        assert can_start is True

        # Register tool as started
        policy.start_tool("nmap", job_id)

        # Same tool for same job tracked correctly
        stats = policy.get_stats()
        assert stats["active_tools"] == 1

        # Finish tool
        policy.finish_tool("nmap", job_id)

        stats = policy.get_stats()
        assert stats["active_tools"] == 0

    def test_scheduler_creation(self):
        """Test that scheduler can be created."""
        scheduler = ScanScheduler()
        assert scheduler is not None
        assert scheduler.db is not None

    @patch("nethical_recon.worker.scheduler.app")
    def test_schedule_recurring_scan(self, mock_app):
        """Test scheduling a recurring scan."""
        mock_app.conf.beat_schedule = {}

        scheduler = ScanScheduler()
        target_id = uuid4()

        schedule_name = scheduler.schedule_recurring_scan(
            target_id=target_id, tools=["nmap"], interval_hours=24.0, name="test_scan"
        )

        assert schedule_name == "test_scan"
        assert "test_scan" in mock_app.conf.beat_schedule

    def test_target_validation_with_policy(self):
        """Test target validation against policy."""
        policy = PolicyEngine()
        policy.config.network.allowlist = ["192.168.1.0/24"]
        policy.config.network.require_explicit_approval = True

        # Target in allowlist should be allowed
        is_allowed, reason = policy.is_target_allowed("192.168.1.10")
        assert is_allowed is True

        # Target outside allowlist should be blocked
        is_allowed, reason = policy.is_target_allowed("10.0.0.1")
        assert is_allowed is False

    def test_high_risk_tool_policy(self):
        """Test high-risk tool requires approval."""
        policy = PolicyEngine()
        policy.config.tools.require_approval_for_high_risk = True

        # High-risk tool should be blocked without approval
        can_start, reason = policy.can_start_tool("sqlmap")
        assert can_start is False
        assert "approval" in reason.lower()

        # Normal tool should be allowed
        can_start, reason = policy.can_start_tool("nmap")
        assert can_start is True

    def test_rate_limiting_enforcement(self):
        """Test rate limiting is enforced correctly."""
        policy = PolicyEngine()
        policy.config.rate_limit.requests_per_second = 1.0
        policy.config.rate_limit.burst_size = 2

        # First two requests should succeed (burst)
        can_proceed, _ = policy.check_rate_limit("test")
        assert can_proceed is True

        can_proceed, _ = policy.check_rate_limit("test")
        assert can_proceed is True

        # Third request should fail
        can_proceed, reason = policy.check_rate_limit("test")
        assert can_proceed is False
        assert "exceeded" in reason.lower()

    def test_concurrency_limits_enforced(self):
        """Test concurrency limits are enforced."""
        policy = PolicyEngine()
        policy.config.concurrency.max_parallel_jobs = 2

        # Start first job
        policy.start_job("job1")
        stats = policy.get_stats()
        assert stats["active_jobs"] == 1

        # Start second job
        policy.start_job("job2")
        stats = policy.get_stats()
        assert stats["active_jobs"] == 2

        # Third job should be blocked
        can_start, reason = policy.can_start_job("job3")
        assert can_start is False
        assert "limit reached" in reason.lower()

    def test_policy_stats_accuracy(self):
        """Test policy stats are accurate."""
        policy = PolicyEngine()

        # Start some jobs and tools
        policy.start_job("job1")
        policy.start_tool("nmap", "job1")
        policy.start_tool("nikto", "job1")

        stats = policy.get_stats()
        assert stats["active_jobs"] == 1
        assert stats["active_tools"] == 2
        assert stats["max_parallel_jobs"] == 5
        assert stats["max_parallel_tools"] == 3

    def test_policy_thread_safety(self):
        """Test policy engine handles concurrent access."""
        import threading

        policy = PolicyEngine()
        results = []

        def start_job(job_id: str):
            can_start, reason = policy.can_start_job(job_id)
            if can_start:
                policy.start_job(job_id)
            results.append(can_start)

        # Try to start same job from multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=start_job, args=("concurrent_job",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Only one thread should have succeeded
        assert sum(results) == 1


class TestWorkerCLI:
    """Test worker CLI commands."""

    def test_worker_cli_import(self):
        """Test that worker CLI can be imported."""
        from nethical_recon.worker import cli

        assert cli is not None
        assert hasattr(cli, "app")

    def test_policy_stats_command_available(self):
        """Test that policy-stats command is available."""
        from nethical_recon.worker.cli import app

        commands = []
        for cmd in app.registered_commands:
            if hasattr(cmd, "callback") and cmd.callback:
                commands.append(cmd.callback.__name__)

        assert "policy_stats" in commands
