"""Tests for Phase C: Worker Queue + Scheduler + Policy Engine."""

from __future__ import annotations

import ipaddress
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from nethical_recon.core.policy import (
    ConcurrencyPolicy,
    NetworkPolicy,
    Policy,
    PolicyEngine,
    PolicyViolationError,
    RateLimitPolicy,
    RiskLevel,
    ToolPolicy,
)
from nethical_recon.scheduler import ScheduleFrequency, ScheduledScan


class TestPolicyModels:
    """Test policy model validation."""

    def test_rate_limit_policy_creation(self):
        """Test rate limit policy creation."""
        policy = RateLimitPolicy(
            enabled=True,
            requests_per_second=10.0,
            burst_size=20,
        )
        assert policy.enabled is True
        assert policy.requests_per_second == 10.0
        assert policy.burst_size == 20

    def test_rate_limit_policy_validation(self):
        """Test rate limit policy validation."""
        with pytest.raises(ValueError):
            RateLimitPolicy(requests_per_second=-1.0)

        with pytest.raises(ValueError):
            RateLimitPolicy(burst_size=0)

    def test_concurrency_policy_creation(self):
        """Test concurrency policy creation."""
        policy = ConcurrencyPolicy(
            enabled=True,
            max_parallel_scans=5,
            max_parallel_tools=3,
            max_workers=4,
        )
        assert policy.enabled is True
        assert policy.max_parallel_scans == 5
        assert policy.max_parallel_tools == 3
        assert policy.max_workers == 4

    def test_network_policy_creation(self):
        """Test network policy creation."""
        policy = NetworkPolicy(
            enabled=True,
            allow_networks=["192.0.2.0/24"],
            deny_networks=["10.0.0.0/8"],
        )
        assert policy.enabled is True
        assert "192.0.2.0/24" in policy.allow_networks
        assert "10.0.0.0/8" in policy.deny_networks

    def test_network_policy_invalid_cidr(self):
        """Test network policy with invalid CIDR."""
        with pytest.raises(ValueError, match="Invalid CIDR"):
            NetworkPolicy(allow_networks=["invalid"])

    def test_tool_policy_creation(self):
        """Test tool policy creation."""
        policy = ToolPolicy(
            enabled=True,
            high_risk_tools=["sqlmap", "metasploit"],
            require_approval_for_high_risk=True,
        )
        assert policy.enabled is True
        assert "sqlmap" in policy.high_risk_tools

    def test_complete_policy_creation(self):
        """Test complete policy creation."""
        policy = Policy(
            name="test_policy",
            description="Test policy",
            risk_level=RiskLevel.MEDIUM,
        )
        assert policy.name == "test_policy"
        assert policy.risk_level == RiskLevel.MEDIUM
        assert isinstance(policy.rate_limit, RateLimitPolicy)
        assert isinstance(policy.concurrency, ConcurrencyPolicy)
        assert isinstance(policy.network, NetworkPolicy)
        assert isinstance(policy.tool, ToolPolicy)


