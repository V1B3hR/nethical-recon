"""Celery tasks for asynchronous scan execution and processing."""

from __future__ import annotations

import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from celery import Task

from nethical_recon.core.models import (
    JobStatus,
    ScanJob,
    Severity,
    Target,
    ToolRun,
    ToolStatus,
)
from nethical_recon. core.parsers. nmap_parser import NmapParser
from nethical_recon.core. storage import init_database
from nethical_recon.core.storage.repository import (
    EvidenceRepository,
    FindingRepository,
    ScanJobRepository,
    TargetRepository,
    ToolRunRepository,
)

from . celery_app import app
from .policy import get_policy_engine

logger = logging.getLogger(__name__)


class PolicyAwareTask(Task):
    """Base task class with policy enforcement."""

    def before_start(self, task_id, args, kwargs):
        """Called before task execution."""
        logger.info(f"Task {self.name} starting with ID {task_id}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {self.name} failed:  {exc}", exc_info=einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {self.name} completed successfully with ID {task_id}")


@app.task(bind=True, base=PolicyAwareTask, name="nethical_recon.worker.tasks.run_scan_job")
def run_scan_job(self, job_id:  str) -> dict:
    """Run a complete scan job with all configured tools.

    Args:
        job_id: UUID of the scan job to execute

    Returns:
        Dictionary with job results
    """
    policy = get_policy_engine()
    job_uuid = UUID(job_id)

    # Check if job can start
    can_start, reason = policy.can_start_job(job_id)
    if not can_start:
        logger.warning(f"Cannot start job {job_id}: {reason}")
        return {"status":  "blocked", "reason": reason}

    try:
        policy.start_job(job_id)
        db = init_database()

        with db.session() as session:
            job_repo = ScanJobRepository(session)
            target_repo = TargetRepository(session)

            # Load job
            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Load target
            target = target_repo.get_by_id(job.target_id)
            if not target:
                raise ValueError(f"Target {job.target_id} not found")

            # Check if target is allowed
            is_allowed, reason = policy.is_target_allowed(target. value)
            if not is_allowed:
                job. status = JobStatus.FAILED
                job.error_message = f"Target blocked by policy: {reason}"
                job_repo.update(job)
                session.commit()
                return {"status": "blocked", "reason": reason}

            # Update job status
            job.status = JobStatus.RUNNING
            job. started_at = datetime.now(UTC)
            job_repo.update(job)
            session.commit()

            logger. info(f"Starting job {job_id} for target {target.value}")

            # Execute each tool
            tool_tasks = []
            for tool_name in job.tools:
                # Submit tool as subtask
                task = run_tool. delay(tool_name, str(job. id), target.value)
                tool_tasks.append(task. id)
                logger.info(f"Submitted tool {tool_name} for job {job_id}:  task {task.id}")

            # Wait for all tools to complete (simplified - in production use Celery groups/chains)
            # For now, just return the task IDs
            return {
                "status": "running",
                "job_id":  job_id,
                "tool_tasks": tool_tasks,
                "tools":  job.tools,
            }

    except Exception as e:
        logger.error(f"Error running job {job_id}: {e}", exc_info=True)
        # Update job status
        try:
            with db.session() as session:
                job_repo = ScanJobRepository(session)
                job = job_repo.get_by_id(job_uuid)
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.now(UTC)
                    job. error_message = str(e)
                    job_repo.update(job)
                    session. commit()
        except Exception as update_error:
            logger.error(f"Error updating job status: {update_error}")

        return {"status": "error", "error": str(e)}
    finally:
        policy.finish_job(job_id)


@app.task(bind=True, base=PolicyAwareTask, name="nethical_recon.worker.tasks.run_tool")
def run_tool(self, tool_name: str, job_id: str, target:  str) -> dict:
    """Run a single security tool against a target.

    Args:
        tool_name: Name of the tool to run
        job_id:  UUID of the parent scan job
        target: Target to scan

    Returns:
        Dictionary with tool run results
    """
    policy = get_policy_engine()
    job_uuid = UUID(job_id)

    # Check rate limit
    can_proceed, reason = policy.check_rate_limit(f"tool:{tool_name}")
    if not can_proceed:
        logger. warning(f"Rate limit hit for {tool_name}: {reason}")
        time.sleep(2)  # Brief backoff

    # Check if tool can start
    can_start, reason = policy.can_start_tool(tool_name, job_id)
    if not can_start:
        logger.warning(f"Cannot start tool {tool_name}: {reason}")
        return {"status": "blocked", "reason": reason}

    try:
        policy.start_tool(tool_name, job_id)
        db = init_database()

        with db.session() as session:
            tool_repo = ToolRunRepository(session)

            # Create tool run record
            tool_run = ToolRun(
                job_id=job_uuid,
                tool_name=tool_name,
                tool_version="unknown",  # Will be detected
                command="",  # Will be set below
                status=ToolStatus. RUNNING,
                started_at=datetime.now(UTC),
            )

            # Build command based on tool
            if tool_name == "nmap":
                command = _build_nmap_command(target)
            elif tool_name == "nikto":
                command = _build_nikto_command(target)
            else:
                raise ValueError(f"Unsupported tool: {tool_name}")

            tool_run.command = command
            tool_run = tool_repo.create(tool_run)
            session.commit()

            logger.info(f"Running {tool_name} for job {job_id}:  {command}")

            # Execute command
            start_time = time.time()
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                )
                duration = time.time() - start_time

                # Update tool run
                tool_run.stdout = result.stdout
                tool_run.stderr = result.stderr
                tool_run.exit_code = result.returncode
                tool_run.status = ToolStatus.COMPLETED if result.returncode == 0 else ToolStatus.FAILED
                tool_run.completed_at = datetime.now(UTC)
                tool_run.duration_seconds = duration

                tool_repo.update(tool_run)
                session.commit()

                logger.info(f"Tool {tool_name} completed for job {job_id} in {duration:.2f}s")

                # Parse and normalize results
                if result. returncode == 0 and tool_run.stdout:
                    normalize_task = normalize_results. delay(str(tool_run.id))
                    logger.info(f"Submitted normalization task:  {normalize_task.id}")

                return {
                    "status": "completed",
                    "tool_run_id": str(tool_run.id),
                    "exit_code": result.returncode,
                    "duration": duration,
                }

            except subprocess.TimeoutExpired:
                tool_run.status = ToolStatus.FAILED
                tool_run.completed_at = datetime.now(UTC)
                tool_run.error_message = "Command timeout"
                tool_repo.update(tool_run)
                session.commit()
                return {"status": "timeout", "tool_run_id": str(tool_run.id)}

    except Exception as e:
        logger.error(f"Error running tool {tool_name}: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        policy.finish_tool(tool_name, job_id)


@app.task(bind=True, base=PolicyAwareTask, name="nethical_recon.worker.tasks.normalize_results")
def normalize_results(self, tool_run_id:  str) -> dict:
    """Parse and normalize tool results into findings.

    Args:
        tool_run_id: UUID of the tool run to normalize

    Returns:
        Dictionary with normalization results
    """
    try:
        db = init_database()
        run_uuid = UUID(tool_run_id)

        with db.session() as session:
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            # Load tool run
            tool_run = tool_repo.get_by_id(run_uuid)
            if not tool_run:
                raise ValueError(f"Tool run {tool_run_id} not found")

            logger.info(f"Normalizing results for {tool_run. tool_name} run {tool_run_id}")

            # Parse based on tool type
            findings = []
            if tool_run.tool_name == "nmap":
                parser = NmapParser()
                if parser.can_parse(tool_run.stdout):
                    findings = parser. parse(tool_run.stdout, run_id=tool_run. id)
            # Add other parsers here
            else:
                logger.warning(f"No parser available for tool {tool_run.tool_name}")

            # Save findings
            for finding in findings:
                finding_repo.create(finding)

            session.commit()

            logger.info(f"Created {len(findings)} findings from {tool_run.tool_name}")

            # Count by severity
            severity_counts = {}
            for finding in findings:
                severity_counts[finding.severity.value] = severity_counts.get(finding.severity.value, 0) + 1

            return {
                "status": "completed",
                "tool_run_id": tool_run_id,
                "findings_count": len(findings),
                "severity_counts": severity_counts,
            }

    except Exception as e:
        logger.error(f"Error normalizing results: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@app.task(bind=True, base=PolicyAwareTask, name="nethical_recon. worker.tasks.generate_report")
def generate_report(self, job_id: str, format: str = "markdown") -> dict:
    """Generate a report for a completed scan job.

    Args:
        job_id: UUID of the scan job
        format: Report format (markdown, json, html, pdf)

    Returns:
        Dictionary with report generation results
    """
    try:
        db = init_database()
        job_uuid = UUID(job_id)

        with db.session() as session:
            job_repo = ScanJobRepository(session)
            finding_repo = FindingRepository(session)
            tool_repo = ToolRunRepository(session)

            # Load job
            job = job_repo.get_by_id(job_uuid)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Get all findings for this job
            tool_runs = tool_repo.get_by_job(job_uuid)
            all_findings = []
            for run in tool_runs:
                findings = finding_repo.get_by_run(run. id)
                all_findings. extend(findings)

            logger.info(f"Generating {format} report for job {job_id} with {len(all_findings)} findings")

            # Generate report (simplified for now)
            if format == "markdown":
                report_content = _generate_markdown_report(job, tool_runs, all_findings)
            else: 
                raise ValueError(f"Unsupported report format: {format}")

            # Save report to file
            report_dir = Path("reports")
            report_dir.mkdir(exist_ok=True)
            report_path = report_dir / f"job_{job_id}. md"
            report_path.write_text(report_content)

            logger.info(f"Report saved to {report_path}")

            return {
                "status": "completed",
                "job_id": job_id,
                "report_path": str(report_path),
                "findings_count": len(all_findings),
            }

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@app.task(name="nethical_recon.worker.tasks.update_baseline")
def update_baseline() -> dict:
    """Periodic task to update baseline data.

    This is called by Celery Beat on a schedule.
    """
    logger.info("Running baseline update task")
    # TODO: Implement baseline update logic
    return {"status": "completed", "message": "Baseline update completed"}


# Helper functions


def _build_nmap_command(target:  str) -> str:
    """Build nmap command for scanning."""
    # Safe defaults:  top 1000 ports, version detection, no aggressive scanning
    return f"nmap -sV -T3 --top-ports 1000 -oX - {target}"


def _build_nikto_command(target: str) -> str:
    """Build nikto command for web scanning."""
    return f"nikto -h {target} -Format xml -output -"


def _generate_markdown_report(job, tool_runs, findings) -> str:
    """Generate a markdown report."""
    lines = [
        f"# Scan Report: {job.name}",
        f"\n## Summary",
        f"- **Job ID**: {job.id}",
        f"- **Status**:  {job.status.value}",
        f"- **Created**: {job.created_at}",
        f"- **Started**: {job.started_at}",
        f"- **Completed**: {job.completed_at}",
        f"- **Total Findings**: {len(findings)}",
        f"\n## Tool Runs",
    ]

    for run in tool_runs:
        lines.append(f"\n### {run.tool_name} ({run.tool_version})")
        lines.append(f"- Status: {run.status.value}")
        lines.append(f"- Duration: {run.duration_seconds:. 2f}s" if run.duration_seconds else "- Duration: N/A")
        lines.append(f"- Exit Code: {run.exit_code}")

    lines.append("\n## Findings by Severity")

    # Group findings by severity
    by_severity = {}
    for finding in findings:
        severity = finding.severity.value
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity]. append(finding)

    # Sort by severity (critical first)
    severity_order = ["critical", "high", "medium", "low", "info"]
    for severity in severity_order:
        if severity in by_severity:
            lines.append(f"\n### {severity.upper()} ({len(by_severity[severity])})")
            for finding in by_severity[severity]:
                lines. append(f"\n#### {finding.title}")
                if finding.description:
                    lines.append(f"{finding.description}")
                if finding.port:
                    lines.append(f"- Port: {finding. port}")
                if finding.service:
                    lines.append(f"- Service: {finding. service}")
                if finding.cve:
                    lines.append(f"- CVE: {', '.join(finding.cve)}")

    return "\n".join(lines)
