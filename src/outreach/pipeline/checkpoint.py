import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from outreach.models.contact import ComposedEmail

console = Console()


def show_checkpoint_summary(
    seed_domain: str,
    emails: list[ComposedEmail],
    dry_run: bool,
) -> bool:
    table = Table(title="Outreach checkpoint — review before send")
    table.add_column("Company", style="cyan")
    table.add_column("Name")
    table.add_column("Title")
    table.add_column("Email", style="green")
    table.add_column("Subject")

    for item in emails:
        c = item.contact
        company = c.company_name or c.company_domain
        table.add_row(company, c.full_name, c.title, c.email, item.subject[:60])

    mode = "DRY RUN" if dry_run else "LIVE SEND"
    console.print(
        Panel(
            f"Seed: [bold]{seed_domain}[/bold]\n"
            f"Recipients: [bold]{len(emails)}[/bold]\n"
            f"Mode: [bold]{mode}[/bold]",
            title="Pipeline summary",
        )
    )
    console.print(table)
    return True


def confirm_send(confirm_flag: bool, interactive: bool = True) -> bool:
    if confirm_flag:
        return True
    if not interactive or not sys.stdin.isatty():
        console.print(
            "[yellow]Send not confirmed. Re-run with --confirm-send to deliver emails.[/yellow]"
        )
        return False

    answer = console.input("\n[bold]Send these emails?[/bold] [y/N]: ").strip().lower()
    return answer in {"y", "yes"}
