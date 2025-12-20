"""Scheduler for periodic scans and maintenance tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from nethical_recon.core.models import ScanJob, Target, TargetScope
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
from nethical_recon.worker.tasks import run_scan_job

logger = logging.getLogger(__name__)


class ScanScheduler:
    """Scheduler for periodic scans and maintenance."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.db = init_database()

    def start(self) -> None:
        """Start the scheduler."""
        logger.info("Starting scan scheduler")
        self.scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        logger.info("Shutting down scan scheduler")
        self.scheduler.shutdown(wait=wait)

    def schedule_periodic_scan(
        self,
        target_value: str,
        tools: list[str],
        schedule: str,
        name: str | None = None,
        description: str | None = None,
    ) -> str:
        """Schedule a periodic scan.

        Args:
            target_value: Target to scan (IP, domain, CIDR)
            tools: List of tools to use
            schedule: Cron schedule string (e.g., "0 */6 * * *" for every 6 hours)
            name: Optional name for the scheduled job
            description: Optional description

        Returns:
            Job ID of the scheduled job
        """
        name = name or f"Periodic scan of {target_value}"

        def scan_job():
            """Execute the scan."""
            try:
                with self.db.session() as session:
                    target_repo = TargetRepository(session)
                    job_repo = ScanJobRepository(session)

                    # Get or create target
                    target = target_repo.get_by_value(target_value)
                    if not target:
                        # Determine target type (simplified)
                        from nethical_recon.core.models import TargetType

                        target = Target(
                            value=target_value,
                            type=TargetType.DOMAIN,  # Could be improved with better detection
                            scope=TargetScope.IN_SCOPE,
                        )
                        target = target_repo.create(target)
                        session.commit()

                    # Create job
                    job = ScanJob(
                        target_id=target.id,
                        name=name,
                        description=description or f"Scheduled scan: {schedule}",
                        tools=tools,
                    )
                    job = job_repo.create(job)
                    session.commit()

                    logger.info(f"Created scheduled job {job.id} for target {target_value}")

                    # Submit to worker queue
                    run_scan_job.delay(str(job.id))
                    logger.info(f"Submitted scheduled job {job.id} to worker queue")

            except Exception as e:
                logger.error(f"Error in scheduled scan job: {e}", exc_info=True)

        # Schedule using cron trigger
        trigger = CronTrigger.from_crontab(schedule, timezone="UTC")
        job_id = self.scheduler.add_job(
            scan_job,
            trigger=trigger,
            id=f"periodic_scan_{target_value}_{datetime.now(timezone.utc).timestamp()}",
            name=name,
            replace_existing=False,
        ).id

        logger.info(f"Scheduled periodic scan {job_id}: {target_value} with schedule {schedule}")
        return job_id

    def schedule_interval_scan(
        self,
        target_value: str,
        tools: list[str],
        interval_hours: int,
        name: str | None = None,
        description: str | None = None,
    ) -> str:
        """Schedule a scan at fixed intervals.

        Args:
            target_value: Target to scan
            tools: List of tools to use
            interval_hours: Interval in hours
            name: Optional name for the scheduled job
            description: Optional description

        Returns:
            Job ID of the scheduled job
        """
        name = name or f"Interval scan of {target_value}"

        def scan_job():
            """Execute the scan."""
            try:
                with self.db.session() as session:
                    target_repo = TargetRepository(session)
                    job_repo = ScanJobRepository(session)

                    # Get or create target
                    target = target_repo.get_by_value(target_value)
                    if not target:
                        from nethical_recon.core.models import TargetType

                        target = Target(
                            value=target_value,
                            type=TargetType.DOMAIN,
                            scope=TargetScope.IN_SCOPE,
                        )
                        target = target_repo.create(target)
                        session.commit()

                    # Create job
                    job = ScanJob(
                        target_id=target.id,
                        name=name,
                        description=description or f"Interval scan: every {interval_hours}h",
                        tools=tools,
                    )
                    job = job_repo.create(job)
                    session.commit()

                    # Submit to worker queue
                    run_scan_job.delay(str(job.id))
                    logger.info(f"Submitted interval job {job.id} to worker queue")

            except Exception as e:
                logger.error(f"Error in interval scan job: {e}", exc_info=True)

        # Schedule using interval trigger
        trigger = IntervalTrigger(hours=interval_hours, timezone="UTC")
        job_id = self.scheduler.add_job(
            scan_job,
            trigger=trigger,
            id=f"interval_scan_{target_value}_{datetime.now(timezone.utc).timestamp()}",
            name=name,
            replace_existing=False,
        ).id

        logger.info(f"Scheduled interval scan {job_id}: {target_value} every {interval_hours}h")
        return job_id

    def schedule_baseline_update(self, interval_hours: int = 24) -> str:
        """Schedule periodic baseline updates.

        Args:
            interval_hours: Update interval in hours (default: 24)

        Returns:
            Job ID of the scheduled job
        """

        def update_baseline():
            """Update baseline data."""
            try:
                logger.info("Updating baseline data")
                # Placeholder for baseline update logic
                # This would analyze recent scans and update baseline metrics
                logger.info("Baseline update completed")
            except Exception as e:
                logger.error(f"Error updating baseline: {e}", exc_info=True)

        trigger = IntervalTrigger(hours=interval_hours, timezone="UTC")
        job_id = self.scheduler.add_job(
            update_baseline,
            trigger=trigger,
            id="baseline_update",
            name="Baseline Update",
            replace_existing=True,
        ).id

        logger.info(f"Scheduled baseline updates every {interval_hours}h")
        return job_id

    def list_scheduled_jobs(self) -> list[dict[str, Any]]:
        """List all scheduled jobs.

        Returns:
            List of scheduled job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def remove_scheduled_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: ID of the job to remove

        Returns:
            True if job was removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False


# Global scheduler instance
_scheduler: ScanScheduler | None = None


def get_scheduler() -> ScanScheduler:
    """Get the global scheduler instance.

    Returns:
        Scheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = ScanScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler(wait: bool = True) -> None:
    """Shutdown the global scheduler.

    Args:
        wait: Whether to wait for running jobs
    """
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=wait)
        _scheduler = None
        logger.info("Scheduler shutdown")
