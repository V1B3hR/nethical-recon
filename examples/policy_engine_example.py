#!/usr/bin/env python3
"""Example: Using the Policy Engine for ethical scanning.

This example demonstrates how to use the Policy Engine to enforce
Rules of Engagement (RoE) for security scanning operations.
"""

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


def example_default_policy():
    """Demonstrate default safe policy."""
    print("=" * 60)
    print("Example 1: Default Safe Policy")
    print("=" * 60)

    # Create default policy
    from nethical_recon.core.policy.models import create_default_policy

    policy = create_default_policy()
    engine = PolicyEngine(policy)

    print(f"\nPolicy: {policy.name}")
    print(f"Risk Level: {policy.risk_level.value}")
    print(f"\nRate Limit: {policy.rate_limit.requests_per_second} req/s")
    print(f"Max Parallel Scans: {policy.concurrency.max_parallel_scans}")
    print(f"Require Consent: {policy.network.require_explicit_consent}")

    # Try to validate some targets
    print("\n--- Target Validation ---")

    targets = [
        "192.0.2.10",  # Public IP (allowed)
        "10.0.0.1",  # Private IP (denied by default)
        "example.com",  # Domain (allowed)
    ]

    for target in targets:
        try:
            engine.validate_target(target)
            print(f"✓ {target} - ALLOWED")
        except PolicyViolationError as e:
            print(f"✗ {target} - DENIED: {e}")


def example_custom_policy():
    """Demonstrate custom policy for authorized testing."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Authorized Testing Policy")
    print("=" * 60)

    # Create custom policy for bug bounty program
    policy = Policy(
        name="bug_bounty",
        description="Policy for authorized bug bounty testing",
        risk_level=RiskLevel.MEDIUM,
        rate_limit=RateLimitPolicy(
            enabled=True,
            requests_per_second=20.0,  # Higher rate
            burst_size=50,  # Larger burst
        ),
        concurrency=ConcurrencyPolicy(
            enabled=True,
            max_parallel_scans=10,  # More parallel scans
            max_parallel_tools=5,  # More tools per scan
            max_workers=8,
        ),
        network=NetworkPolicy(
            enabled=True,
            allow_networks=["192.0.2.0/24", "198.51.100.0/24"],  # Authorized ranges
            deny_networks=[],  # No denials for authorized testing
            require_explicit_consent=True,
        ),
        tool=ToolPolicy(
            enabled=True,
            allowed_tools=["nmap", "nikto", "dirb", "nuclei"],  # Approved tools
            high_risk_tools=["sqlmap"],  # Still block dangerous tools
            require_approval_for_high_risk=True,
        ),
    )

    engine = PolicyEngine(policy)

    print(f"\nPolicy: {policy.name}")
    print(f"Risk Level: {policy.risk_level.value}")
    print(f"Rate Limit: {policy.rate_limit.requests_per_second} req/s")
    print(f"Max Parallel Scans: {policy.concurrency.max_parallel_scans}")

    # Try tools
    print("\n--- Tool Validation ---")
    tools = ["nmap", "nikto", "sqlmap", "metasploit"]

    for tool in tools:
        try:
            engine.validate_tool(tool)
            print(f"✓ {tool} - ALLOWED")
        except PolicyViolationError as e:
            print(f"✗ {tool} - DENIED: {e}")


def example_concurrency_control():
    """Demonstrate concurrency control."""
    print("\n" + "=" * 60)
    print("Example 3: Concurrency Control")
    print("=" * 60)

    policy = Policy(
        name="limited",
        concurrency=ConcurrencyPolicy(
            enabled=True,
            max_parallel_scans=2,  # Only 2 concurrent scans
            max_parallel_tools=2,  # Only 2 tools per scan
        ),
    )

    engine = PolicyEngine(policy)

    print(f"\nMax Parallel Scans: {policy.concurrency.max_parallel_scans}")
    print(f"Max Parallel Tools: {policy.concurrency.max_parallel_tools}")

    # Try to acquire scan slots
    print("\n--- Scan Slot Acquisition ---")
    for i in range(1, 4):
        try:
            engine.acquire_scan_slot(f"job_{i}")
            print(f"✓ Job {i} - Slot acquired")
        except PolicyViolationError as e:
            print(f"✗ Job {i} - DENIED: {e}")

    # Release and try again
    print("\n--- After releasing slot 1 ---")
    engine.release_scan_slot("job_1")
    try:
        engine.acquire_scan_slot("job_4")
        print("✓ Job 4 - Slot acquired")
    except PolicyViolationError as e:
        print(f"✗ Job 4 - DENIED: {e}")

    # Show statistics
    stats = engine.get_stats()
    print(f"\n--- Current Statistics ---")
    print(f"Active scans: {stats['active_scans']}")
    print(f"Total active tools: {stats['total_active_tools']}")


def example_rate_limiting():
    """Demonstrate rate limiting."""
    print("\n" + "=" * 60)
    print("Example 4: Rate Limiting")
    print("=" * 60)

    policy = Policy(
        name="rate_limited",
        rate_limit=RateLimitPolicy(
            enabled=True,
            requests_per_second=2.0,  # Very low for demo
            burst_size=3,  # Small burst
        ),
    )

    engine = PolicyEngine(policy)

    print(f"\nRate Limit: {policy.rate_limit.requests_per_second} req/s")
    print(f"Burst Size: {policy.rate_limit.burst_size}")

    # Try to acquire tokens
    print("\n--- Token Acquisition ---")
    for i in range(1, 6):
        try:
            engine.acquire_rate_limit()
            print(f"✓ Request {i} - Token acquired")
        except PolicyViolationError as e:
            print(f"✗ Request {i} - DENIED: {e}")

    print("\n(In real usage, tokens refill over time)")


def example_aggressive_policy():
    """Demonstrate aggressive policy for penetration testing."""
    print("\n" + "=" * 60)
    print("Example 5: Aggressive Policy (Authorized Pen Testing)")
    print("=" * 60)

    from nethical_recon.core.policy.models import create_aggressive_policy

    policy = create_aggressive_policy()
    engine = PolicyEngine(policy)

    print(f"\nPolicy: {policy.name}")
    print(f"Risk Level: {policy.risk_level.value}")
    print(f"Rate Limit: {policy.rate_limit.requests_per_second} req/s")
    print(f"Max Parallel Scans: {policy.concurrency.max_parallel_scans}")
    print(f"Max Parallel Tools: {policy.concurrency.max_parallel_tools}")
    print(f"Timeout: {policy.tool.timeout_seconds}s")

    print(
        "\n⚠️  WARNING: This policy should ONLY be used for authorized penetration testing"
    )
    print("    with explicit written permission from the target organization.")


if __name__ == "__main__":
    print("\n🔒 Nethical Recon - Policy Engine Examples")
    print("Demonstrating ethical security scanning with enforced policies\n")

    example_default_policy()
    example_custom_policy()
    example_concurrency_control()
    example_rate_limiting()
    example_aggressive_policy()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Always use appropriate policies for your use case")
    print("2. Default policy is safe for most scenarios")
    print("3. Custom policies allow fine-grained control")
    print("4. Rate limiting prevents accidental overload")
    print("5. Concurrency control prevents resource exhaustion")
    print("6. Always get explicit authorization before scanning")
    print("\n💡 See WORKER_DEPLOYMENT.md for more information")
