"""Celery tasks for asynchronous job processing."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from uuid import UUID

from celery import Task

from nethical_recon.core.models import JobStatus, ToolRun, ToolStatus
from nethical_recon.core.policy import PolicyEngine, PolicyViolationError
from nethical_recon.core.storage import DatabaseConfig, init_database

from .celery_app import app


class DatabaseTask(Task):
    """Base task with database session management."""

    _db = None
    _policy_engine = None

    @property
    def database(self):
        """Get database instance."""
        if self._db is None:
            from nethical_recon.core.storage import DatabaseConfig

            self._db = init_database(DatabaseConfig(os.getenv("NETHICAL_DATABASE_URL", "sqlite:///nethical_recon.db")))
        return self._db

    @property
    def policy_engine(self):
        """Get policy engine instance."""
        if self._policy_engine is None:
            from nethical_recon.core.policy.models import create_default_policy

            self._policy_engine = PolicyEngine(create_default_policy())
        return self._policy_engine


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def run_scan_job(self, job_id: str) -> dict:
    """Execute a complete scan job.

    Args:
        job_id: UUID of the scan job

    Returns:
        Job execution summary
    """
    from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository

    job_uuid = UUID(job_id)

    with self.database.session() as session:
        job_repo = ScanJobRepository(session)
        target_repo = TargetRepository(session)

        # Get job and target
        job = job_repo.get_by_id(job_uuid)
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}

        target = target_repo.get_by_id(job.target_id)
        if not target:
            return {"status": "error", "message": f"Target {job.target_id} not found"}

        try:
            # Validate target with policy
            self.policy_engine.validate_target(target.value)

            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            session.commit()

            # Acquire scan slot after validation
            self.policy_engine.acquire_scan_slot(job_id)

            # Schedule tool runs
            tool_tasks = []
            for tool_name in job.tools:
                task = run_tool.delay(tool_name, job_id, str(target.id))
                tool_tasks.append(task.id)

            # Wait for all tools to complete (in production, use callbacks)
            # For now, we just return the task IDs
            return {
                "status": "running",
                "job_id": job_id,
                "target": target.value,
                "tool_tasks": tool_tasks,
            }

        except PolicyViolationError as e:
            job.status = JobStatus.FAILED
            job.error_message = f"Policy violation: {e}"
            job.completed_at = datetime.utcnow()
            session.commit()
            self.policy_engine.release_scan_slot(job_id)
            return {"status": "error", "message": str(e)}

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            session.commit()
            self.policy_engine.release_scan_slot(job_id)
            # Retry on failure
            raise self.retry(exc=e, countdown=60) from e


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def run_tool(self, tool_name: str, job_id: str, target_id: str) -> dict:
    """Execute a single tool run.

    Args:
        tool_name: Name of the tool to run
        job_id: UUID of the parent scan job
        target_id: UUID of the target

    Returns:
        Tool execution summary
    """
    from nethical_recon.core.storage.repository import TargetRepository, ToolRunRepository

    job_uuid = UUID(job_id)
    target_uuid = UUID(target_id)

    with self.database.session() as session:
        tool_repo = ToolRunRepository(session)
        target_repo = TargetRepository(session)

        target = target_repo.get_by_id(target_uuid)
        if not target:
            return {"status": "error", "message": f"Target {target_id} not found"}

        try:
            # Validate tool with policy
            self.policy_engine.validate_tool(tool_name)

            # Acquire tool slot
            self.policy_engine.acquire_tool_slot(job_id)

            # Acquire rate limit token
            self.policy_engine.acquire_rate_limit(f"tool:{tool_name}")

            # Get tool version and build command
            tool_version = _get_tool_version(tool_name)
            command = _build_tool_command(tool_name, target.value)

            # Create tool run record
            tool_run = ToolRun(
                job_id=job_uuid,
                tool_name=tool_name,
                tool_version=tool_version,
                command=command,
                status=ToolStatus.RUNNING,
                started_at=datetime.utcnow(),
            )

            db_tool_run = tool_repo.create(tool_run)
            session.commit()

            # Execute the tool
            start_time = time.time()
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.policy_engine.get_tool_timeout(),
            )
            duration = time.time() - start_time

            # Update tool run with results
            db_tool_run.status = ToolStatus.COMPLETED if result.returncode == 0 else ToolStatus.FAILED
            db_tool_run.exit_code = result.returncode
            db_tool_run.stdout = result.stdout
            db_tool_run.stderr = result.stderr
            db_tool_run.completed_at = datetime.utcnow()
            db_tool_run.duration_seconds = duration
            session.commit()

            # Release tool slot
            self.policy_engine.release_tool_slot(job_id)

            # Schedule result normalization
            if result.returncode == 0 and result.stdout:
                normalize_results.delay(str(db_tool_run.id))

            return {
                "status": "completed",
                "tool_run_id": str(db_tool_run.id),
                "exit_code": result.returncode,
                "duration": duration,
            }

        except subprocess.TimeoutExpired:
            self.policy_engine.release_tool_slot(job_id)
            return {"status": "timeout", "message": f"Tool {tool_name} timed out"}

        except PolicyViolationError as e:
            self.policy_engine.release_tool_slot(job_id)
            return {"status": "error", "message": f"Policy violation: {e}"}

        except Exception as e:
            self.policy_engine.release_tool_slot(job_id)
            # Retry on failure
            raise self.retry(exc=e, countdown=30) from e


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def normalize_results(self, run_id: str) -> dict:
    """Parse and normalize tool output into findings.

    Args:
        run_id: UUID of the tool run

    Returns:
        Normalization summary
    """
    from nethical_recon.core.parsers.nmap_parser import NmapParser
    from nethical_recon.core.storage.repository import FindingRepository, ToolRunRepository

    run_uuid = UUID(run_id)

    with self.database.session() as session:
        tool_repo = ToolRunRepository(session)
        finding_repo = FindingRepository(session)

        tool_run = tool_repo.get_by_id(run_uuid)
        if not tool_run:
            return {"status": "error", "message": f"Tool run {run_id} not found"}

        try:
            # Select parser based on tool name
            if tool_run.tool_name == "nmap":
                parser = NmapParser()
            else:
                # No parser available for this tool yet
                return {"status": "skipped", "message": f"No parser for tool {tool_run.tool_name}"}

            # Parse output
            if not tool_run.stdout:
                return {"status": "skipped", "message": "No output to parse"}

            findings = parser.parse(tool_run.stdout, run_uuid)

            # Save findings
            for finding in findings:
                finding_repo.create(finding)

            session.commit()

            return {
                "status": "completed",
                "run_id": run_id,
                "findings_count": len(findings),
            }

        except Exception as e:
            # Retry on failure
            raise self.retry(exc=e, countdown=10) from e


@app.task(base=DatabaseTask, bind=True)
def generate_report(self, job_id: str) -> dict:
    """Generate report for a completed job.

    Args:
        job_id: UUID of the scan job

    Returns:
        Report generation summary
    """
    from nethical_recon.core.storage.repository import FindingRepository, ScanJobRepository, ToolRunRepository

    job_uuid = UUID(job_id)

    with self.database.session() as session:
        job_repo = ScanJobRepository(session)
        tool_repo = ToolRunRepository(session)
        finding_repo = FindingRepository(session)

        job = job_repo.get_by_id(job_uuid)
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}

        # Get all tool runs for this job
        tool_runs = tool_repo.get_by_job(job_uuid)

        # Get all findings
        all_findings = []
        for tool_run in tool_runs:
            findings = finding_repo.get_by_run(tool_run.id)
            all_findings.extend(findings)

        # Generate report (simplified for now)
        report = {
            "job_id": job_id,
            "job_name": job.name,
            "status": job.status.value,
            "tools_run": len(tool_runs),
            "findings_count": len(all_findings),
            "findings_by_severity": {},
        }

        # Count findings by severity
        for finding in all_findings:
            severity = finding.severity.value
            report["findings_by_severity"][severity] = report["findings_by_severity"].get(severity, 0) + 1

        return report


# Helper functions

def _get_tool_version(tool_name: str) -> str:
    """Get tool version.

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
                    return line.split()[2]
        return "unknown"
    except Exception:
        return "unknown"


def _build_tool_command(tool_name: str, target: str) -> str:
    """Build command for tool execution.

    Args:
        tool_name: Name of the tool
        target: Target to scan

    Returns:
        Command string
    """
    # Basic command building (expand this in production)
    if tool_name == "nmap":
        return f"nmap -sV -T4 {target}"
    elif tool_name == "nikto":
        return f"nikto -h {target}"
    elif tool_name == "dirb":
        return f"dirb http://{target}/"
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
