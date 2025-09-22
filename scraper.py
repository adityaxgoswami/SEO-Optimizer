# scraper.py
import json
import pprint
import sys
import time
from collections import defaultdict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests import Session, exceptions
from tqdm import tqdm


def extract_seo_data(url: str) -> dict | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }

    with Session() as session:
        session.headers.update(headers)

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            parsed_url = urlparse(url)

            seo_data = {
                "url": url,
                "title": "No Title Tag Found",
                "meta_description": "No Meta Description Found",
                "canonical": "",
                "word_count": 0,
                "body_text": "",
                "structured_data": {},
                "performance": {
                    "ttfb": None,
                    "has_viewport": False,
                    "is_https": False, 
                },
                "site_files": { 
                    "has_robots_txt": False,
                    "has_sitemap": False,
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
            }

            seo_data["performance"]["ttfb"] = response.elapsed.total_seconds()
            if soup.find("meta", {"name": "viewport"}):
                seo_data["performance"]["has_viewport"] = True
            if parsed_url.scheme == 'https':
                seo_data["performance"]["is_https"] = True

            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            try:
                robots_res = session.get(f"{base_url}/robots.txt", timeout=5)
                if robots_res.status_code == 200:
                    seo_data["site_files"]["has_robots_txt"] = True
            except exceptions.RequestException:
                pass
            
            try:
                sitemap_res = session.get(f"{base_url}/sitemap.xml", timeout=5)
                if sitemap_res.status_code == 200:
                    seo_data["site_files"]["has_sitemap"] = True
            except exceptions.RequestException:
                pass 


           
            json_ld_script = soup.find("script", {"type": "application/ld+json"})
            if json_ld_script and json_ld_script.string:
                try:
                    seo_data["structured_data"] = json.loads(json_ld_script.string)
                except json.JSONDecodeError:
                    seo_data["structured_data"] = {"error": "Invalid JSON format"}
            
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
                seo_data["word_count"] = len(body_text.split())
                seo_data["body_text"] = body_text

            image_tags = soup.find_all("img")
            seo_data["image_analysis"]["count"] = len(image_tags)
            for tag in image_tags:
                if tag.get("alt") is None:
                    seo_data["image_analysis"]["missing_alt_count"] += 1
                else:
                    seo_data["image_analysis"]["alt_texts"].append(tag.get("alt", "").strip())

            h1_tags = soup.find_all("h1")
            for tag in h1_tags:
                seo_data["h1"].append(tag.get_text(strip=True))

            for i in range(2, 7):
                header_tags = soup.find_all(f"h{i}")
                for tag in header_tags:
                    seo_data["headers"][f"h{i}"].append(tag.get_text(strip=True))

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

            links_to_check = unique_links[:20]
            for link in tqdm(links_to_check, desc="Checking links for status...", unit="link"):
                try:
                    link_response = session.head(link, timeout=5, allow_redirects=True)
                    if link_response.status_code >= 400:
                        seo_data["link_analysis"]["broken_links"]["count"] += 1
                        seo_data["link_analysis"]["broken_links"]["urls"].append({"url": link, "status_code": link_response.status_code})
                except exceptions.RequestException:
                    seo_data["link_analysis"]["broken_links"]["count"] += 1
                    seo_data["link_analysis"]["broken_links"]["urls"].append({"url": link, "status_code": "Connection Error"})
                time.sleep(0.1)

            return seo_data

        except exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            print(f"An error occurred during parsing: {e}")
            return None


# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         test_url = sys.argv[1]
#     else:
#         print("Usage: python scraper.py \"<url>\"")
#         sys.exit(1)
        
#     print(f"Scraping {test_url} for SEO data...")
#     analysis_report = extract_seo_data(test_url)

#     if analysis_report:
        pprint.pprint(analysis_report)