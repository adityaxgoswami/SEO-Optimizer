import json
import pprint
import sys
import socket
import ssl
import io
import asyncio
import re
import logging
import random
import subprocess
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
from collections import defaultdict
from urllib.parse import urljoin, urlparse
from datetime import datetime
import os
import asyncio
from fastapi.concurrency import run_in_threadpool
from bs4 import BeautifulSoup
from requests import Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
from Features.MinificationTest import minification_test
from Features.RelatedKeywordsTest import related_keywords_test
from Features.PageSpeedInsightsTest import pagespeed_insights_test
from Features.HSTSHeaderTest import hsts_header_test
from Features.HTMLCompressionTest import html_compression_test
from Features.MobileSnapTest import mobile_snapshot_test_sync

from utils.async_helper import check_urls_async,get_url_headers_async

load_dotenv()
try:
    from PIL import Image
except Exception:
    Image = None

import concurrent.futures

#different user-agents to mimic various browers and operating systems
#bypass bot detection mechanisms
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
]

#maps http respponse headers to there correspondng cdn providers
CDN_HEADERS = {
    "cf-ray": "Cloudflare", "cf-cache-status": "Cloudflare",
    "x-amz-cf-id": "Amazon CloudFront", "x-amz-cf-pop": "Amazon CloudFront",
    "x-served-by": "Fastly", "x-cache": "Fastly",
    "x-akamai-transformed": "Akamai",
    "x-sp-cache": "StackPath", "x-ec-cache": "Edgecast", "server": "Google Frontend"
}
#combining playwright asyncio with processpoolexecutor causes issues on windows
#to avoid this we run playwright in a separate python process using subprocess
def collect_browser_data_with_playwright(url: str, timeout: int = 30):
    worker = os.path.join(os.path.dirname(__file__), "playwright_worker.py")
    cmd = [sys.executable, "-u", worker, url, str(timeout)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        logging.error("Playwright worker timed out.")
        return None

    stdout = proc.stdout.strip()
    if not stdout:
        logging.error("Playwright worker returned empty output. Stderr: %s", proc.stderr)
        return None

    try:
        data = json.loads(stdout)
    except Exception as e:
        logging.exception("Failed to parse Playwright worker output: %s", e)
        return None

    # if worker returned error, propagate
    if data.get("error"):
        logging.error("Playwright worker error: %s", data.get("error"))
        return data

    return data

def get_ssl_info(hostname: str, port: int = 443, timeout: int = 5):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expires = datetime.strptime(cert.get("notAfter"), "%b %d %H:%M:%S %Y %Z")
                days_left = (expires - datetime.utcnow()).days
                return {
                    "days_to_expiry": days_left,
                    "issuer": cert.get("issuer", ()),
                    "subjectAltName": cert.get("subjectAltName", ()),
                }
    except Exception:
        return None

async def extract_seo_data(url: str,target_keywords:list=None,run_playwright: bool = False,link_check_limit:int =30, resource_check_limit: int = 120, timeout: int = 60) -> dict | None:
    session = Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    })

    playwright_data = {}
    response_headers = {}
    ttfb = None
    html_size_bytes = 0
    http_version = "unknown"

    try:
        if run_playwright:
            logging.info("... Running headless browser to render JavaScript ...")
            playwright_data = collect_browser_data_with_playwright(url, timeout=timeout)
            if not playwright_data or not playwright_data.get("rendered_html"):
                logging.error("Error: Playwright failed to fetch rendered HTML.")
                return None
            
            soup = BeautifulSoup(playwright_data["rendered_html"], "lxml")
            response_data = playwright_data.get("response", {})
            response_headers = {k.lower(): v for k, v in response_data.get("headers", {}).items()}
            ttfb_ms = response_data.get("ttfb_ms")
            ttfb = ttfb_ms / 1000 if ttfb_ms is not None else None
            html_size_bytes = len(playwright_data["rendered_html"].encode('utf-8'))
            http_version = "2.0" if response_data.get('http_version') else "1.1" # Simplified for playwright
        else:
            response = session.get(url, timeout=15, stream=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            ttfb = response.elapsed.total_seconds()
            html_size_bytes = len(response.content)
            http_version_code = response.raw.version
            if http_version_code == 10: http_version = "1.0"
            elif http_version_code == 11: http_version = "1.1"
            elif http_version_code == 20: http_version = "2.0"


        seo_data = {
            "url": url, "title": "No Title Tag Found", "meta_description": "No Meta Description Found",
            "meta_robots": "Not Found", "canonical": "", "word_count": 0, "body_text": "", "structured_data": {},
            "performance": {"ttfb": ttfb, "has_viewport": False, "is_https": False, "text_to_html_ratio": 0.0, "http_version": http_version},
            "site_files": {"has_robots_txt": False, "has_sitemap": False},
            "branding": {"has_favicon": False, "open_graph_tags": {}},
            "image_analysis": {"count": 0, "missing_alt_count": 0, "alt_texts": []},
            "h1": [], "headers": defaultdict(list),
            "link_analysis": {"internal_links": {"count": 0, "urls": []}, "external_links": {"count": 0, "urls": []}, "broken_links": {"count": 0, "urls": []}},
            "response_headers": response_headers, "html_size_bytes": html_size_bytes, "dom_nodes": 0,
            "charset": None, "deprecated_tags": {}, "has_google_analytics": False,
            "resources": {"items": [], "content_size_by_type": {}, "requests_by_type": {}},
            "cdn_providers": [], "ssl": None,
            "render_blocking_resources": {"found": False, "details": []},
            "core_web_vitals": playwright_data.get("metrics"), "console_errors": playwright_data.get("console_errors"),
            "canonicalization_check": None,
            "unsafe_cross_origin_links": {"count": 0, "urls": []},
            "plaintext_emails": {"count": 0, "emails": []},
            "mixed_content_test": None, "seo_friendly_url": None, "disallow_directive": None, "meta_refresh": None,
            "error_page_test": None, "spell_check": None, "responsive_image_test": None, "image_ratio_test": None,
            "media_query_responsive_test": None, "mobile_snapshot_test": None, "minification_test": None,
            "related_keyword_test": None, "pagespeed_insights": None, "hsts_test": None, "html_compression_test": None,
        }

        if run_playwright and playwright_data.get("error"):
            logging.error(f"Playwright returned an error: {playwright_data['error']}")
            if soup.title: seo_data["title"] = soup.title.string.strip()
            return seo_data 

        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if parsed_url.scheme == 'https': seo_data["performance"]["is_https"] = True
        
        if soup.title and soup.title.string: seo_data["title"] = soup.title.string.strip()
        if meta_desc := soup.find("meta", attrs={"name": "description"}): seo_data["meta_description"] = meta_desc.get("content", "").strip()
        if canonical := soup.find("link", attrs={"rel": "canonical"}): seo_data["canonical"] = canonical.get("href", "").strip()
        if soup.find("meta", {"name": "viewport"}): seo_data["performance"]["has_viewport"] = True
        if meta_robots := soup.find("meta", {"name": "robots"}): seo_data["meta_robots"] = meta_robots.get("content", "Not Found")

        robots_txt_content = None
        sitemap_url_from_robots = None
        try:
            robots_res = session.get(f"{base_url}/robots.txt", timeout=6)
            if robots_res.status_code == 200:
                seo_data["site_files"]["has_robots_txt"] = True
                robots_txt_content = robots_res.text
                match = re.search(r"Sitemap:\s*(.*)", robots_txt_content, re.IGNORECASE)
                if match:
                    sitemap_url_from_robots = match.group(1).strip()
        except exceptions.RequestException as e:
            logging.warning(f"Could not fetch robots.txt: {e}")


        try:
            sitemap_to_check = sitemap_url_from_robots if sitemap_url_from_robots else f"{base_url}/sitemap.xml"
            sitemap_res = session.head(sitemap_to_check, timeout=6)
            if sitemap_res.status_code == 200:
                seo_data["site_files"]["has_sitemap"] = True
        except exceptions.RequestException:
            pass 

        if soup.find("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon"]):
            seo_data["branding"]["has_favicon"] = True
        for tag in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
            if prop := tag.get("property"):
                seo_data["branding"]["open_graph_tags"][prop] = tag.get("content", "")

        if soup.body:
            body_text = soup.body.get_text(separator=" ", strip=True)
            seo_data["body_text"] = body_text
            seo_data["word_count"] = len(body_text.split())
            if html_size_bytes > 0: seo_data["performance"]["text_to_html_ratio"] = (len(body_text.encode('utf-8')) / html_size_bytes) * 100
            
            found_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", body_text)
            if found_emails:
                seo_data["plaintext_emails"]["count"] = len(found_emails)
                seo_data["plaintext_emails"]["emails"] = list(set(found_emails))


        if json_ld := soup.find("script", {"type": "application/ld+json"}):
            if json_ld.string:
                try: seo_data["structured_data"] = json.loads(json_ld.string)
                except json.JSONDecodeError: seo_data["structured_data"] = {"error": "Invalid JSON format"}
        
        image_tags = soup.find_all("img")
        seo_data["image_analysis"]["count"] = len(image_tags)
        for tag in image_tags:
            alt = tag.get("alt")
            if not alt or alt.strip() == "": seo_data["image_analysis"]["missing_alt_count"] += 1
            else: seo_data["image_analysis"]["alt_texts"].append(alt.strip())

        seo_data["h1"] = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
        for i in range(2, 7):
            seo_data["headers"][f"h{i}"] = [h.get_text(strip=True) for h in soup.find_all(f"h{i}")]
        
        seo_data["dom_nodes"] = len(soup.find_all(True))
        
        ga_present = False
        for script in soup.find_all("script"):
            combined = (script.get("src", "") or "") + (script.string or "")
            if re.search(r"google-analytics\.com|googletagmanager\.com|gtag\(|ga\(", combined, re.I):
                ga_present = True
                break
        seo_data["has_google_analytics"] = ga_present
        
        deprecated_tags_list = ["center", "font", "marquee", "bgsound", "blink"]
        seo_data["deprecated_tags"] = {tag: len(soup.find_all(tag)) for tag in deprecated_tags_list if soup.find(tag)}

        for a in soup.find_all("a", target="_blank"):
            rel = (a.get("rel") or [])
            if "noopener" not in rel and "noreferrer" not in rel:
                seo_data["unsafe_cross_origin_links"]["count"] += 1
                seo_data["unsafe_cross_origin_links"]["urls"].append(a.get("href", "N/A"))


        all_links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True) if a.get("href") and not a["href"].startswith(('mailto:', 'tel:', '#'))]
        unique_links = sorted(list(set(all_links)))
        
        resource_urls = []
        for tag in soup.find_all(["img", "script"], src=True):
            if src := tag.get("src"):
                if not src.startswith("data:"): resource_urls.append(urljoin(url, src))
        for tag in soup.find_all("link", rel="stylesheet"):
            if href := tag.get("href"): resource_urls.append(urljoin(url, href))
        
        unique_resource_urls = sorted(list(set(resource_urls)))
        
        async def _gather_async_data():
            results = await asyncio.gather(
                check_urls_async(unique_links[:link_check_limit], per_request_timeout=10),
                get_url_headers_async(unique_resource_urls[:resource_check_limit], per_request_timeout=10)
            )
            return results

        link_statuses, resource_details = await _gather_async_data()
        
        for link in unique_links:
            if urlparse(link).netloc == parsed_url.netloc:
                seo_data["link_analysis"]["internal_links"]["count"] += 1
                seo_data["link_analysis"]["internal_links"]["urls"].append(link)
            else:
                seo_data["link_analysis"]["external_links"]["count"] += 1
                seo_data["link_analysis"]["external_links"]["urls"].append(link)

        broken_links = [url for url, status in link_statuses if status is None or status >= 400]
        if broken_links:
            seo_data["link_analysis"]["broken_links"] = {"count": len(broken_links), "urls": broken_links}
        
        detected_cdns = {cdn for header, cdn in CDN_HEADERS.items() if header in response_headers}
        content_size_by_type = defaultdict(int)
        requests_by_type = defaultdict(int)

        for details in resource_details:
            resource_item = {"url": details["url"]}
            status_code = details.get("status")
            if status_code is not None and status_code < 400:
                for header, cdn in CDN_HEADERS.items():
                    if header in details.get("headers", {}): detected_cdns.add(cdn)
                
                ct = details.get("content_type") or ""
                if "javascript" in ct: r_type = "js"
                elif "css" in ct: r_type = "css"
                elif "image" in ct: r_type = "image"
                else: r_type = "other"

                requests_by_type[r_type] += 1
                if length := details.get("content_length"):
                    content_size_by_type[r_type] += length
                
                resource_item.update(details) 
            seo_data["resources"]["items"].append(resource_item)

        seo_data["cdn_providers"] = list(detected_cdns)
        seo_data["resources"]["content_size_by_type"] = dict(content_size_by_type)
        seo_data["resources"]["requests_by_type"] = dict(requests_by_type)

        if head_tag := soup.find("head"):
            for link in head_tag.find_all("link", rel="stylesheet"):
                if href := link.get("href"):
                    seo_data["render_blocking_resources"]["details"].append({"type": "css", "url": urljoin(url, href)})
                    seo_data["render_blocking_resources"]["found"] = True
            for script in head_tag.find_all("script", src=True):
                if not script.has_attr("defer") and not script.has_attr("async"):
                    if src := script.get("src"):
                        seo_data["render_blocking_resources"]["details"].append({"type": "script", "url": urljoin(url, src)})
                        seo_data["render_blocking_resources"]["found"] = True
        
        if parsed_url.scheme == "https":
            seo_data["ssl"] = get_ssl_info(parsed_url.hostname, port=parsed_url.port or 443)
        
        try:
            host = parsed_url.netloc
            alt_host = f"www.{host}" if not host.startswith("www.") else host[4:]
            r1 = session.head(f"{parsed_url.scheme}://{host}", timeout=8, allow_redirects=True, verify=False)
            r2 = session.head(f"{parsed_url.scheme}://{alt_host}", timeout=8, allow_redirects=True, verify=False)
            seo_data["canonicalization_check"] = {"base_url_final": r1.url, "alt_url_final": r2.url, "consistent": r1.url == r2.url}
        except Exception as e:
            logging.error(f"Canonicalization check failed: {e}")
            seo_data["canonicalization_check"] = {"error": "Failed to check canonicalization.", "consistent": False}


        if target_keywords:
            seo_data["related_keywords_test"] = related_keywords_test(body_text=seo_data["body_text"], target_keyword=target_keywords[0])
            seo_data["seo_friendly_url"] = seo_friendly_url_test(url, keywords=target_keywords)
        
        seo_data["disallow_directive"] = disallow_directive_test(url=url, robots_txt_content=robots_txt_content)
        seo_data["meta_refresh"] = meta_refresh_test(soup)
        seo_data["error_page_test"] = error_page_test(url)
        seo_data["spell_check"] = spell_check_test(seo_data["body_text"])
        seo_data["responsive_image_test"] = responsive_image_test(soup)
        seo_data["image_ratio_test"] = image_ratio_test(url, soup)
        seo_data["media_query_responsive_test"] = media_query_responsive_test(soup, seo_data["resources"]["items"], session)
        seo_data["mixed_content_test"] = mixed_content_test(is_https=seo_data["performance"]["is_https"], resources=seo_data["resources"]["items"])
        seo_data["minification_test"] = minification_test(resources=seo_data["resources"]["items"], session=session)
        seo_data["hsts_test"] = hsts_header_test(response_headers)
        seo_data["html_compression_test"] = html_compression_test(response_headers, html_size_bytes)


        if run_playwright:
            logging.info("📸 Generating mobile snapshot...")
            try:
                seo_data["mobile_snapshot_test"] = await asyncio.get_event_loop().run_in_executor(
                    None, mobile_snapshot_test_sync, url
                )
            except Exception as e:
                logging.warning(f"Mobile snapshot failed: {e}")
                seo_data["mobile_snapshot_test"] = {
                    "success": False,
                    "error": f"Mobile snapshot failed: {str(e)}"
                }


        logging.info("📊 Fetching Google PageSpeed Insights data...")
        api_key = os.getenv("PAGESPEED_API_KEY")
        if not api_key:
            logging.warning("PAGESPEED_API_KEY environment variable not set. Skipping PageSpeed Insights test.")
            seo_data["pagespeed_insights"] = {"success": False, "error": "API key not configured."}
        else:
            seo_data["pagespeed_insights"] = pagespeed_insights_test(url, api_key)
        
        return seo_data

    except exceptions.RequestException as e:
        logging.exception(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logging.exception(f"An error occurred during parsing: {e}")
        return None

