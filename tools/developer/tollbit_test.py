"""
Tollbit Developer API Test Harness
===================================
A CLI tool to test the full Tollbit Developer API flow against the
Carli Wines sommelier website (carliwines.robertocarli.com).

Exercises the following APIs:
  1. Licensed Search — find content across the web
  2. Get Rate — check pricing for a specific page
  3. Bulk Get Rate — check pricing for multiple pages
  4. Generate Content Token — obtain a one-time JWT for content access
  5. Get Content — retrieve clean Markdown content
  6. List Content Catalog — paginated sitemap of a website
  7. Self Report Usage — async self-report for billing

Usage:
  python tollbit_test.py search "wine tasting"
  python tollbit_test.py rate /learn/blind-tasting-guide
  python tollbit_test.py bulk-rate /learn/blind-tasting-guide /regions/burgundy
  python tollbit_test.py get-content /learn/blind-tasting-guide
  python tollbit_test.py catalog
  python tollbit_test.py full-flow "sommelier wine education"
  python tollbit_test.py self-report <content_path> <token>
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

# Load .env from the same directory as this script
load_dotenv(Path(__file__).parent / ".env")

TOLLBIT_API_KEY = os.getenv("TOLLBIT_API_KEY", "")
TOLLBIT_AGENT_ID = os.getenv("TOLLBIT_AGENT_ID", "")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "carliwines.robertocarli.com")
BASE_URL = "https://gateway.tollbit.com"

console = Console()


def get_headers():
    """Common headers for Tollbit API requests."""
    if not TOLLBIT_API_KEY:
        console.print("[red]Error: TOLLBIT_API_KEY not set. Copy .env.example to .env and fill in your key.[/red]")
        sys.exit(1)
    return {
        "TollbitKey": TOLLBIT_API_KEY,
        "User-Agent": TOLLBIT_AGENT_ID or "carliwines-test-agent/1.0",
        "Content-Type": "application/json",
    }


# ─── 1. Licensed Search ─────────────────────────────────────────────────────

def cmd_search(query: str, limit: int = 10):
    """Search for content across the web using Tollbit's Licensed Search API."""
    console.print(Panel(f"[bold]Licensed Search[/bold]: '{query}'", style="blue"))

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/dev/v2/search",
            headers=get_headers(),
            params={"q": query, "limit": limit},
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    data = resp.json()
    results = data.get("results", [])

    table = Table(title=f"Search Results ({len(results)} found)")
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("URL", style="green", max_width=50)
    table.add_column("Discoverable", style="yellow")
    table.add_column("Ready to License", style="magenta")

    for r in results:
        table.add_row(
            r.get("title", "N/A"),
            r.get("url", "N/A"),
            str(r.get("discoverable", "N/A")),
            str(r.get("readyToLicense", "N/A")),
        )

    console.print(table)
    return data


# ─── 2. Get Rate ─────────────────────────────────────────────────────────────

def cmd_rate(content_path: str):
    """Get the price/license options for a single page."""
    console.print(Panel(f"[bold]Get Rate[/bold]: {SITE_DOMAIN}{content_path}", style="blue"))

    url = f"{BASE_URL}/tollbit/dev/v2/rate/{SITE_DOMAIN}{content_path}"

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=get_headers())

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    data = resp.json()
    console.print_json(json.dumps(data, indent=2))
    return data


# ─── 3. Bulk Get Rate ────────────────────────────────────────────────────────

def cmd_bulk_rate(content_paths: list[str]):
    """Get rates for multiple URLs at once."""
    urls = [f"https://{SITE_DOMAIN}{p}" for p in content_paths]
    console.print(Panel(f"[bold]Bulk Get Rate[/bold]: {len(urls)} URLs", style="blue"))

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/tollbit/dev/v2/rate/batch",
            headers=get_headers(),
            json={"urls": urls},
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    data = resp.json()
    console.print_json(json.dumps(data, indent=2))
    return data


# ─── 4. Generate Content Token ───────────────────────────────────────────────

def cmd_generate_token(content_path: str, max_price_micros: int = 100000, license_type: str = "ON_DEMAND_LICENSE"):
    """Generate a one-time JWT token for content access."""
    console.print(Panel(f"[bold]Generate Content Token[/bold]: {SITE_DOMAIN}{content_path}", style="blue"))

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/dev/v2/tokens/content",
            headers=get_headers(),
            json={
                "url": f"https://{SITE_DOMAIN}{content_path}",
                "maxPriceMicros": max_price_micros,
                "currency": "USD",
                "licenseType": license_type,
            },
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return None

    data = resp.json()
    token = data.get("token", "")
    console.print(f"[green]Token generated[/green] (first 50 chars): {token[:50]}...")
    return data


# ─── 5. Get Content ──────────────────────────────────────────────────────────

def cmd_get_content(content_path: str, token: str = None):
    """Retrieve the clean Markdown content of a page using a content token."""
    console.print(Panel(f"[bold]Get Content[/bold]: {SITE_DOMAIN}{content_path}", style="blue"))

    headers = get_headers()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/dev/v2/content/{SITE_DOMAIN}{content_path}",
            headers=headers,
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    data = resp.json()
    content = data.get("content", data.get("markdown", ""))

    if content:
        console.print(Panel(Markdown(content[:2000]), title="Content Preview (first 2000 chars)", style="green"))
    else:
        console.print_json(json.dumps(data, indent=2))

    return data


# ─── 6. List Content Catalog ─────────────────────────────────────────────────

