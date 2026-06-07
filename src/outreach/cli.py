import logging
import sys

import typer
from rich.console import Console
from rich.logging import RichHandler

from outreach.config import get_settings
from outreach.pipeline.orchestrator import PipelineOrchestrator

app = typer.Typer(
    name="outreach",
    help="Automated cold-outreach pipeline: Ocean.io → Prospeo → Eazyreach → Brevo",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


@app.command("run")
def run_pipeline(
    domain: str = typer.Argument(..., help="Seed company domain, e.g. stripe.com"),
    mock: bool = typer.Option(False, "--mock", help="Use fixture data instead of live APIs"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compose emails but do not call Brevo send"
    ),
    confirm_send: bool = typer.Option(
        False, "--confirm-send", help="Skip interactive prompt and send after checkpoint"
    ),
    max_companies: int = typer.Option(25, "--max-companies", min=1, max=500),
    max_contacts_per_company: int = typer.Option(
        1, "--max-contacts-per-company", min=1, max=5
    ),
    use_llm: bool = typer.Option(
        False, "--use-llm", help="Generate personalized copy via OpenAI-compatible API"
    ),
    save_run: bool = typer.Option(False, "--save-run", help="Persist run JSON to runs/"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the full outreach pipeline for a seed domain."""
    _setup_logging(verbose)
    settings = get_settings()

    if not mock:
        missing = []
        if not settings.ocean_api_token:
            missing.append("OCEAN_API_TOKEN")
        if not settings.prospeo_api_key:
            missing.append("PROSPEO_API_KEY")
        if not settings.eazyreach_api_key:
            missing.append("EAZYREACH_API_KEY")
        if not settings.brevo_api_key and not dry_run:
            missing.append("BREVO_API_KEY")
        if missing:
            console.print(
                f"[red]Missing env vars: {', '.join(missing)}[/red]\n"
                "Use [bold]--mock --dry-run[/bold] to test without API keys."
            )
            raise typer.Exit(code=1)

    orchestrator = PipelineOrchestrator(
        settings,
        mock=mock,
        dry_run=dry_run,
        use_llm=use_llm,
    )

    console.print(f"[bold]Starting pipeline[/bold] for seed domain: [cyan]{domain}[/cyan]")
    if mock:
        console.print("[yellow]Mock mode enabled[/yellow]")

    run = orchestrator.run(
        domain,
        max_companies=max_companies,
        max_contacts_per_company=max_contacts_per_company,
        confirm_send_flag=confirm_send,
        save_run=save_run,
    )

    sent = sum(1 for r in run.send_results if r.success)
    console.print(
        f"\n[bold]Done.[/bold] Companies: {len(run.companies)} | "
        f"Contacts: {len(run.contacts)} | Enriched: {len(run.enriched_contacts)} | "
        f"Sent: {sent}"
    )
    if run.errors:
        console.print(f"[yellow]{len(run.errors)} warning(s)/error(s) logged[/yellow]")
        for err in run.errors:
            console.print(f"  [{err.stage}] {err.message}")

    if any(e.stage == "checkpoint" for e in run.errors):
        raise typer.Exit(code=0)
    if run.errors and not run.send_results:
        raise typer.Exit(code=1)


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
