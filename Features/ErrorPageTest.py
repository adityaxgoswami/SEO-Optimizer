import requests
from urllib.parse import urljoin, urlparse

def error_page_test(url: str) -> dict:
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
    test_url = urljoin(base_url, "/this-page-should-not-exist-404-test")
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
        snippet = resp.text[:500].strip()
        result["page_snippet"] = snippet

        if resp.status_code == 403:
            result["issues"].append(
                "Received 403 Forbidden. The host may block non-browser requests or require honoring robots.txt. "
                "Consider using Playwright/headful browser rendering or checking robots.txt before scanning."
            )

        # Check for custom 404 indicators
        if resp.status_code == 404:
            if any(phrase in snippet.lower() for phrase in [
                "page not found", "404 error", "not found", "sorry", "doesn't exist", "cannot be found"
            ]):
                result["custom_404_detected"] = True
            else:
                result["issues"].append("404 page does not appear to be custom or user-friendly.")
        elif resp.status_code not in (404, 403):
            result["issues"].append(f"Expected 404 status code, got {resp.status_code}.")
    except Exception as e:
        result["issues"].append(f"Error requesting error page: {e}")

    return result

print(error_page_test("https://wikipedia.com/"))