def cmd_catalog(page: int = 1, limit: int = 50):
    """List the content catalog (paginated sitemap) of the site."""
    console.print(Panel(f"[bold]Content Catalog[/bold]: {SITE_DOMAIN} (page {page})", style="blue"))

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/dev/v2/content/{SITE_DOMAIN}/catalog/list",
            headers=get_headers(),
            params={"page": page, "limit": limit},
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    data = resp.json()
    items = data.get("items", data.get("urls", []))

    table = Table(title=f"Content Catalog ({len(items)} items)")
    table.add_column("URL", style="cyan")
    table.add_column("Last Modified", style="green")

    for item in items:
        if isinstance(item, str):
            table.add_row(item, "N/A")
        else:
            table.add_row(item.get("url", "N/A"), item.get("lastModified", "N/A"))

    console.print(table)
    return data


# ─── 7. Self Report Usage ────────────────────────────────────────────────────

def cmd_self_report(content_path: str, token: str):
    """Self-report usage for billing purposes."""
    console.print(Panel(f"[bold]Self Report Usage[/bold]: {SITE_DOMAIN}{content_path}", style="blue"))

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/tollbit/dev/v2/transactions/selfReport",
            headers=get_headers(),
            json={
                "url": f"https://{SITE_DOMAIN}{content_path}",
                "token": token,
            },
        )

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
        return

    console.print("[green]Usage reported successfully[/green]")
    return resp.json() if resp.text else {}


# ─── Full Flow ────────────────────────────────────────────────────────────────

def cmd_full_flow(query: str):
    """
    Execute the complete Tollbit Developer API flow:
    Search → Get Rate → Generate Token → Get Content
    """
    console.print(Panel("[bold yellow]Full Tollbit API Flow[/bold yellow]", style="yellow"))
    console.print(f"Query: '{query}'\nSite: {SITE_DOMAIN}\n")

    # Step 1: Search
    console.rule("[bold]Step 1: Licensed Search[/bold]")
    search_data = cmd_search(query, limit=5)
    if not search_data or not search_data.get("results"):
        console.print("[yellow]No search results. Trying direct content path instead...[/yellow]")
        content_path = "/learn/how-to-choose-wine"
    else:
        # Pick the first result that's from our site
        our_results = [r for r in search_data["results"] if SITE_DOMAIN in r.get("url", "")]
        if our_results:
            from urllib.parse import urlparse
            parsed = urlparse(our_results[0]["url"])
            content_path = parsed.path
        else:
            console.print("[yellow]No results from our site. Using first result.[/yellow]")
            from urllib.parse import urlparse
            parsed = urlparse(search_data["results"][0]["url"])
            content_path = parsed.path

    console.print(f"\n[cyan]Selected content path: {content_path}[/cyan]\n")

    # Step 2: Get Rate
    console.rule("[bold]Step 2: Get Rate[/bold]")
    rate_data = cmd_rate(content_path)

    # Step 3: Generate Token
    console.rule("[bold]Step 3: Generate Content Token[/bold]")
    token_data = cmd_generate_token(content_path)
    if not token_data:
        console.print("[red]Failed to generate token. Aborting.[/red]")
        return

    token = token_data.get("token", "")

    # Step 4: Get Content
    console.rule("[bold]Step 4: Get Content[/bold]")
    cmd_get_content(content_path, token=token)

    console.print("\n[bold green]✓ Full flow completed successfully![/bold green]")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tollbit Developer API Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="API command to run")

    # search
    p_search = subparsers.add_parser("search", help="Licensed Search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    # rate
    p_rate = subparsers.add_parser("rate", help="Get Rate for a page")
    p_rate.add_argument("path", help="Content path (e.g., /learn/blind-tasting-guide)")

    # bulk-rate
    p_bulk = subparsers.add_parser("bulk-rate", help="Bulk Get Rate for multiple pages")
    p_bulk.add_argument("paths", nargs="+", help="Content paths")

    # get-content
    p_content = subparsers.add_parser("get-content", help="Get Content (generates token automatically)")
    p_content.add_argument("path", help="Content path")
    p_content.add_argument("--max-price", type=int, default=100000, help="Max price in micros")

    # catalog
    p_catalog = subparsers.add_parser("catalog", help="List Content Catalog")
    p_catalog.add_argument("--page", type=int, default=1, help="Page number")
    p_catalog.add_argument("--limit", type=int, default=50, help="Items per page")

    # self-report
    p_report = subparsers.add_parser("self-report", help="Self Report Usage")
    p_report.add_argument("path", help="Content path")
    p_report.add_argument("token", help="Content token used")

    # full-flow
    p_flow = subparsers.add_parser("full-flow", help="Execute full API flow: Search → Rate → Token → Content")
    p_flow.add_argument("query", help="Search query")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    console.print(Panel(
        f"[bold]Tollbit Developer Test Harness[/bold]\n"
        f"Site: {SITE_DOMAIN}\n"
        f"Agent: {TOLLBIT_AGENT_ID or 'carliwines-test-agent/1.0'}\n"
        f"Time: {datetime.now().isoformat()}",
        style="bold blue",
    ))

    if args.command == "search":
        cmd_search(args.query, args.limit)
    elif args.command == "rate":
        cmd_rate(args.path)
    elif args.command == "bulk-rate":
        cmd_bulk_rate(args.paths)
    elif args.command == "get-content":
        # Auto-generate token then get content
        token_data = cmd_generate_token(args.path, max_price_micros=args.max_price)
        if token_data:
            cmd_get_content(args.path, token=token_data.get("token"))
    elif args.command == "catalog":
        cmd_catalog(args.page, args.limit)
    elif args.command == "self-report":
        cmd_self_report(args.path, args.token)
    elif args.command == "full-flow":
        cmd_full_flow(args.query)


if __name__ == "__main__":
    main()
