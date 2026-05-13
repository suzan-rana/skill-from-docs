# Scrapling Installation and Maintenance

## Package Managers

Both pip and uv are supported — run the commands for whichever package manager the project actually uses. Detection rule: if `uv.lock` exists at the project root or `pyproject.toml` contains `[tool.uv]`, use uv; otherwise use pip.

## Installation Tiers

| extras | pip | uv (project) | Contents |
|---|---|---|---|
| core | `pip install scrapling` | `uv add scrapling` | Selector only, no network fetching |
| **fetchers** (recommended) | `pip install "scrapling[fetchers]"` | `uv add "scrapling[fetchers]"` | + Fetcher/StealthyFetcher/DynamicFetcher |
| ai | `pip install "scrapling[ai]"` | `uv add "scrapling[ai]"` | + transformers |
| shell | `pip install "scrapling[shell]"` | `uv add "scrapling[shell]"` | + interactive shell |
| all | `pip install "scrapling[all]"` | `uv add "scrapling[all]"` | All features |

For uv global / non-pyproject scenarios, replace `uv add` with `uv pip install`.

**Recommendation**: For most scenarios `scrapling[fetchers]` is sufficient.

## Check Installation Status

```bash
# Show version (works across package managers)
python -c "import scrapling; print(scrapling.__version__)"

# Verify the base package is available
python -c "from scrapling.parser import Selector; print('Parser OK')"

# Verify Fetcher is available (requires [fetchers])
python -c "from scrapling.fetchers import Fetcher; print('Fetcher OK')"

# Verify StealthyFetcher is available
python -c "from scrapling.fetchers import StealthyFetcher; print('StealthyFetcher OK')"

# Verify DynamicFetcher is available
python -c "from scrapling.fetchers import DynamicFetcher; print('DynamicFetcher OK')"
```

## Install Browser Dependencies

StealthyFetcher and DynamicFetcher require browser engines. After installing, run:

```bash
# pip / global Python (when PATH contains the Scripts directory)
scrapling install

# inside a uv project
uv run scrapling install

# Universal fallback (avoids PATH issues)
python -c "from scrapling.cli import main; main(['install'])"
```

## Upgrade

```bash
# pip
pip install --upgrade "scrapling[fetchers]"

# uv (project)
uv lock --upgrade-package scrapling
uv sync

# uv (global / no pyproject)
uv pip install --upgrade "scrapling[fetchers]"
```

After upgrading, it's recommended to re-verify that all three Fetchers work (see the check commands above).

## Full Three-Fetcher Verification Script

```python
#!/usr/bin/env python3
"""Verify that all three scrapling Fetchers work properly"""
import scrapling

print(f"scrapling version: {scrapling.__version__}")

# 1. Fetcher (curl_cffi)
from scrapling.fetchers import Fetcher
page = Fetcher.get("https://httpbin.org/get", impersonate='chrome', timeout=15)
print(f"Fetcher: status={page.status}")

# 2. StealthyFetcher (Camoufox)
from scrapling.fetchers import StealthyFetcher
page = StealthyFetcher.fetch("https://httpbin.org/get", headless=True, timeout=30000)
print(f"StealthyFetcher: status={page.status}")

# 3. DynamicFetcher (Playwright)
from scrapling.fetchers import DynamicFetcher
page = DynamicFetcher.fetch("https://httpbin.org/get", headless=True, timeout=30000)
print(f"DynamicFetcher: status={page.status}")

print("\nAll Fetchers verified successfully")
```
