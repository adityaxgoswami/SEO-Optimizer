import requests

def pagespeed_insights_test(url: str, api_key: str) -> dict:
    results = {
        "success": False,
        "error": None,
        "lcp": None,
        "cls": None,
        "fcp": None,
        "speed_index": None,
        "overall_score": None
    }

    if not api_key:
        results["error"] = "Google PageSpeed API key is missing."
        return results

    # The API endpoint
    api_endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={api_key}&category=PERFORMANCE"

    try:
        response = requests.get(api_endpoint, timeout=60) # This can be a slow API
        response.raise_for_status()
        data = response.json()

        # Extract the key metrics from the complex JSON response
        metrics = data.get("lighthouseResult", {}).get("audits", {})
        
        # Core Web Vitals
        lcp_metric = metrics.get("largest-contentful-paint", {})
        cls_metric = metrics.get("cumulative-layout-shift", {})
        fcp_metric = metrics.get("first-contentful-paint", {})
        
        # Other useful metrics
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

    except requests.RequestException as e:
        results["error"] = f"API request failed: {str(e)}"
    except Exception as e:
        results["error"] = f"An unexpected error occurred: {str(e)}"

    return results