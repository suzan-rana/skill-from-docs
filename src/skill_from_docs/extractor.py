from __future__ import annotations

import re
from dataclasses import dataclass

import html2text
from scrapling.parser import Selector


@dataclass
class ExtractedPage:
    url: str
    title: str
    markdown: str
    headings: list[str]
    word_count: int


def _build_converter() -> html2text.HTML2Text:
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_images = True
    h.ignore_emphasis = False
    h.protect_links = True
    h.skip_internal_links = False
    return h


_CONV = _build_converter()


def extract(url: str, html: str) -> ExtractedPage:
    sel = Selector(html)

    title = ""
    try:
        t = sel.css_first("title")
        if t is not None:
            title = (t.text or "").strip()
    except Exception:
        pass
    if not title:
        try:
            h1 = sel.css_first("h1")
            if h1 is not None:
                title = (h1.text or "").strip()
        except Exception:
            pass

    main_html = html
    for selector in ("main", "article", "[role=main]", ".document", ".rst-content", "#content"):
        try:
            node = sel.css_first(selector)
            if node is not None:
                main_html = node.html_content or html
                break
        except Exception:
            continue

    md = _CONV.handle(main_html)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()

    headings = re.findall(r"^#{1,4}\s+(.+?)\s*$", md, flags=re.MULTILINE)
    word_count = len(md.split())

    return ExtractedPage(
        url=url,
        title=title or url,
        markdown=md,
        headings=headings,
        word_count=word_count,
    )
