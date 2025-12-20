"""Command line interface for nethical_recon."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="nethical",
    help="Nethical Recon - Advanced Cybersecurity Reconnaissance & Threat Hunting Platform",
    no_args_is_help=True,
)

# Job management subcommand
job_app = typer.Typer(help="Job management commands")
app.add_typer(job_app, name="job")

# Scheduler management subcommand
scheduler_app = typer.Typer(help="Scheduler management commands")
app.add_typer(scheduler_app, name="scheduler")

# Policy configuration subcommand
policy_app = typer.Typer(help="Policy configuration commands")
app.add_typer(policy_app, name="policy")


@app.command()
def version():
    """Show version information."""
    from . import __author__, __version__

    typer.echo(f"Nethical Recon v{__version__}")
    typer.echo(f"Author: {__author__}")


@app.command()
def interactive():
    """Launch interactive mode (original interface)."""
    typer.echo("Interactive mode - Coming in Phase B")


@app.command()
def scan(
    target: str = typer.Argument(..., help="Target to scan (domain, IP, or CIDR)"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
):
    """Scan a target."""
    typer.echo(f"Scan command - Target: {target}, Output: {output}")
    typer.echo("Full implementation coming in Phase B")


# Job management commands
@job_app.command("submit")
def job_submit(
    target: str = typer.Argument(..., help="Target to scan"),
    name: str = typer.Option(..., "--name", "-n", help="Job name"),
    tools: str = typer.Option("nmap", "--tools", "-t", help="Comma-separated list of tools"),
    description: str | None = typer.Option(None, "--description", "-d", help="Job description"),
):
    """Submit a new scan job to the worker queue."""
    import ipaddress

    from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
    from nethical_recon.core.storage import init_database
    from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
    from nethical_recon.worker.tasks import run_scan_job

    try:
        # Initialize database
        db = init_database()

        with db.session() as session:
            target_repo = TargetRepository(session)
            job_repo = ScanJobRepository(session)

            # Create or find target
            existing_target = target_repo.get_by_value(target)
            if existing_target:
                target_obj = existing_target
                typer.echo(f"Using existing target: {target_obj.id}")
            else:
                # Determine target type using proper IP validation
                target_type = TargetType.DOMAIN  # Default to domain
                try:
                    # Validate IP address and determine type
                    ipaddress.ip_address(target)
                    # Both IPv4 and IPv6 use the same IP type
                    target_type = TargetType.IP
                except ValueError:
                    # Not a valid IP, treat as domain/hostname
                    target_type = TargetType.DOMAIN

                target_obj = Target(
                    value=target,
                    type=target_type,
                    scope=TargetScope.IN_SCOPE,
                )
                target_obj = target_repo.create(target_obj)
                typer.echo(f"Created new target: {target_obj.id}")

            # Create scan job
            tool_list = [t.strip() for t in tools.split(",")]
            job = ScanJob(
                target_id=target_obj.id,
                name=name,
                description=description,
                tools=tool_list,
            )
            job = job_repo.create(job)
            session.commit()

            typer.echo(f"✓ Created job: {job.id}")
            typer.echo(f"  Target: {target}")
            typer.echo(f"  Tools: {', '.join(tool_list)}")

            # Submit to worker queue
            task = run_scan_job.delay(str(job.id))
            typer.echo("✓ Submitted to worker queue")
            typer.echo(f"  Task ID: {task.id}")
            typer.echo(f"\nUse 'nethical job status {job.id}' to check progress")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@job_app.command("status")
def job_status(
    job_id: str = typer.Argument(..., help="Job ID to check"),
):
    """Check the status of a scan job."""
    from uuid import UUID

    from nethical_recon.core.storage import init_database
    from nethical_recon.core.storage.repository import (
        FindingRepository,
        ScanJobRepository,
        ToolRunRepository,
    )

    try:
        db = init_database()

        with db.session() as session:
            job_repo = ScanJobRepository(session)
            tool_repo = ToolRunRepository(session)
            finding_repo = FindingRepository(session)

            job = job_repo.get_by_id(UUID(job_id))
            if not job:
                typer.echo(f"Job {job_id} not found", err=True)
                raise typer.Exit(1)

            typer.echo(f"\n=== Job Status:  {job.name} ===")
            typer.echo(f"ID: {job.id}")
            typer.echo(f"Status: {job.status.value.upper()}")
            typer.echo(f"Created: {job.created_at}")
            if job.started_at:
                typer.echo(f"Started: {job.started_at}")
            if job.completed_at:
                typer.echo(f"Completed: {job.completed_at}")
            if job.error_message:
                typer.echo(f"Error: {job.error_message}")

            # Get tool runs
            tool_runs = tool_repo.get_by_job(UUID(job_id))
            if tool_runs:
                typer.echo(f"\n=== Tool Runs ({len(tool_runs)}) ===")
                for run in tool_runs:
                    typer.echo(f"\n  {run.tool_name} ({run.tool_version})")
                    typer.echo(f"    Status: {run.status.value}")
                    typer.echo(f"    Exit code: {run.exit_code}")
                    if run.duration_seconds:
                        typer.echo(f"    Duration: {run.duration_seconds:.2f}s")

                    # Get findings for this run
                    findings = finding_repo.get_by_run(run.id)
                    if findings:
                        typer.echo(f"    Findings: {len(findings)}")
                        severity_counts = {}
                        for finding in findings:
                            severity_counts[finding.severity.value] = severity_counts.get(finding.severity.value, 0) + 1
                        for severity, count in sorted(severity_counts.items()):
                            typer.echo(f"      {severity}: {count}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@job_app.command("list")
def job_list(
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of jobs to show"),
):
    """List recent scan jobs."""
    from sqlalchemy import select

    from nethical_recon.core.storage import init_database
    from nethical_recon.core.storage.models import ScanJobModel

    try:
        db = init_database()

        with db.session() as session:
            # Get all jobs (in production, add pagination)
            stmt = select(ScanJobModel).order_by(ScanJobModel.created_at.desc()).limit(limit)
            result = session.execute(stmt)
            jobs = result.scalars().all()

            if not jobs:
                typer.echo("No jobs found")
                return

            typer.echo(f"\n=== Recent Jobs (showing {len(jobs)}) ===\n")
            for job in jobs:
                status_emoji = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✓",
                    "failed": "✗",
                    "cancelled": "⊘",
                }.get(job.status, "?")

                typer.echo(f"{status_emoji} {job.name}")
                typer.echo(f"  ID: {job.id}")
                typer.echo(f"  Status: {job.status}")
                typer.echo(f"  Created: {job.created_at}")
                typer.echo(f"  Tools: {', '.join(job.tools)}")
                typer.echo()

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@job_app.command("logs")
def job_logs(
    job_id: str = typer.Argument(..., help="Job ID to show logs for"),
    tool: str | None = typer.Option(None, "--tool", "-t", help="Filter by tool name"),
):
    """Show logs for a scan job."""
    from uuid import UUID

    from nethical_recon.core.storage import init_database
    from nethical_recon.core.storage.repository import ToolRunRepository

    try:
        db = init_database()

        with db.session() as session:
            tool_repo = ToolRunRepository(session)

            tool_runs = tool_repo.get_by_job(UUID(job_id))
            if not tool_runs:
                typer.echo("No tool runs found for this job")
                return

            for run in tool_runs:
                if tool and run.tool_name != tool:
                    continue

                typer.echo(f"\n=== {run.tool_name} ({run.id}) ===")
                typer.echo(f"Command: {run.command}")
                typer.echo(f"Status: {run.status.value}")

                if run.stdout:
                    typer.echo("\n--- STDOUT ---")
                    typer.echo(run.stdout[:1000])  # Limit output
                    if len(run.stdout) > 1000:
                        typer.echo(f"... ({len(run.stdout) - 1000} more characters)")

                if run.stderr:
                    typer.echo("\n--- STDERR ---")
                    typer.echo(run.stderr[:1000])
                    if len(run.stderr) > 1000:
                        typer.echo(f"... ({len(run.stderr) - 1000} more characters)")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def report(job_id: str | None = typer.Argument(None, help="Job ID to generate report for")):
    """Generate reports."""
    typer.echo(f"Report generation - Job ID: {job_id}")
    typer.echo("Full implementation coming in Phase B")


# Scheduler commands
@scheduler_app.command("start")
def scheduler_start():
    """Start the scan scheduler."""
    from nethical_recon.scheduler import ScanScheduler

    try:
        scheduler = ScanScheduler()
        scheduler.start()
        typer.echo("✓ Scheduler started")
        typer.echo("Scheduler is running in the background")
        typer.echo("Use 'nethical scheduler stop' to stop it")
    except Exception as e:
        typer.echo(f"Error starting scheduler: {e}", err=True)
        raise typer.Exit(1) from e


@scheduler_app.command("schedule")
def scheduler_schedule(
    target: str = typer.Argument(..., help="Target to scan"),
    tools: str = typer.Option("nmap", "--tools", "-t", help="Comma-separated list of tools"),
    interval: int = typer.Option(24, "--interval", "-i", help="Interval in hours"),
    name: str | None = typer.Option(None, "--name", "-n", help="Schedule name"),
    cron: str | None = typer.Option(None, "--cron", "-c", help="Cron expression (alternative to interval)"),
):
    """Schedule a periodic scan."""
    from nethical_recon.scheduler import ScanScheduler

    try:
        scheduler = ScanScheduler()
        scheduler.start()

        tool_list = [t.strip() for t in tools.split(",")]

        if cron:
            job_id = scheduler.schedule_cron_scan(
                target=target,
                tools=tool_list,
                cron_expression=cron,
                name=name,
            )
            typer.echo(f"✓ Scheduled cron scan: {job_id}")
            typer.echo(f"  Target: {target}")
            typer.echo(f"  Tools: {', '.join(tool_list)}")
            typer.echo(f"  Cron: {cron}")
        else:
            job_id = scheduler.schedule_periodic_scan(
                target=target,
                tools=tool_list,
                interval_hours=interval,
                name=name,
            )
            typer.echo(f"✓ Scheduled periodic scan: {job_id}")
            typer.echo(f"  Target: {target}")
            typer.echo(f"  Tools: {', '.join(tool_list)}")
            typer.echo(f"  Interval: every {interval} hours")

    except Exception as e:
        typer.echo(f"Error scheduling scan: {e}", err=True)
        raise typer.Exit(1) from e


@scheduler_app.command("list")
def scheduler_list():
    """List all scheduled scans."""
    from nethical_recon.scheduler import ScanScheduler

    try:
        scheduler = ScanScheduler()
        scheduler.start()

        jobs = scheduler.list_jobs()

        if not jobs:
            typer.echo("No scheduled jobs")
            return

        typer.echo(f"\n=== Scheduled Jobs ({len(jobs)}) ===\n")
        for job in jobs:
            typer.echo(f"📅 {job['name']}")
            typer.echo(f"  ID: {job['id']}")
            typer.echo(f"  Next run: {job['next_run']}")
            typer.echo(f"  Trigger: {job['trigger']}")
            typer.echo()

    except Exception as e:
        typer.echo(f"Error listing scheduled jobs: {e}", err=True)
        raise typer.Exit(1) from e


@scheduler_app.command("remove")
def scheduler_remove(
    job_id: str = typer.Argument(..., help="Scheduled job ID to remove"),
):
    """Remove a scheduled scan."""
    from nethical_recon.scheduler import ScanScheduler

    try:
        scheduler = ScanScheduler()
        scheduler.start()

        success = scheduler.remove_job(job_id)

        if success:
            typer.echo(f"✓ Removed scheduled job: {job_id}")
        else:
            typer.echo(f"Job not found: {job_id}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error removing job: {e}", err=True)
        raise typer.Exit(1) from e


# Policy commands
@policy_app.command("show")
def policy_show():
    """Show current policy configuration."""
    from nethical_recon.worker.policy import PolicyEngine

    try:
        engine = PolicyEngine()
        config = engine.config

        typer.echo("\n=== Rules of Engagement (RoE) Configuration ===\n")
        typer.echo("Rate Limiting:")
        typer.echo(f"  Max requests/sec: {config.max_requests_per_second}")
        typer.echo(f"  Max concurrent tools: {config.max_concurrent_tools}")
        typer.echo(f"  Max concurrent jobs: {config.max_concurrent_jobs}")

        typer.echo("\nScan Limits:")
        typer.echo(f"  Max scan duration: {config.max_scan_duration_seconds}s")
        typer.echo(f"  Max ports to scan: {config.max_ports_to_scan}")
        typer.echo(f"  Max threads: {config.max_threads}")

        typer.echo("\nTool Restrictions:")
        typer.echo(f"  Allowed tools: {', '.join(config.allowed_tools) if config.allowed_tools else 'All'}")
        typer.echo(f"  High-risk tools: {', '.join(config.high_risk_tools)}")
        typer.echo(f"  Require explicit auth for high-risk: {config.require_explicit_auth_for_high_risk}")

        typer.echo("\nNetwork Restrictions:")
        if config.allowed_networks:
            typer.echo(f"  Allowed networks: {', '.join(config.allowed_networks)}")
        else:
            typer.echo("  Allowed networks: All")
        if config.denied_networks:
            typer.echo(f"  Denied networks: {', '.join(config.denied_networks)}")

        status = engine.get_status()
        typer.echo("\nCurrent Status:")
        typer.echo(f"  Active tools: {status['active_tools']}/{status['max_concurrent_tools']}")
        typer.echo(f"  Active jobs: {status['active_jobs']}/{status['max_concurrent_jobs']}")

    except Exception as e:
        typer.echo(f"Error showing policy: {e}", err=True)
        raise typer.Exit(1) from e


@policy_app.command("validate")
def policy_validate(
    target: str = typer.Argument(..., help="Target to validate"),
    tool: str = typer.Option(..., "--tool", "-t", help="Tool to validate"),
):
    """Validate if a scan is allowed by policy."""
    from nethical_recon.worker.policy import PolicyEngine

    try:
        engine = PolicyEngine()

        # Check if tool can run
        can_run = engine.can_run_tool(tool)
        typer.echo(f"\nTool '{tool}': {'✓ ALLOWED' if can_run else '✗ DENIED'}")

        # Check if network is allowed
        is_allowed = engine.is_network_allowed(target)
        typer.echo(f"Target '{target}': {'✓ ALLOWED' if is_allowed else '✗ DENIED'}")

        # Check if job can start
        can_start = engine.can_start_job()
        typer.echo(f"New job: {'✓ CAN START' if can_start else '✗ DENIED (limit reached)'}")

        if can_run and is_allowed and can_start:
            typer.echo("\n✓ Scan is ALLOWED by policy")
            return 0
        else:
            typer.echo("\n✗ Scan is DENIED by policy")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error validating policy: {e}", err=True)
        raise typer.Exit(1) from e


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI."""
    try:
        app()
        return 0
    except SystemExit as e:
        return e.code if e.code else 0
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        return 1
