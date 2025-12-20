"""Tests for policy engine."""

from __future__ import annotations

import ipaddress

import pytest

from nethical_recon.core.policy import (
    ConcurrencyPolicy,
    NetworkPolicy,
    PolicyEngine,
    RateLimitPolicy,
    RiskLevel,
    RulesOfEngagement,
    ToolPolicy,
)
from nethical_recon.core.policy.engine import PolicyViolation


class TestPolicyModels:
    """Test policy models."""

    def test_rate_limit_policy_defaults(self):
        """Test rate limit policy with defaults."""
        policy = RateLimitPolicy()
        assert policy.requests_per_second == 1.0
        assert policy.burst_size == 5
        assert policy.enabled is True

    def test_rate_limit_policy_custom(self):
        """Test rate limit policy with custom values."""
        policy = RateLimitPolicy(requests_per_second=10.0, burst_size=20, enabled=False)
        assert policy.requests_per_second == 10.0
        assert policy.burst_size == 20
        assert policy.enabled is False

    def test_concurrency_policy_defaults(self):
        """Test concurrency policy with defaults."""
        policy = ConcurrencyPolicy()
        assert policy.max_parallel_tools == 3
        assert policy.max_parallel_jobs == 5
        assert policy.enabled is True

    def test_network_policy_defaults(self):
        """Test network policy with defaults."""
        policy = NetworkPolicy()
        assert policy.allowed_networks == []
        assert policy.denied_networks == []
        assert policy.require_explicit_approval is False

    def test_network_policy_valid_networks(self):
        """Test network policy with valid CIDR networks."""
        policy = NetworkPolicy(
            allowed_networks=["10.0.0.0/8", "192.168.0.0/16"],
            denied_networks=["10.10.10.0/24"],
        )
        assert len(policy.allowed_networks) == 2
        assert len(policy.denied_networks) == 1

    def test_network_policy_invalid_networks(self):
        """Test network policy rejects invalid CIDR."""
        with pytest.raises(ValueError, match="Invalid network CIDR"):
            NetworkPolicy(allowed_networks=["not-a-cidr"])

    def test_tool_policy_defaults(self):
        """Test tool policy with defaults."""
        policy = ToolPolicy(tool_name="nmap")
        assert policy.tool_name == "nmap"
        assert policy.risk_level == RiskLevel.MEDIUM
        assert policy.requires_approval is False
        assert policy.enabled is True
        assert policy.max_duration_seconds is None

    def test_rules_of_engagement_defaults(self):
        """Test RoE with defaults."""
        roe = RulesOfEngagement()
        assert roe.name == "default"
        assert roe.rate_limit.requests_per_second == 1.0
        assert roe.concurrency.max_parallel_tools == 3
        assert roe.authorized_only is True
        assert roe.audit_logging_enabled is True
        assert "sqlmap" in roe.high_risk_tools

    def test_rules_of_engagement_custom(self):
        """Test RoE with custom configuration."""
        roe = RulesOfEngagement(
            name="strict",
            rate_limit=RateLimitPolicy(requests_per_second=0.5),
            concurrency=ConcurrencyPolicy(max_parallel_tools=1),
            network=NetworkPolicy(allowed_networks=["10.0.0.0/8"]),
        )
        assert roe.name == "strict"
        assert roe.rate_limit.requests_per_second == 0.5
        assert roe.concurrency.max_parallel_tools == 1
        assert len(roe.network.allowed_networks) == 1

    def test_is_tool_allowed_default(self):
        """Test tool allowed check for default tools."""
        roe = RulesOfEngagement()
        assert roe.is_tool_allowed("nmap") is True
        assert roe.is_tool_allowed("nikto") is True

    def test_is_tool_allowed_high_risk(self):
        """Test high-risk tools require explicit policy."""
        roe = RulesOfEngagement()
        assert roe.is_tool_allowed("sqlmap") is False
        assert roe.is_tool_allowed("metasploit") is False

    def test_is_tool_allowed_with_policy(self):
        """Test tool allowed with explicit policy."""
        roe = RulesOfEngagement(
            tool_policies={
                "sqlmap": ToolPolicy(tool_name="sqlmap", enabled=True),
            }
        )
        assert roe.is_tool_allowed("sqlmap") is True

    def test_get_tool_policy_existing(self):
        """Test getting existing tool policy."""
        policy = ToolPolicy(tool_name="nmap", risk_level=RiskLevel.LOW)
        roe = RulesOfEngagement(tool_policies={"nmap": policy})
        retrieved = roe.get_tool_policy("nmap")
        assert retrieved.tool_name == "nmap"
        assert retrieved.risk_level == RiskLevel.LOW

    def test_get_tool_policy_default(self):
        """Test getting default policy for tool."""
        roe = RulesOfEngagement()
        policy = roe.get_tool_policy("nmap")
        assert policy.tool_name == "nmap"
        assert policy.risk_level == RiskLevel.MEDIUM
        assert policy.requires_approval is False


