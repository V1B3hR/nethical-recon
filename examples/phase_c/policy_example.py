"""
Example: Using the Policy Engine

This example demonstrates how to use the Rules of Engagement (RoE)
policy engine to enforce security and operational policies.
"""

from nethical_recon.core.policy import (
    ConcurrencyPolicy,
    NetworkPolicy,
    PolicyEngine,
    RateLimitPolicy,
    RiskLevel,
    RulesOfEngagement,
    ToolPolicy,
)


def example_basic_policy():
    """Create a basic policy engine with default settings."""
    print("=== Basic Policy Engine ===")

    # Create with defaults
    engine = PolicyEngine()

    # Check if target is allowed
    allowed, reason = engine.check_target_allowed("192.168.1.1")
    print(f"Target 192.168.1.1: {allowed} - {reason}")

    # Check if tool is allowed
    allowed, reason = engine.check_tool_allowed("nmap")
    print(f"Tool nmap: {allowed} - {reason}")

    # High-risk tools are blocked by default
    allowed, reason = engine.check_tool_allowed("sqlmap")
    print(f"Tool sqlmap: {allowed} - {reason}")

    print()


def example_custom_policy():
    """Create a custom policy with specific rules."""
    print("=== Custom Policy ===")

    # Create custom RoE
    roe = RulesOfEngagement(
        name="strict-policy",
        description="Strict policy for production scanning",
        rate_limit=RateLimitPolicy(
            requests_per_second=0.5,  # Very conservative
            burst_size=3,
        ),
        concurrency=ConcurrencyPolicy(
            max_parallel_tools=2,
            max_parallel_jobs=3,
        ),
        network=NetworkPolicy(
            allowed_networks=["10.0.0.0/8", "192.168.0.0/16"],
            denied_networks=["10.10.10.0/24"],
        ),
        tool_policies={
            "nmap": ToolPolicy(
                tool_name="nmap",
                risk_level=RiskLevel.LOW,
                enabled=True,
                max_duration_seconds=300,
            ),
            "sqlmap": ToolPolicy(
                tool_name="sqlmap",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                enabled=True,
            ),
        },
    )

    engine = PolicyEngine(roe)

    # Test network restrictions
    test_targets = ["192.168.1.1", "10.10.10.5", "8.8.8.8"]
    for target in test_targets:
        allowed, reason = engine.check_target_allowed(target)
        print(f"Target {target:15s}: {allowed:5s} - {reason}")

    print()


def example_validate_job():
    """Validate a complete job before execution."""
    print("=== Job Validation ===")

    # Create policy with network restrictions
    roe = RulesOfEngagement(
        network=NetworkPolicy(allowed_networks=["192.168.0.0/16"]),
        tool_policies={
            "sqlmap": ToolPolicy(tool_name="sqlmap", enabled=True),
        },
    )
    engine = PolicyEngine(roe)

    # Valid job
    try:
        result = engine.validate_job("192.168.1.1", ["nmap", "nikto"])
        print("✓ Job validation passed:")
        print(f"  Target allowed: {result['target_allowed']}")
        print(f"  Tools allowed: {list(result['tools_allowed'].keys())}")
    except Exception as e:
        print(f"✗ Job validation failed: {e}")

    # Invalid job (target not in allowed network)
    try:
        result = engine.validate_job("8.8.8.8", ["nmap"])
        print("✓ Job validation passed")
    except Exception as e:
        print(f"✗ Job validation failed: {e}")

    # Invalid job (high-risk tool without policy)
    try:
        result = engine.validate_job("192.168.1.1", ["metasploit"])
        print("✓ Job validation passed")
    except Exception as e:
        print(f"✗ Job validation failed: {e}")

    print()


def example_rate_limiting():
    """Demonstrate rate limiting."""
    print("=== Rate Limiting ===")

    roe = RulesOfEngagement(
        rate_limit=RateLimitPolicy(
            requests_per_second=2.0,
            burst_size=5,
        )
    )
    engine = PolicyEngine(roe)

    # Try to acquire tokens
    print("Acquiring tokens (burst=5):")
    for i in range(7):
        acquired, wait_time = engine.acquire_rate_limit()
        if acquired:
            print(f"  Request {i+1}: ✓ Acquired")
        else:
            print(f"  Request {i+1}: ✗ Rate limited (wait {wait_time:.2f}s)")

    print()


def example_concurrency_control():
    """Demonstrate concurrency limits."""
    print("=== Concurrency Control ===")

    roe = RulesOfEngagement(
        concurrency=ConcurrencyPolicy(
            max_parallel_jobs=2,
            max_parallel_tools=3,
        )
    )
    engine = PolicyEngine(roe)

    # Register jobs
    print("Starting jobs:")
    for i in range(3):
        job_id = f"job-{i+1}"
        allowed, reason = engine.check_concurrency_limits(job_id=job_id)
        if allowed:
            engine.register_job_start(job_id)
            print(f"  Job {job_id}: ✓ Started")
        else:
            print(f"  Job {job_id}: ✗ {reason}")

    # Clean up
    engine.register_job_end("job-1")
    engine.register_job_end("job-2")

    print()


def example_policy_from_file():
    """Load policy from a JSON file."""
    print("=== Policy from File ===")

    import json
    import tempfile
    from pathlib import Path

    # Create example policy file
    policy_config = {
        "name": "production",
        "description": "Production scanning policy",
        "rate_limit": {"requests_per_second": 1.0, "burst_size": 5, "enabled": True},
        "concurrency": {"max_parallel_tools": 3, "max_parallel_jobs": 5, "enabled": True},
        "network": {
            "allowed_networks": ["10.0.0.0/8", "192.168.0.0/16"],
            "denied_networks": [],
        },
        "tool_policies": {
            "nmap": {
                "tool_name": "nmap",
                "risk_level": "medium",
                "requires_approval": False,
                "enabled": True,
            }
        },
        "high_risk_tools": ["sqlmap", "metasploit"],
        "authorized_only": True,
        "audit_logging_enabled": True,
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(policy_config, f, indent=2)
        temp_path = f.name

    try:
        # Load from file
        engine = PolicyEngine.from_file(temp_path)
        print(f"✓ Loaded policy '{engine.roe.name}' from file")
        print(f"  Description: {engine.roe.description}")
        print(f"  Rate limit: {engine.roe.rate_limit.requests_per_second} req/s")
        print(f"  Max parallel tools: {engine.roe.concurrency.max_parallel_tools}")
        print(f"  Allowed networks: {engine.roe.network.allowed_networks}")
    finally:
        # Clean up
        Path(temp_path).unlink()

    print()


if __name__ == "__main__":
    print("Nethical Recon - Policy Engine Examples\n")
    print("=" * 50)
    print()

    example_basic_policy()
    example_custom_policy()
    example_validate_job()
    example_rate_limiting()
    example_concurrency_control()
    example_policy_from_file()

    print("=" * 50)
    print("\nAll examples completed!")
