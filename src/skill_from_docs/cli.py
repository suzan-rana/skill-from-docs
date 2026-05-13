from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from urllib.parse import urlparse

import click
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from .crawler import crawl
from .extractor import extract
from .synthesizer import DEFAULT_MODEL, Synthesizer
from .writer import write_skill

console = Console()


@click.group()
def main() -> None:
    """Crawl docs sites → synthesize Claude Code skills via Claude API."""


@main.command("build")
@click.argument("url")
@click.option("--name", default=None, help="Library/skill name. Default: inferred from host.")
@click.option("--out", "out_dir", default="./output", help="Output root directory.")
@click.option("--max-pages", default=150, type=int, help="Max pages to crawl.")
@click.option("--stealth", is_flag=True, help="Use StealthyFetcher (slower, bypasses CF).")
@click.option(
    "--model",
    default=lambda: os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
    help="OpenRouter model id (e.g. anthropic/claude-sonnet-4.5, openai/gpt-4o, google/gemini-2.0-flash).",
)
@click.option("--cache-dir", default=".skill-cache", help="Cache crawled+extracted pages here.")
@click.option("--no-cache", is_flag=True, help="Ignore existing crawl cache.")
def build(
    url: str,
    name: str | None,
    out_dir: str,
    max_pages: int,
    stealth: bool,
    model: str,
    cache_dir: str,
    no_cache: bool,
) -> None:
    """Build a Claude Code skill from documentation site URL."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise click.UsageError("Set OPENROUTER_API_KEY environment variable.")

    library_name = name or urlparse(url).netloc.split(".")[0]
    cache_path = Path(cache_dir) / f"{library_name}.pkl"

    pages = None
    if not no_cache and cache_path.exists():
        console.print(f"[cyan]Loading cached crawl from {cache_path}[/cyan]")
        pages = pickle.loads(cache_path.read_bytes())

    if pages is None:
        console.print(f"[cyan]Crawling {url} (max {max_pages} pages, stealth={stealth})[/cyan]")
        crawled = crawl(url, max_pages=max_pages, stealth=stealth)
        console.print(f"[cyan]Extracting markdown from {len(crawled)} pages[/cyan]")
        pages = [extract(c.url, c.html) for c in crawled]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(pickle.dumps(pages))
        console.print(f"[green]Cached → {cache_path}[/green]")

    pages = [p for p in pages if p.word_count >= 30]
    if not pages:
        raise click.ClickException("No usable pages extracted.")

    synth = Synthesizer(model=model)
    synth.load(pages, library_name)

    console.print("[cyan]Planning skill structure...[/cyan]")
    plan = synth.plan()
    console.print(f"[green]Plan: {plan.name} — {len(plan.files)} files[/green]")
    for f in plan.files:
        console.print(f"  • {f.path}")

    generated = []
    for f in plan.files:
        console.print(f"[cyan]Generating {f.path}...[/cyan]")
        generated.append(synth.generate_file(plan, f))

    out_path = write_skill(Path(out_dir), plan, generated)
    plan_dump = plan.model_dump()
    (out_path / ".skill-plan.json").write_text(json.dumps(plan_dump, indent=2), encoding="utf-8")
    console.print(f"[bold green]Skill written → {out_path}[/bold green]")


@main.command("crawl")
@click.argument("url")
@click.option("--max-pages", default=150, type=int)
@click.option("--stealth", is_flag=True)
@click.option("--out", "out_file", default="crawl.json")
def crawl_only(url: str, max_pages: int, stealth: bool, out_file: str) -> None:
    """Crawl + extract, write JSON. No LLM."""
    crawled = crawl(url, max_pages=max_pages, stealth=stealth)
    pages = [extract(c.url, c.html) for c in crawled]
    data = [
        {"url": p.url, "title": p.title, "headings": p.headings, "word_count": p.word_count}
        for p in pages
    ]
    Path(out_file).write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"[green]Wrote {len(pages)} pages → {out_file}[/green]")


if __name__ == "__main__":
    main()
