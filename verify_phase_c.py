#!/usr/bin/env python
"""Verification script for PHASE C implementation.

This script verifies that all Phase C components are properly installed
and functional.
"""

import sys


def check_imports():
    """Verify all modules can be imported."""
    print("=== Checking Imports ===")
    errors = []

    try:
        from nethical_recon.worker import celery_app
        print("✓ Worker celery_app module")
    except ImportError as e:
        errors.append(f"✗ Worker celery_app: {e}")

    try:
        from nethical_recon.worker import tasks
        print("✓ Worker tasks module")
    except ImportError as e:
        errors.append(f"✗ Worker tasks: {e}")

    try:
        from nethical_recon.worker import policy
        print("✓ Worker policy module")
    except ImportError as e:
        errors.append(f"✗ Worker policy: {e}")

    try:
        from nethical_recon.worker import scheduler
        print("✓ Worker scheduler module")
    except ImportError as e:
        errors.append(f"✗ Worker scheduler: {e}")

    try:
        from nethical_recon.worker import cli
        print("✓ Worker CLI module")
    except ImportError as e:
        errors.append(f"✗ Worker CLI: {e}")

    return errors


def check_dependencies():
    """Verify required dependencies are installed."""
    print("\n=== Checking Dependencies ===")
    errors = []

    try:
        import celery
        print(f"✓ Celery {celery.__version__}")
    except ImportError:
        errors.append("✗ Celery not installed")

    try:
        import redis
        print(f"✓ Redis {redis.__version__}")
    except ImportError:
        errors.append("✗ Redis not installed")

    try:
        import yaml
        print("✓ PyYAML")
    except ImportError:
        errors.append("✗ PyYAML not installed")

    return errors


def check_policy_engine():
    """Verify policy engine functionality."""
    print("\n=== Checking Policy Engine ===")
    errors = []

    try:
        from nethical_recon.worker.policy import PolicyEngine, RulesOfEngagement

        # Create policy engine
        policy = PolicyEngine()
        print("✓ Policy engine initialization")

        # Test job management
        can_start, reason = policy.can_start_job("test_job")
        if can_start:
            print("✓ Job management")
        else:
            errors.append(f"✗ Job management: {reason}")

        # Test tool management
        can_start, reason = policy.can_start_tool("nmap")
        if can_start:
            print("✓ Tool management")
        else:
            errors.append(f"✗ Tool management: {reason}")

        # Test rate limiting
        can_proceed, reason = policy.check_rate_limit("test")
        if can_proceed:
            print("✓ Rate limiting")
        else:
            errors.append(f"✗ Rate limiting: {reason}")

        # Test statistics
        stats = policy.get_stats()
        if "active_jobs" in stats:
            print("✓ Policy statistics")
        else:
            errors.append("✗ Policy statistics missing")

    except Exception as e:
        errors.append(f"✗ Policy engine error: {e}")

    return errors


def check_scheduler():
    """Verify scheduler functionality."""
    print("\n=== Checking Scheduler ===")
    errors = []

    try:
        from nethical_recon.worker.scheduler import ScanScheduler

        scheduler = ScanScheduler()
        print("✓ Scheduler initialization")

        # Check list_schedules method
        schedules = scheduler.list_schedules()
        print("✓ Schedule listing")

    except Exception as e:
        errors.append(f"✗ Scheduler error: {e}")

    return errors


def check_tasks():
    """Verify task definitions."""
    print("\n=== Checking Tasks ===")
    errors = []

    try:
        from nethical_recon.worker.tasks import (
            generate_report,
            normalize_results,
            run_scan_job,
            run_tool,
            update_baseline,
        )

        print("✓ run_scan_job task")
        print("✓ run_tool task")
        print("✓ normalize_results task")
        print("✓ generate_report task")
        print("✓ update_baseline task")

    except ImportError as e:
        errors.append(f"✗ Task import error: {e}")

    return errors


def check_cli():
    """Verify CLI commands."""
    print("\n=== Checking CLI ===")
    errors = []

    try:
        from nethical_recon.worker.cli import app

        commands = []
        for cmd in app.registered_commands:
            if hasattr(cmd, "callback") and cmd.callback:
                commands.append(cmd.callback.__name__)

        expected = ["start", "beat", "status", "active", "purge", "policy_stats"]
        for cmd in expected:
            if cmd in commands:
                print(f"✓ {cmd} command")
            else:
                errors.append(f"✗ {cmd} command missing")

    except Exception as e:
        errors.append(f"✗ CLI error: {e}")

    return errors


def check_configuration():
    """Verify configuration files exist."""
    print("\n=== Checking Configuration ===")
    errors = []

    from pathlib import Path

    files = [
        "policy.yaml.example",
        "docker-compose.yml",
        "PHASE_C_SUMMARY.md",
        "src/nethical_recon/worker/README.md",
        "examples/worker_usage.py",
    ]

    for file in files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            errors.append(f"✗ {file} missing")

    return errors


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("PHASE C VERIFICATION - Worker Queue + Scheduler + Policy Engine")
    print("=" * 70)

    all_errors = []

    all_errors.extend(check_imports())
    all_errors.extend(check_dependencies())
    all_errors.extend(check_policy_engine())
    all_errors.extend(check_scheduler())
    all_errors.extend(check_tasks())
    all_errors.extend(check_cli())
    all_errors.extend(check_configuration())

    print("\n" + "=" * 70)
    if not all_errors:
        print("✓ ALL CHECKS PASSED - PHASE C IMPLEMENTATION VERIFIED")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Start Redis: docker-compose up -d redis")
        print("2. Start worker: nethical-worker start")
        print("3. Start scheduler: nethical-worker beat")
        print("4. Submit a job: nethical job submit example.com --name 'Test' --tools nmap")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("=" * 70)
        print("\nErrors:")
        for error in all_errors:
            print(f"  {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
