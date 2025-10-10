#checking js and css files to see if they have been minified or not---> helps in download speed

# Features/MinificationTest.py
import requests

def is_minified(content: str) -> bool:
    if not content:
        return False
    
    total_chars = len(content)
    non_whitespace_chars = len("".join(content.split()))
    
    # If the ratio of non-whitespace to total characters is very high,
    # it's likely minified.
    ratio = non_whitespace_chars / total_chars
    return ratio > 0.95

def minification_test(resources: list, session: requests.Session) -> dict:

    results = {
        "js": {"total": 0, "minified_count": 0, "unminified_list": []},
        "css": {"total": 0, "minified_count": 0, "unminified_list": []}
    }

    js_to_check = [r['url'] for r in resources if r['type'] == 'js'][:5]
    css_to_check = [r['url'] for r in resources if r['type'] == 'css'][:5]

    for url in js_to_check:
        results["js"]["total"] += 1
        try:
            res = session.get(url, timeout=10)
            res.raise_for_status()
            content = res.text
            if is_minified(content):
                results["js"]["minified_count"] += 1
            else:
                results["js"]["unminified_list"].append(url)
        except requests.RequestException:
            pass

    for url in css_to_check:
        results["css"]["total"] += 1
        try:
            res = session.get(url, timeout=10)
            res.raise_for_status()
            content = res.text
            if is_minified(content):
                results["css"]["minified_count"] += 1
            else:
                results["css"]["unminified_list"].append(url)
        except requests.RequestException:
            pass

    return results