import re
from bs4 import BeautifulSoup
from requests import Session, exceptions
import logging

def media_query_responsive_test(soup: BeautifulSoup, resources: list, session: Session) -> dict:
    """
    Checks for the presence of CSS media queries in both inline styles and external stylesheets.

    Args:
        soup: The BeautifulSoup object of the page.
        resources: A list of resource dictionaries from the scraper.
        session: The requests Session object to fetch external files.

    Returns:
        A dictionary containing the test result.
    """
    has_media_queries = False
    analysis = "No CSS media queries were found. The page may not be properly responsive."

    # 1. Check for media queries in inline <style> tags
    for style_tag in soup.find_all("style"):
        if style_tag.string and re.search(r"@media", style_tag.string, re.IGNORECASE):
            has_media_queries = True
            analysis = "CSS media queries found in inline <style> tags."
            break
    
    if has_media_queries:
        return {"has_media_queries": True, "analysis": analysis}

    # 2. If not found inline, check external CSS files
    css_urls = [
        item['url'] for item in resources 
        if item.get('url') and (
            (item.get('content_type') and 'css' in item.get('content_type')) or 
            item['url'].lower().endswith('.css')
        )
    ]
    
    for css_url in css_urls:
        try:
            # Use the existing session to make the request, respecting existing headers
            response = session.get(css_url, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            css_content = response.text
            if re.search(r"@media", css_content, re.IGNORECASE):
                has_media_queries = True
                analysis = "CSS media queries found in external stylesheets."
                break  # Exit as soon as we find the first one
        except exceptions.RequestException as e:
            logging.warning(f"Could not fetch or read CSS file {css_url} for media query check: {e}")
            continue

    return {"has_media_queries": has_media_queries, "analysis": analysis}
