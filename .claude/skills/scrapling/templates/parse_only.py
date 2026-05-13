#!/usr/bin/env python3
"""Pure HTML parsing template (does not require the fetchers dependency)
Purpose: when you already have HTML content (from WebFetch/file/API) and only need to parse and extract
Replace: HTML_SOURCE, BASE_URL, CSS_SELECTOR
"""
from scrapling.parser import Selector

HTML_SOURCE = """{{HTML}}"""
# Or read from a file: HTML_SOURCE = open('page.html').read()

page = Selector(HTML_SOURCE, url='{{BASE_URL}}')

results = page.css('{{CSS_SELECTOR}}')
for item in results:
    print(item.get_all_text(strip=True))
