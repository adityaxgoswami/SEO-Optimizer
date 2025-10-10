
def mixed_content_test(is_https: bool, resources: list) -> dict:
    result = {
        "has_mixed_content": False,
        "insecure_urls": []
    }

    if not is_https:
        return result

    insecure_urls = []
    for resource in resources:
        if resource.get("url", "").startswith("http://"):
            insecure_urls.append(resource.get("url"))

    if insecure_urls:
        result["has_mixed_content"] = True
        result["insecure_urls"] = insecure_urls

    return result