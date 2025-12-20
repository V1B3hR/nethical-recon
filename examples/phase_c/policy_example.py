"""Example: Policy engine usage."""

from nethical_recon.worker.policy import PolicyEngine, RoEConfig


def main():
    """Demonstrate policy engine usage."""
    # Create custom RoE configuration
    config = RoEConfig(
        max_requests_per_second=5.0,
        max_concurrent_tools=3,
        max_concurrent_jobs=5,
        allowed_networks=["192.168.0.0/16", "10.0.0.0/8"],
        denied_networks=["192.168.100.0/24"],
        high_risk_tools=["metasploit", "sqlmap"],
        allowed_tools=["nmap", "nikto", "dirb", "whatweb"],
        require_explicit_auth_for_high_risk=True,
    )

    # Initialize policy engine
    engine = PolicyEngine(config)

    # Check if tools can run
    print("=== Tool Authorization ===")
    tools_to_check = ["nmap", "nikto", "metasploit", "sqlmap", "masscan"]
    for tool in tools_to_check:
        can_run = engine.can_run_tool(tool)
        status = "✓ ALLOWED" if can_run else "✗ DENIED"
        print(f"{tool}: {status}")

    # Check high-risk tool with explicit auth
    print("\n=== High-Risk Tool with Explicit Auth ===")
    can_run_with_auth = engine.can_run_tool("metasploit", explicit_auth=True)
    status = "✓ ALLOWED" if can_run_with_auth else "✗ DENIED"
    print(f"metasploit (with auth): {status}")

    # Check network restrictions
    print("\n=== Network Authorization ===")
    targets_to_check = ["192.168.1.1", "192.168.100.10", "10.10.10.10", "8.8.8.8", "example.com"]
    for target in targets_to_check:
        is_allowed = engine.is_network_allowed(target)
        status = "✓ ALLOWED" if is_allowed else "✗ DENIED"
        print(f"{target}: {status}")

    # Validate scan configuration
    print("\n=== Scan Configuration Validation ===")
    configs = [
        {"ports": list(range(100)), "threads": 5, "timeout": 1000},
        {"ports": list(range(2000)), "threads": 20, "timeout": 5000},
    ]

    for i, scan_config in enumerate(configs, 1):
        is_valid, errors = engine.validate_scan_config(scan_config)
        print(f"Config {i}: {'✓ VALID' if is_valid else '✗ INVALID'}")
        if errors:
            for error in errors:
                print(f"  - {error}")

    # Show current status
    print("\n=== Policy Engine Status ===")
    status = engine.get_status()
    print(f"Active tools: {status['active_tools']}/{status['max_concurrent_tools']}")
    print(f"Active jobs: {status['active_jobs']}/{status['max_concurrent_jobs']}")
    print(f"Max requests/sec: {status['max_requests_per_second']}")


if __name__ == "__main__":
    main()
