# import os
# import sys
# import asyncio
# from urllib.parse import urlparse

# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# try:
#     from playwright.async_api import async_playwright, Error as PlaywrightError
# except ImportError:
#     async_playwright = None
#     PlaywrightError = None


# async def mobile_snapshot_test(url: str) -> dict:
#     if not async_playwright:
#         return {
#             "success": False,
#             "error": "Playwright is not installed. Run 'pip install playwright' and 'playwright install'."
#         }

#     mobile_viewport = {"width": 375, "height": 812}
#     domain = urlparse(url).netloc.replace(".", "_")
#     filename = f"{domain}_mobile_snapshot.png"
#     output_dir = "snapshots"
#     os.makedirs(output_dir, exist_ok=True)
#     filepath = os.path.join(output_dir, filename)

#     try:
#         async with async_playwright() as p:
#             browser = await p.chromium.launch(headless=True)
#             context = await browser.new_context(
#                 viewport=mobile_viewport,
#                 user_agent=(
#                     "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
#                     "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 "
#                     "Mobile/15E148 Safari/604.1"
#                 ),
#                 java_script_enabled=True,
#                 ignore_https_errors=True
#             )
#             page = await context.new_page()
#             await page.goto(url, wait_until="load", timeout=30000)
#             await page.screenshot(path=filepath, full_page=True)
#             await browser.close()

#         return {
#             "success": True,
#             "screenshot_path": filepath
#         }

#     except PlaywrightError as e:
#         return {"success": False, "error": f"Playwright failed to generate snapshot: {str(e)}"}
#     except Exception as e:
#         return {"success": False, "error": f"Unexpected error: {str(e)}"}


# # For standalone testing
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python MobileSnapTest.py \"<url>\"")
#         sys.exit(1)

#     url = sys.argv[1]
#     print(f"Running mobile snapshot for {url}...")
#     result = asyncio.run(mobile_snapshot_test(url))
#     print(result)

import os
import sys
import asyncio
from urllib.parse import urlparse

def mobile_snapshot_test_sync(url: str) -> dict:
    """Synchronous version for better Windows compatibility"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "success": False,
            "error": "Playwright is not installed. Run 'pip install playwright' and 'playwright install'."
        }

    mobile_viewport = {"width": 375, "height": 812}
    domain = urlparse(url).netloc.replace(".", "_")
    filename = f"{domain}_mobile_snapshot.png"
    output_dir = "snapshots"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security'
                ]
            )
            context = browser.new_context(
                viewport=mobile_viewport,
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 "
                    "Mobile/15E148 Safari/604.1"
                ),
                ignore_https_errors=True
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.screenshot(path=filepath, full_page=True)
            browser.close()

        return {
            "success": True,
            "screenshot_path": filepath
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to generate snapshot: {str(e)}"}


# For standalone testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python MobileSnapTest.py \"<url>\"")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Running mobile snapshot for {url}...")
    
    # Call the sync function directly
    result = mobile_snapshot_test_sync(url)
    print(result)