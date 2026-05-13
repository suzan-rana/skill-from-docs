# Scrapling API Quick Reference

## Fetcher (based on curl_cffi, fastest)

```python
from scrapling.fetchers import Fetcher

# GET request
page = Fetcher.get(url, impersonate='chrome', timeout=30, headers=None, cookies=None)

# POST request
page = Fetcher.post(url, data=None, json=None, impersonate='chrome', timeout=30)
```

**Cookie format**: `dict` — `{'name': 'value'}`
**Timeout unit**: seconds

## FetcherSession (maintains session cookies)

```python
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as s:
    s.post(login_url, data={'user': '...', 'pass': '...'})
    page = s.get(target_url)
```

## StealthyFetcher (Camoufox, bypasses anti-bot)

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    url,
    headless=True,           # headless mode
    solve_cloudflare=True,   # automatically pass Cloudflare
    cookies=None,            # list[dict] format
    timeout=60000,           # milliseconds
    network_idle=True,       # wait for network idle
    hide_canvas=True,        # hide canvas fingerprint
    block_webrtc=True,       # block WebRTC IP leaks
    disable_resources=False, # disable images/fonts for speed
)
```

**Cookie format**: `list[dict]` — `[{'name': 'n', 'value': 'v', 'domain': '.site.com', 'path': '/'}]`
**Timeout unit**: milliseconds

## DynamicFetcher (Playwright, JS rendering)

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    url,
    headless=True,
    cookies=None,            # list[dict] format
    timeout=30000,           # milliseconds
    network_idle=True,       # wait for network idle
    wait_selector=None,      # wait for a specific element to appear
    disable_resources=True,  # skip images/fonts/CSS for speed
)
```

**Cookie format**: `list[dict]`
**Timeout unit**: milliseconds

## Selector (pure HTML parsing, no network request)

```python
from scrapling.parser import Selector

page = Selector(html_string, url='https://base-url.com')
```

## Common Response Attributes

```python
page.status          # HTTP status code (int)
page.text            # raw HTML/text content (str)
page.url             # final URL (may have been redirected)
page.cookies         # response cookies
page.headers         # response headers
```

## Selector Methods

```python
# CSS selector
page.css('div.content')              # returns a list of elements
page.css_first('h1')                 # returns the first matching element

# XPath selector
page.xpath('//div[@class="content"]')

# Text extraction pseudo-elements
page.css('h1::text')                 # extract text content
page.css('a::attr(href)')            # extract attribute value

# Get text of all matching results
results = page.css('h1::text').getall()  # list[str]

# Get text of the first matching result
result = page.css('h1::text').get()      # str | None
```

## Element Methods

```python
element = page.css_first('div.post')

element.text                          # direct child text
element.get_all_text(strip=True)      # recursively get all text
element.attrib                        # attribute dict
element.attrib.get('href')            # get a single attribute
element.css('span.author::text')      # continue selecting within the subtree
element.parent                        # parent element
element.children                      # list of child elements
```

## Regex Extraction

```python
# Extract matches from text
page.re(r'price: \$(\d+\.\d+)')      # list[str] — all matches
page.re_first(r'price: \$(\d+\.\d+)')  # str | None — first match
```
