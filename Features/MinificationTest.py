import requests
import logging

# Configure logging to see warnings about failed fetches
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def is_minified(content: str) -> bool:
    """
    Determines if a string of content (CSS or JS) is likely minified.
    It does this by calculating the ratio of non-whitespace characters to total characters.
    """
    if not content:
        return False
    
    total_chars = len(content)
    # Efficiently count non-whitespace characters
    non_whitespace_chars = len("".join(content.split()))
    
    # If the ratio is very high (e.g., > 95%), it's almost certainly minified.
    ratio = non_whitespace_chars / total_chars if total_chars > 0 else 0
    return ratio > 0.95

def minification_test(resources: list, session: requests.Session) -> dict:
    """
    Checks a sample of linked CSS and JavaScript files for minification.

    Args:
        resources (list): A list of resource dictionaries from the scraper.
        session (requests.Session): The session to use for making requests.

    Returns:
        dict: A dictionary containing the minification test results.
    """
    results = {
        "js": {"total_checked": 0, "minified_count": 0, "unminified_list": []},
        "css": {"total_checked": 0, "minified_count": 0, "unminified_list": []}
    }

    # Get up to 5 JS and 5 CSS files to check to avoid excessive requests
    js_to_check = [r['url'] for r in resources if r.get('type') == 'js' and r.get('url')][:5]
    css_to_check = [r['url'] for r in resources if r.get('type') == 'css' and r.get('url')][:5]

    for url in js_to_check:
        results["js"]["total_checked"] += 1
        try:
            res = session.get(url, timeout=10)
            res.raise_for_status()  # Raise an exception for bad status codes
            content = res.text
            if is_minified(content):
                results["js"]["minified_count"] += 1
            else:
                results["js"]["unminified_list"].append(url)
        except requests.RequestException as e:
            # Log the error instead of silently passing
            logging.warning(f"Could not fetch JS file for minification check: {url}, Error: {e}")

    for url in css_to_check:
        results["css"]["total_checked"] += 1
        try:
            res = session.get(url, timeout=10)
            res.raise_for_status()
            content = res.text
            if is_minified(content):
                results["css"]["minified_count"] += 1
            else:
                results["css"]["unminified_list"].append(url)
        except requests.RequestException as e:
            # Log the error instead of silently passing
            logging.warning(f"Could not fetch CSS file for minification check: {url}, Error: {e}")

    return results

# Standalone execution block for testing
if __name__ == '__main__':
    import json
    # Mock resources for a standalone test
    mock_resources = [
        # A minified JS file from a CDN
        {'type': 'js', 'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'},
        # A non-minified CSS file (hypothetical)
        {'type': 'css', 'url': 'https://www.w3schools.com/w3css/4/w3.css'},
    ]
    
    print("Running Minification Test with mock resources...")
    with requests.Session() as s:
        test_results = minification_test(mock_resources, s)
    
    print(json.dumps(test_results, indent=2))
