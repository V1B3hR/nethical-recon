"""APScheduler integration for periodic scan scheduling."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
from nethical_recon.worker.tasks import run_scan_job

logger = logging.getLogger(__name__)


class ScanScheduler:
    """
    Scheduler for periodic scans and baseline updates.

    Uses APScheduler to manage recurring scan jobs.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.db = init_database()
        logger.info("Scan scheduler initialized")

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scan scheduler started")
        else:
            logger.warning("Scan scheduler already running")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scan scheduler shutdown")
        else:
            logger.warning("Scan scheduler not running")

    def schedule_periodic_scan(
        self,
        target: str,
        tools: list[str],
        interval_hours: int,
        name: str | None = None,
        job_id: str | None = None,
    ) -> str:
        """
        Schedule a periodic scan that runs at regular intervals.

        Args:
            target: Target to scan (domain, IP, or CIDR)
            tools: List of tools to run
            interval_hours: Interval in hours between scans
            name: Optional job name
            job_id: Optional custom job ID

        Returns:
            Scheduler job ID
        """
        name = name or f"Periodic scan: {target}"

        def run_periodic_scan():
            """Execute the periodic scan."""
            try:
                logger.info(f"Starting periodic scan for {target}")
                job_uuid = self._create_scan_job(target, tools, name)
                run_scan_job.delay(str(job_uuid))
                logger.info(f"Periodic scan job created: {job_uuid}")
            except Exception as e:
                logger.error(f"Failed to create periodic scan: {e}")

        trigger = IntervalTrigger(hours=interval_hours, timezone="UTC")
        scheduler_job = self.scheduler.add_job(
            run_periodic_scan,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=True,
        )

        logger.info(
            f"Scheduled periodic scan for {target} every {interval_hours} hours (job: {scheduler_job.id})"
        )
        return scheduler_job.id

    def schedule_cron_scan(
        self,
        target: str,
        tools: list[str],
        cron_expression: str,
        name: str | None = None,
        job_id: str | None = None,
    ) -> str:
        """
        Schedule a scan using a cron expression.

        Args:
            target: Target to scan
            tools: List of tools to run
            cron_expression: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
            name: Optional job name
            job_id: Optional custom job ID

        Returns:
            Scheduler job ID
        """
        name = name or f"Cron scan: {target}"

        def run_cron_scan():
            """Execute the cron scan."""
            try:
                logger.info(f"Starting cron scan for {target}")
                job_uuid = self._create_scan_job(target, tools, name)
                run_scan_job.delay(str(job_uuid))
                logger.info(f"Cron scan job created: {job_uuid}")
            except Exception as e:
                logger.error(f"Failed to create cron scan: {e}")

        # Parse cron expression (format: minute hour day month day_of_week)
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="UTC",
        )

        scheduler_job = self.scheduler.add_job(
            run_cron_scan,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=True,
        )

        logger.info(f"Scheduled cron scan for {target} with expression '{cron_expression}' (job: {scheduler_job.id})")
        return scheduler_job.id

    def schedule_baseline_update(
        self,
        target_ids: list[str] | None = None,
        interval_hours: int = 24,
    ) -> str:
        """
        Schedule periodic baseline updates for targets.

        Args:
            target_ids: List of target UUIDs to update (None for all in-scope targets)
            interval_hours: Interval in hours between updates

        Returns:
            Scheduler job ID
        """

        def update_baselines():
            """Execute baseline updates."""
            try:
                logger.info("Starting baseline update")
                with self.db.session() as session:
                    target_repo = TargetRepository(session)

                    if target_ids:
                        targets = [target_repo.get_by_id(UUID(tid)) for tid in target_ids]
                        targets = [t for t in targets if t]  # Filter out None values
                    else:
                        # Get all in-scope targets
                        # TODO: Add method to repository to get by scope
                        targets = []

                    logger.info(f"Updating baselines for {len(targets)} targets")
                    # TODO: Implement actual baseline update logic
                    # For Phase C, we create the structure

            except Exception as e:
                logger.error(f"Failed to update baselines: {e}")

        trigger = IntervalTrigger(hours=interval_hours, timezone="UTC")
        job = self.scheduler.add_job(
            update_baselines,
            trigger=trigger,
            id="baseline_update",
            name="Baseline Update",
            replace_existing=True,
        )

        logger.info(f"Scheduled baseline updates every {interval_hours} hours")
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: ID of the job to remove

        Returns:
            True if job was removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        """
        List all scheduled jobs.

        Returns:
            List of job information dictionaries
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

    def _create_scan_job(self, target: str, tools: list[str], name: str) -> UUID:
        """
        Create a scan job in the database.

        Args:
            target: Target to scan
            tools: List of tools to run
            name: Job name

        Returns:
            UUID of created job
        """
        with self.db.session() as session:
            target_repo = TargetRepository(session)
            job_repo = ScanJobRepository(session)

            # Get or create target
            existing_target = target_repo.get_by_value(target)
            if existing_target:
                target_obj = existing_target
            else:
                # Determine target type
                import ipaddress

                try:
                    ipaddress.ip_address(target)
                    target_type = TargetType.IP
                except ValueError:
                    target_type = TargetType.DOMAIN

                target_obj = Target(
                    value=target,
                    type=target_type,
                    scope=TargetScope.IN_SCOPE,
                )
                target_obj = target_repo.create(target_obj)

            # Create scan job
            job = ScanJob(
                target_id=target_obj.id,
                name=name,
                tools=tools,
                created_by="scheduler",
            )
            job = job_repo.create(job)
            session.commit()

            logger.info(f"Created scan job {job.id} for target {target}")
            return job.id