class TestPolicyEngine:
    """Test policy engine enforcement."""

    def test_engine_creation(self):
        """Test policy engine creation."""
        policy = Policy(name="test")
        engine = PolicyEngine(policy)
        assert engine.policy == policy

    def test_validate_target_allowed(self):
        """Test target validation for allowed targets."""
        policy = Policy(
            name="test",
            network=NetworkPolicy(
                enabled=True,
                allow_networks=["192.0.2.0/24"],
                deny_networks=[],
            ),
        )
        engine = PolicyEngine(policy)

        # Should allow target in allowed network
        assert engine.validate_target("192.0.2.10") is True

    def test_validate_target_denied(self):
        """Test target validation for denied targets."""
        policy = Policy(
            name="test",
            network=NetworkPolicy(
                enabled=True,
                deny_networks=["10.0.0.0/8"],
            ),
        )
        engine = PolicyEngine(policy)

        # Should deny target in denied network
        with pytest.raises(PolicyViolationError, match="denied network"):
            engine.validate_target("10.0.0.1")

    def test_validate_target_not_in_allowlist(self):
        """Test target validation when not in allowlist."""
        policy = Policy(
            name="test",
            network=NetworkPolicy(
                enabled=True,
                allow_networks=["192.0.2.0/24"],
            ),
        )
        engine = PolicyEngine(policy)

        # Should deny target not in allowed networks
        with pytest.raises(PolicyViolationError, match="not in any allowed network"):
            engine.validate_target("203.0.113.1")

    def test_validate_target_hostname(self):
        """Test target validation for hostnames."""
        policy = Policy(name="test")
        engine = PolicyEngine(policy)

        # Hostnames should be allowed (will be resolved later)
        assert engine.validate_target("example.com") is True

    def test_validate_tool_allowed(self):
        """Test tool validation for allowed tools."""
        policy = Policy(name="test", tool=ToolPolicy(enabled=True, allowed_tools=["nmap", "nikto"]))
        engine = PolicyEngine(policy)

        assert engine.validate_tool("nmap") is True
        assert engine.validate_tool("nikto") is True

    def test_validate_tool_not_allowed(self):
        """Test tool validation for non-allowed tools."""
        policy = Policy(name="test", tool=ToolPolicy(enabled=True, allowed_tools=["nmap"]))
        engine = PolicyEngine(policy)

        with pytest.raises(PolicyViolationError, match="not in allowed tools"):
            engine.validate_tool("sqlmap")

    def test_validate_tool_high_risk(self):
        """Test tool validation for high-risk tools."""
        policy = Policy(
            name="test",
            tool=ToolPolicy(
                enabled=True,
                high_risk_tools=["sqlmap", "metasploit"],
                require_approval_for_high_risk=True,
            ),
        )
        engine = PolicyEngine(policy)

        with pytest.raises(PolicyViolationError, match="requires explicit approval"):
            engine.validate_tool("sqlmap")

    def test_acquire_scan_slot(self):
        """Test scan slot acquisition."""
        policy = Policy(name="test", concurrency=ConcurrencyPolicy(max_parallel_scans=2))
        engine = PolicyEngine(policy)

        # Should acquire first slot
        assert engine.acquire_scan_slot("job1") is True

        # Should acquire second slot
        assert engine.acquire_scan_slot("job2") is True

        # Should fail on third slot
        with pytest.raises(PolicyViolationError, match="Max parallel scans"):
            engine.acquire_scan_slot("job3")

    def test_release_scan_slot(self):
        """Test scan slot release."""
        policy = Policy(name="test", concurrency=ConcurrencyPolicy(max_parallel_scans=1))
        engine = PolicyEngine(policy)

        engine.acquire_scan_slot("job1")
        engine.release_scan_slot("job1")

        # Should be able to acquire again after release
        assert engine.acquire_scan_slot("job2") is True

    def test_acquire_tool_slot(self):
        """Test tool slot acquisition."""
        policy = Policy(name="test", concurrency=ConcurrencyPolicy(max_parallel_tools=2))
        engine = PolicyEngine(policy)

        # Should acquire first tool slot
        assert engine.acquire_tool_slot("job1") is True

        # Should acquire second tool slot
        assert engine.acquire_tool_slot("job1") is True

        # Should fail on third tool slot
        with pytest.raises(PolicyViolationError, match="Max parallel tools"):
            engine.acquire_tool_slot("job1")

    def test_release_tool_slot(self):
        """Test tool slot release."""
        policy = Policy(name="test", concurrency=ConcurrencyPolicy(max_parallel_tools=1))
        engine = PolicyEngine(policy)

        engine.acquire_tool_slot("job1")
        engine.release_tool_slot("job1")

        # Should be able to acquire again after release
        assert engine.acquire_tool_slot("job1") is True

    def test_rate_limiter(self):
        """Test rate limiting."""
        policy = Policy(
            name="test",
            rate_limit=RateLimitPolicy(
                enabled=True,
                requests_per_second=10.0,
                burst_size=5,
            ),
        )
        engine = PolicyEngine(policy)

        # Should acquire tokens up to burst size
        for _ in range(5):
            assert engine.acquire_rate_limit() is True

        # Should fail after burst
        with pytest.raises(PolicyViolationError, match="Rate limit exceeded"):
            engine.acquire_rate_limit()

    def test_policy_disabled(self):
        """Test that disabled policies don't enforce."""
        policy = Policy(
            name="test",
            rate_limit=RateLimitPolicy(enabled=False),
            concurrency=ConcurrencyPolicy(enabled=False),
            network=NetworkPolicy(enabled=False),
            tool=ToolPolicy(enabled=False),
        )
        engine = PolicyEngine(policy)

        # All checks should pass when disabled
        assert engine.validate_target("10.0.0.1") is True
        assert engine.validate_tool("sqlmap") is True
        assert engine.acquire_scan_slot("job1") is True
        assert engine.acquire_tool_slot("job1") is True
        assert engine.acquire_rate_limit() is True

    def test_get_stats(self):
        """Test getting engine statistics."""
        policy = Policy(name="test")
        engine = PolicyEngine(policy)

        stats = engine.get_stats()
        assert "active_scans" in stats
        assert "active_tools_by_job" in stats
        assert "max_parallel_scans" in stats
        assert stats["active_scans"] == 0


