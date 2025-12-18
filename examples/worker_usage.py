#!/usr/bin/env python
"""Example usage of Nethical Recon worker and scheduler.

This script demonstrates:
1. Creating targets
2. Submitting scan jobs
3. Scheduling recurring scans
4. Checking job status
5. Policy configuration
"""

from datetime import datetime
from uuid import uuid4

from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
from nethical_recon.worker.policy import PolicyEngine, RulesOfEngagement
from nethical_recon.worker.scheduler import ScanScheduler
from nethical_recon.worker.tasks import run_scan_job


def example_1_create_target():
    """Example 1: Create a target in the database."""
    print("\n=== Example 1: Create Target ===")

    db = init_database()

    with db.session() as session:
        target_repo = TargetRepository(session)

        # Create a target
        target = Target(
            value="example.com",
            type=TargetType.DOMAIN,
            scope=TargetScope.IN_SCOPE,
            tags=["production", "web"],
        )

        # Save to database
        target = target_repo.create(target)
        session.commit()

        print(f"Created target: {target.id}")
        print(f"  Value: {target.value}")
        print(f"  Type: {target.type.value}")
        print(f"  Scope: {target.scope.value}")

        return target


def example_2_submit_job(target: Target):
    """Example 2: Submit a scan job to the worker queue."""
    print("\n=== Example 2: Submit Scan Job ===")

    db = init_database()

    with db.session() as session:
        job_repo = ScanJobRepository(session)

        # Create scan job
        job = ScanJob(
            target_id=target.id,
            name="Example Scan",
            description="Demonstration of job submission",
            tools=["nmap"],
        )

        # Save to database
        job = job_repo.create(job)
        session.commit()

        print(f"Created job: {job.id}")
        print(f"  Name: {job.name}")
        print(f"  Target: {target.value}")
        print(f"  Tools: {', '.join(job.tools)}")

        # Submit to worker queue
        task = run_scan_job.delay(str(job.id))

        print(f"\nSubmitted to worker queue")
        print(f"  Task ID: {task.id}")
        print(f"  State: {task.state}")

        return job


def example_3_schedule_recurring_scan(target: Target):
    """Example 3: Schedule a recurring scan."""
    print("\n=== Example 3: Schedule Recurring Scan ===")

    scheduler = ScanScheduler()

    # Schedule scan every 24 hours
    schedule_name = scheduler.schedule_recurring_scan(
        target_id=target.id,
        tools=["nmap"],
        interval_hours=24.0,
        name=f"daily_scan_{target.value}",
    )

    print(f"Scheduled recurring scan: {schedule_name}")
    print(f"  Target: {target.value}")
    print(f"  Interval: 24 hours")
    print(f"  Tools: nmap")


def example_4_schedule_cron_scan(target: Target):
    """Example 4: Schedule scan with cron expression."""
    print("\n=== Example 4: Schedule Cron Scan ===")

    scheduler = ScanScheduler()

    # Schedule scan every Monday at 2 AM
    schedule_name = scheduler.schedule_cron_scan(
        target_id=target.id,
        tools=["nmap", "nikto"],
        cron_expression={"hour": 2, "minute": 0, "day_of_week": "mon"},
        name=f"weekly_scan_{target.value}",
    )

    print(f"Scheduled cron scan: {schedule_name}")
    print(f"  Target: {target.value}")
    print(f"  Schedule: Every Monday at 2:00 AM")
    print(f"  Tools: nmap, nikto")


def example_5_check_policy():
    """Example 5: Check policy engine configuration."""
    print("\n=== Example 5: Policy Engine ===")

    policy = PolicyEngine()

    # Check if target is allowed
    is_allowed, reason = policy.is_target_allowed("192.168.1.10")
    print(f"\nTarget 192.168.1.10: {'ALLOWED' if is_allowed else 'BLOCKED'}")
    print(f"  Reason: {reason}")

    # Check if tool can start
    can_start, reason = policy.can_start_tool("nmap")
    print(f"\nTool 'nmap': {'CAN START' if can_start else 'BLOCKED'}")
    print(f"  Reason: {reason}")

    # Check rate limit
    can_proceed, reason = policy.check_rate_limit("test")
    print(f"\nRate limit: {'OK' if can_proceed else 'EXCEEDED'}")
    print(f"  Reason: {reason}")

    # Get statistics
    stats = policy.get_stats()
    print("\nPolicy Statistics:")
    print(f"  Active Jobs: {stats['active_jobs']}/{stats['max_parallel_jobs']}")
    print(f"  Active Tools: {stats['active_tools']}/{stats['max_parallel_tools']}")
    print(f"  Rate Limit: {stats['rate_limit_rps']} req/sec")


def example_6_custom_policy():
    """Example 6: Create custom policy configuration."""
    print("\n=== Example 6: Custom Policy Configuration ===")

    # Create custom rules of engagement
    roe = RulesOfEngagement(
        rate_limit={"requests_per_second": 2.0, "burst_size": 10},
        concurrency={"max_parallel_jobs": 10, "max_parallel_tools": 5, "max_parallel_tools_per_job": 3},
        network={
            "allowlist": ["192.168.0.0/16", "10.0.0.0/8"],
            "denylist": ["127.0.0.0/8"],
            "require_explicit_approval": True,
        },
        tools={"high_risk_tools": ["sqlmap", "metasploit"], "require_approval_for_high_risk": True},
    )

    print("Custom Policy Configuration:")
    print(f"  Rate Limit: {roe.rate_limit.requests_per_second} req/sec")
    print(f"  Burst Size: {roe.rate_limit.burst_size}")
    print(f"  Max Parallel Jobs: {roe.concurrency.max_parallel_jobs}")
    print(f"  Max Parallel Tools: {roe.concurrency.max_parallel_tools}")
    print(f"  Allowlist: {', '.join(roe.network.allowlist)}")
    print(f"  High-Risk Tools: {', '.join(roe.tools.high_risk_tools)}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Nethical Recon Worker Examples")
    print("=" * 60)

    # Example 1: Create target
    target = example_1_create_target()

    # Example 2: Submit job
    job = example_2_submit_job(target)

    # Example 3: Schedule recurring scan
    example_3_schedule_recurring_scan(target)

    # Example 4: Schedule cron scan
    example_4_schedule_cron_scan(target)

    # Example 5: Check policy
    example_5_check_policy()

    # Example 6: Custom policy
    example_6_custom_policy()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start Redis: docker-compose up -d redis")
    print("2. Start worker: nethical-worker start")
    print("3. Start scheduler: nethical-worker beat")
    print(f"4. Check job status: nethical job status {job.id}")


if __name__ == "__main__":
    main()
