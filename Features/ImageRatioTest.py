from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import re

try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def extract_css_dimensions(style: str):
    width = height = None
    if style:
        width_match = re.search(r'width\s*:\s*([0-9.]+)px', style)
        height_match = re.search(r'height\s*:\s*([0-9.]+)px', style)
        if width_match:
            width = int(float(width_match.group(1)))
        if height_match:
            height = int(float(height_match.group(1)))
    return width, height

def image_ratio_test(url: str, validate_real_size: bool = False) -> dict:
    """
    Extracts image width/height from HTML attributes, inline CSS, and optionally validates with Pillow.
    Returns a dict with image info and issues.
    """
    result = {
        "url": url,
        "images_checked": 0,
        "images_with_ratio": [],
        "images_missing_dimensions": [],
        "images_real_size_mismatch": [],
        "issues": []
    }

    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        img_tags = soup.find_all("img")
        result["images_checked"] = len(img_tags)
        for img in img_tags:
            src = img.get("src")
            img_url = urljoin(url, src) if src else None

            # Try HTML attributes
            width = img.get("width")
            height = img.get("height")

            # Try inline CSS
            if not width or not height:
                style = img.get("style", "")
                css_width, css_height = extract_css_dimensions(style)
                width = width or css_width
                height = height or css_height

            if width and height:
                try:
                    w = int(width)
                    h = int(height)
                    aspect_ratio = round(w / h, 2) if h != 0 else None
                    img_info = {
                        "src": img_url,
                        "width": w,
                        "height": h,
                        "aspect_ratio": aspect_ratio
                    }
                    # Optional: Validate real size with Pillow
                    if validate_real_size and PIL_AVAILABLE and img_url:
                        try:
                            img_resp = requests.get(img_url, timeout=10)
                            pil_img = Image.open(BytesIO(img_resp.content))
                            real_w, real_h = pil_img.size
                            img_info["real_width"] = real_w
                            img_info["real_height"] = real_h
                            img_info["real_aspect_ratio"] = round(real_w / real_h, 2) if real_h != 0 else None
                            if real_w != w or real_h != h:
                                result["images_real_size_mismatch"].append(img_info)
                        except Exception as e:
                            result["issues"].append(f"Pillow error for {img_url}: {e}")
                    result["images_with_ratio"].append(img_info)
                except Exception:
                    result["issues"].append(f"Invalid width/height for image: {img_url}")
            else:
                result["images_missing_dimensions"].append(img_url)
        if result["images_missing_dimensions"]:
            result["issues"].append(
                f"{len(result['images_missing_dimensions'])} images are missing width or height attributes or CSS."
            )
        if validate_real_size and not PIL_AVAILABLE:
            result["issues"].append("Pillow is not installed; real-size validation skipped.")
    except Exception as e:
        result["issues"].append(f"Error checking image aspect ratios: {e}")

    return result
