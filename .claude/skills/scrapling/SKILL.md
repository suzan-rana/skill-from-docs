---
name: scrapling
description: |
  Use scrapling for web scraping and data extraction. Automatically selects the best Fetcher
  based on target website characteristics, then generates and executes a Python script to complete the task. Use when:
  (1) Scraping/crawling web content or data (scrape, crawl, fetch page, extract data)
  (2) Need to bypass Cloudflare/WAF and similar anti-bot protection
  (3) Scraping protected pages after login
  (4) Parsing existing HTML to extract structured data
  (5) User provides a URL and requests page content or specific elements
  (6) Batch collection of multiple pages
allowed-tools: Bash(python*), Bash(pip*), Bash(uv*), Bash(scrapling*)
---

# Scrapling Web Scraping Skill

## Step 0: Check Version

```bash
python -c "import scrapling; print(scrapling.__version__)"
```

Execute using the package manager the project uses (pip / uv equivalents in `references/maintenance.md`):

- Not installed → install `scrapling[fetchers]` + `scrapling install`
- Newer version available → upgrade → check changelog and inform the user
- Already latest → continue

> If the project root contains `uv.lock` or `pyproject.toml` includes `[tool.uv]`, prefer `uv` (`uv add` / `uv run scrapling install`); otherwise use `pip`.

## Step 1: Choose a Fetcher

```
Target website →
│
├─ Already have HTML string/file, only need to parse?
│   → Selector (pure parsing, no network requests)
│   → Template: parse_only.py
│
├─ Static page, no JS rendering, no anti-bot?
│   → Fetcher (fastest, based on curl_cffi)
│   → Template: basic_fetch.py
│
├─ Login required (HTTP form, not JS-based login)?
│   → FetcherSession (maintains session cookies)
│   → Template: session_login.py
│
├─ Cloudflare / WAF protection present?
│   → StealthyFetcher (Camoufox browser, auto-bypasses CF)
│   → Template: stealth_cloudflare.py
│
├─ SPA application (React/Vue), JS rendering required?
│   → DynamicFetcher (Playwright browser)
│   → Generate on-the-fly based on template
│
└─ Unsure?
    → Try Fetcher first; if 403 / empty content → upgrade to StealthyFetcher
```

## Step 2: Execute Workflow

```
1. Check version (Step 0)
2. Consult references/site-patterns.md — reuse directly if a matching pattern exists
3. No match → use the decision tree to choose a Fetcher
4. Read the corresponding template → replace parameters → generate complete script
5. Execute the script → return results
6. **Capture lessons learned (mandatory)**:
   - New site → append to site-patterns.md
   - New cookie / user-provided cookie → save to cookie-vault.md
   - **After scraping completes, always check**: are there new cookies or site patterns to save?
```

## Cookie Format Quick Reference

| Fetcher Type | Cookie Format | Example |
|-------------|---------------|---------|
| Fetcher / FetcherSession | `dict` | `{'name': 'value', 'token': 'abc'}` |
| StealthyFetcher / DynamicFetcher | `list[dict]` | `[{'name': 'n', 'value': 'v', 'domain': '.site.com', 'path': '/'}]` |

**Required cookie fields for browser-based Fetchers**: `name`, `value`, `domain`, `path`

## Timeout Units Quick Reference

| Fetcher Type | Timeout Unit | Example |
|-------------|--------------|---------|
| Fetcher / FetcherSession | seconds | `timeout=30` |
| StealthyFetcher / DynamicFetcher | milliseconds | `timeout=60000` |

## Template Index

| Template | File | When to Read |
|----------|------|--------------|
| Basic HTTP scraping | `templates/basic_fetch.py` | Target is a static page with no anti-bot protection |
| Cloudflare bypass | `templates/stealth_cloudflare.py` | Target has CF/WAF protection |
| Session login | `templates/session_login.py` | HTTP form login required before scraping |
| Pure HTML parsing | `templates/parse_only.py` | Already have HTML string, only need to extract data |

## References Index

| File | When to Read |
|------|--------------|
| `references/site-patterns.md` | **Consult before every scrape** — check whether the target site has a recorded pattern |
| `references/api-quick-ref.md` | Consult when generating scripts — Fetcher/Selector method signatures and parameters |
| `references/troubleshooting.md` | Consult when execution errors occur — look up causes and solutions by error message |
| `references/cookie-vault.md` | Consult when login cookies are needed — check whether historical entries can be reused |
| `references/maintenance.md` | Consult for installation/upgrade/dependency issues — installation tiers and verification commands |