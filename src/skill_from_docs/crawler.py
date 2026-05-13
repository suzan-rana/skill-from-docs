from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

from rich.console import Console
from scrapling.fetchers import Fetcher, StealthyFetcher

console = Console()


@dataclass
class CrawledPage:
    url: str
    status: int
    html: str
    links: list[str] = field(default_factory=list)


def _normalize(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/")


def _same_site(seed_host: str, candidate: str) -> bool:
    try:
        host = urlparse(candidate).netloc
    except Exception:
        return False
    if not host:
        return False
    return host == seed_host or host.endswith("." + seed_host)


def _allowed_path(seed_path: str, candidate: str) -> bool:
    """Restrict to descendants of seed path (treat docs root as scope)."""
    try:
        p = urlparse(candidate).path
    except Exception:
        return False
    if not seed_path or seed_path == "/":
        return True
    base = seed_path.rstrip("/")
    return p == base or p.startswith(base + "/")


def crawl(
    seed_url: str,
    max_pages: int = 200,
    stealth: bool = False,
    timeout: int = 30,
) -> list[CrawledPage]:
    """BFS crawl confined to the seed URL's host + path subtree."""
    seed = _normalize(seed_url)
    parsed = urlparse(seed)
    seed_host = parsed.netloc
    seed_path = parsed.path or "/"

    seen: set[str] = {seed}
    queue: deque[str] = deque([seed])
    out: list[CrawledPage] = []

    while queue and len(out) < max_pages:
        url = queue.popleft()
        try:
            if stealth:
                resp = StealthyFetcher.fetch(
                    url,
                    timeout=timeout * 1000,
                    headless=True,
                    network_idle=True,
                    block_webrtc=True,
                )
            else:
                resp = Fetcher.get(url, timeout=timeout, stealthy_headers=True)
        except Exception as e:
            console.log(f"[yellow]fetch fail[/yellow] {url}: {e}")
            continue

        status = getattr(resp, "status", 0) or 0
        if status >= 400:
            console.log(f"[yellow]{status}[/yellow] {url}")
            continue

        html = (
            getattr(resp, "html_content", None)
            or getattr(resp, "text", None)
            or getattr(resp, "body", "")
            or ""
        )
        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="replace")

        anchors: list[str] = []
        try:
            anchors = list(resp.css("a::attr(href)").getall())
        except Exception:
            try:
                anchors = [a.attrib.get("href", "") for a in resp.css("a[href]")]
            except Exception:
                pass

        links: list[str] = []
        for href in anchors:
            full = _normalize(urljoin(url, href))
            if not full.startswith(("http://", "https://")):
                continue
            if not _same_site(seed_host, full):
                continue
            if not _allowed_path(seed_path, full):
                continue
            links.append(full)
            if full not in seen and len(seen) < max_pages * 2:
                seen.add(full)
                queue.append(full)

        out.append(CrawledPage(url=url, status=status, html=html, links=links))
        console.log(f"[green]ok[/green] [{len(out)}/{max_pages}] {url}")

    return out
