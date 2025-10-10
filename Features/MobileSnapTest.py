
import os
from urllib.parse import urlparse
try:
    from playwright.sync_api import sync_playwright, Error
except ImportError:
    sync_playwright = None
    Error = None

def mobile_snapshot_test(url: str) -> dict:
    if not sync_playwright:
        return {
            "success": False,
            "error": "Playwright is not installed. Please run 'pip install playwright'."
        }

    # Defining a common mobile viewport
    mobile_viewport = {"width": 414, "height": 896}
    
    # Generate a safe filename from the URL
    domain = urlparse(url).netloc.replace(".", "_")
    filename = f"{domain}_mobile_snapshot.png"
    
    # Create a directory for screenshots if it doesn't exist
    output_dir = "snapshots"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport=mobile_viewport,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1"
            )
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=20000)
            page.screenshot(path=filepath, full_page=True)
            browser.close()
        
        return {
            "success": True,
            "screenshot_path": filepath
        }
    except Error as e:
        return {
            "success": False,
            "error": f"Playwright failed to generate snapshot: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }