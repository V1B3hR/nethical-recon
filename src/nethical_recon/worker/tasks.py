"""Celery tasks for scan execution."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from celery import chain, group

from nethical_recon.adapters.nmap_adapter import NmapAdapter
from nethical_recon.core.models import (
    Finding,
    JobStatus,
    Target,
    ToolRun,
    ToolStatus,
)
from nethical_recon.core.parsers.nmap_parser import NmapParser
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import (
    EvidenceRepository,
    FindingRepository,
    ScanJobRepository,
    TargetRepository,
    ToolRunRepository,
)
from nethical_recon.worker.celery_app import celery_app
from nethical_recon.worker.policy import get_policy_engine

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.run_scan_job")
def run_scan_job(self, job_id: str) -> dict[str, Any]:
    """
    Run a complete scan job.

    Args:
        job_id: UUID of the scan job

    Returns:
        Dictionary with job results
    """
    logger.info(f"Starting scan job {job_id}")
    job_uuid = UUID(job_id)
    db = init_database()

    try:
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            target_repo = TargetRepository(session)

            # Get job and target
            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            target = target_repo.get_by_id(job.target_id)
            if not target:
                raise ValueError(f"Target {job.target_id} not found")

            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            session.commit()

            # Validate with policy engine
            policy = get_policy_engine()
            is_valid, messages = policy.validate_scan(target.value, job.tools)

            if not is_valid:
                job.status = JobStatus.FAILED
                job.error_message = "Policy validation failed: " + "; ".join(messages)
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                logger.error(f"Job {job_id} failed policy validation: {messages}")
                return {"status": "failed", "error": job.error_message}

            logger.info(f"Policy validation passed for job {job_id}: {messages}")

            # Create tasks for each tool
            tool_tasks = []
            for tool in job.tools:
                run_id = uuid4()
                tool_tasks.append(
                    chain(
                        run_tool.s(str(job_uuid), tool, str(run_id), target.value),
                        normalize_results.s(str(run_id)),
                    )
                )

            # Execute tools in parallel (respecting concurrency limits)
            job_chain = group(tool_tasks) | finalize_job.s(str(job_uuid))
            job_chain.apply_async()

            logger.info(f"Submitted {len(tool_tasks)} tool tasks for job {job_id}")
            return {
                "status": "running",
                "job_id": str(job_uuid),
                "tools": job.tools,
                "target": target.value,
            }

    except Exception as e:
        logger.error(f"Error running scan job {job_id}: {e}", exc_info=True)
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            job = job_repo.get_by_id(job_uuid)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
        raise


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.run_tool")
def run_tool(self, job_id: str, tool_name: str, run_id: str, target: str) -> dict[str, Any]:
    """
    Run a single tool.

    Args:
        job_id: UUID of the scan job
        tool_name: Name of the tool to run
        run_id: UUID for this tool run
        target: Target to scan

    Returns:
        Dictionary with tool run results
    """
    logger.info(f"Running tool {tool_name} for job {job_id}, run {run_id}")
    job_uuid = UUID(job_id)
    run_uuid = UUID(run_id)
    db = init_database()

    try:
        # Only nmap is supported for now
        if tool_name.lower() != "nmap":
            raise ValueError(f"Unsupported tool: {tool_name}")

        # Run the tool
        adapter = NmapAdapter()
        tool_run = adapter.run(target, job_uuid, run_uuid)

        # Save tool run to database
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            tool_repo.create(tool_run)

            # Save evidence
            if tool_run.stdout:
                evidence_repo = EvidenceRepository(session)
                evidence = adapter.save_evidence(tool_run)
                if evidence:
                    evidence_repo.create(evidence)

            session.commit()

        logger.info(f"Tool {tool_name} completed for run {run_id}, status: {tool_run.status}")
        return {
            "status": tool_run.status.value,
            "run_id": str(run_uuid),
            "exit_code": tool_run.exit_code,
            "duration": tool_run.duration_seconds,
        }

    except Exception as e:
        logger.error(f"Error running tool {tool_name} for job {job_id}: {e}", exc_info=True)

        # Save failed run to database
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            failed_run = ToolRun(
                id=run_uuid,
                job_id=job_uuid,
                tool_name=tool_name,
                tool_version="unknown",
                command=f"{tool_name} {target}",
                status=ToolStatus.FAILED,
                stderr=str(e),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            tool_repo.create(failed_run)
            session.commit()

        raise


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.normalize_results")
def normalize_results(self, tool_result: dict[str, Any], run_id: str) -> dict[str, Any]:
    """
    Normalize tool results into findings.

    Args:
        tool_result: Result from run_tool task
        run_id: UUID of the tool run

    Returns:
        Dictionary with normalized findings count
    """
    logger.info(f"Normalizing results for run {run_id}")
    run_uuid = UUID(run_id)
    db = init_database()

    try:
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            # Get tool run
            tool_run = tool_repo.get_by_id(run_uuid)
            if not tool_run:
                raise ValueError(f"Tool run {run_id} not found")

            # Parse results based on tool
            findings: list[Finding] = []
            if tool_run.tool_name.lower() == "nmap" and tool_run.stdout:
                parser = NmapParser()
                findings = parser.parse(tool_run.stdout, run_uuid)

            # Save findings
            for finding in findings:
                finding_repo.create(finding)

            session.commit()

            logger.info(f"Normalized {len(findings)} findings for run {run_id}")
            return {
                "run_id": str(run_uuid),
                "findings_count": len(findings),
            }

    except Exception as e:
        logger.error(f"Error normalizing results for run {run_id}: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.finalize_job")
def finalize_job(self, results: list[Any], job_id: str) -> dict[str, Any]:
    """
    Finalize a scan job after all tools complete.

    Args:
        results: Results from all tool tasks
        job_id: UUID of the scan job

    Returns:
        Dictionary with final job status
    """
    logger.info(f"Finalizing job {job_id}")
    job_uuid = UUID(job_id)
    db = init_database()

    try:
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            # Get job
            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Check all tool runs
            tool_runs = tool_repo.get_by_job(job_uuid)
            all_completed = all(run.status in [ToolStatus.COMPLETED, ToolStatus.FAILED] for run in tool_runs)
            any_failed = any(run.status == ToolStatus.FAILED for run in tool_runs)

            # Count findings
            total_findings = 0
            for run in tool_runs:
                findings = finding_repo.get_by_run(run.id)
                total_findings += len(findings)

            # Update job status
            if all_completed:
                if any_failed:
                    job.status = JobStatus.COMPLETED  # Partial success
                else:
                    job.status = JobStatus.COMPLETED

                job.completed_at = datetime.now(timezone.utc)

            session.commit()

            logger.info(f"Job {job_id} finalized with {total_findings} findings")
            return {
                "job_id": str(job_uuid),
                "status": job.status.value,
                "findings": total_findings,
                "tool_runs": len(tool_runs),
            }

    except Exception as e:
        logger.error(f"Error finalizing job {job_id}: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.generate_report")
def generate_report(self, job_id: str, format: str = "json") -> dict[str, Any]:
    """
    Generate a report for a scan job.

    Args:
        job_id: UUID of the scan job
        format: Report format (json, markdown, html)

    Returns:
        Dictionary with report data
    """
    logger.info(f"Generating {format} report for job {job_id}")
    job_uuid = UUID(job_id)
    db = init_database()

    try:
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)
            target_repo = TargetRepository(session)

            # Get job and related data
            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            target = target_repo.get_by_id(job.target_id)
            tool_runs = tool_repo.get_by_job(job_uuid)

            # Collect all findings
            all_findings = []
            for run in tool_runs:
                findings = finding_repo.get_by_run(run.id)
                all_findings.extend(findings)

            # Generate report (simplified for now)
            report = {
                "job_id": str(job.id),
                "job_name": job.name,
                "target": target.value if target else "unknown",
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "tools": job.tools,
                "tool_runs": [
                    {
                        "tool": run.tool_name,
                        "status": run.status.value,
                        "duration": run.duration_seconds,
                    }
                    for run in tool_runs
                ],
                "findings": {
                    "total": len(all_findings),
                    "by_severity": {},
                },
            }

            # Count by severity
            for finding in all_findings:
                severity = finding.severity.value
                report["findings"]["by_severity"][severity] = report["findings"]["by_severity"].get(severity, 0) + 1

            logger.info(f"Generated report for job {job_id}")
            return report

    except Exception as e:
        logger.error(f"Error generating report for job {job_id}: {e}", exc_info=True)
        raise


# Scheduled tasks
@celery_app.task(bind=True, name="nethical_recon.worker.tasks.update_baselines")
def update_baselines(self) -> dict[str, Any]:
    """
    Update security baselines for monitored targets.

    This is a scheduled task that runs periodically.

    Returns:
        Dictionary with update results
    """
    logger.info("Starting baseline update")
    # TODO: Implement baseline update logic
    return {"status": "success", "message": "Baseline update not yet implemented"}


@celery_app.task(bind=True, name="nethical_recon.worker.tasks.cleanup_old_results")
def cleanup_old_results(self) -> dict[str, Any]:
    """
    Clean up old scan results and evidence.

    This is a scheduled task that runs periodically.

    Returns:
        Dictionary with cleanup results
    """
    logger.info("Starting cleanup of old results")
    db = init_database()

    try:
        # Delete results older than 30 days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

        with db.session() as session:
            # TODO: Implement cleanup logic
            # For now, just log
            logger.info(f"Would clean up results older than {cutoff_date}")

        return {"status": "success", "cutoff_date": cutoff_date.isoformat()}

    except Exception as e:
        logger.error(f"Error cleaning up old results: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
