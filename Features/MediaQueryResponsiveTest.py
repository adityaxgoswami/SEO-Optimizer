import requests
from bs4 import BeautifulSoup
import logging
import sys
from urllib.parse import urljoin
import json

def media_query_responsive_test(soup: BeautifulSoup, resources: list, session: requests.Session) -> dict:
    """
    Checks for the presence of CSS media queries in both inline <style> tags
    and external CSS files to determine if a page is responsive.

    Args:
        soup (BeautifulSoup): The parsed HTML of the page.
        resources (list): A list of all resource dictionaries collected by the scraper.
        session (requests.Session): The existing session from the scraper to reuse for requests.

    Returns:
        dict: A dictionary containing the test results.
    """
    result = {
        "has_media_queries": False,
        "checked_inline_styles": False,
        "checked_css_files": 0,
        "reason": ""
    }

    # 1. Check for @media rules in inline <style> tags
    inline_styles = soup.find_all("style")
    for style_tag in inline_styles:
        if style_tag.string and "@media" in style_tag.string:
            result["has_media_queries"] = True
            result["reason"] = "Found @media rule in an inline <style> tag."
            # We can return early as we've confirmed responsiveness
            return result
    
    result["checked_inline_styles"] = True

    # 2. If not found inline, check external CSS files
    css_files = [res for res in resources if res.get("type") == "css"]
    result["checked_css_files"] = len(css_files)

    for css_file in css_files:
        url = css_file.get("url")
        if not url:
            continue
        
        try:
            # Use the existing session to fetch CSS content
            css_response = session.get(url, timeout=10)
            css_response.raise_for_status()
            if "@media" in css_response.text:
                result["has_media_queries"] = True
                result["reason"] = f"Found @media rule in external stylesheet: {url}"
                return result
        except requests.RequestException as e:
            logging.warning(f"Could not fetch CSS file for media query check: {url}, Error: {e}")
            continue # Move to the next file if one fails

    if not result["has_media_queries"]:
        result["reason"] = "No @media rules were found in any inline styles or linked CSS files."

    return result

# --- NEW: Standalone execution block ---
if __name__ == "__main__":
    # This code only runs when you execute the file directly
    if len(sys.argv) < 2:
        print("Usage: python Features/MediaQueryResponsiveTest.py \"<url>\"")
        sys.exit(1)

    test_url = sys.argv[1]
    print(f"Running Media Query Responsive Test for: {test_url}")

    try:
        # 1. Create a session and get the page HTML
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        session.headers.update(headers)
        
        response = session.get(test_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # 2. Manually build a basic 'resources' list for the test function
        resources = []
        for link in soup.find_all("link", rel="stylesheet", href=True):
            css_url = urljoin(test_url, link["href"])
            resources.append({"type": "css", "url": css_url})

        # 3. Call the test function with the data we gathered
        test_result = media_query_responsive_test(soup, resources, session)

        # 4. Print a user-friendly result
        print("\n--- Test Results ---")
        print(json.dumps(test_result, indent=2))
        
        if test_result["has_media_queries"]:
            print("\n✅ Status: Pass")
            print(f"Conclusion: This site appears to be responsive. {test_result['reason']}")
        else:
            print("\n⚠️ Status: Fail")
            print(f"Conclusion: {test_result['reason']}")

    except requests.RequestException as e:
        print(f"\n❌ Error: Could not fetch the URL. {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

