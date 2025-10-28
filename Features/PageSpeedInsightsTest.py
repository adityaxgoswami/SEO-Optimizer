import requests
import os

def pagespeed_insights_test(url: str, api_key: str = None) -> dict:
    """
    Fetches key web performance metrics from the Google PageSpeed Insights API.

    Args:
        url (str): The URL to analyze.
        api_key (str, optional): Your Google PageSpeed API key. Defaults to None.

    Returns:
        dict: A dictionary containing performance scores and metrics.
    """
    results = {
        "success": False,
        "error": None,
        "lcp": None,
        "cls": None,
        "fcp": None,
        "speed_index": None,
        "overall_score": None
    }
    
    # Try to get API key from environment variable if not provided
    if not api_key:
        api_key = os.getenv("PAGESPEED_API_KEY")

    if not api_key:
        results["error"] = "Google PageSpeed API key is missing. Provide it as an argument or set the 'PAGESPEED_API_KEY' environment variable."
        return results

    # The Google PageSpeed Insights API endpoint
    api_endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={api_key}&category=PERFORMANCE"

    try:
        # This API can be slow, so a long timeout is necessary
        response = requests.get(api_endpoint, timeout=90)
        response.raise_for_status()
        data = response.json()
        
        if "error" in data:
            results["error"] = data["error"].get("message", "An unknown API error occurred.")
            return results

        # Extract the key metrics from the complex JSON response
        metrics = data.get("lighthouseResult", {}).get("audits", {})
        
        # Core Web Vitals
        lcp_metric = metrics.get("largest-contentful-paint", {})
        cls_metric = metrics.get("cumulative-layout-shift", {})
        fcp_metric = metrics.get("first-contentful-paint", {})
        speed_index_metric = metrics.get("speed-index", {})
        
        # Overall performance score (0-100)
        performance_category = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {})
        
        # Populate the results dictionary
        results["success"] = True
        results["overall_score"] = int(performance_category.get("score", 0) * 100)
        results["lcp"] = lcp_metric.get("displayValue")
        results["cls"] = cls_metric.get("displayValue")
        results["fcp"] = fcp_metric.get("displayValue")
        results["speed_index"] = speed_index_metric.get("displayValue")

    except requests.Timeout:
        results["error"] = "The request to the PageSpeed Insights API timed out."
    except requests.RequestException as e:
        results["error"] = f"API request failed: {str(e)}"
    except Exception as e:
        results["error"] = f"An unexpected error occurred: {str(e)}"

    return results

# Standalone execution block for testing
if __name__ == '__main__':
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python PageSpeedInsightsTest.py \"<url>\" [api_key]")
        sys.exit(1)
        
    test_url = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Running PageSpeed Insights Test for: {test_url}")
    test_results = pagespeed_insights_test(test_url, api_key=key)
    print(json.dumps(test_results, indent=2))
