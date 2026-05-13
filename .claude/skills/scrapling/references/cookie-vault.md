# Cookie Vault

Records historical cookies partitioned by site, for quick lookup and reuse during scraping.

> **Security note**: This file stores sensitive cookie values. Do not commit it to version control or share it with others.
> For actual use, copy this file to `cookie-vault.local.md` and fill in real values.

---

## Example Site (example.com)

**Last updated**: YYYY-MM-DD
**Status**: valid / possibly expired
**Login cookie fields**: `session_id`, `auth_token`
**Fetcher type**: StealthyFetcher

### Playwright Format (for StealthyFetcher/DynamicFetcher)

```python
cookies = [
    {'name': 'session_id', 'value': '<YOUR_SESSION_ID>', 'domain': '.example.com', 'path': '/'},
    {'name': 'auth_token', 'value': '<YOUR_AUTH_TOKEN>', 'domain': '.example.com', 'path': '/'},
]
```

### Notes

- Obtain real values from your browser's DevTools > Application > Cookies
- Cookie expiry depends on the site's settings; re-fetch once expired

---

## Template: Adding a New Site

Copy the template below, replace with specific content, and append to this file:

```markdown
## Site Name (domain)

**Last updated**: YYYY-MM-DD
**Status**: valid / possibly expired
**Login cookie fields**: `field1`, `field2`
**Fetcher type**: Fetcher / StealthyFetcher / DynamicFetcher

### Playwright Format

\```python
cookies = [
    {'name': 'field1', 'value': '...', 'domain': '.example.com', 'path': '/'},
]
\```

### Notes

- relevant caveats
```
