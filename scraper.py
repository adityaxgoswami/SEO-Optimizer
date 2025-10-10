import json
import pprint
import sys
import socket
import ssl
import io
import asyncio
import re
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
from collections import defaultdict
from urllib.parse import urljoin, urlparse
from datetime import datetime
import os 
from bs4 import BeautifulSoup
from requests import Session, exceptions
from dotenv import load_dotenv
from Features.seo_friendly import seo_friendly_url_test
from Features.DirectiveTest import disallow_directive_test
from Features.MetaRefreshTest import meta_refresh_test
from Features.ErrorPageTest import error_page_test
from Features.SpellCheckTest import spell_check_test
from Features.ResponsiveImageTest import responsive_image_test
from Features.ImageRatioTest import image_ratio_test
from Features.MediaQueryResponsiveTest import media_query_responsive_test
from Features.MixedContentTest import mixed_content_test
from Features.MobileSnapTest import mobile_snapshot_test
from Features.MinificationTest import minification_test
from Features.RelatedKeywordsTest import related_keywords_test  
from Features.PageSpeedInsightsTest import pagespeed_insights_test 

from utils.async_helper import check_urls_async,get_url_headers_async

load_dotenv()
#PIL (Pillow) for reading image EXIF/metadata if you want deeper image checks
try:
    from PIL import Image
except Exception:
    Image = None

#chromium browser for js heavy sites
import concurrent.futures

def _run_playwright_task(url: str, timeout: int):
    """This helper runs in a separate process to ensure a clean environment."""
    from playwright.sync_api import sync_playwright
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            console_errors = []
            main_response_data = {}

            def on_response(response):
                if response.request.resource_type == 'document' and not main_response_data:
                    if hasattr(response, 'timing'):
                        try:
                            timing = response.timing()
                            ttfb = timing['responseStart'] - timing['requestStart']
                            main_response_data['ttfb_ms'] = ttfb if ttfb > 0 else None
                        except Exception as e:
                            print(f"!!! PLAYWRIGHT TIMING ERROR: {e}")
                            main_response_data['ttfb_ms'] = None
                    else:
                        print("!!! PLAYWRIGHT WARNING: response.timing() method not found. Cannot calculate TTFB.")
                        main_response_data['ttfb_ms'] = None
                    
                    main_response_data['status'] = response.status
                    main_response_data['headers'] = response.headers

            def on_console(msg):
                if msg.type == "error":
                    console_errors.append({"text": msg.text, "location": msg.location})

            page.on("response", on_response)
            page.on("console", on_console)

            page.goto(url, wait_until="load", timeout=timeout * 1000)
            rendered_html = page.content()

            metrics = page.evaluate(
                """() => {
                    const perf = window.performance || {};
                    const fcpEntry = perf.getEntriesByType('paint').find(e => e.name === 'first-contentful-paint');
                    const lcpEntries = perf.getEntriesByType('largest-contentful-paint');
                    const clsEntries = perf.getEntriesByType('layout-shift');
                    let cls = 0;
                    clsEntries.forEach(e => { if (!e.hadRecentInput) cls += e.value || 0; });
                    return {
                        fcp: fcpEntry ? fcpEntry.startTime : null,
                        lcp: lcpEntries.length ? lcpEntries[lcpEntries.length - 1].startTime : null,
                        cls: cls
                    };
                }"""
            )
            browser.close()
            
            return {
                "metrics": metrics,
                "console_errors": console_errors,
                "rendered_html": rendered_html,
                "response": main_response_data,
            }
    except Exception as e:
        print(f"!!! PLAYWRIGHT PROCESS ERROR: {e}")
        return None

def collect_browser_data_with_playwright(url: str, timeout: int = 30):
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_playwright_task, url, timeout)
        try:
            return future.result(timeout=timeout + 15)
        except concurrent.futures.TimeoutError:
            logging.error("Playwright process timed out.")
            return None
        except Exception as e:
            logging.error(f"Playwright process failed with an exception: {e}")
            return None

