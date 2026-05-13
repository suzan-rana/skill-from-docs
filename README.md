# skill-from-docs

CLI agentic tool. Crawls a documentation site with [scrapling](https://scrapling.readthedocs.io), then synthesizes a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) folder via any LLM available on [OpenRouter](https://openrouter.ai).

## Install

```bash
uv sync
cp .env.example .env   # then fill in OPENROUTER_API_KEY
```

## Use

```bash
# Full pipeline: crawl + LLM synthesis
uv run sfd build https://scrapling.readthedocs.io/en/latest/ \
  --name scrapling \
  --out ./output \
  --max-pages 150

# Crawl only (no LLM cost)
uv run sfd crawl https://scrapling.readthedocs.io/en/latest/ \
  --max-pages 50 \
  --out crawl.json

# Cloudflare-protected site
uv run sfd build https://example.com/docs --stealth
```

Output: `./output/<skill-name>/` containing `SKILL.md`, `references/*.md`, `templates/*.py`.

## How it works

1. **Crawl** — scrapling BFS, same-host + same-path-subtree, dedup, link extraction.
2. **Extract** — HTML → markdown via html2text, picks `main`/`article`/docs containers.
3. **Plan** — Claude reads the full corpus (cached via prompt caching) and proposes skill structure.
4. **Synthesize** — Per-file generation; corpus cache is reused across calls → cheap iterations.
5. **Write** — Emit skill folder + `.skill-plan.json` for inspection.

## Architecture

```
src/skill_from_docs/
  cli.py          # click commands: build, crawl
  crawler.py      # scrapling BFS
  extractor.py    # HTML → markdown + title + headings
  synthesizer.py  # Anthropic SDK, prompt caching, plan + per-file gen
  writer.py       # emit skill folder
```

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--name` | host prefix | Skill name (kebab-case) |
| `--out` | `./output` | Output root |
| `--max-pages` | 150 | Hard cap on crawl |
| `--stealth` | off | StealthyFetcher (slower, bypasses CF/WAF) |
| `--model` | `anthropic/claude-sonnet-4.5` | Any OpenRouter model id (e.g. `openai/gpt-4o`, `google/gemini-2.0-flash`) |
| `--cache-dir` | `.skill-cache` | Cache extracted pages between runs |
| `--no-cache` | off | Force re-crawl |