class TestPolicyEngine:
    """Test policy engine."""

    def test_policy_engine_default(self):
        """Test policy engine with default RoE."""
        engine = PolicyEngine()
        assert engine.roe is not None
        assert engine.roe.name == "default"

    def test_policy_engine_custom_roe(self):
        """Test policy engine with custom RoE."""
        roe = RulesOfEngagement(name="custom")
        engine = PolicyEngine(roe)
        assert engine.roe.name == "custom"

    def test_check_target_allowed_no_restrictions(self):
        """Test target allowed with no restrictions."""
        engine = PolicyEngine()
        allowed, reason = engine.check_target_allowed("192.168.1.1")
        assert allowed is True
        assert "No network restrictions" in reason

    def test_check_target_allowed_in_allowed_network(self):
        """Test target in allowed network."""
        roe = RulesOfEngagement(
            network=NetworkPolicy(allowed_networks=["192.168.0.0/16"])
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_target_allowed("192.168.1.1")
        assert allowed is True
        assert "allowed network" in reason.lower()

    def test_check_target_allowed_not_in_allowed_network(self):
        """Test target not in allowed network."""
        roe = RulesOfEngagement(
            network=NetworkPolicy(allowed_networks=["10.0.0.0/8"])
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_target_allowed("192.168.1.1")
        assert allowed is False
        assert "not in any allowed network" in reason.lower()

    def test_check_target_allowed_in_denied_network(self):
        """Test target in denied network."""
        roe = RulesOfEngagement(
            network=NetworkPolicy(denied_networks=["192.168.0.0/16"])
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_target_allowed("192.168.1.1")
        assert allowed is False
        assert "denied network" in reason.lower()

    def test_check_target_allowed_domain(self):
        """Test domain target (not subject to network restrictions)."""
        roe = RulesOfEngagement(
            network=NetworkPolicy(allowed_networks=["10.0.0.0/8"])
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_target_allowed("example.com")
        assert allowed is True

    def test_check_tool_allowed_default(self):
        """Test tool allowed by default."""
        engine = PolicyEngine()
        allowed, reason = engine.check_tool_allowed("nmap")
        assert allowed is True
        assert "allowed" in reason.lower()

    def test_check_tool_allowed_high_risk(self):
        """Test high-risk tool not allowed without policy."""
        engine = PolicyEngine()
        allowed, reason = engine.check_tool_allowed("sqlmap")
        assert allowed is False
        assert "high-risk" in reason.lower()

    def test_check_tool_allowed_disabled(self):
        """Test disabled tool."""
        roe = RulesOfEngagement(
            tool_policies={
                "nmap": ToolPolicy(tool_name="nmap", enabled=False),
            }
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_tool_allowed("nmap")
        assert allowed is False
        assert "disabled" in reason.lower()

    def test_check_concurrency_limits_enabled(self):
        """Test concurrency limits when enabled."""
        engine = PolicyEngine()
        allowed, reason = engine.check_concurrency_limits(job_id="job1")
        assert allowed is True

    def test_check_concurrency_limits_disabled(self):
        """Test concurrency limits when disabled."""
        roe = RulesOfEngagement(
            concurrency=ConcurrencyPolicy(enabled=False)
        )
        engine = PolicyEngine(roe)
        allowed, reason = engine.check_concurrency_limits(job_id="job1")
        assert allowed is True
        assert "disabled" in reason.lower()

    def test_check_concurrency_limits_jobs(self):
        """Test job concurrency limits."""
        roe = RulesOfEngagement(
            concurrency=ConcurrencyPolicy(max_parallel_jobs=2)
        )
        engine = PolicyEngine(roe)

        # Register two jobs
        engine.register_job_start("job1")
        engine.register_job_start("job2")

        # Third job should fail
        allowed, reason = engine.check_concurrency_limits(job_id="job3")
        assert allowed is False
        assert "Max parallel jobs" in reason

        # Cleanup
        engine.register_job_end("job1")

    def test_check_concurrency_limits_tools(self):
        """Test tool concurrency limits."""
        roe = RulesOfEngagement(
            concurrency=ConcurrencyPolicy(max_parallel_tools=2)
        )
        engine = PolicyEngine(roe)

        # Register two tools
        engine.register_tool_start("tool1", "nmap")
        engine.register_tool_start("tool2", "nikto")

        # Third tool should fail
        allowed, reason = engine.check_concurrency_limits(tool_id="tool3")
        assert allowed is False
        assert "Max parallel tools" in reason

        # Cleanup
        engine.register_tool_end("tool1")

    def test_validate_job_success(self):
        """Test successful job validation."""
        engine = PolicyEngine()
        result = engine.validate_job("192.168.1.1", ["nmap", "nikto"])
        assert result["allowed"] is True
        assert result["target_allowed"] is True
        assert result["tools_allowed"]["nmap"]["allowed"] is True
        assert result["tools_allowed"]["nikto"]["allowed"] is True

    def test_validate_job_target_not_allowed(self):
        """Test job validation with disallowed target."""
        roe = RulesOfEngagement(
            network=NetworkPolicy(denied_networks=["192.168.0.0/16"])
        )
        engine = PolicyEngine(roe)

        with pytest.raises(PolicyViolation):
            engine.validate_job("192.168.1.1", ["nmap"])

    def test_validate_job_tool_not_allowed(self):
        """Test job validation with disallowed tool."""
        engine = PolicyEngine()

        with pytest.raises(PolicyViolation):
            engine.validate_job("192.168.1.1", ["sqlmap"])

    def test_rate_limiter_acquire(self):
        """Test rate limiter acquire."""
        from nethical_recon.core.policy.engine import RateLimiter

        limiter = RateLimiter(rate=10.0, burst=5)

        # Should be able to acquire burst size
        for _ in range(5):
            assert limiter.acquire() is True

        # Next one should fail
        assert limiter.acquire() is False

    def test_rate_limiter_wait_time(self):
        """Test rate limiter wait time calculation."""
        from nethical_recon.core.policy.engine import RateLimiter

        limiter = RateLimiter(rate=1.0, burst=1)

        # Exhaust tokens
        limiter.acquire()

        # Should need to wait
        wait = limiter.wait_time(1)
        assert wait > 0
