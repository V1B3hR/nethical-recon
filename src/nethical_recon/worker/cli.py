#!/usr/bin/env python
"""Worker management CLI for Nethical Recon."""

from __future__ import annotations

import sys

import typer

app = typer.Typer(
    name="nethical-worker",
    help="Nethical Recon Worker - Manage worker processes and scheduler",
)


@app.command()
def start(
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Number of worker processes"),
    queues: str = typer.Option("scans,tools,processing,reports", "--queues", "-Q", help="Comma-separated queue names"),
    loglevel: str = typer.Option("info", "--loglevel", "-l", help="Log level"),
):
    """Start the Celery worker."""
    import subprocess

    queue_list = queues.split(",")
    cmd = [
        "celery",
        "-A",
        "nethical_recon.worker.celery_app",
        "worker",
        "--concurrency",
        str(concurrency),
        "--loglevel",
        loglevel,
        "-Q",
        ",".join(queue_list),
    ]

    typer.echo(f"Starting worker with {concurrency} processes...")
    typer.echo(f"Queues: {', '.join(queue_list)}")
    typer.echo(f"Log level: {loglevel}")
    typer.echo()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nWorker stopped.")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting worker: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def beat(
    loglevel: str = typer.Option("info", "--loglevel", "-l", help="Log level"),
):
    """Start the Celery beat scheduler."""
    import subprocess

    cmd = [
        "celery",
        "-A",
        "nethical_recon.worker.celery_app",
        "beat",
        "--loglevel",
        loglevel,
    ]

    typer.echo("Starting Celery beat scheduler...")
    typer.echo(f"Log level: {loglevel}")
    typer.echo()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nScheduler stopped.")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting scheduler: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def status():
    """Show worker status and statistics."""
    import subprocess

    cmd = ["celery", "-A", "nethical_recon.worker.celery_app", "inspect", "stats"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        typer.echo(result.stdout)
    except subprocess.CalledProcessError as e:
        typer.echo("No workers are currently running.", err=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def active():
    """Show active tasks."""
    import subprocess

    cmd = ["celery", "-A", "nethical_recon.worker.celery_app", "inspect", "active"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        typer.echo(result.stdout)
    except subprocess.CalledProcessError as e:
        typer.echo("No workers are currently running.", err=True)
        raise typer.Exit(1) from e


@app.command()
def purge(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Purge all tasks from queues."""
    import subprocess

    if not force:
        confirm = typer.confirm("This will delete all pending tasks. Continue?")
        if not confirm:
            typer.echo("Cancelled.")
            return

    cmd = ["celery", "-A", "nethical_recon.worker.celery_app", "purge", "-f"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        typer.echo(result.stdout)
        typer.echo("All tasks purged.")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error purging tasks: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def policy_stats():
    """Show policy engine statistics."""
    from nethical_recon.worker.policy import get_policy_engine

    try:
        policy = get_policy_engine()
        stats = policy.get_stats()

        typer.echo("\n=== Policy Engine Statistics ===\n")
        typer.echo(f"Active Jobs: {stats['active_jobs']}/{stats['max_parallel_jobs']}")
        typer.echo(f"Active Tools: {stats['active_tools']}/{stats['max_parallel_tools']}")
        typer.echo(f"Rate Limit: {stats['rate_limit_rps']} requests/sec")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
