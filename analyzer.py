# analyzer.py
import json
import pprint
from urllib.parse import urlparse
from scraper import extract_seo_data

def generate_seo_report(seo_data: dict) -> dict:
    report = {
        "overall_score": 100,
        "issues": [],
        "analysis": {}
    }

    def add_issue(points: int, description: str):
        report["overall_score"] -= points
        report["issues"].append(f"(-{points} pts) {description}")

  
    title = seo_data.get("title", "")
    title_text = title
    title_len = len(title_text)
    if not title or title == "No Title Tag Found":
        add_issue(15, "Critical: Page is missing a title tag.")
    elif title_len > 60:
        add_issue(5, "Warning: Title is too long (over 60 characters).")
    elif title_len < 30:
        add_issue(5, "Warning: Title is too short (under 30 characters).")
    report["analysis"]["title"] = {"text": title_text, "length": title_len}
    
    
    meta = seo_data.get("meta_description", "")
    meta_text = meta
    meta_len = len(meta_text)
    if not meta or meta == "No Meta Description Found":
        add_issue(10, "Critical: Page is missing a meta description.")
    elif meta_len > 160:
        add_issue(5, "Warning: Meta description is too long (over 160 characters).")
    report["analysis"]["meta_description"] = {"text": meta_text, "length": meta_len}
    
   
    h1_list = seo_data.get("h1", [])
    h1_count = len(h1_list)
    if h1_count == 0:
        add_issue(15, "Critical: Page is missing an H1 tag.")
    elif h1_count > 1:
        add_issue(10, "Warning: Multiple H1 tags found. There should be only one.")
    report["analysis"]["h1_tags"] = {"count": h1_count, "tags": h1_list}
    
 
    canonical = seo_data.get("canonical", "")
    if not canonical:
        add_issue(10, "Warning: Canonical tag is missing.")
    report["analysis"]["canonical"] = {"url": canonical if canonical else "None"}

  
    word_count = seo_data.get("word_count", 0)
    if word_count < 300:
        add_issue(10, "Warning: Content may be too 'thin' (under 300 words).")
    report["analysis"]["word_count"] = {"count": word_count}
    
  
    headers = seo_data.get("headers", {})
    if headers.get("h3") and not headers.get("h2"):
        add_issue(5, "Warning: H3 tags found without any H2 tags, suggesting poor structure.")
    report["analysis"]["header_structure"] = headers

    report["overall_score"] = max(0, report["overall_score"])
    return report

def export_to_json(report: dict, filename: str):
    """Exports the report dictionary to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"Report exported to {filename}")

def export_to_markdown(report: dict, url: str, filename: str):
    """Exports the report to a formatted Markdown file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# SEO Report for {url}\n\n")
        f.write(f"## 💯 Overall Score: {report['overall_score']}/100\n\n")
        
        f.write("### Issues Found:\n")
        if report['issues']:
            for issue in report['issues']:
                f.write(f"- {issue}\n")
        else:
            f.write("- None! Great job.\n")
        f.write("\n---\n\n")

        f.write("### Detailed Analysis:\n")
        for key, value in report['analysis'].items():
            f.write(f"- **{key.replace('_', ' ').title()}:**\n")
            f.write("```json\n")
            f.write(json.dumps(value, indent=2))
            f.write("\n```\n\n")

    print(f"Report exported to {filename}")


if __name__ == "__main__":
    test_url = "https://takeuforward.org/"
    
    print(f"Analyzing {test_url}...")
    raw_data = extract_seo_data(test_url)
    
    if raw_data:
        final_report = generate_seo_report(raw_data)
        
        print("\n--- SEO Report Summary ---")
        print(f"Overall Score: {final_report['overall_score']}/100")
        print("Issues:")
        pprint.pprint(final_report['issues'])
        print("--------------------------\n")

        domain = urlparse(test_url).netloc
        filename_base = domain.replace('.', '_')

   
        export_to_json(final_report, f"{filename_base}_report.json")
        export_to_markdown(final_report, test_url, f"{filename_base}_report.md")