"""Tests for the policy engine."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from nethical_recon.worker.policy import PolicyEngine, RulesOfEngagement


class TestPolicyEngine:
    """Test the policy engine."""

    def test_default_configuration(self):
        """Test policy engine with default configuration."""
        policy = PolicyEngine()
        assert policy.config is not None
        assert policy.config.rate_limit.requests_per_second == 1.0
        assert policy.config.concurrency.max_parallel_jobs == 5

    def test_job_concurrency_limit(self):
        """Test that job concurrency limits are enforced."""
        policy = PolicyEngine()
        # Override for testing
        policy.config.concurrency.max_parallel_jobs = 2

        # Start first job - should succeed
        can_start, reason = policy.can_start_job("job1")
        assert can_start is True
        policy.start_job("job1")

        # Start second job - should succeed
        can_start, reason = policy.can_start_job("job2")
        assert can_start is True
        policy.start_job("job2")

        # Try to start third job - should fail
        can_start, reason = policy.can_start_job("job3")
        assert can_start is False
        assert "limit reached" in reason.lower()

        # Finish first job
        policy.finish_job("job1")

        # Now third job should succeed
        can_start, reason = policy.can_start_job("job3")
        assert can_start is True

    def test_duplicate_job_rejection(self):
        """Test that duplicate job IDs are rejected."""
        policy = PolicyEngine()

        can_start, reason = policy.can_start_job("job1")
        assert can_start is True
        policy.start_job("job1")

        # Try to start same job again
        can_start, reason = policy.can_start_job("job1")
        assert can_start is False
        assert "already running" in reason.lower()

    def test_tool_concurrency_limit(self):
        """Test that tool concurrency limits are enforced."""
        policy = PolicyEngine()
        policy.config.concurrency.max_parallel_tools = 2

        # Start first tool
        can_start, reason = policy.can_start_tool("nmap")
        assert can_start is True
        policy.start_tool("nmap")

        # Start second tool
        can_start, reason = policy.can_start_tool("nikto")
        assert can_start is True
        policy.start_tool("nikto")

        # Try third tool - should fail
        can_start, reason = policy.can_start_tool("dirb")
        assert can_start is False

        # Finish first tool
        policy.finish_tool("nmap")

        # Now third tool should succeed
        can_start, reason = policy.can_start_tool("dirb")
        assert can_start is True

    def test_per_job_tool_limit(self):
        """Test per-job tool concurrency limits."""
        policy = PolicyEngine()
        policy.config.concurrency.max_parallel_tools_per_job = 1

        # Start tool for job1
        can_start, reason = policy.can_start_tool("nmap", "job1")
        assert can_start is True
        policy.start_tool("nmap", "job1")

        # Try second tool for same job - should fail
        can_start, reason = policy.can_start_tool("nikto", "job1")
        assert can_start is False

        # Tool for different job should succeed
        can_start, reason = policy.can_start_tool("nmap", "job2")
        assert can_start is True

    def test_high_risk_tool_blocking(self):
        """Test that high-risk tools are blocked without approval."""
        policy = PolicyEngine()
        policy.config.tools.require_approval_for_high_risk = True

        # Try to use high-risk tool without approval
        can_start, reason = policy.can_start_tool("sqlmap")
        assert can_start is False
        assert "approval" in reason.lower()

    def test_disabled_tool_blocking(self):
        """Test that disabled tools are blocked."""
        policy = PolicyEngine()
        policy.config.tools.disabled_tools = ["nmap"]

        can_start, reason = policy.can_start_tool("nmap")
        assert can_start is False
        assert "disabled" in reason.lower()

    def test_target_allowlist(self):
        """Test target allowlist enforcement."""
        policy = PolicyEngine()
        policy.config.network.allowlist = ["192.168.1.0/24"]
        policy.config.network.require_explicit_approval = True

        # IP in allowlist should be allowed
        is_allowed, reason = policy.is_target_allowed("192.168.1.10")
        assert is_allowed is True

        # IP outside allowlist should be blocked
        is_allowed, reason = policy.is_target_allowed("10.0.0.1")
        assert is_allowed is False

    def test_target_denylist(self):
        """Test target denylist enforcement."""
        policy = PolicyEngine()
        policy.config.network.allowlist = ["0.0.0.0/0"]  # Allow all
        policy.config.network.denylist = ["127.0.0.0/8"]
        policy.config.network.require_explicit_approval = False

        # Regular IP should be allowed
        is_allowed, reason = policy.is_target_allowed("192.168.1.10")
        assert is_allowed is True

        # Localhost should be blocked
        is_allowed, reason = policy.is_target_allowed("127.0.0.1")
        assert is_allowed is False

    def test_rate_limiting(self):
        """Test rate limiting with token bucket."""
        policy = PolicyEngine()
        policy.config.rate_limit.requests_per_second = 2.0
        policy.config.rate_limit.burst_size = 3

        # Should allow burst of 3 requests immediately
        for i in range(3):
            can_proceed, reason = policy.check_rate_limit("test")
            assert can_proceed is True, f"Request {i+1} should succeed"

        # 4th request should fail (no tokens left)
        can_proceed, reason = policy.check_rate_limit("test")
        assert can_proceed is False

        # Wait for tokens to refill (0.5 seconds = 1 token at 2 req/s)
        time.sleep(0.6)

        # Now should succeed again
        can_proceed, reason = policy.check_rate_limit("test")
        assert can_proceed is True

    def test_rate_limiting_different_resources(self):
        """Test that rate limiting is per-resource."""
        policy = PolicyEngine()
        policy.config.rate_limit.requests_per_second = 1.0
        policy.config.rate_limit.burst_size = 1

        # Use up tokens for resource1
        can_proceed, reason = policy.check_rate_limit("resource1")
        assert can_proceed is True

        # resource1 should be limited
        can_proceed, reason = policy.check_rate_limit("resource1")
        assert can_proceed is False

        # But resource2 should still work
        can_proceed, reason = policy.check_rate_limit("resource2")
        assert can_proceed is True

    def test_get_stats(self):
        """Test getting policy engine statistics."""
        policy = PolicyEngine()
        policy.start_job("job1")
        policy.start_tool("nmap", "job1")

        stats = policy.get_stats()
        assert stats["active_jobs"] == 1
        assert stats["active_tools"] == 1
        assert "max_parallel_jobs" in stats
        assert "max_parallel_tools" in stats


class TestRulesOfEngagement:
    """Test RoE configuration models."""

    def test_default_roe(self):
        """Test default RoE configuration."""
        roe = RulesOfEngagement()
        assert roe.rate_limit.requests_per_second == 1.0
        assert roe.concurrency.max_parallel_jobs == 5
        assert roe.audit_all_actions is True
        assert roe.require_legal_consent is True

    def test_roe_validation(self):
        """Test RoE validation."""
        # Rate limit must be positive
        with pytest.raises(ValueError):
            RulesOfEngagement(rate_limit={"requests_per_second": 0.0})

        # Max parallel jobs must be at least 1
        with pytest.raises(ValueError):
            RulesOfEngagement(concurrency={"max_parallel_jobs": 0})

    def test_roe_serialization(self):
        """Test RoE can be serialized to dict."""
        roe = RulesOfEngagement()
        data = roe.model_dump()
        assert "rate_limit" in data
        assert "concurrency" in data
        assert "network" in data
        assert "tools" in data
