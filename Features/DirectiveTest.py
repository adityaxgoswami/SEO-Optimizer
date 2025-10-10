import requests
from urllib.parse import urlparse

def disallow_directive_test(url: str, robots_txt_content: str = None) -> dict:
    result = {
        "url": url,
        "robots_txt_url": "",
        "disallow_rules": [],
        "issues": [],
        "robots_txt_found": False
    }

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    result["robots_txt_url"] = robots_url

    content_to_parse = None

    headers = {
        "User-Agent": "MySEOAnalyzerBot/1.0 (+https://example.com/contact)"  # 👈 Add this
    }

    if robots_txt_content:
        result["robots_txt_found"] = True
        content_to_parse = robots_txt_content
    else:
        try:
            resp = requests.get(robots_url, headers=headers, timeout=8)  # 👈 Add headers here
            if resp.status_code == 200:
                result["robots_txt_found"] = True
                content_to_parse = resp.text
            else:
                result["issues"].append(f"robots.txt not found (HTTP {resp.status_code}).")
        except Exception as e:
            result["issues"].append(f"Error fetching robots.txt: {e}")

    if content_to_parse:
        lines = content_to_parse.splitlines()
        for line in lines:
            line = line.strip()
            if line.lower().startswith("disallow:"):
                rule = line[9:].strip()
                if rule:
                    result["disallow_rules"].append(rule)

        if not result["disallow_rules"]:
            result["issues"].append("No Disallow rules found in robots.txt.")

    return result


print(disallow_directive_test("https://wikipedia.com/"))
