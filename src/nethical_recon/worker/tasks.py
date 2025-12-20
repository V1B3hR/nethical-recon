"""Celery tasks for scanning operations."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from celery import Task

from nethical_recon.core.models import (
    Finding,
    JobStatus,
    ToolStatus,
    ScanJob,
    Severity,
    ToolRun,
)
from nethical_recon.core.parsers.nmap_parser import NmapParser
from nethical_recon.core.policy import PolicyEngine, RulesOfEngagement
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import (
    FindingRepository,
    ScanJobRepository,
    TargetRepository,
    ToolRunRepository,
)

from .celery_app import app

logger = logging.getLogger(__name__)

# Initialize policy engine (can be configured via file)
POLICY_FILE = os.getenv("NETHICAL_POLICY_FILE")
if POLICY_FILE and Path(POLICY_FILE).exists():
    policy_engine = PolicyEngine.from_file(POLICY_FILE)
    logger.info(f"Loaded policy from {POLICY_FILE}")
else:
    policy_engine = PolicyEngine()
    logger.info("Using default policy")


class ScanTask(Task):
    """Base task for scanning operations."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        logger.error(f"Exception info: {einfo}")


@app.task(base=ScanTask, bind=True, name="nethical_recon.worker.tasks.run_scan_job")
def run_scan_job(self, job_id: str) -> dict:
    """Execute a complete scan job.

    Args:
        job_id: UUID of the scan job

    Returns:
        Job execution result
    """
    job_uuid = UUID(job_id)
    db = init_database()

    try:
        # Register job start with policy engine
        policy_engine.register_job_start(job_id)

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

            logger.info(f"Starting job {job_id} for target {target.value}")

            # Validate with policy engine
            try:
                validation = policy_engine.validate_job(target.value, job.tools)
                logger.info(f"Policy validation passed: {validation}")
            except Exception as e:
                # Update job status to failed
                job.status = JobStatus.FAILED
                job.error_message = f"Policy violation: {e}"
                job.completed_at = datetime.now(timezone.utc)
                job_repo.update(job)
                session.commit()
                raise

            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job_repo.update(job)
            session.commit()

        # Execute each tool
        tool_tasks = []
        for tool_name in job.tools:
            # Check rate limiting
            acquired, wait_time = policy_engine.acquire_rate_limit()
            if not acquired:
                logger.info(f"Rate limit hit, waiting {wait_time:.2f}s")
                self.retry(countdown=wait_time)
                return {"status": "rate_limited", "retry_after": wait_time}

            # Submit tool task
            task = run_tool.delay(job_id, tool_name, target.value)
            tool_tasks.append({"tool": tool_name, "task_id": task.id})
            logger.info(f"Submitted tool task: {tool_name} ({task.id})")

        # Wait for all tools to complete (in a production setup, use chord/group)
        # For now, we'll mark the job as completed in a separate task or when checking status

        result = {
            "status": "submitted",
            "job_id": job_id,
            "tools": tool_tasks,
            "target": target.value,
        }

        logger.info(f"Job {job_id} tools submitted: {len(tool_tasks)}")
        return result

    except Exception as e:
        logger.error(f"Error in job {job_id}: {e}", exc_info=True)
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            job = job_repo.get_by_id(job_uuid)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                job_repo.update(job)
                session.commit()
        raise
    finally:
        # Unregister job
        policy_engine.register_job_end(job_id)


