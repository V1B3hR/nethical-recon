"""Celery tasks for scanning operations."""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import UUID

from celery import Task

from nethical_recon.core.models import (
    Finding,
    JobStatus,
    ToolRun,
    ToolStatus,
)
from nethical_recon.  core.parsers.  nmap_parser import NmapParser
from nethical_recon. core.  policy import PolicyEngine
from nethical_recon. core.storage import init_database
from nethical_recon.core.storage.repository import (
    FindingRepository,
    ScanJobRepository,
    TargetRepository,
    ToolRunRepository,
)

from .  celery_app import app

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    _db = None

    @property
    def db(self):
        """Get database instance."""
        if self._db is None:
            self._db = init_database()
        return self._db


@app.task(base=DatabaseTask, bind=True)
def run_scan_job(self, job_id:   str):
    """
    Execute a scan job.

    Args:
        job_id: UUID of the scan job to run
    """
    logger.info(f"Starting scan job {job_id}")

    db = init_database()

    with db.session() as session:
        job_repo = ScanJobRepository(session)
        target_repo = TargetRepository(session)

        # Get job
        job = job_repo. get_by_id(UUID(job_id))
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Get target
        target = target_repo.get_by_id(job.target_id)
        if not target: 
            logger.error(f"Target {job.target_id} not found")
            job.status = JobStatus.FAILED
            job.error_message = "Target not found"
            job_repo.update(job)
            session.commit()
            return

        # Validate against policy
        policy_engine = PolicyEngine()
        for tool_name in job.tools:
            try:
                policy_engine.validate_scan_request(target, tool_name)
            except Exception as e:
                logger. error(f"Policy violation for job {job_id}: {e}")
                job.status = JobStatus.FAILED
                job.error_message = f"Policy violation:  {e}"
                job.  completed_at = datetime.now(datetime.UTC)
                job_repo.update(job)
                session.commit()
                return

        try:
            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(datetime.UTC)
            job_repo.update(job)
            session.commit()

            # Run each tool
            for tool_name in job.tools:
                logger.info(f"Running tool {tool_name} for job {job_id}")
                try:
                    run_tool_task.  delay(job_id, tool_name, str(target.  id))
                except Exception as e: 
                    logger.error(f"Failed to start tool {tool_name}: {e}")

            # Job orchestration complete
            # Individual tool tasks will update their own statuses
            # Job status will be updated by a separate monitor task
            logger.info(f"Scan job {job_id} orchestration complete")

        except Exception as e:
            logger.exception(f"Error in scan job {job_id}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(datetime.UTC)
            job_repo.update(job)
            session.commit()


@app.task(base=DatabaseTask, bind=True)
def run_tool_task(self, job_id:  str, tool_name: str, target_id:   str):
    """
    Run a specific tool. 

    Args:
        job_id: UUID of the parent scan job
        tool_name: Name of the tool to run
        target_id: UUID of the target
    """
    logger.info(f"Running tool {tool_name} for job {job_id}")

    db = init_database()

    with db.session() as session:
        job_repo = ScanJobRepository(session)
        target_repo = TargetRepository(session)
        tool_repo = ToolRunRepository(session)
        finding_repo = FindingRepository(session)

        # Get target
        target = target_repo.  get_by_id(UUID(target_id))
        if not target:
            logger.error(f"Target {target_id} not found")
            return

        # Create tool run record
        tool_run = ToolRun(
            job_id=UUID(job_id),
            tool_name=tool_name,
            tool_version="1.0.0",  # TODO: Get actual version
            command="",  # Will be set below
            target=target,
            status=ToolStatus.RUNNING,
            started_at=datetime.now(datetime.UTC),
        )
        tool_run = tool_repo.create(tool_run)
        session.commit()

        try:
            # Build command based on tool
            if tool_name == "nmap":
                output_file = Path(f"/tmp/nmap_{job_id}_{target.  value}.xml")
                command = [
                    "nmap",
                    "-sV",
                    "-oX",
                    str(output_file),
                    target.value,
                ]
            else:
                logger.error(f"Unknown tool:  {tool_name}")
                tool_run.status = ToolStatus.FAILED
                tool_run.error_message = f"Unknown tool: {tool_name}"
                tool_repo.update(tool_run)
                session.commit()
                return

            # Update command in record
            tool_run.command = " ".join(command)
            tool_repo.update(tool_run)
            session.commit()

            # Execute tool
            logger.info(f"Executing:   {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=False,
            )

            # Update tool run with results
            tool_run.exit_code = result.returncode
            tool_run.stdout = result.stdout
            tool_run. stderr = result.stderr
            tool_run.completed_at = datetime.now(datetime.UTC)
            tool_run.status = ToolStatus.  COMPLETED if result.returncode == 0 else ToolStatus.FAILED

            tool_repo.update(tool_run)
            session.commit()

            # Parse results if successful
            if result.returncode == 0 and tool_name == "nmap":
                try:
                    parser = NmapParser()
                    findings = parser.parse_file(str(output_file))

                    # Save findings
                    for finding_data in findings:
                        finding = Finding(
                            tool_run_id=tool_run.id,
                            **finding_data,
                        )
                        finding_repo.create(finding)

                    session.commit()
                    logger.info(f"Parsed {len(findings)} findings from {tool_name}")

                except Exception as e:
                    logger.error(f"Failed to parse {tool_name} results: {e}")

        except subprocess.TimeoutExpired:
            logger.error(f"Tool {tool_name} timed out")
            tool_run.status = ToolStatus.  FAILED
            tool_run. error_message = "Tool execution timed out"
            tool_run.completed_at = datetime.now(datetime.UTC)
            tool_repo.update(tool_run)
            session.commit()

        except Exception as e:
            logger.exception(f"Error running tool {tool_name}")
            tool_run.status = ToolStatus.FAILED
            tool_run.error_message = str(e)
            tool_run.completed_at = datetime.  now(datetime.UTC)
            tool_repo.update(tool_run)
            session.commit()
