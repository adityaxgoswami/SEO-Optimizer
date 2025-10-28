from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import re

# Conditional import of Pillow for image analysis
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def extract_css_dimensions(style: str):
    """Extracts width and height from an inline style string."""
    width = height = None
    if style:
        # Regex to find width and height in pixels
        width_match = re.search(r'width\s*:\s*([0-9.]+)px', style)
        height_match = re.search(r'height\s*:\s*([0-9.]+)px', style)
        if width_match:
            width = int(float(width_match.group(1)))
        if height_match:
            height = int(float(height_match.group(1)))
    return width, height

def image_ratio_test(url: str, soup: BeautifulSoup, validate_real_size: bool = False) -> dict:
    """
    Extracts image width/height from HTML attributes and inline CSS.
    Optionally validates dimensions by fetching the image file if Pillow is installed.
    """
    result = {
        "url": url,
        "images_checked": 0,
        "images_with_dimensions": [],
        "images_missing_dimensions": [],
        "images_dimension_mismatch": [],
        "issues": []
    }

    img_tags = soup.find_all("img")
    result["images_checked"] = len(img_tags)

    for img in img_tags:
        src = img.get("src")
        # Skip empty or data URIs
        if not src or src.startswith('data:'):
            continue
        
        img_url = urljoin(url, src)

        # Try to get dimensions from HTML attributes first
        width = img.get("width")
        height = img.get("height")

        # If not present, try to get from inline CSS
        if not width or not height:
            style = img.get("style", "")
            css_width, css_height = extract_css_dimensions(style)
            width = width or css_width
            height = height or css_height

        if width and height:
            try:
                w, h = int(width), int(height)
                aspect_ratio = round(w / h, 2) if h != 0 else 'N/A'
                img_info = {"src": img_url, "declared_width": w, "declared_height": h, "declared_aspect_ratio": aspect_ratio}

                # Optional: Validate real size with Pillow if requested and available
                if validate_real_size and PIL_AVAILABLE:
                    try:
                        img_resp = requests.get(img_url, timeout=5, stream=True)
                        img_resp.raise_for_status()
                        pil_img = Image.open(BytesIO(img_resp.content))
                        real_w, real_h = pil_img.size
                        
                        img_info["real_width"] = real_w
                        img_info["real_height"] = real_h
                        
                        if real_w != w or real_h != h:
                            result["images_dimension_mismatch"].append(img_info)
                    except Exception as e:
                        result["issues"].append(f"Could not validate real image size for {img_url}: {e}")
                
                result["images_with_dimensions"].append(img_info)
            except (ValueError, TypeError):
                result["issues"].append(f"Invalid width/height attributes for image: {img_url} (width='{width}', height='{height}')")
        else:
            result["images_missing_dimensions"].append(img_url)

    if result["images_missing_dimensions"]:
        count = len(result['images_missing_dimensions'])
        result["issues"].append(f"{count} image(s) are missing explicit width and height attributes, which can cause layout shifts.")
    
    if result["images_dimension_mismatch"]:
        count = len(result['images_dimension_mismatch'])
        result["issues"].append(f"{count} image(s) have declared dimensions that mismatch their actual size.")

    if validate_real_size and not PIL_AVAILABLE:
        result["issues"].append("Pillow library not installed; real image size validation was skipped. Run 'pip install Pillow' to enable.")

    return result

# Standalone execution block for testing
if __name__ == '__main__':
    import json
    test_url = "https://www.wikipedia.org/"
    print(f"Running Image Ratio Test for: {test_url}")
    try:
        response = requests.get(test_url, timeout=10)
        page_soup = BeautifulSoup(response.text, "lxml")
        # Set validate_real_size to True to test Pillow functionality (can be slow)
        test_result = image_ratio_test(test_url, page_soup, validate_real_size=False)
        print(json.dumps(test_result, indent=2))
    except requests.RequestException as e:
        print(f"Failed to fetch URL: {e}")
