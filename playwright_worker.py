import sys
import json
import asyncio
import random

if sys.platform == "win32":
    try:
        # Use ProactorEventLoop instead of SelectorEventLoop
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    except Exception:
        pass

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception as e:
    print(json.dumps({"error": f"playwright_import_failed: {e}"}))
    sys.exit(1)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def run_worker(url: str, timeout: int = 30):
    out = {"error": None}
    
    try:
        with sync_playwright() as p:
            # FIX: Use more explicit browser launch
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # FIX: Create context with proper options
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            # ... rest of your existing code remains the same ...
            console_errors = []
            main_response_data = {}

            def on_response(response):
                try:
                    if response.request.resource_type == 'document' and not main_response_data:
                        ttfb_ms = None
                        try:
                            if hasattr(response, "timing"):
                                timing = response.timing()
                                req = timing.get("requestStart")
                                resp = timing.get("responseStart")
                                if isinstance(req, (int, float)) and isinstance(resp, (int, float)):
                                    ttfb_ms = resp - req
                        except Exception:
                            ttfb_ms = None

                        main_response_data["ttfb_ms"] = ttfb_ms
                        main_response_data["status"] = response.status
                        try:
                            main_response_data["headers"] = dict(response.headers)
                        except Exception:
                            main_response_data["headers"] = {}
                except Exception:
                    pass

            def on_console(msg):
                try:
                    if msg.type == "error":
                        console_errors.append({"text": msg.text})
                except Exception:
                    pass

            page.on("response", on_response)
            page.on("console", on_console)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            except Exception as e:
                rendered_html = ""
                try:
                    rendered_html = page.content()
                except Exception:
                    rendered_html = ""
                browser.close()
                out.update({
                    "rendered_html": rendered_html,
                    "console_errors": console_errors,
                    "response": main_response_data,
                    "error": f"navigation_failed: {e}"
                })
                print(json.dumps(out), flush=True)
                return

            try:
                page.wait_for_selector('h1, body', state='visible', timeout=15000)
            except PlaywrightTimeoutError:
                pass

            try:
                rendered_html = page.content()
            except Exception:
                rendered_html = ""

            metrics = {}
            try:
                metrics = page.evaluate(
                    """() => {
                        const perf = window.performance || {};
                        const paint = (perf.getEntriesByType && perf.getEntriesByType('paint')) || [];
                        const fcpEntry = paint.find(e => e.name === 'first-contentful-paint');
                        const lcpEntries = (perf.getEntriesByType && perf.getEntriesByType('largest-contentful-paint')) || [];
                        const clsEntries = (perf.getEntriesByType && perf.getEntriesByType('layout-shift')) || [];
                        let cls = 0;
                        clsEntries.forEach(e => { if (!e.hadRecentInput) cls += e.value || 0; });
                        const timing = perf.timing || {};
                        const requestStart = timing.requestStart || 0;
                        const responseStart = timing.responseStart || 0;
                        const ttfb = (responseStart && requestStart) ? (responseStart - requestStart) : null;
                        return {
                            fcp: fcpEntry ? fcpEntry.startTime : null,
                            lcp: lcpEntries.length ? lcpEntries[lcpEntries.length - 1].startTime : null,
                            cls: cls,
                            ttfb_ms: ttfb
                        };
                    }"""
                )
            except Exception:
                metrics = {}

            browser.close()
            out.update({
                "metrics": metrics,
                "console_errors": console_errors,
                "rendered_html": rendered_html,
                "response": main_response_data
            })
            print(json.dumps(out), flush=True)
            
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(json.dumps({"error": f"worker_exception: {e}\n{tb_str}"}), flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing_url"}))
        sys.exit(1)
    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    run_worker(url, timeout)