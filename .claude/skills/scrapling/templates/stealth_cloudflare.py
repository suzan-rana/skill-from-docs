#!/usr/bin/env python3
"""Cloudflare anti-bot bypass template
Purpose: sites protected by Cloudflare/WAF
Replace: URL, COOKIES (optional), CSS_SELECTOR
"""
from scrapling.fetchers import StealthyFetcher

URL = "{{URL}}"
COOKIES = {{COOKIES}}  # None or [{'name': ..., 'value': ..., 'domain': ..., 'path': '/'}]
CSS_SELECTOR = "{{CSS_SELECTOR}}"

page = StealthyFetcher.fetch(
    URL,
    headless=True,
    solve_cloudflare=True,
    cookies=COOKIES,
    timeout=60000,
    network_idle=True,
)

print(f"Status: {page.status}")

if CSS_SELECTOR:
    results = page.css(CSS_SELECTOR).getall()
    for r in results:
        print(r)
else:
    print(page.get_all_text(strip=True)[:2000])
