"""
CLI entry point for Nethical Recon
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Add the project root to the path to allow imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

console = Console()
app = typer.Typer(
    name="nethical",
    help="Nethical Recon - Advanced Cybersecurity Reconnaissance & Threat Hunting Platform",
    add_completion=True,
)


@app.command()
def version():
    """Show version information"""
    from nethical_recon import __version__

    console.print(f"Nethical Recon version {__version__}", style="bold green")


@app.command()
def interactive():
    """Launch interactive mode (original nethical_recon.py interface)"""
    console.print("[bold yellow]Launching interactive mode...[/bold yellow]")

    # Import and run the original nethical_recon.py main function
    try:
        # Import from the root directory
        import nethical_recon as original

        if hasattr(original, "main"):
            original.main()
        else:
            console.print("[red]Error: Interactive mode not available yet[/red]")
            raise typer.Exit(1)
    except ImportError:
        console.print("[red]Error: Could not load interactive mode[/red]")
        raise typer.Exit(1) from None


@app.command()
def scan(
    target: str = typer.Argument(..., help="Target IP address or domain"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for results"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated list of tools to run"),
):
    """Run security scan on a target"""
    console.print(f"[bold green]Scanning target: {target}[/bold green]")

    if output:
        console.print(f"Output directory: {output}")
    if tools:
        console.print(f"Tools: {tools}")

    console.print("[yellow]Note: Full scan implementation in progress (Phase B)[/yellow]")
    console.print("[yellow]For now, use 'nethical interactive' for full functionality[/yellow]")


@app.command()
def job():
    """Job management commands (coming in Phase C)"""
    console.print("[yellow]Job management will be available in Phase C[/yellow]")
    console.print("Future commands:")
    console.print("  - nethical job submit")
    console.print("  - nethical job status")
    console.print("  - nethical job list")


@app.command()
def report(
    job_id: Optional[str] = typer.Argument(None, help="Job ID to generate report for"),
):
    """Generate reports (coming in Phase B)"""
    console.print("[yellow]Report generation will be enhanced in Phase B[/yellow]")
    if job_id:
        console.print(f"Would generate report for job: {job_id}")
    console.print("Future formats: JSON, Markdown, PDF, STIX 2.1")


def main():
    """Main entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
