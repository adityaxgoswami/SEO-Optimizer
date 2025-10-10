from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

def responsive_image_test(url: str) -> dict:
    """
    Checks for responsive image attributes (srcset or sizes) and lazy-loading in <img> tags.
    Returns a dict with counts and issues.
    """
    result = {
        "url": url,
        "total_images": 0,
        "responsive_images": 0,
        "non_responsive_images": 0,
        "lazy_loaded_images": 0,
        "non_responsive_img_urls": [],
        "issues": []
    }

    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        img_tags = soup.find_all("img")
        result["total_images"] = len(img_tags)
        for img in img_tags:
            is_responsive = img.has_attr("srcset") or img.has_attr("sizes")
            is_lazy = img.has_attr("loading") and img["loading"].lower() == "lazy"
            if is_responsive:
                result["responsive_images"] += 1
            else:
                result["non_responsive_images"] += 1
                # Clean URL using urljoin
                if img.has_attr("src"):
                    clean_url = urljoin(url, img["src"])
                    result["non_responsive_img_urls"].append(clean_url)
            if is_lazy:
                result["lazy_loaded_images"] += 1
        if result["non_responsive_images"] > 0:
            result["issues"].append(
                f"{result['non_responsive_images']} images lack responsive attributes (srcset or sizes)."
            )
        if result["lazy_loaded_images"] == 0 and result["total_images"] > 0:
            result["issues"].append("No images use lazy-loading (loading='lazy').")
    except Exception as e:
        result["issues"].append(f"Error checking responsive images: {e}")

    return result
