"""Command line interface for nethical_recon."""

from __future__ import annotations

import typer
from typing import Optional

app = typer.Typer(
    name="nethical",
    help="Nethical Recon - Advanced Cybersecurity Reconnaissance & Threat Hunting Platform",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version information."""
    from . import __version__, __author__

    typer.echo(f"Nethical Recon v{__version__}")
    typer.echo(f"Author: {__author__}")


@app.command()
def interactive():
    """Launch interactive mode (original interface)."""
    typer.echo("Interactive mode - Coming in Phase B")


@app.command()
def scan(
    target: str = typer.Argument(..., help="Target to scan (domain, IP, or CIDR)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
):
    """Scan a target."""
    typer.echo(f"Scan command - Target: {target}, Output: {output}")
    typer.echo("Full implementation coming in Phase B")


@app.command()
def job():
    """Job management commands."""
    typer.echo("Job management - Coming in Phase C")


@app.command()
def report(job_id: Optional[str] = typer.Argument(None, help="Job ID to generate report for")):
    """Generate reports."""
    typer.echo(f"Report generation - Job ID: {job_id}")
    typer.echo("Full implementation coming in Phase B")


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