@app.task(base=ScanTask, bind=True, name="nethical_recon.worker.tasks.run_tool")
def run_tool(self, job_id: str, tool_name: str, target: str) -> dict:
    """Execute a specific tool.

    Args:
        job_id: UUID of the scan job
        tool_name: Name of the tool to run
        target: Target to scan

    Returns:
        Tool execution result
    """
    db = init_database()

    try:
        with db.session() as session:
            tool_repo = ToolRunRepository(session)

            # Create tool run record
            tool_run = ToolRun(
                job_id=UUID(job_id),
                tool_name=tool_name,
                target=target,
                status=ToolStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            tool_run = tool_repo.create(tool_run)
            session.commit()
            tool_run_id = tool_run.id

            logger.info(f"Starting tool run {tool_run_id}: {tool_name} on {target}")

            # Register with policy engine
            policy_engine.register_tool_start(str(tool_run_id), tool_name)

        # Build command based on tool
        if tool_name == "nmap":
            # Basic nmap scan - can be enhanced with more options
            cmd = ["nmap", "-sV", "-oX", "-", target]
            tool_version = _get_tool_version("nmap")
        elif tool_name == "nikto":
            cmd = ["nikto", "-h", target, "-Format", "txt"]
            tool_version = _get_tool_version("nikto")
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")

        # Execute tool
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Update tool run with results
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            tool_run = tool_repo.get_by_id(tool_run_id)

            tool_run.command = " ".join(cmd)
            tool_run.tool_version = tool_version
            tool_run.exit_code = result.returncode
            tool_run.stdout = result.stdout
            tool_run.stderr = result.stderr
            tool_run.completed_at = datetime.now(timezone.utc)
            tool_run.status = ToolStatus.COMPLETED if result.returncode == 0 else ToolStatus.FAILED

            # Calculate duration
            if tool_run.started_at and tool_run.completed_at:
                duration = (tool_run.completed_at - tool_run.started_at).total_seconds()
                tool_run.duration_seconds = duration

            tool_repo.update(tool_run)
            session.commit()

            logger.info(f"Tool run {tool_run_id} completed with exit code {result.returncode}")

        # If successful, normalize results
        if result.returncode == 0 and result.stdout:
            normalize_results.delay(str(tool_run_id))

        return {
            "status": "completed",
            "tool_run_id": str(tool_run_id),
            "exit_code": result.returncode,
            "stdout_length": len(result.stdout),
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Tool {tool_name} timed out")
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            tool_run = tool_repo.get_by_id(tool_run_id)
            if tool_run:
                tool_run.status = ToolStatus.FAILED
                tool_run.error_message = "Tool execution timed out"
                tool_run.completed_at = datetime.now(timezone.utc)
                tool_repo.update(tool_run)
                session.commit()
        raise
    except Exception as e:
        logger.error(f"Error running tool {tool_name}: {e}", exc_info=True)
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            tool_run = tool_repo.get_by_id(tool_run_id)
            if tool_run:
                tool_run.status = ToolStatus.FAILED
                tool_run.error_message = str(e)
                tool_run.completed_at = datetime.now(timezone.utc)
                tool_repo.update(tool_run)
                session.commit()
        raise
    finally:
        # Unregister tool
        policy_engine.register_tool_end(str(tool_run_id))


@app.task(base=ScanTask, name="nethical_recon.worker.tasks.normalize_results")
def normalize_results(tool_run_id: str) -> dict:
    """Parse and normalize tool output to findings.

    Args:
        tool_run_id: UUID of the tool run

    Returns:
        Normalization result
    """
    db = init_database()

    try:
        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            tool_run = tool_repo.get_by_id(UUID(tool_run_id))
            if not tool_run:
                raise ValueError(f"Tool run {tool_run_id} not found")

            logger.info(f"Normalizing results for tool run {tool_run_id}: {tool_run.tool_name}")

            # Parse based on tool
            findings: list[Finding] = []

            if tool_run.tool_name == "nmap" and tool_run.stdout:
                parser = NmapParser()
                if parser.can_parse(tool_run.stdout):
                    findings = parser.parse(tool_run.stdout, UUID(tool_run_id))
                    logger.info(f"Parsed {len(findings)} findings from nmap output")
            # Add more parsers here for other tools

            # Save findings
            for finding in findings:
                finding_repo.create(finding)

            session.commit()

            logger.info(f"Saved {len(findings)} findings for tool run {tool_run_id}")

            return {
                "status": "completed",
                "tool_run_id": tool_run_id,
                "findings_count": len(findings),
            }

    except Exception as e:
        logger.error(f"Error normalizing results for {tool_run_id}: {e}", exc_info=True)
        raise


@app.task(base=ScanTask, name="nethical_recon.worker.tasks.generate_report")
def generate_report(job_id: str, report_format: str = "json") -> dict:
    """Generate a report for a completed job.

    Args:
        job_id: UUID of the scan job
        report_format: Format for the report (json, markdown, html)

    Returns:
        Report generation result
    """
    db = init_database()

    try:
        with db.session() as session:
            job_repo = ScanJobRepository(session)
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            job = job_repo.get_by_id(UUID(job_id))
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Get all tool runs
            tool_runs = tool_repo.get_by_job(UUID(job_id))

            # Get all findings
            all_findings: list[Finding] = []
            for run in tool_runs:
                findings = finding_repo.get_by_run(run.id)
                all_findings.extend(findings)

            logger.info(f"Generating report for job {job_id}: {len(tool_runs)} runs, {len(all_findings)} findings")

            # Generate report based on format
            if report_format == "json":
                report = {
                    "job_id": str(job.id),
                    "job_name": job.name,
                    "target_id": str(job.target_id),
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "tool_runs": len(tool_runs),
                    "findings": {
                        "total": len(all_findings),
                        "by_severity": {},
                    },
                }

                # Count by severity
                for finding in all_findings:
                    severity = finding.severity.value
                    report["findings"]["by_severity"][severity] = (
                        report["findings"]["by_severity"].get(severity, 0) + 1
                    )

                return {"status": "completed", "report": report, "format": report_format}

            else:
                raise ValueError(f"Unsupported report format: {report_format}")

    except Exception as e:
        logger.error(f"Error generating report for job {job_id}: {e}", exc_info=True)
        raise


def _get_tool_version(tool_name: str) -> str:
    """Get version of a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool version string
    """
    try:
        if tool_name == "nmap":
            result = subprocess.run(["nmap", "--version"], capture_output=True, text=True, timeout=5)
            # Parse version from output
            for line in result.stdout.split("\n"):
                if "Nmap version" in line:
                    return line.split("Nmap version")[1].strip().split()[0]
        elif tool_name == "nikto":
            result = subprocess.run(["nikto", "-Version"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        return "unknown"
    except Exception:
        return "unknown"