class TestSchedulerModels:
    """Test scheduler models."""

    def test_scheduled_scan_creation(self):
        """Test scheduled scan creation."""
        target_id = uuid4()
        scan = ScheduledScan(
            target_id=target_id,
            name="Daily scan",
            frequency=ScheduleFrequency.DAILY,
            tools=["nmap", "nikto"],
        )
        assert scan.target_id == target_id
        assert scan.name == "Daily scan"
        assert scan.frequency == ScheduleFrequency.DAILY
        assert scan.enabled is True
        assert "nmap" in scan.tools

    def test_scheduled_scan_with_cron(self):
        """Test scheduled scan with custom cron."""
        scan = ScheduledScan(
            target_id=uuid4(),
            name="Custom scan",
            frequency=ScheduleFrequency.CUSTOM,
            cron_expression="0 */6 * * *",  # Every 6 hours
            tools=["nmap"],
        )
        assert scan.frequency == ScheduleFrequency.CUSTOM
        assert scan.cron_expression == "0 */6 * * *"

    def test_frequency_to_cron_daily(self):
        """Test frequency to cron conversion for daily."""
        from nethical_recon.scheduler.models import frequency_to_cron

        cron = frequency_to_cron(ScheduleFrequency.DAILY)
        assert cron == "0 2 * * *"  # 2 AM daily

    def test_frequency_to_cron_weekly(self):
        """Test frequency to cron conversion for weekly."""
        from nethical_recon.scheduler.models import frequency_to_cron

        cron = frequency_to_cron(ScheduleFrequency.WEEKLY)
        assert cron == "0 2 * * 0"  # Sunday 2 AM

    def test_frequency_to_cron_custom_raises(self):
        """Test frequency to cron raises for custom."""
        from nethical_recon.scheduler.models import frequency_to_cron

        with pytest.raises(ValueError, match="Cannot convert"):
            frequency_to_cron(ScheduleFrequency.CUSTOM)


class TestWorkerIntegration:
    """Test worker task structure (without actual execution)."""

    def test_tasks_importable(self):
        """Test that worker tasks can be imported."""
        from nethical_recon.worker import generate_report, normalize_results, run_scan_job, run_tool

        assert run_scan_job is not None
        assert run_tool is not None
        assert normalize_results is not None
        assert generate_report is not None

    def test_celery_app_importable(self):
        """Test that Celery app can be imported."""
        from nethical_recon.worker import celery_app

        assert celery_app is not None
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
