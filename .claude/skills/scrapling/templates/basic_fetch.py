#!/usr/bin/env python3
"""Basic HTTP scraping template
Purpose: scraping static pages, no JS rendering, no anti-bot protection
Replace: URL, CSS_SELECTOR, output handling logic
"""
from scrapling.fetchers import Fetcher

URL = "{{URL}}"
CSS_SELECTOR = "{{CSS_SELECTOR}}"  # e.g. '.article h1::text'

page = Fetcher.get(URL, impersonate='chrome', timeout=30)
print(f"Status: {page.status}")

if CSS_SELECTOR:
    results = page.css(CSS_SELECTOR).getall()
    for r in results:
        print(r)
else:
    print(page.get_all_text(strip=True)[:2000])
