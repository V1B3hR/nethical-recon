"""Scheduler module for periodic and recurring scans."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from celery.schedules import crontab, schedule

from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository

from .celery_app import app
from .tasks import run_scan_job

logger = logging.getLogger(__name__)


class ScanScheduler:
    """Scheduler for managing recurring scans and baseline updates."""

    def __init__(self):
        """Initialize the scheduler."""
        self.db = init_database()

    def schedule_recurring_scan(
        self,
        target_id: UUID,
        tools: list[str],
        interval_hours: float,
        name: str | None = None,
    ) -> str:
        """Schedule a recurring scan for a target.

        Args:
            target_id: UUID of the target to scan
            tools: List of tools to run
            interval_hours: Interval between scans in hours
            name: Optional name for the scheduled task

        Returns:
            Schedule entry name
        """
        schedule_name = name or f"recurring_scan_{target_id}"

        # Add to Celery Beat schedule dynamically
        app.conf.beat_schedule[schedule_name] = {
            "task": "nethical_recon.worker.tasks.run_scan_job",
            "schedule": timedelta(hours=interval_hours),
            "args": (str(target_id),),
        }

        logger.info(f"Scheduled recurring scan '{schedule_name}' every {interval_hours} hours")
        return schedule_name

    def schedule_cron_scan(
        self,
        target_id: UUID,
        tools: list[str],
        cron_expression: dict[str, Any],
        name: str | None = None,
    ) -> str:
        """Schedule a scan with cron-like expression.

        Args:
            target_id: UUID of the target to scan
            tools: List of tools to run
            cron_expression: Dictionary with cron fields (minute, hour, day_of_week, etc.)
            name: Optional name for the scheduled task

        Returns:
            Schedule entry name

        Example:
            schedule_cron_scan(
                target_id,
                ["nmap", "nikto"],
                {"hour": 2, "minute": 0, "day_of_week": "mon,wed,fri"},
                "weekly_scan"
            )
        """
        schedule_name = name or f"cron_scan_{target_id}"

        # Create crontab schedule
        cron_schedule = crontab(**cron_expression)

        app.conf.beat_schedule[schedule_name] = {
            "task": "nethical_recon.worker.tasks.run_scan_job",
            "schedule": cron_schedule,
            "args": (str(target_id),),
        }

        logger.info(f"Scheduled cron scan '{schedule_name}' with expression {cron_expression}")
        return schedule_name

    def create_baseline_scan(self, target: Target, tools: list[str]) -> ScanJob:
        """Create a baseline scan job for a target.

        Args:
            target: Target to scan
            tools: List of tools to run

        Returns:
            Created scan job
        """
        with self.db.session() as session:
            target_repo = TargetRepository(session)
            job_repo = ScanJobRepository(session)

            # Ensure target is saved
            existing_target = target_repo.get_by_value(target.value)
            if existing_target:
                target = existing_target
            else:
                target = target_repo.create(target)

            # Create baseline job
            job = ScanJob(
                target_id=target.id,
                name=f"Baseline scan for {target.value}",
                description="Automated baseline scan for change detection",
                tools=tools,
            )
            job = job_repo.create(job)
            session.commit()

            logger.info(f"Created baseline scan job {job.id} for target {target.value}")
            return job

    def schedule_baseline_updates(self, targets: list[Target], interval_hours: float = 24.0) -> list[str]:
        """Schedule baseline updates for multiple targets.

        Args:
            targets: List of targets to monitor
            interval_hours: Interval between baseline scans (default: 24 hours)

        Returns:
            List of schedule entry names
        """
        schedule_names = []

        for target in targets:
            # Create a job for this target
            job = self.create_baseline_scan(target, tools=["nmap"])

            # Schedule it
            schedule_name = self.schedule_recurring_scan(
                target_id=target.id,
                tools=["nmap"],
                interval_hours=interval_hours,
                name=f"baseline_{target.value}",
            )
            schedule_names.append(schedule_name)

        logger.info(f"Scheduled {len(schedule_names)} baseline updates")
        return schedule_names

    def unschedule_task(self, schedule_name: str) -> bool:
        """Remove a scheduled task.

        Args:
            schedule_name: Name of the schedule entry to remove

        Returns:
            True if removed, False if not found
        """
        if schedule_name in app.conf.beat_schedule:
            del app.conf.beat_schedule[schedule_name]
            logger.info(f"Unscheduled task '{schedule_name}'")
            return True
        else:
            logger.warning(f"Schedule entry '{schedule_name}' not found")
            return False

    def list_schedules(self) -> dict[str, Any]:
        """List all scheduled tasks.

        Returns:
            Dictionary of schedule entries
        """
        return dict(app.conf.beat_schedule)


# CLI integration
def schedule_scan_from_cli(
    target: str,
    tools: list[str],
    interval_hours: float | None = None,
    cron: dict | None = None,
    name: str | None = None,
) -> str:
    """Schedule a scan from CLI parameters.

    Args:
        target: Target string (domain, IP, CIDR)
        tools: List of tool names
        interval_hours: Interval for recurring scans
        cron: Cron expression dictionary
        name: Optional schedule name

    Returns:
        Schedule entry name
    """
    # Determine target type
    target_type = TargetType.DOMAIN  # Default
    try:
        import ipaddress

        ip = ipaddress.ip_address(target)
        if isinstance(ip, ipaddress.IPv4Address):
            target_type = TargetType.IPV4
        elif isinstance(ip, ipaddress.IPv6Address):
            target_type = TargetType.IPV6
    except ValueError:
        pass

    # Create target
    target_obj = Target(
        value=target,
        type=target_type,
        scope=TargetScope.IN_SCOPE,
    )

    # Save target and schedule
    scheduler = ScanScheduler()
    with scheduler.db.session() as session:
        target_repo = TargetRepository(session)
        existing = target_repo.get_by_value(target)
        if existing:
            target_obj = existing
        else:
            target_obj = target_repo.create(target_obj)
        session.commit()

    # Schedule based on parameters
    if interval_hours:
        return scheduler.schedule_recurring_scan(target_obj.id, tools, interval_hours, name)
    elif cron:
        return scheduler.schedule_cron_scan(target_obj.id, tools, cron, name)
    else:
        raise ValueError("Either interval_hours or cron must be provided")
