# analyzer.py
import json
import pprint
import sys
from urllib.parse import urlparse

from scraper import extract_seo_data
from collections import defaultdict


def generate_seo_report(seo_data: dict, target_keyword: str) -> dict:
    report = {
        "overall_score": 100,
        "issues": [],
        "analysis": {}
    }
    target_keyword = target_keyword.lower()

    def add_issue(points: int, description: str):
        report["overall_score"] -= points
        report["issues"].append(f"(-{points} pts) {description}")

    title = seo_data.get("title", "")
    if not title or title == "No Title Tag Found":
        add_issue(15, "Critical: Page is missing a title tag.")
    report["analysis"]["title"] = {"text": title, "length": len(title)}
    
    meta = seo_data.get("meta_description", "")
    if not meta or meta == "No Meta Description Found":
        add_issue(10, "Critical: Page is missing a meta description.")
    report["analysis"]["meta_description"] = {"text": meta, "length": len(meta)}
    
    h1_list = seo_data.get("h1", [])
    if len(h1_list) == 0:
        add_issue(15, "Critical: Page is missing an H1 tag.")
    elif len(h1_list) > 1:
        add_issue(10, "Warning: Multiple H1 tags found.")
    report["analysis"]["h1_tags"] = {"count": len(h1_list), "tags": h1_list}

    canonical = seo_data.get("canonical", "")
    if not canonical:
        add_issue(10, "Warning: Canonical tag is missing.")
    report["analysis"]["canonical"] = {"url": canonical if canonical else "None"}

    structured_data = seo_data.get("structured_data", {})
    if not structured_data or "error" in structured_data:
        add_issue(5, "Warning: No valid Structured Data (Schema) found.")
    report["analysis"]["structured_data"] = structured_data
    
    performance_data = seo_data.get("performance", {})
    ttfb = performance_data.get("ttfb")
    if ttfb and ttfb > 0.8:
        add_issue(5, f"Warning: Server response time (TTFB) is slow ({ttfb:.2f}s).")
    if not performance_data.get("has_viewport"):
        add_issue(10, "Critical: The mobile viewport meta tag is missing.")
    report["analysis"]["performance"] = performance_data

    
    site_data = seo_data.get("site_files", {})
    if not site_data.get("has_robots_txt"):
        add_issue(5, "Warning: No robots.txt file found.")
    if not site_data.get("has_sitemap"):
        add_issue(5, "Warning: No sitemap.xml file found.")
    report["analysis"]["site_files"] = site_data
    
    
    
    keyword_analysis = {}
    
    keyword_in_title = target_keyword in title.lower()
    if not keyword_in_title:
        add_issue(10, "High Priority: Target keyword is missing from the title tag.")
    keyword_analysis["keyword_in_title"] = keyword_in_title
    
   
    keyword_in_meta = target_keyword in meta.lower()
    if not keyword_in_meta:
        add_issue(5, "Medium Priority: Target keyword is missing from the meta description.")
    keyword_analysis["keyword_in_meta_description"] = keyword_in_meta
    

    keyword_in_h1 = any(target_keyword in h1.lower() for h1 in h1_list)
    if not keyword_in_h1:
        add_issue(10, "High Priority: Target keyword is missing from the H1 tag.")
    keyword_analysis["keyword_in_h1"] = keyword_in_h1
    

    word_count = seo_data.get("word_count", 0)
    body_text = seo_data.get("body_text", "")
    keyword_count = body_text.lower().count(target_keyword)
    density = (keyword_count / word_count * 100) if word_count > 0 else 0
    if not (0.5 <= density <= 2.5):
        add_issue(5, f"Warning: Keyword density is {density:.2f}%. A healthy range is 0.5% to 2.5%.")
    keyword_analysis["keyword_density"] = f"{density:.2f}%"
    keyword_analysis["keyword_count"] = keyword_count
    
    report["analysis"]["keyword_analysis"] = keyword_analysis

    sites_files=seo_data.get("site_files",{})
    
 
    image_analysis = seo_data.get("image_analysis",{})
    count = image_analysis.get("count",0)
    missing_alt = image_analysis.get("missing_alt_count",0)
    alt_texts = image_analysis.get("alt_texts",[])

    if count == 0:
        add_issue(5, "Warning: No images found on the page.")
    if missing_alt > 0:
        missing_ratio = missing_alt / count
        if missing_ratio > 0.25:
            add_issue(10, f"Critical: {missing_alt}/{count} ({missing_ratio:.0%}) of images are missing alt attributes.")
        elif missing_ratio > 0.05:
            add_issue(5, f"Warning: {missing_alt}/{count} ({missing_ratio:.0%}) of images are missing alt attributes.")

    low_quality_alts = 0
    generic_alts = ["image", "picture", "graphic", "photo", "alt text"]
    for text in alt_texts:
        text_lower = text.lower()
        if text_lower in generic_alts or len(text) > 125 or (1 < len(text) < 5):
            low_quality_alts += 1
            
    if low_quality_alts > 0:
        add_issue(5, f"Warning: Found {low_quality_alts} image(s) with low-quality alt text.")

    report["analysis"]["image_alt_tag_analysis"] = {
        "total_images": count,
        "images_missing_alt_attr": missing_alt,
        "low_quality_alt_tags": low_quality_alts,
    }
    report["analysis"]["word_count"] = {"count": word_count}
    headers = seo_data.get("headers", {})
    if headers.get("h3") and not headers.get("h2"):
        add_issue(5, "Warning: H3 tags found without any H2 tags.")
    report["analysis"]["header_structure"] = headers

    report["overall_score"] = max(0, report["overall_score"])
    return report


def export_to_json(report: dict, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"Report exported to {filename}")

def export_to_markdown(report: dict, url: str, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# SEO Report for {url}\n\n## 💯 Overall Score: {report['overall_score']}/100\n\n")
        f.write("### Issues Found:\n")
        if report['issues']:
            for issue in report['issues']: f.write(f"- {issue}\n")
        else:
            f.write("- None! Great job.\n")
        f.write("\n---\n\n### Detailed Analysis:\n")
        for key, value in report['analysis'].items():
            f.write(f"- **{key.replace('_', ' ').title()}:**\n```json\n{json.dumps(value, indent=2)}\n```\n\n")
    print(f"Report exported to {filename}")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        test_url = sys.argv[1]
        target_keyword = sys.argv[2]
    else:
        print("Error: Please provide a URL and a target keyword as arguments.")
        print("Usage: python analyzer.py \"<url>\" \"<keyword>\"")
        sys.exit(1)
    
    print(f"Analyzing {test_url} for the keyword '{target_keyword}'...")
    raw_data = extract_seo_data(test_url)
    
    if raw_data:
        final_report = generate_seo_report(raw_data, target_keyword)
        
        print("\n--- SEO Report Summary ---")
        print(f"Overall Score: {final_report['overall_score']}/100")
        print("Issues:")
        pprint.pprint(final_report['issues'])
        print("--------------------------\n")

        domain = urlparse(test_url).netloc
        filename_base = f"{domain.replace('.', '_')}_{target_keyword.replace(' ', '_')}"

        export_to_json(final_report, f"{filename_base}_report.json")
        export_to_markdown(final_report, test_url, f"{filename_base}_report.md")