"""Celery tasks for asynchronous scan execution."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from celery import Task

from nethical_recon.core.models import JobStatus, ToolStatus
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import (
    FindingRepository,
    ScanJobRepository,
    ToolRunRepository,
)
from nethical_recon.worker.celery_app import celery_app
from nethical_recon.worker.policy import PolicyEngine

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task that handles database connections."""

    _db = None

    @property
    def db(self):
        """Get or create database connection."""
        if self._db is None:
            self._db = init_database()
        return self._db


@celery_app.task(base=DatabaseTask, bind=True, name="nethical_recon.worker.tasks.run_scan_job")
def run_scan_job(self: DatabaseTask, job_id: str) -> dict[str, Any]:
    """
    Execute a complete scan job by running all configured tools.

    Args:
        job_id: UUID of the scan job to execute

    Returns:
        Dictionary with job results summary
    """
    job_uuid = UUID(job_id)
    logger.info(f"Starting scan job {job_id}")

    try:
        with self.db.session() as session:
            job_repo = ScanJobRepository(session)
            job = job_repo.get_by_id(job_uuid)

            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job_repo.update(job)
            session.commit()

            logger.info(f"Job {job_id}: Running {len(job.tools)} tools")

            # Run each tool
            tool_results = []
            for tool_name in job.tools:
                try:
                    logger.info(f"Job {job_id}: Starting tool {tool_name}")
                    result = run_tool.apply_async(
                        args=[tool_name, job_id],
                        queue="nethical",
                    )
                    tool_results.append({"tool": tool_name, "task_id": result.id})
                except Exception as e:
                    logger.error(f"Job {job_id}: Failed to start tool {tool_name}: {e}")
                    tool_results.append({"tool": tool_name, "error": str(e)})

            # Wait for all tools to complete (in production, use Celery groups)
            # For now, we mark as completed immediately
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job_repo.update(job)
            session.commit()

            logger.info(f"Job {job_id}: Completed with {len(tool_results)} tools")

            return {
                "job_id": job_id,
                "status": "completed",
                "tools": tool_results,
            }

    except Exception as e:
        logger.error(f"Job {job_id}: Failed with error: {e}")
        try:
            with self.db.session() as session:
                job_repo = ScanJobRepository(session)
                job = job_repo.get_by_id(job_uuid)
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = str(e)
                    job_repo.update(job)
                    session.commit()
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")

        raise


@celery_app.task(base=DatabaseTask, bind=True, name="nethical_recon.worker.tasks.run_tool")
def run_tool(self: DatabaseTask, tool_name: str, job_id: str) -> dict[str, Any]:
    """
    Execute a single tool as part of a scan job.

    Args:
        tool_name: Name of the tool to run (e.g., "nmap", "nikto")
        job_id: UUID of the parent scan job

    Returns:
        Dictionary with tool execution results
    """
    from nethical_recon.core.models import ToolRun

    job_uuid = UUID(job_id)
    logger.info(f"Starting tool {tool_name} for job {job_id}")

    # Check policy before running
    policy = PolicyEngine()
    if not policy.can_run_tool(tool_name):
        raise ValueError(f"Tool {tool_name} is not authorized by policy")

    try:
        with self.db.session() as session:
            tool_repo = ToolRunRepository(session)

            # Create tool run record
            tool_run = ToolRun(
                job_id=job_uuid,
                tool_name=tool_name,
                tool_version="1.0.0",  # TODO: Get actual version
                command="",  # TODO: Build actual command
                status=ToolStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            tool_run = tool_repo.create(tool_run)
            session.commit()

            logger.info(f"Tool run {tool_run.id} created for {tool_name}")

            # TODO: Implement actual tool execution
            # For Phase C, we create the structure without actual tool execution
            # Actual tool execution will be added in follow-up work

            # Simulate successful execution
            tool_run.status = ToolStatus.COMPLETED
            tool_run.completed_at = datetime.now(timezone.utc)
            tool_run.exit_code = 0
            tool_run.stdout = f"{tool_name} executed successfully (placeholder)"
            tool_repo.update(tool_run)
            session.commit()

            logger.info(f"Tool run {tool_run.id} completed")

            # Normalize results
            normalize_results.apply_async(
                args=[str(tool_run.id)],
                queue="nethical",
            )

            return {
                "tool": tool_name,
                "run_id": str(tool_run.id),
                "status": "completed",
            }

    except Exception as e:
        logger.error(f"Tool {tool_name} failed for job {job_id}: {e}")
        raise


@celery_app.task(base=DatabaseTask, bind=True, name="nethical_recon.worker.tasks.normalize_results")
def normalize_results(self: DatabaseTask, run_id: str) -> dict[str, Any]:
    """
    Normalize tool output to standard Finding format.

    Args:
        run_id: UUID of the tool run to normalize

    Returns:
        Dictionary with normalization results
    """
    run_uuid = UUID(run_id)
    logger.info(f"Normalizing results for run {run_id}")

    try:
        with self.db.session() as session:
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            tool_run = tool_repo.get_by_id(run_uuid)
            if not tool_run:
                raise ValueError(f"Tool run {run_id} not found")

            # TODO: Implement actual parser selection and execution
            # For Phase C, we create the structure without actual parsing
            # Actual parsing will be enhanced in follow-up work

            findings_count = 0
            logger.info(f"Normalized {findings_count} findings from run {run_id}")

            return {
                "run_id": run_id,
                "findings_count": findings_count,
            }

    except Exception as e:
        logger.error(f"Failed to normalize results for run {run_id}: {e}")
        raise


@celery_app.task(base=DatabaseTask, bind=True, name="nethical_recon.worker.tasks.generate_report")
def generate_report(self: DatabaseTask, job_id: str, format: str = "json") -> dict[str, Any]:
    """
    Generate a report for a completed scan job.

    Args:
        job_id: UUID of the scan job
        format: Report format (json, html, pdf)

    Returns:
        Dictionary with report generation results
    """
    job_uuid = UUID(job_id)
    logger.info(f"Generating {format} report for job {job_id}")

    try:
        with self.db.session() as session:
            job_repo = ScanJobRepository(session)
            finding_repo = FindingRepository(session)
            tool_repo = ToolRunRepository(session)

            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Get all tool runs for this job
            tool_runs = tool_repo.get_by_job(job_uuid)

            # Get all findings
            all_findings = []
            for run in tool_runs:
                findings = finding_repo.get_by_run(run.id)
                all_findings.extend(findings)

            # TODO: Implement actual report generation
            # For Phase C, we create the structure without actual report generation
            # Actual report generation will be enhanced in follow-up work

            logger.info(f"Generated report for job {job_id} with {len(all_findings)} findings")

            return {
                "job_id": job_id,
                "format": format,
                "findings_count": len(all_findings),
                "tools_count": len(tool_runs),
            }

    except Exception as e:
        logger.error(f"Failed to generate report for job {job_id}: {e}")
        raise