def get_ssl_info(hostname: str, port: int = 443, timeout: int = 5):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                not_before = cert.get("notBefore")
                not_after = cert.get("notAfter")
                san = cert.get("subjectAltName", ())
                issuer = cert.get("issuer", ())
                days_left = None
                try:
                    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_left = (expires - datetime.utcnow()).days
                except Exception:
                    days_left = None

                return {
                    "not_before": not_before,
                    "not_after": not_after,
                    "days_to_expiry": days_left,
                    "subjectAltName": san,
                    "issuer": issuer,
                }
    except Exception:
        return None

def extract_seo_data(url: str,target_keywords:list=None,run_playwright: bool = False,link_check_limit:int =30, resource_check_limit: int = 120, timeout: int = 60) -> dict | None:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1'
    }
    cdn_keywords = ("cdn", "cloudfront", "akamai", "fastly", "cloudflare", "edgekey", "stackpath", "maxcdn", "edgesuite")

    session = Session()
    session.headers.update(headers)

    try:
        if run_playwright:
            logging.info("... Running headless browser to render JavaScript ...")
            playwright_data = collect_browser_data_with_playwright(url, timeout=timeout)
            if not playwright_data or not playwright_data.get("rendered_html"):
                logging.error("Error: Playwright failed to fetch rendered HTML.")
                return None
            
            soup = BeautifulSoup(playwright_data["rendered_html"], "lxml")
            
            response_data = playwright_data.get("response", {})
            # --- CHANGE 1: Convert all header keys to lowercase ---
            response_headers = {k.lower(): v for k, v in response_data.get("headers", {}).items()}
            ttfb_ms = response_data.get("ttfb_ms")
            ttfb = ttfb_ms / 1000 if ttfb_ms is not None else None

            html_size_bytes = len(playwright_data["rendered_html"].encode('utf-8'))
            response = None

        else:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            # --- CHANGE 2: Convert all header keys to lowercase ---
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            ttfb = response.elapsed.total_seconds()
            html_size_bytes = len(response.content)
            playwright_data = {}
            
        seo_data = {
                "url": url,
                "title": "No Title Tag Found",
                "meta_description": "No Meta Description Found",
                "meta_robots": "Not Found",
                "canonical": "",
                "word_count": 0,
                "body_text": "",
                "structured_data": {},
                "performance": {
                    "ttfb": ttfb,
                    "has_viewport": False,
                    "is_https": False,
                    "text_to_html_ratio": 0.0,
                },
                "site_files": {
                    "has_robots_txt": False,
                    "has_sitemap": False,
                },
                "branding": {
                    "has_favicon": False,
                    "open_graph_tags": {}
                },
                "image_analysis": {
                    "count": 0,
                    "missing_alt_count": 0,
                    "alt_texts": [],
                },
                "h1": [],
                "headers": defaultdict(list),
                "link_analysis": {
                    "internal_links": {"count": 0, "urls": []},
                    "external_links": {"count": 0, "urls": []},
                    "broken_links": {"count": 0, "urls": []},
                },
                "response_headers": response_headers,
                "html_size_bytes": html_size_bytes,
                "dom_nodes": 0,
                "charset": None,
                "deprecated_tags": {},
                "has_google_analytics": False,
                "resources": {
                    "items": [],
                    "content_size_by_type": {},
                    "requests_by_type": {}
                },
                "cdn_usage": False,
                "ssl": None,
                "render_blocking_resources": {
                    "found": False,
                    "details": []
                },
                "core_web_vitals": None,   
                "console_errors": None,
                "mixed_content_test": None,
                "canonicalization_check": None,
                "seo_friendly_url": None,
                "disallow_directive": None,
                "meta_refresh": None,
                "error_page_test": None,
                "spell_check": None,
                "responsive_image_test": None,
                "image_ratio_test": None,
                "media_query_responsive_test": None,
                "mobile_snapshot_test": None,
                "minification_test": None,
                "related_keyword_test":None,
                "pagespeed_insights": None,
            }
            
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  
              
        if soup.find("meta", {"name": "viewport"}):
            seo_data["performance"]["has_viewport"] = True
        if parsed_url.scheme == 'https':
            seo_data["performance"]["is_https"] = True

        meta_robots_tag = soup.find("meta", {"name": "robots"})
        if meta_robots_tag:
            seo_data["meta_robots"] = meta_robots_tag.get("content", "Not Found")

        robots_txt_content=None
        sitemap_url_from_robots=None
         
        try:
            robots_res = session.get(f"{base_url}/robots.txt", timeout=6)
            if robots_res.status_code == 200:
                seo_data["site_files"]["has_robots_txt"] = True
                robots_txt_content=robots_res.text
                
                match=re.search(r"Sitemap:\s*(.*)",robots_txt_content,re.IGNORECASE)
                if match:
                    sitemap_url_from_robots = match.group(1).strip()
        except exceptions.RequestException:
            seo_data["site_files"]["has_robots_txt"] = False

        try:
            sitemap_to_check=sitemap_url_from_robots if sitemap_url_from_robots else f"{base_url}/sitemap.xml"
            # --- CHANGE 3: Use .get() for more reliability ---
            sitemap_res = session.get(sitemap_to_check, timeout=6)
            if sitemap_res.status_code == 200:
                seo_data["site_files"]["has_sitemap"] = True
        except exceptions.RequestException:
            seo_data["site_files"]["has_sitemap"] = False

        favicon_tag = soup.find("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon"])
        if favicon_tag:
            seo_data["branding"]["has_favicon"] = True

        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        for tag in og_tags:
            prop = tag.get("property")
            content = tag.get("content")
            if prop and content:
                seo_data["branding"]["open_graph_tags"][prop] = content

        if soup.title and soup.title.string:
            seo_data["title"] = soup.title.string.strip()

        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        if meta_desc_tag:
            seo_data["meta_description"] = meta_desc_tag.get("content", "").strip()

        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        if canonical_tag:
            seo_data["canonical"] = canonical_tag.get("href", "").strip()

        if soup.body:
            body_text = soup.body.get_text(separator=" ", strip=True)
            seo_data["body_text"] = body_text
            seo_data["word_count"] = len(body_text.split())

            if run_playwright:
                raw_html_size = len(playwright_data["rendered_html"].encode('utf-8'))
            else:
                raw_html_size = len(response.text.encode('utf-8'))
            
            text_size = len(body_text.encode('utf-8'))
            if raw_html_size > 0:
                ratio = (text_size / raw_html_size) * 100
                seo_data["performance"]["text_to_html_ratio"] = ratio

        json_ld_script = soup.find("script", {"type": "application/ld+json"})
        if json_ld_script and json_ld_script.string:
            try:
                seo_data["structured_data"] = json.loads(json_ld_script.string)
            except json.JSONDecodeError:
                seo_data["structured_data"] = {"error": "Invalid JSON format"}

        image_tags = soup.find_all("img")
        seo_data["image_analysis"]["count"] = len(image_tags)
        for tag in image_tags:
            alt = tag.get("alt")
            if alt is None or alt.strip() == "":
                seo_data["image_analysis"]["missing_alt_count"] += 1
            else:
                seo_data["image_analysis"]["alt_texts"].append(alt.strip())

        h1_tags = soup.find_all("h1")
        for tag in h1_tags:
            seo_data["h1"].append(tag.get_text(strip=True))

        for i in range(2, 7):
            header_tags = soup.find_all(f"h{i}")
            for tag in header_tags:
                seo_data["headers"][f"h{i}"].append(tag.get_text(strip=True))

        seo_data["dom_nodes"] = len(soup.find_all(True))

        charset = None
        meta_charset = soup.find("meta", charset=True)
        if meta_charset and meta_charset.get("charset"):
            charset = meta_charset.get("charset")
            
        elif not run_playwright:
            ct = response_headers.get("content-type", "")
            m = re.search(r"charset=([\w-]+)", ct, re.I)
            if m:
                charset = m.group(1)
        
        if charset:
            seo_data["charset"]=charset
        elif not run_playwright:
            seo_data["charset"]=response.encoding or "unknown"
        else:
            seo_data["charset"] = "unknown"

        deprecated = ["center", "font", "marquee", "bgsound", "blink"]
        found_deprecated = {}
        for tag in deprecated:
            els = soup.find_all(tag)
            if els:
                found_deprecated[tag] = len(els)
        seo_data["deprecated_tags"] = found_deprecated

        ga_present = False
        for script in soup.find_all("script"):
            src = script.get("src", "") or ""
            txt = (script.string or "")[:500]
            combined = (src + " " + txt).lower()
            if ("google-analytics" in combined or "gtag(" in combined or "ga(" in combined or
                    "analytics.js" in combined or "googletagmanager.com" in combined):
                ga_present = True
                break
        seo_data["has_google_analytics"] = ga_present

        all_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(url, href)
            if absolute_url.startswith("http") and "#" not in absolute_url:
                all_links.append(absolute_url)

        unique_links = sorted(list(set(all_links)))
        for link in unique_links:
            if urlparse(link).netloc == parsed_url.netloc:
                seo_data["link_analysis"]["internal_links"]["count"] += 1
                seo_data["link_analysis"]["internal_links"]["urls"].append(link)
            else:
                seo_data["link_analysis"]["external_links"]["count"] += 1
                seo_data["link_analysis"]["external_links"]["urls"].append(link)

        links_to_check = unique_links[:link_check_limit]
        link_statuses = asyncio.run(check_urls_async(links_to_check,timeout=timeout))
        for url_checked,status_code in link_statuses:
            if status_code is None or status_code >= 400:
                    seo_data["link_analysis"]["broken_links"]["count"] += 1
                    seo_data["link_analysis"]["broken_links"]["urls"].append(url_checked)
        
        resources = []
        for tag in soup.find_all("img", src=True):
            src = tag.get("src")
            if not src or src.strip().startswith("data:"):
                continue
            absolute = urljoin(url, src)
            resources.append({"type": "image", "url": absolute, "tag": tag})

        for tag in soup.find_all("link", rel=lambda x: x and "stylesheet" in x.lower()):
            href = tag.get("href")
            if href:
                absolute = urljoin(url, href)
                resources.append({"type": "css", "url": absolute, "tag": tag})

        for tag in soup.find_all("script", src=True):
            src = tag.get("src")
            if src:
                absolute = urljoin(url, src)
                resources.append({"type": "js", "url": absolute, "tag": tag})

        for tag in soup.find_all("link", rel=lambda x: x and ("icon" in x.lower() or "shortcut icon" in x.lower())):
            href = tag.get("href")
            if href:
                absolute = urljoin(url, href)
                resources.append({"type": "favicon", "url": absolute, "tag": tag})

        seen = set()
        deduped = []
        for r in resources:
            if r["url"] not in seen:
                seen.add(r["url"])
                deduped.append(r)
        resources = deduped
        seo_data["resources"]["items"] = [{"type": r["type"], "url": r["url"]} for r in resources]


        content_size_by_type = defaultdict(int)
        requests_by_type = defaultdict(int)
        cdn_found = False
        
        resource_urls = [r["url"] for r in resources[:resource_check_limit]]
        
        resource_details = asyncio.run(get_url_headers_async(resource_urls,timeout=timeout))
        
        for details in resource_details:
            if details.get("status") is not None and details["status"]<400:
                original_resource = next((r for r in resources if r["url"]==details["url"]),{})
                r_type = original_resource.get("type","unknown")
                
                if details.get("content_length"):
                    content_size_by_type[r_type] += details["content_length"]
                requests_by_type[r_type] +=1
                
                host = urlparse(details["url"]).netloc.lower()
                is_cdn = any(k in host for k in cdn_keywords)
                if is_cdn:
                    cdn_found = True
                    
                for item in seo_data["resources"]["items"]:
                    if item["url"] == details["url"]:
                        item.update({
                            "status": details["status"],
                            "content_type": details.get("content_type"),
                            "content_length": details.get("content_length"),
                            "cache_control": details.get("cache_control"),
                            "content_encoding": details.get("content_encoding"),
                            "is_cdn": is_cdn
                        })
                        break

        seo_data["resources"]["content_size_by_type"] = dict(content_size_by_type)
        seo_data["resources"]["requests_by_type"] = dict(requests_by_type)
        seo_data["cdn_usage"] = cdn_found

        rb_details = []
        found_rb = False
        head_tag = soup.find("head")
        if head_tag:
            for link in head_tag.find_all("link", rel=lambda x: x and "stylesheet" in x.lower()):
                href = link.get("href")
                if href:
                    rb_details.append({"type": "css", "url": urljoin(url, href)})
                    found_rb = True
            for script in head_tag.find_all("script", src=True):
                if not script.has_attr("defer") and not script.has_attr("async"):
                    src = script.get("src")
                    if src:
                        rb_details.append({"type": "script", "url": urljoin(url, src)})
                        found_rb = True

        seo_data["render_blocking_resources"]["found"] = found_rb
        seo_data["render_blocking_resources"]["details"] = rb_details

        if parsed_url.scheme == "https":
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            ssl_info = get_ssl_info(hostname, port=port)
            seo_data["ssl"] = ssl_info

        try:
            host = parsed_url.netloc
            if host.startswith("www."):
                alt_host = host[4:]
            else:
                alt_host = f"www.{host}"
            
            r1 = session.head(f"{parsed_url.scheme}://{host}", timeout=8, allow_redirects=True)
            r2 = session.head(f"{parsed_url.scheme}://{alt_host}", timeout=8, allow_redirects=True)
            seo_data["canonicalization_check"] = {"base_url_final": r1.url, "alt_url_final": r2.url}
        except Exception:
            seo_data["canonicalization_check"] = None

        if run_playwright:
            seo_data["core_web_vitals"] = playwright_data.get("metrics")
            seo_data["console_errors"] = playwright_data.get("console_errors")

        if target_keywords:
            seo_data["related_keywords_test"] = related_keywords_test(
                body_text=seo_data.get("body_text", ""),
                target_keyword=target_keywords[0]
            )
            seo_data["seo_friendly_url"] = seo_friendly_url_test(url, keywords=target_keywords)

        seo_data["disallow_directive"] = disallow_directive_test(url=url,robots_txt_content=robots_txt_content)
        seo_data["meta_refresh"] = meta_refresh_test(url)
        seo_data["error_page_test"] = error_page_test(url)
        seo_data["spell_check"] = spell_check_test(seo_data.get("body_text", ""))
        seo_data["responsive_image_test"] = responsive_image_test(url)
        seo_data["image_ratio_test"] = image_ratio_test(url,soup, validate_real_size=True)
        
        seo_data["media_query_responsive_test"] = media_query_responsive_test(
            soup, 
            seo_data.get("resources", {}).get("items", []), 
            session
        )
        
        seo_data["mixed_content_test"] = mixed_content_test(
            is_https=seo_data["performance"]["is_https"],
            resources=seo_data.get("resources", {}).get("items", [])
        )
        seo_data["minification_test"] = minification_test(
            resources=seo_data.get("resources", {}).get("items", []),
            session=session
        )
        if run_playwright:
            logging.info("📸 Generating mobile snapshot...")
            seo_data["mobile_snapshot_test"] = mobile_snapshot_test(url)
        
        logging.info("📊 Fetching Google PageSpeed Insights data...")
        api_key = os.getenv("PAGESPEED_API_KEY")
        logging.debug(f"--- DEBUG: Found API Key: {api_key} ---")
        seo_data["pagespeed_insights"] = pagespeed_insights_test(url, api_key)   
        return seo_data

    except exceptions.RequestException as e:
            logging.exception(f"Error fetching {url}: {e}")
            return None
    except Exception as e:
            logging.exception(f"An error occurred during parsing: {e}")
            return None

