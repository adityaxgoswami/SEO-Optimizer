import requests
from urllib.parse import urljoin, urlparse

def error_page_test(url: str) -> dict:
    """
    Tests if a website has a custom 404 error page.

    Args:
        url (str): The base URL of the site to check.

    Returns:
        dict: A dictionary containing the test results.
    """
    result = {
        "url": url,
        "test_url": "",
        "status_code": None,
        "custom_404_detected": False,
        "issues": [],
        "page_snippet": ""
    }

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    # Create a URL that is highly unlikely to exist
    test_url = urljoin(base_url, "/this-page-should-definitely-not-exist-404-test")
    result["test_url"] = test_url

    try:
        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        resp = session.get(test_url, timeout=10, headers=headers)
        result["status_code"] = resp.status_code
        # Get a snippet of the page content to analyze
        snippet = resp.text[:500].strip()
        result["page_snippet"] = snippet

        # Handle cases where access is forbidden
        if resp.status_code == 403:
            result["issues"].append(
                "Received 403 Forbidden. The host may block automated requests. "
                "Consider more advanced scanning methods if this persists."
            )

        # Check for indicators of a custom 404 page
        if resp.status_code == 404:
            # List of common phrases found on user-friendly 404 pages
            if any(phrase in snippet.lower() for phrase in [
                "page not found", "404 error", "not found", "sorry", "doesn't exist", "cannot be found"
            ]):
                result["custom_404_detected"] = True
            else:
                result["issues"].append("A 404 status was returned, but the page does not appear to be a custom, user-friendly error page.")
        # If the server returns a success code for a non-existent page, it's a "soft 404" issue
        elif resp.status_code >= 200 and resp.status_code < 300:
            result["issues"].append(f"Expected a 404 status code for a non-existent page, but got {resp.status_code}. This is a 'soft 404' and is bad for SEO.")
        elif resp.status_code not in (404, 403):
            result["issues"].append(f"Expected 404 status code, but received {resp.status_code}.")

    except requests.RequestException as e:
        result["issues"].append(f"An error occurred while requesting the test error page: {e}")

    return result

# Standalone execution block for testing
if __name__ == '__main__':
    import json
    test_url = "https://www.wikipedia.org/"
    print(f"Running Custom Error Page Test for: {test_url}")
    test_result = error_page_test(test_url)
    print(json.dumps(test_result, indent=2))
