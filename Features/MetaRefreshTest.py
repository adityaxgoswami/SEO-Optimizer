from bs4 import BeautifulSoup
import requests

def meta_refresh_test(url: str) -> dict:
    """
    Checks for <meta http-equiv="refresh"> tags in the HTML.
    Returns a dict with findings and issues.
    """
    result = {
        "url": url,
        "meta_refresh_found": False,
        "meta_refresh_content": [],
        "issues": []
    }

    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        meta_tags = soup.find_all("meta", attrs={"http-equiv": "refresh"})
        if meta_tags:
            result["meta_refresh_found"] = True
            for tag in meta_tags:
                content = tag.get("content", "")
                result["meta_refresh_content"].append(content)
            result["issues"].append("Meta refresh tag found. This can negatively affect SEO and user experience.")
        else:
            result["meta_refresh_found"] = False
    except Exception as e:
        result["issues"].append(f"Error checking meta refresh: {e}")

    return result
