# Scrapling Pitfalls and Solutions

## ModuleNotFoundError: curl_cffi

**Error message**: `ModuleNotFoundError: No module named 'curl_cffi'`
**Cause**: Installed the base package `pip install scrapling`, which doesn't include fetcher dependencies
**Solution**:
```bash
pip install "scrapling[fetchers]"
```

## Cloudflare 403 + "Just a moment"

**Error message**: Returns 403, page contains "Just a moment" or "Checking your browser"
**Cause**: Fetcher (curl_cffi) cannot pass Cloudflare verification
**Solution**: Switch to StealthyFetcher with `solve_cloudflare=True`
```python
from scrapling.fetchers import StealthyFetcher
page = StealthyFetcher.fetch(url, headless=True, solve_cloudflare=True, timeout=60000)
```

## cf_clearance cookie invalid

**Error message**: Passing in `cf_clearance` cookie manually but still blocked by Cloudflare
**Cause**: `cf_clearance` is bound to the browser fingerprint (TLS/JA3/UA) and cannot be reused across clients
**Solution**: Don't manually pass `cf_clearance`; let StealthyFetcher obtain it itself by passing Cloudflare

## Expected array, got object at $.cookies

**Error message**: `Expected array, got object` at `$.cookies`
**Cause**: Browser-based Fetchers (StealthyFetcher/DynamicFetcher) require cookies as `list[dict]`, not `dict`
**Solution**:
```python
# ❌ Wrong
cookies = {'name': 'value'}

# ✅ Correct
cookies = [{'name': 'cookie_name', 'value': 'cookie_value', 'domain': '.site.com', 'path': '/'}]
```

## Cookie should have a url or a domain/path pair

**Error message**: `Cookie should have a url or a domain/path pair`
**Cause**: The cookie dict is missing `domain` and `path` fields
**Solution**: Every cookie dict must include `domain` (starting with `.`) and `path` (usually `/`)
```python
cookies = [
    {'name': 'token', 'value': 'abc', 'domain': '.example.com', 'path': '/'},
]
```

## 404 "page is private"

**Error message**: Returns 404, page indicates content is private
**Cause**: Cloudflare has been passed, but the target page requires a logged-in session
**Solution**: Include login cookies (obtained manually from the browser); see `cookie-vault.md`
```python
page = StealthyFetcher.fetch(
    url,
    solve_cloudflare=True,
    cookies=[{'name': '_session', 'value': '...', 'domain': '.site.com', 'path': '/'}],
    timeout=60000,
)
```

## Cloudflare Multi-round Turnstile

**Symptom**: StealthyFetcher takes a long time to run (30-90 seconds), logs show multiple Turnstile verifications
**Cause**: Normal behavior — Cloudflare sometimes requires 2-3 rounds of verification
**Solution**: Be patient and make sure `timeout` is long enough (at least 60000ms). If it fails on timeout, increase to 120000ms and retry

## scrapling: command not found

**Error message**: `scrapling: command not found`
**Cause**: The Python Scripts directory is not in PATH
**Solution**:
```python
# Option 1: use python -c
python -c "from scrapling.cli import main; main(['install'])"

# Option 2: use python -m (if supported)
python -m scrapling install
```

## StealthyFetcher/DynamicFetcher reports browser not installed

**Error message**: Something like "browser not found" or Playwright/Camoufox-related errors
**Cause**: Browser dependencies are not installed
**Solution**:
```bash
# Install scrapling browser dependencies
scrapling install
# or
python -c "from scrapling.cli import main; main(['install'])"
```
