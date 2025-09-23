# analyzer.py
import json
import pprint
import sys
from urllib.parse import urlparse
import nltk
import textstat
from scraper import extract_seo_data

from sklearn.feature_extraction.text import TfidfVectorizer
# The complete knowledge base for all checks
SUGGESTIONS_KNOWLEDGE_BASE = {
    # Technical SEO
    "https_missing": {"text": "Your site is not using HTTPS. Enabling HTTPS is critical for security, user trust, and SEO.", "impact": "Critical", "effort": "Medium"},
    "viewport_missing": {"text": "The mobile viewport meta tag is missing, which harms the user experience on mobile devices.", "impact": "Critical", "effort": "Low"},
    "ttfb_slow": {"text": "Your server's Time to First Byte (TTFB) was {value:.2f}s. Aim for under 0.8s for a better user experience.", "impact": "High", "effort": "High"},
    "robots_txt_missing": {"text": "A robots.txt file was not found. This file is important for guiding search engine crawlers.", "impact": "Medium", "effort": "Low"},
    "sitemap_missing": {"text": "A sitemap.xml file was not found. Sitemaps help search engines discover and index your pages.", "impact": "Medium", "effort": "Low"},
    # On-Page Content
    "title_missing": {"text": "The page is missing a title tag. The title tag is a critical on-page SEO factor.", "impact": "Critical", "effort": "Low"},
    "title_too_long": {"text": "The title tag is {value} characters long. Aim for under 60 characters to avoid truncation in search results.", "impact": "Medium", "effort": "Low"},
    "meta_description_missing": {"text": "The page is missing a meta description, which can lead to lower click-through rates from search results.", "impact": "High", "effort": "Low"},
    "canonical_missing": {"text": "The canonical tag is missing. This can lead to duplicate content issues.", "impact": "High", "effort": "Low"},
    "h1_missing": {"text": "The page is missing an H1 tag. Every page should have one main heading.", "impact": "High", "effort": "Low"},
    "multiple_h1s": {"text": "Multiple H1 tags were found. A page should only have a single H1 tag.", "impact": "Medium", "effort": "Low"},
    "header_structure_issue": {"text": "H3 tags were found without any preceding H2 tags, suggesting poor content structure.", "impact": "Low", "effort": "Medium"},
    "word_count_low": {"text": "The word count is only {value} words. Content may be too 'thin'. Aim for 300+ words for substantive content.", "impact": "Medium", "effort": "Medium"},
    "readability_low": {"text": "The content's Flesch Reading Ease score is {value:.2f}, which may be difficult to read. Aim for a score of 60 or higher.", "impact": "Low", "effort": "High"},
    # Image Analysis
    "images_missing_alt_critical": {"text": "{value} of images are missing alt attributes. This is a critical accessibility and SEO issue.", "impact": "Critical", "effort": "Medium"},
    "images_missing_alt_warning": {"text": "{value} of images are missing alt attributes. Adding descriptive alt text helps with accessibility and image SEO.", "impact": "Medium", "effort": "Medium"},
    "images_low_quality_alts": {"text": "{value} image(s) have low-quality alt text (e.g., generic, too long, or too short).", "impact": "Low", "effort": "Medium"},
    # Keyword Analysis
    "keyword_missing_title": {"text": "The target keyword was not found in the title tag.", "impact": "High", "effort": "Low"},
    "keyword_missing_meta": {"text": "The target keyword was not found in the meta description.", "impact": "Medium", "effort": "Low"},
    "keyword_missing_h1": {"text": "The target keyword was not found in the H1 tag.", "impact": "High", "effort": "Low"},
    "keyword_density_off": {"text": "Keyword density is {value:.2f}%. A healthy range is typically 0.5% to 2.5%.", "impact": "Medium", "effort": "Medium"},
}

#getting the best keywords for seo
def extract_keywords(text: str, num_cnt: int = 5) -> list:
    try:
        nltk.data.find('corpora/stopwords')
    except nltk.downloader.DownloadError:
        print("Downloading 'stopwords' for NLTK (this happens only once)...")
        nltk.download('stopwords', quiet=True)
        
    stop_words = nltk.corpus.stopwords.words('english')

    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        max_features=num_cnt
    )
    try:
        vectorizer.fit_transform([text])
        return vectorizer.get_feature_names_out().tolist()
    except ValueError:
        return [] 

