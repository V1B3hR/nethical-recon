"""Tests for worker tasks and policy engine."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from nethical_recon.worker.policy import PolicyEngine, RoEConfig


class TestPolicyEngine:
    """Tests for policy engine."""

    def test_default_config(self):
        """Test default RoE configuration."""
        config = RoEConfig()
        assert config.max_requests_per_second == 10.0
        assert config.max_concurrent_tools == 5
        assert config.max_concurrent_jobs == 10
        assert config.require_explicit_auth_for_high_risk is True

    def test_policy_engine_initialization(self):
        """Test policy engine initialization."""
        engine = PolicyEngine()
        assert engine.config is not None
        assert engine._active_tools == 0
        assert engine._active_jobs == 0

    def test_can_run_allowed_tool(self):
        """Test that allowed tools can be run."""
        config = RoEConfig(allowed_tools=["nmap", "nikto"])
        engine = PolicyEngine(config)
        assert engine.can_run_tool("nmap") is True
        assert engine.can_run_tool("nikto") is True

    def test_can_run_disallowed_tool(self):
        """Test that disallowed tools cannot be run."""
        config = RoEConfig(allowed_tools=["nmap"])
        engine = PolicyEngine(config)
        assert engine.can_run_tool("metasploit") is False

    def test_high_risk_tool_without_auth(self):
        """Test that high-risk tools require explicit auth."""
        config = RoEConfig(
            allowed_tools=["nmap", "metasploit"],
            high_risk_tools=["metasploit"],
            require_explicit_auth_for_high_risk=True,
        )
        engine = PolicyEngine(config)
        assert engine.can_run_tool("metasploit", explicit_auth=False) is False
        assert engine.can_run_tool("metasploit", explicit_auth=True) is True

    def test_concurrent_tool_limit(self):
        """Test concurrent tool limit enforcement."""
        config = RoEConfig(max_concurrent_tools=2)
        engine = PolicyEngine(config)
        engine._active_tools = 2
        assert engine.can_run_tool("nmap") is False

    def test_concurrent_job_limit(self):
        """Test concurrent job limit enforcement."""
        config = RoEConfig(max_concurrent_jobs=3)
        engine = PolicyEngine(config)
        engine._active_jobs = 3
        assert engine.can_start_job() is False
        engine._active_jobs = 2
        assert engine.can_start_job() is True

    def test_network_allowlist(self):
        """Test network allowlist enforcement."""
        config = RoEConfig(allowed_networks=["192.168.0.0/16", "10.0.0.0/8"])
        engine = PolicyEngine(config)
        assert engine.is_network_allowed("192.168.1.1") is True
        assert engine.is_network_allowed("10.10.10.10") is True
        assert engine.is_network_allowed("8.8.8.8") is False

    def test_network_denylist(self):
        """Test network denylist enforcement."""
        config = RoEConfig(denied_networks=["192.168.100.0/24"])
        engine = PolicyEngine(config)
        assert engine.is_network_allowed("192.168.100.10") is False
        assert engine.is_network_allowed("192.168.1.1") is True

    def test_domain_always_allowed(self):
        """Test that domain names are allowed by default."""
        config = RoEConfig(allowed_networks=["192.168.0.0/16"])
        engine = PolicyEngine(config)
        assert engine.is_network_allowed("example.com") is True

    def test_validate_scan_config_ports(self):
        """Test scan config validation for port count."""
        config = RoEConfig(max_ports_to_scan=100)
        engine = PolicyEngine(config)

        valid_config = {"ports": list(range(50))}
        is_valid, errors = engine.validate_scan_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0

        invalid_config = {"ports": list(range(200))}
        is_valid, errors = engine.validate_scan_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_scan_config_threads(self):
        """Test scan config validation for thread count."""
        config = RoEConfig(max_threads=5)
        engine = PolicyEngine(config)

        valid_config = {"threads": 3}
        is_valid, errors = engine.validate_scan_config(valid_config)
        assert is_valid is True

        invalid_config = {"threads": 10}
        is_valid, errors = engine.validate_scan_config(invalid_config)
        assert is_valid is False

    def test_validate_scan_config_timeout(self):
        """Test scan config validation for timeout."""
        config = RoEConfig(max_scan_duration_seconds=1800)
        engine = PolicyEngine(config)

        valid_config = {"timeout": 1000}
        is_valid, errors = engine.validate_scan_config(valid_config)
        assert is_valid is True

        invalid_config = {"timeout": 3600}
        is_valid, errors = engine.validate_scan_config(invalid_config)
        assert is_valid is False

    def test_increment_decrement_counters(self):
        """Test counter increment and decrement."""
        engine = PolicyEngine()
        assert engine._active_tools == 0

        engine.increment_active_tools()
        assert engine._active_tools == 1

        engine.increment_active_tools()
        assert engine._active_tools == 2

        engine.decrement_active_tools()
        assert engine._active_tools == 1

        engine.decrement_active_tools()
        assert engine._active_tools == 0

        # Should not go below 0
        engine.decrement_active_tools()
        assert engine._active_tools == 0

    def test_get_status(self):
        """Test getting policy engine status."""
        config = RoEConfig(max_concurrent_tools=5, max_concurrent_jobs=10)
        engine = PolicyEngine(config)
        engine._active_tools = 2
        engine._active_jobs = 3

        status = engine.get_status()
        assert status["active_tools"] == 2
        assert status["max_concurrent_tools"] == 5
        assert status["active_jobs"] == 3
        assert status["max_concurrent_jobs"] == 10


class TestWorkerTasks:
    """Tests for worker tasks."""

    @patch("nethical_recon.worker.tasks.init_database")
    @patch("nethical_recon.worker.tasks.run_tool")
    def test_run_scan_job_task(self, mock_run_tool, mock_init_db):
        """Test run_scan_job task."""
        # This is a basic structure test
        # Full integration tests would require a running Celery worker
        from nethical_recon.worker.tasks import run_scan_job

        # Verify task is registered
        assert run_scan_job.name == "nethical_recon.worker.tasks.run_scan_job"

    @patch("nethical_recon.worker.tasks.init_database")
    @patch("nethical_recon.worker.tasks.PolicyEngine")
    def test_run_tool_task(self, mock_policy, mock_init_db):
        """Test run_tool task."""
        from nethical_recon.worker.tasks import run_tool

        # Verify task is registered
        assert run_tool.name == "nethical_recon.worker.tasks.run_tool"

    def test_normalize_results_task(self):
        """Test normalize_results task."""
        from nethical_recon.worker.tasks import normalize_results

        # Verify task is registered
        assert normalize_results.name == "nethical_recon.worker.tasks.normalize_results"

    def test_generate_report_task(self):
        """Test generate_report task."""
        from nethical_recon.worker.tasks import generate_report

        # Verify task is registered
        assert generate_report.name == "nethical_recon.worker.tasks.generate_report"
