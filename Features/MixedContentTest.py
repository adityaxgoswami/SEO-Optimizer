def mixed_content_test(is_https: bool, resources: list) -> dict:
    """
    Identifies insecure (HTTP) resources being loaded on a secure (HTTPS) page.

    Args:
        is_https (bool): True if the main page was loaded over HTTPS.
        resources (list): A list of all resource dictionaries collected by the scraper.

    Returns:
        dict: A dictionary containing the test results.
    """
    result = {
        "has_mixed_content": False,
        "insecure_urls": []
    }

    # This test is only relevant for pages served over HTTPS.
    if not is_https:
        return result

    insecure_urls = []
    for resource in resources:
        url = resource.get("url", "")
        # Check if a resource URL starts with "http://" (and not "https://")
        if url.startswith("http://"):
            insecure_urls.append(url)

    if insecure_urls:
        result["has_mixed_content"] = True
        result["insecure_urls"] = insecure_urls

    return result

# Standalone execution block for testing
if __name__ == '__main__':
    import json
    
    # Mock resources for testing scenarios
    mock_resources_clean = [
        {'url': 'https://example.com/style.css'},
        {'url': 'https://example.com/script.js'},
    ]
    mock_resources_mixed = [
        {'url': 'https://example.com/style.css'},
        {'url': 'http://example.com/script.js'}, # Insecure JS
        {'url': 'http://unsecure.com/image.jpg'}, # Insecure image
    ]

    print("--- Testing on HTTPS page with NO mixed content ---")
    result_clean = mixed_content_test(is_https=True, resources=mock_resources_clean)
    print(json.dumps(result_clean, indent=2))
    
    print("\n--- Testing on HTTPS page WITH mixed content ---")
    result_mixed = mixed_content_test(is_https=True, resources=mock_resources_mixed)
    print(json.dumps(result_mixed, indent=2))

    print("\n--- Testing on non-HTTPS page (test should be skipped) ---")
    result_http = mixed_content_test(is_https=False, resources=mock_resources_mixed)
    print(json.dumps(result_http, indent=2))
