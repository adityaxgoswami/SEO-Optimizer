import re
from urllib.parse import urlparse, unquote

def seo_friendly_url_test(url: str, keywords: list[str] = None) -> dict:
    result = {
        "url": url,
        "is_seo_friendly": True,
        "issues": [],
        "keyword_found": [],
        "path": "",
        "query": "",
        "fragment": "",
    }

    parsed = urlparse(url)
    path = unquote(parsed.path)
    query = parsed.query
    fragment = parsed.fragment

    result["path"] = path
    result["query"] = query
    result["fragment"] = fragment

    # Check for session IDs or tracking parameters
    if re.search(r"(sid=|phpsessid=|jsessionid=|sessionid=)", query, re.I):
        result["is_seo_friendly"] = False
        result["issues"].append("Session ID or tracking parameter found in query string.")

    # Check for excessive query parameters
    if query and len(query.split("&")) > 3:
        result["is_seo_friendly"] = False
        result["issues"].append("Too many query parameters.")

    # Check for hashes/fragments
    if fragment:
        result["is_seo_friendly"] = False
        result["issues"].append("URL contains fragment/hash.")

    # Check for uppercase letters
    if re.search(r"[A-Z]", path):
        result["is_seo_friendly"] = False
        result["issues"].append("Uppercase letters found in path.")

    # Check for special characters (allow hyphens and slashes)
    if re.search(r"[^a-z0-9\-\/]", path, re.I):
        result["is_seo_friendly"] = False
        result["issues"].append("Special characters found in path.")

    # Check for underscores
    if "_" in path:
        result["is_seo_friendly"] = False
        result["issues"].append("Underscores found in path (prefer hyphens).")

    # Check for readability (words separated by hyphens)
    words = re.split(r"[\-/]", path.strip("/"))
    if any(len(word) > 30 for word in words if word):  # very long words
        result["is_seo_friendly"] = False
        result["issues"].append("Very long word found in path.")

    # Keyword check
    if keywords:
        for kw in keywords:
            if kw.lower() in path.lower():
                result["keyword_found"].append(kw)

    if keywords and not result["keyword_found"]:
        result["issues"].append("No target keywords found in URL path.")

    return result