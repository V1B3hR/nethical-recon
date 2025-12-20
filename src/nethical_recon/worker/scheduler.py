"""Scheduler for periodic and scheduled scan jobs."""

from __future__ import annotations

from collections.abc import Callable
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler. triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class ScanScheduler:
    """
    Scheduler for managing periodic and scheduled scans.
    
    Wraps APScheduler for scan job scheduling.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler.
        
        Args:
            wait:  Wait for jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            self.logger. info("Scheduler shutdown")

    def schedule_periodic_scan(
        self,
        scan_job: Callable,
        target_value: str,
        cron_expression: str,
        name: str | None = None,
        **kwargs,
    ) -> str:
        """
        Schedule a periodic scan using cron expression.
        
        Args:
            scan_job:  Callable to execute
            target_value: Target to scan
            cron_expression:  Cron expression (e.g., '0 */6 * * *' for every 6 hours)
            name: Optional job name
            **kwargs: Additional arguments for scan_job
            
        Returns: 
            Job ID
            
        Example:
            >>> scheduler.schedule_periodic_scan(
            ...     scan_job=run_scan,
            ...     target_value="example.com",
            ...     cron_expression="0 0 * * *",  # Daily at midnight
            ...     name="Daily scan of example.com"
            ... )
        """
        # Parse cron expression
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{cron_expression}'. "
                "Expected format: 'minute hour day month day_of_week'"
            )

        minute, hour, day, month, day_of_week = parts

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        job = self.scheduler.add_job(
            scan_job,
            trigger=trigger,
            id=f"periodic_scan_{target_value}_{datetime.now(datetime.UTC).timestamp()}",
            name=name,
            replace_existing=False,
            kwargs={"target": target_value, **kwargs},
        )

        self.logger.info(
            f"Scheduled periodic scan for {target_value} with cron '{cron_expression}' (Job ID: {job.id})"
        )
        return job.id

    def schedule_interval_scan(
        self,
        scan_job: Callable,
        target_value: str,
        interval_seconds: int,
        name: str | None = None,
        **kwargs,
    ) -> str:
        """
        Schedule a scan to run at fixed intervals.
        
        Args:
            scan_job: Callable to execute
            target_value:  Target to scan
            interval_seconds: Interval in seconds
            name: Optional job name
            **kwargs: Additional arguments for scan_job
            
        Returns:
            Job ID
            
        Example:
            >>> scheduler. schedule_interval_scan(
            ...     scan_job=run_scan,
            ...     target_value="192.168.1.1",
            ...     interval_seconds=3600,  # Every hour
            ...     name="Hourly scan of 192.168.1.1"
            ... )
        """
        trigger = IntervalTrigger(seconds=interval_seconds)

        job = self.scheduler.add_job(
            scan_job,
            trigger=trigger,
            id=f"interval_scan_{target_value}_{datetime.now(datetime.UTC).timestamp()}",
            name=name,
            replace_existing=False,
            kwargs={"target": target_value, **kwargs},
        )

        self.logger.info(
            f"Scheduled interval scan for {target_value} every {interval_seconds}s (Job ID: {job. id})"
        )
        return job.id

    def schedule_one_time_scan(
        self,
        scan_job: Callable,
        target_value: str,
        run_date: datetime,
        name: str | None = None,
        **kwargs,
    ) -> str:
        """
        Schedule a one-time scan at a specific datetime.
        
        Args:
            scan_job: Callable to execute
            target_value: Target to scan
            run_date:  When to run the scan
            name:  Optional job name
            **kwargs:  Additional arguments for scan_job
            
        Returns:
            Job ID
        """
        job = self.scheduler.add_job(
            scan_job,
            trigger="date",
            run_date=run_date,
            id=f"onetime_scan_{target_value}_{run_date.timestamp()}",
            name=name,
            kwargs={"target": target_value, **kwargs},
        )

        self.logger.info(f"Scheduled one-time scan for {target_value} at {run_date} (Job ID: {job.id})")
        return job.id

    def remove_job(self, job_id:  str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: ID of job to remove
            
        Returns: 
            True if removed successfully
        """
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Removed job {job_id}")
            return True
        except Exception as e: 
            self.logger.error(f"Failed to remove job {job_id}:  {e}")
            return False

    def get_jobs(self) -> list:
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    def pause_job(self, job_id: str):
        """Pause a scheduled job."""
        self.scheduler.pause_job(job_id)
        self.logger.info(f"Paused job {job_id}")

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        self.scheduler. resume_job(job_id)
        self.logger.info(f"Resumed job {job_id}")
