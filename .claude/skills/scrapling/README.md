# Claude Code Skill: Scrapling

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill for web scraping and data extraction using [scrapling](https://github.com/D4Vinci/Scrapling).

Automatically selects the best Fetcher based on target website characteristics, generates and executes Python scripts.

## Features

- **Fetcher Decision Tree** — Auto-select between Fetcher, StealthyFetcher, DynamicFetcher, FetcherSession, or Selector
- **Cloudflare Bypass** — Built-in support for Cloudflare/WAF protected sites via StealthyFetcher (Camoufox)
- **Session Login** — HTTP form-based login with cookie persistence
- **Site Pattern Library** — Reusable patterns for common site types (Discourse, SPA, static blogs, APIs)
- **Cookie Vault** — Local storage for login cookies with per-site templates
- **Troubleshooting Guide** — Solutions for common errors indexed by error message

## Installation

### 1. Install scrapling

Pick whichever package manager your project uses:

```bash
# pip
pip install "scrapling[fetchers]"
scrapling install  # Install browser dependencies

# uv (project)
uv add "scrapling[fetchers]"
uv run scrapling install

# uv (global / standalone, no pyproject.toml)
uv pip install "scrapling[fetchers]"
scrapling install
```

### 2. Install this skill

Copy the skill directory to your Claude Code skills folder:

```bash
# Copy to user-level skills (available in all projects)
cp -r . ~/.claude/skills/scrapling

# Or copy to a specific project
cp -r . /path/to/project/.claude/skills/scrapling
```

## Structure

```
.
├── SKILL.md                           # Skill definition (entry point)
├── references/
│   ├── api-quick-ref.md               # Fetcher/Selector API cheat sheet
│   ├── cookie-vault.md                # Cookie storage template
│   ├── maintenance.md                 # Installation & upgrade guide
│   ├── site-patterns.md               # Site-specific scraping patterns
│   └── troubleshooting.md             # Error solutions
└── templates/
    ├── basic_fetch.py                 # Static page scraping
    ├── stealth_cloudflare.py          # Cloudflare bypass
    ├── session_login.py               # Login + multi-page scraping
    └── parse_only.py                  # HTML parsing without network
```

## Usage

Once installed, Claude Code will automatically activate this skill when you ask it to:

- Scrape or crawl a website
- Extract data from a URL
- Bypass Cloudflare protection
- Parse HTML content
- Login and scrape protected pages

### Examples

```
> Scrape the title and content from https://example.com/blog

> Extract all product prices from this page: https://shop.example.com

> This site has Cloudflare, scrape it anyway: https://protected.example.com

> I have this HTML, extract all links from it
```

## Cookie Vault

The `references/cookie-vault.md` file is a **template**. For actual use:

1. Copy it to `cookie-vault.local.md` (or keep it in your local skill installation)
2. Fill in real cookie values from your browser's DevTools
3. **Never commit real cookie values to version control**

## License

MIT
