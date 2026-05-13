# Site Scraping Pattern Library

After every successful scrape of a new type of site, the Agent should prompt the user whether to append the experience to this file.

---

## Discourse Forums (linux.do, meta.discourse.org, etc.)

**Site characteristics**: Cloudflare protection + Ember.js SPA + login state differentiation
**Recommended Fetcher**: StealthyFetcher
**Key parameters**:
- `solve_cloudflare=True` — required
- `network_idle=True` — wait for Ember rendering to complete
- `timeout=60000` — CF verification is slow, at least 60 seconds (milliseconds)
**Login cookie fields**: `_forum_session`, `_t`
**Not needed**: `cf_clearance` (StealthyFetcher obtains it automatically)
**JSON API**: `/t/topic/{id}.json` (only available after passing CF)
**Selector reference**:
- Post list: `.topic-post`
- Author: `[data-user-card]::attr(data-user-card)`
- Content: `.cooked` → `.get_all_text(strip=True)`

---

## Static Blogs / Doc Sites (GitHub Pages, Hugo, Jekyll)

**Site characteristics**: Pure static HTML, no JS rendering dependency, no anti-bot
**Recommended Fetcher**: Fetcher (fastest)
**Key parameters**: `impersonate='chrome'`, `timeout=30`
**Selector reference**: `article`, `.content`, `.post-body`

---

## SPA Applications (React/Vue/Next.js)

**Site characteristics**: JS-rendered, content not in initial HTML
**Recommended Fetcher**: DynamicFetcher
**Key parameters**:
- `network_idle=True` — wait for API requests to complete
- `wait_selector='.content-loaded'` — wait for a key element (adjust to reality)
- `disable_resources=True` — skip fonts/images for speed
**Notes**: First check whether an API endpoint exists that can be called directly with Fetcher (faster and more stable)

---

## API Endpoints (REST/GraphQL)

**Site characteristics**: Returns JSON, no HTML parsing needed
**Recommended Fetcher**: Fetcher
**Key parameters**: `impersonate='chrome'`, custom `headers`
**Handling**: `page.text` to get the JSON → parse with `json.loads()`
**Notes**: If the API has anti-bot protection, you may need to include Referer/Origin and similar headers

---

## TAPD Project Management (tapd.cn)

**Site characteristics**: React SPA + enterprise login state + paginated lazy loading ("Load more" button)
**Recommended approach**: Drive Playwright directly (not the scrapling Fetcher)
**Reason**: DynamicFetcher can render the first screen but can't click to interact; the scrapling Fetcher returns empty `page.text` when calling the API; curl can reach the API but gets 500 (CSRF validation requires a browser environment)
**Key flow**:
1. Load the page with Playwright + cookies, `wait_until='networkidle'`
2. Loop-click the "Load more" button to load all data
3. `page.inner_text('body')` to extract plain text, parse line by line
**Cookie format**: `list[dict]`, required `name/value/domain/path`, domain is `.tapd.cn`
**API endpoint** (for reference, used internally by the browser): `POST /api/my_worktable/my_worktable/get_my_worktable_by_page`
**CSRF**: the value of cookie `dsc-token` must be sent as the `DSC-TOKEN` header (added automatically by the axios interceptor)
**Known limitations**: The scrapling Fetcher returns an empty response to the TAPD API (`page.text` is empty); use Playwright or curl instead
**Data structure**: Text is arranged line by line, type prefix (P/E/PROGRAM/TEST/BUG) → title → status → priority → ...

---

## Template: Adding a New Site Pattern

Copy the template below, replace with specific content, and append to this file:

```markdown
## Site Name/Type (representative domain)

**Site characteristics**: description
**Recommended Fetcher**: Fetcher / StealthyFetcher / DynamicFetcher
**Key parameters**:
- `param_name=value` — explanation
**Selector reference**: CSS selector examples
**Notes**: lessons learned
```