def generate_seo_report(seo_data: dict, target_keyword: str) -> dict:
    report = {
        "overall_score": 100,
        "suggestions": [],
        "analysis": {}
    }
    target_keyword = target_keyword.lower()
    findings = []

    title = seo_data.get("title", "")
    if not title or title == "No Title Tag Found":
        findings.append({"key": "title_missing"})
    elif len(title) > 60:
        findings.append({"key": "title_too_long", "value": len(title)})
    report["analysis"]["title"] = {"text": title, "length": len(title)}

    meta = seo_data.get("meta_description", "")
    if not meta or meta == "No Meta Description Found":
        findings.append({"key": "meta_description_missing"})
    report["analysis"]["meta_description"] = {"text": meta, "length": len(meta)}

    canonical = seo_data.get("canonical", "")
    if not canonical:
        findings.append({"key": "canonical_missing"})
    report["analysis"]["canonical"] = {"url": canonical if canonical else "None"}

    h1_list = seo_data.get("h1", [])
    if len(h1_list) == 0:
        findings.append({"key": "h1_missing"})
    elif len(h1_list) > 1:
        findings.append({"key": "multiple_h1s"})
    report["analysis"]["h1_tags"] = {"count": len(h1_list), "tags": h1_list}

    headers = seo_data.get("headers", {})
    if headers.get("h3") and not headers.get("h2"):
        findings.append({"key": "header_structure_issue"})
    report["analysis"]["header_structure"] = headers

    performance_data = seo_data.get("performance", {})
    if not performance_data.get("is_https"):
        findings.append({"key": "https_missing"})
    if not performance_data.get("has_viewport"):
        findings.append({"key": "viewport_missing"})
    ttfb = performance_data.get("ttfb")
    if ttfb and ttfb > 0.8:
        findings.append({"key": "ttfb_slow", "value": ttfb})
    report["analysis"]["performance"] = performance_data

    site_files_data = seo_data.get("site_files", {})
    if not site_files_data.get("has_robots_txt"):
        findings.append({"key": "robots_txt_missing"})
    if not site_files_data.get("has_sitemap"):
        findings.append({"key": "sitemap_missing"})
    report["analysis"]["site_files"] = site_files_data

    body_text = seo_data.get("body_text", "")
    if body_text:
        flesch_score = textstat.flesch_reading_ease(body_text)
        if flesch_score < 50:
            findings.append({"key": "readability_low", "value": flesch_score})
        report["analysis"]["readability"] = {"flesch_reading_ease_score": flesch_score}
        keywords = extract_keywords(body_text, num_cnt=5)
        report["analysis"]["extracted_keywords"] = keywords
    word_count = seo_data.get("word_count", 0)
    if 0 < word_count < 300:
        findings.append({"key": "word_count_low", "value": word_count})
    report["analysis"]["word_count"] = {"count": word_count}

    image_data = seo_data.get("image_analysis", {})
    total_images = image_data.get("count", 0)
    missing_alt_count = image_data.get("missing_alt_count", 0)
    if total_images > 0:
        missing_ratio = missing_alt_count / total_images
        if missing_ratio > 0.25:
            findings.append({"key": "images_missing_alt_critical", "value": f"{missing_ratio:.0%}"})
        elif missing_ratio > 0.05:
            findings.append({"key": "images_missing_alt_warning", "value": f"{missing_ratio:.0%}"})
    
    low_quality_alts = 0
    generic_alts = ["image", "picture", "graphic", "photo", "alt text"]
    alt_texts = image_data.get("alt_texts", [])
    for text in alt_texts:
        if text.lower() in generic_alts or len(text) > 125 or (1 < len(text) < 5):
            low_quality_alts += 1
    if low_quality_alts > 0:
        findings.append({"key": "images_low_quality_alts", "value": low_quality_alts})
    report["analysis"]["image_analysis"] = {"total_images": total_images, "missing_alt_count": missing_alt_count, "low_quality_alt_tags": low_quality_alts}

    #target keyword
    if target_keyword:
        if target_keyword not in title.lower():
            findings.append({"key": "keyword_missing_title"})
        if target_keyword not in meta.lower():
            findings.append({"key": "keyword_missing_meta"})
        if not any(target_keyword in h1.lower() for h1 in h1_list):
            findings.append({"key": "keyword_missing_h1"})
        
        keyword_count = body_text.lower().count(target_keyword)
        density = (keyword_count / word_count * 100) if word_count > 0 else 0
        if not (0.5 <= density <= 2.5):
            findings.append({"key": "keyword_density_off", "value": density})
        report["analysis"]["keyword_analysis"] = {"keyword_density": f"{density:.2f}%", "keyword_count": keyword_count}

    impact_scores = {"Critical": 10, "High": 7, "Medium": 4, "Low": 1}
    effort_scores = {"Low": 1, "Medium": 3, "High": 5}
    point_deductions = {"Critical": 15, "High": 10, "Medium": 5, "Low": 2}

    for finding in findings:
        key = finding["key"]
        if key in SUGGESTIONS_KNOWLEDGE_BASE:
            template = SUGGESTIONS_KNOWLEDGE_BASE[key]
            impact = template["impact"]
            effort = template["effort"]
            priority_score = impact_scores.get(impact, 1) / effort_scores.get(effort, 1)
            points = point_deductions.get(impact, 0)
            report["overall_score"] -= points
            
            suggestion_text = template["text"].format(value=finding.get("value"))

            report["suggestions"].append({
                "priority_score": round(priority_score, 2),
                "impact": impact,
                "effort": effort,
                "suggestion": f"(-{points} pts) {suggestion_text}"
            })

    report["suggestions"].sort(key=lambda x: x["priority_score"], reverse=True)
    report["overall_score"] = max(0, report["overall_score"])
    return report

#exporting the report to json file 
def export_to_json(report: dict, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"Report exported to {filename}")

#.md file 
def export_to_markdown(report: dict, url: str, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# SEO Report for {url}\n\n## 💯 Overall Score: {report['overall_score']}/100\n\n")
        f.write("### Prioritized Suggestions:\n")
        if report["suggestions"]:
            for item in report["suggestions"]:
                f.write(f"- **Impact: {item['impact']} | Effort: {item['effort']}**\n")
                f.write(f"  - {item['suggestion']}\n\n")
        else:
            f.write("- None! Great job.\n")
        f.write("\n---\n\n### Detailed Analysis:\n")
        for key, value in report['analysis'].items():
            f.write(f"- **{key.replace('_', ' ').title()}:**\n```json\n{json.dumps(value, indent=2)}\n```\n\n")
    print(f"Report exported to {filename}")

#main part
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
        print("Prioritized Suggestions:")
        pprint.pprint([item['suggestion'] for item in final_report['suggestions']])
        print("--------------------------\n")

        domain = urlparse(test_url).netloc
        filename_base = f"{domain.replace('.', '_')}_{target_keyword.replace(' ', '_')}"

        export_to_json(final_report, f"{filename_base}_report.json")
        export_to_markdown(final_report, test_url, f"{filename_base}_report.md")