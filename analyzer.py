import json
import pprint
import sys
from urllib.parse import urlparse
import re
import nltk
import textstat
from scraper import extract_seo_data
from Features.SpellCheckTest import spell_check_test
from Features.ResponsiveImageTest import responsive_image_test
from Features.ImageRatioTest import image_ratio_test
from Features.seo_friendly import seo_friendly_url_test
from Features.DirectiveTest import disallow_directive_test
from Features.MetaRefreshTest import meta_refresh_test
from Features.ErrorPageTest import error_page_test
from Features.MediaQueryResponsiveTest import media_query_responsive_test
from Features.KeywordCloudTest import generate_keyword_cloud 
# Ensure NLTK data is available
try:
    nltk.data.find('corpora/stopwords')
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    TfidfVectorizer = None

FEATURE_ANALYSIS_MAP = {
    # --- Content Category ---
    "title_tag": {
        "feature_name": "HTML Title Tag", "category": "Content",
        "description": "The title tag specifies the title of a web page, displayed in browser tabs and on SERPs.",
        "pros": "A well-crafted title is a primary factor for click-through rates and helps search engines understand the page's content.",
        "pass_message": "The page has a title tag within the optimal length (10-60 characters).",
        "fail_messages": {
            "title_missing": "The page is missing a title tag, a critical on-page SEO factor.",
            "title_too_long": "The title tag is too long. Titles over 60 characters may be truncated in search results."
        },
        "recommendation": "Write a unique, descriptive title between 10 and 60 characters that includes the primary keyword."
    },
    "meta_description": {
        "feature_name": "Meta Description", "category": "Content",
        "description": "The meta description provides a brief summary of a web page, often used as the snippet in search results.",
        "pros": "A compelling meta description can significantly improve click-through rates from search.",
        "pass_message": "The page has a meta description.",
        "fail_messages": {"meta_description_missing": "The page is missing a meta description, which can lead to lower click-through rates."},
        "recommendation": "Add a unique meta description between 50 and 160 characters that summarizes the page and encourages clicks."
    },
    "h1_heading": {
        "feature_name": "H1 Heading Tag", "category": "Content",
        "description": "The H1 tag is the main heading on a page and should represent its primary topic.",
        "pros": "A clear H1 helps users and search engines quickly understand the page's main topic and improves content structure.",
        "pass_message": "The page has exactly one H1 tag, which is ideal for SEO.",
        "fail_messages": {
            "h1_missing": "The page is missing an H1 tag. Every page should have one main heading.",
            "multiple_h1s": "The page has multiple H1 tags. Using more than one can dilute its SEO value."
        },
        "recommendation": "Ensure every page has one, and only one, H1 tag that accurately describes the page content."
    },
    "header_structure": {
        "feature_name": "Heading Structure", "category": "Content",
        "description": "Headings (H1-H6) should follow a logical, hierarchical order to structure the content.",
        "pros": "A proper heading structure improves readability for both users and search engines, and enhances accessibility.",
        "pass_message": "The heading structure appears to be logical.",
        "fail_messages": {"header_structure_issue": "The page uses H3 tags without a preceding H2, indicating a potentially broken heading hierarchy."},
        "recommendation": "Ensure headings follow a logical sequence (e.g., H1 -> H2 -> H3) without skipping levels."
    },
    "structured_data": {
    "feature_name": "Structured Data (Schema)", "category": "Technical",
    "description": "Checks for the presence of structured data (like JSON-LD), which helps search engines understand your content for rich snippets.",
    "pros": "Correctly implemented structured data can lead to enhanced search results (rich snippets), improving visibility and CTR.",
    "pass_message": "Structured data (JSON-LD) was found on the page.",
    "fail_messages": {
        "structured_data_missing": "No structured data (JSON-LD) was found. This is a missed opportunity for rich snippets."
    },
    "recommendation": "Implement structured data (Schema.org) using JSON-LD to describe your content to search engines."
    },
    "word_count": {
        "feature_name": "Word Count", "category": "Content",
        "description": "The total number of words in the main body of the page.",
        "pros": "Sufficient content length (typically 300+ words) is often necessary to cover a topic in detail, which is favored by search engines.",
        "pass_message": "The page has a sufficient word count, suggesting it contains substantial content.",
        "fail_messages": {"word_count_low": "The word count is low. Content may be too 'thin' to rank for competitive keywords."},
        "recommendation": "Aim for a word count of at least 300 words, ensuring the content is comprehensive and valuable to the reader."
    },
    "link_analysis": {
    "feature_name": "Link Health Check", "category": "Technical",
    "description": "Analyzes the internal, external, and broken links on the page.",
    "pros": "A clean link profile with no broken links improves user experience and crawlability.",
    "pass_message": "No broken links were found on the page.",
    "fail_messages": {
        "broken_links_found": "Broken links (4xx errors) were detected. These harm user experience and SEO.",
        "no_external_links": "The page does not contain any external links, which can be a missed opportunity to cite sources and provide value."
    },
    "recommendation": "Review and fix all broken links immediately. Ensure you are linking out to relevant, high-authority external resources where appropriate."
    },
   
    "mixed_content": {
    "feature_name": "Mixed Content (HTTP in HTTPS)", "category": "Technical",
    "description": "Checks if a secure (HTTPS) page is loading insecure (HTTP) resources like images, scripts, or stylesheets.",
    "pros": "A page free of mixed content is fully secure, protects users, and avoids browser security warnings.",
    "pass_message": "The page does not have any mixed content issues.",
    "fail_messages": {
        "mixed_content_found": "Insecure (HTTP) resources were found on this secure (HTTPS) page. This creates security vulnerabilities and can cause browser warnings."
    },
    "recommendation": "Identify and update all insecure resource links from 'http://' to 'https://' or remove them."
    },
    "readability": {
        "feature_name": "Content Readability", "category": "Content",
        "description": "Readability scores (like Flesch Reading Ease) measure how easy it is to understand the text.",
        "pros": "Easy-to-read content keeps users engaged, reduces bounce rates, and is accessible to a wider audience.",
        "pass_message": "The content's readability score indicates it is easy for most users to understand.",
        "fail_messages": {"readability_low": "The content may be difficult to read, which can lead to poor user engagement."},
        "recommendation": "Simplify complex sentences, use shorter paragraphs, and avoid jargon to improve the Flesch Reading Ease score to 60 or higher."
    },
    "image_alt_text": {
        "feature_name": "Image Alt Text", "category": "Content",
        "description": "Alt (alternative) text is an HTML attribute on `<img>` tags that describes the image for accessibility and SEO.",
        "pros": "Improves accessibility for screen readers and helps search engines index images, creating another opportunity to rank.",
        "pass_message": "All or most images on the page have descriptive alt text attributes.",
        "fail_messages": {
            "images_missing_alt_critical": "A high percentage of images are missing alt text. This is a major accessibility and SEO issue.",
            "images_missing_alt_warning": "Some images are missing alt text, a missed opportunity for SEO and accessibility.",
            "images_low_quality_alts": "Some images have low-quality alt text (e.g., too generic, too long, or stuffed with keywords)."
        },
        "recommendation": "Add descriptive, concise alt text to every meaningful image on the page."
    },
    "keyword_analysis": {
        "feature_name": "Target Keyword Usage", "category": "Content",
        "description": "Checks if a specific target keyword is present in key on-page elements (title, meta, H1) and at a reasonable density.",
        "pros": "Proper keyword placement is a fundamental signal to search engines about the page's topic.",
        "pass_message": "The target keyword is well-integrated into the page's key SEO elements.",
        "fail_messages": {
            "keyword_missing_title": "The target keyword was not found in the title tag.",
            "keyword_missing_meta": "The target keyword was not found in the meta description.",
            "keyword_missing_h1": "The target keyword was not found in the H1 tag.",
            "keyword_density_off": "Keyword density is outside the healthy range of 0.5%-2.5%."
        },
        "recommendation": "Ensure the target keyword appears naturally in the title, meta description, H1 tag, and throughout the body content."
    },
    "spell_check": {
        "feature_name": "Spelling and Grammar", "category": "Content",
        "description": "Checks for misspelled words in the page's body text.",
        "pros": "Correct spelling and grammar enhance user trust, professionalism, and credibility.",
        "pass_message": "No significant spelling errors were detected.",
        "fail_messages": {"spell_check_misspelled": "Misspelled words were detected on the page."},
        "recommendation": "Proofread the content carefully and correct any spelling or grammatical errors."
    },

    # --- Technical Category ---
    "https_usage": {
        "feature_name": "HTTPS Usage", "category": "Technical",
        "description": "HTTPS encrypts data between a user's browser and your website, ensuring security and trust.",
        "pros": "Crucial for user trust, data security, and is a confirmed Google ranking factor.",
        "pass_message": "The page is served over a secure HTTPS connection.",
        "fail_messages": {"https_missing": "The page is not using HTTPS. This is a critical security and SEO issue."},
        "recommendation": "Install an SSL/TLS certificate and redirect all HTTP traffic to HTTPS."
    },
    "ssl_certificate": {
        "feature_name": "SSL Certificate Validity", "category": "Technical",
        "description": "Checks if the SSL certificate is valid and not expiring soon.",
        "pros": "A valid SSL certificate is required for HTTPS and prevents security warnings in browsers.",
        "pass_message": "The SSL certificate is valid and not expiring soon.",
        "fail_messages": {"certificate_expiring_soon": "The site's SSL certificate is expiring soon, which could lead to security warnings."},
        "recommendation": "Renew the SSL certificate well before its expiration date to avoid site downtime or security issues."
    },
    "viewport_meta_tag": {
        "feature_name": "Viewport Meta Tag", "category": "Technical",
        "description": "The viewport meta tag instructs the browser on how to control the page's dimensions and scaling, making it responsive.",
        "pros": "Essential for mobile-friendliness, ensuring your website displays correctly on all screen sizes.",
        "pass_message": "A mobile viewport meta tag is present, which is great for mobile usability.",
        "fail_messages": {"viewport_missing": "The mobile viewport meta tag is missing, which will cause rendering issues on mobile devices."},
        "recommendation": "Add `<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">` to the `<head>` section."
    },
    "robots_txt": {
        "feature_name": "robots.txt File", "category": "Technical",
        "description": "A robots.txt file tells search engine crawlers which pages or files the crawler can or can't request from your site.",
        "pros": "Allows control over crawler access, preventing issues with duplicate content and saving crawl budget.",
        "pass_message": "A robots.txt file was found at the root of the domain.",
        "fail_messages": {"robots_txt_missing": "A robots.txt file was not found. This is highly recommended for guiding search engines."},
        "recommendation": "Create a robots.txt file in the root directory. At a minimum, it should link to your sitemap."
    },
    "sitemap": {
        "feature_name": "XML Sitemap", "category": "Technical",
        "description": "An XML sitemap is a file that lists the important URLs on a website, helping search engines with discovery and indexing.",
        "pros": "Helps search engines find all your important content, especially for large websites or those with complex structures.",
        "pass_message": "An XML sitemap was found.",
        "fail_messages": {"sitemap_missing": "A sitemap.xml file was not found. This can slow down the indexing of your pages."},
        "recommendation": "Create and submit an XML sitemap to Google Search Console and list its location in your robots.txt file."
    },
    "canonical_tag": {
        "feature_name": "Canonical Tag", "category": "Technical",
        "description": "The canonical tag tells search engines which version of a URL is the master copy to prevent duplicate content issues.",
        "pros": "Consolidates link equity for similar or duplicate pages into a single, authoritative source, strengthening its ranking potential.",
        "pass_message": "The page specifies a canonical URL.",
        "fail_messages": {"canonical_missing": "The canonical tag is missing. This can lead to duplicate content issues if the page is accessible via multiple URLs."},
        "recommendation": "Add a self-referencing canonical tag (`<link rel=\"canonical\" href=\"...\">`) to all indexable pages."
    },
    "meta_robots": {
        "feature_name": "Meta Robots Tag", "category": "Technical",
        "description": "The meta robots tag provides crawlers with instructions on how to crawl or index page content.",
        "pros": "Provides granular control over how search engines interact with individual pages.",
        "pass_message": "The meta robots tag does not prevent indexing.",
        "fail_messages": {"meta_robots_noindex": "This page has a \"noindex\" meta tag, which prevents it from being shown in search results."},
        "recommendation": "Remove the 'noindex' directive from the meta robots tag unless you intentionally want to keep this page out of search engines."
    },
    "seo_friendly_url": {
        "feature_name": "SEO-Friendly URL Structure", "category": "Technical",
        "description": "An SEO-friendly URL is short, descriptive, and easy for both users and search engines to understand.",
        "pros": "Improves user experience, is easier to share, and can provide a small SEO boost when it contains relevant keywords.",
        "pass_message": "The URL structure appears to be SEO-friendly.",
        "fail_messages": {"seo_friendly_url_fail": "The URL contains elements that are not SEO-friendly (e.g., uppercase letters, underscores, excessive parameters)."},
        "recommendation": "Use lowercase letters, separate words with hyphens (-), and keep URLs short and descriptive."
    },
    "custom_404_page": {
        "feature_name": "Custom 404 Error Page", "category": "Technical",
        "description": "A custom 404 page helps guide users back to relevant content when they land on a nonexistent page.",
        "pros": "Improves user experience by keeping users on your site, which can reduce bounce rates.",
        "pass_message": "A custom, user-friendly 404 error page was detected.",
        "fail_messages": {
            "custom_404_missing": "The site does not appear to serve a custom 404 page.",
            "custom_404_status_issue": "The 404 page is returning an incorrect HTTP status code (e.g., 200 OK), which can confuse search engines."
            },
        "recommendation": "Create a custom 404 error page with your site's branding and helpful navigation links, and ensure it returns a 404 HTTP status code."
    },
      "mobile_snapshot": {
        "feature_name": "Mobile Snapshot", "category": "Technical",
        "description": "A visual snapshot of how the page renders on a standard mobile device viewport.",
        "pros": "Provides a quick, visual confirmation of mobile-friendliness and helps identify layout or rendering issues on small screens.",
        "pass_message": "A mobile snapshot was successfully generated.",
        "fail_messages": {
            "snapshot_failed": "Could not generate a mobile snapshot. This may indicate a page loading error or a problem with the headless browser."
        },
        "recommendation": "Check the page for loading errors. The snapshot is a key tool for debugging the mobile user experience."
    },
    "meta_refresh": {
        "feature_name": "Meta Refresh Tag", "category": "Technical",
        "description": "A meta refresh tag is an HTML element that instructs the browser to automatically refresh the page or redirect to a different URL after a time interval.",
        "pros": "There are very few modern use cases; 301 redirects are strongly preferred for SEO.",
        "pass_message": "No meta refresh tags were found on the page.",
        "fail_messages": {"meta_refresh_found": "A meta refresh tag was found. Search engines may interpret this as a sneaky redirect, and it can harm usability."},
        "recommendation": "Avoid using meta refresh tags. Use server-side 301 redirects for permanent URL changes."
    },
    "console_errors": {
        "feature_name": "JavaScript Console Errors", "category": "Technical",
        "description": "Checks for errors in the browser's JavaScript console, which can indicate broken functionality.",
        "pros": "A clean console is a sign of a well-maintained site and ensures all interactive elements work as intended.",
        "pass_message": "No JavaScript console errors were detected.",
        "fail_messages": {"js_console_errors": "JavaScript console errors were detected, which could break site functionality and harm user experience."},
        "recommendation": "Review the browser's developer console to identify and fix any JavaScript errors."
    },

    # --- Performance Category ---
    "ttfb": {
        "feature_name": "Time to First Byte (TTFB)", "category": "Performance",
        "description": "TTFB measures the responsiveness of a web server; it's the time it takes for a browser to receive the first byte of data.",
        "pros": "A fast TTFB is the foundation of a fast-loading page and a good user experience.",
        "pass_message": "The server's Time to First Byte (TTFB) is fast.",
        "fail_messages": {"ttfb_slow": "The server's TTFB is slow, indicating potential issues with server configuration, hosting, or backend code."},
        "recommendation": "Aim for a TTFB under 0.8 seconds. This can be improved with better hosting, server-side caching, or a Content Delivery Network (CDN)."
    },
    "dom_size": {
    "feature_name": "DOM Size", "category": "Performance",
    "description": "The DOM (Document Object Model) represents all the HTML elements on your page. A very large DOM can slow down page rendering and interactivity.",
    "pros": "A lean DOM is processed faster by the browser, leading to a quicker and smoother user experience.",
    "pass_message": "The page has a reasonable number of DOM nodes.",
    "fail_messages": {
        "dom_size_large": "The DOM size is very large. Excessive DOM nodes can harm rendering performance and memory usage."
    },
    "recommendation": "Aim for fewer than 1,500 total DOM nodes. Reduce complexity by removing unnecessary HTML elements or containers."
    },
    "html_page_size": {
    "feature_name": "HTML Page Size", "category": "Performance",
    "description": "This is the size of the initial HTML document downloaded by the browser.",
    "pros": "A small HTML document size allows the browser to start rendering the page very quickly.",
    "pass_message": "The HTML document size is lean and optimized.",
    "fail_messages": {
        "html_page_size_large": "The HTML file size is large. This can delay the start of the page rendering process."
    },
    "recommendation": "Keep your HTML document under 100-150 KB. Minify HTML and avoid embedding large amounts of CSS or JavaScript directly in the page."
    },
    "total_requests": {
    "feature_name": "Total Network Requests", "category": "Performance",
    "description": "The total number of resources (CSS, JS, images, fonts, etc.) the browser needs to fetch to render the page.",
    "pros": "Fewer requests mean less network overhead and faster load times, especially on mobile connections.",
    "pass_message": "The page makes a reasonable number of network requests.",
    "fail_messages": {
        "too_many_requests": "The page makes a high number of network requests, which can significantly slow down loading."
    },
    "recommendation": "Reduce the number of requests by combining CSS and JS files, using CSS sprites for images, and removing unnecessary third-party scripts. Aim for under 75 requests."
    },
    "core_web_vitals": {
        "feature_name": "Core Web Vitals", "category": "Performance",
        "description": "A set of metrics related to speed, responsiveness, and visual stability (LCP, FID/INP, CLS).",
        "pros": "Good Core Web Vitals scores are a confirmed Google ranking factor and are essential for a good user experience.",
        "pass_message": "Core Web Vitals metrics are within the 'Good' thresholds.",
        "fail_messages": {
            "lcp_slow": "Largest Contentful Paint (LCP) is slow, indicating the main content takes too long to load.",
            "cls_bad": "Cumulative Layout Shift (CLS) is high, indicating poor visual stability which frustrates users.",
            "fcp_slow": "First Contentful Paint (FCP) is slow, meaning users see a blank screen for too long."
        },
        "recommendation": "Optimize images, defer non-critical CSS/JS, and properly size image/ad spaces to improve LCP and CLS. Aim for LCP < 2.5s and CLS < 0.1."
    },
    "canonicalization_check": {
    "feature_name": "URL Canonicalization", "category": "Technical",
    "description": "Checks if different versions of the homepage (e.g., www vs. non-www) resolve to a single, consistent URL.",
    "pros": "Proper canonicalization prevents duplicate content issues and consolidates link equity to a single URL.",
    "pass_message": "The www and non-www versions of the URL resolve consistently.",
    "fail_messages": {
        "canonicalization_issue": "The www and non-www versions of the URL resolve to different final destinations, which can cause duplicate content issues."
    },
    "recommendation": "Implement a server-side 301 redirect to consolidate all versions of your domain to a single, preferred version (either www or non-www)."
    },
   
    "hsts_test": {
    "feature_name": "HSTS Header Test", "category": "Technical",
    "description": "Checks for the presence of the HTTP Strict-Transport-Security (HSTS) header, which forces browsers to use secure connections.",
    "pros": "HSTS enhances security by preventing protocol downgrade attacks and cookie hijacking.",
    "pass_message": "The HSTS header is correctly implemented.",
    "fail_messages": {
        "hsts_missing": "The HSTS (Strict-Transport-Security) header was not found. This is a missed security enhancement."
    },
    "recommendation": "Implement the HSTS header to ensure all connections to your site are secure."
},
    "disallow_directive": {
    "feature_name": "Robots.txt Disallow Check", "category": "Technical",
    "description": "Checks if the current URL is explicitly disallowed for crawling in the robots.txt file.",
    "pros": "Ensuring important pages are not disallowed is critical for indexing.",
    "pass_message": "The URL is not disallowed by the robots.txt file.",
    "fail_messages": {
        "url_disallowed": "This URL is disallowed from crawling by the robots.txt file, which will prevent it from being indexed by search engines."
    },
    "recommendation": "Remove the 'disallow' rule for this URL from your robots.txt file if you want it to be indexed."
},
    "html_compression": {
        "feature_name": "HTML Compression", "category": "Performance",
        "description": "Compressing HTML files (using GZIP or Brotli) before sending them from the server reduces their file size.",
        "pros": "Reduces the amount of data that needs to be transferred, significantly speeding up page load times.",
        "pass_message": "The HTML response is compressed.",
        "fail_messages": {"html_compression_missing": "The HTML response is not compressed. This is a missed opportunity for a major performance improvement."},
        "recommendation": "Enable GZIP or Brotli compression on your web server."
    },
        "js_minification": {
        "feature_name": "JavaScript Minification", "category": "Performance",
        "description": "Minification removes unnecessary characters from JS files (like whitespace and comments) to reduce their size.",
        "pros": "Smaller JS files download and parse faster, speeding up page interactivity and improving the user experience.",
        "pass_message": "JavaScript files appear to be minified.",
        "fail_messages": {
            "js_unminified": "Some JavaScript files are not minified, increasing page load time."
        },
        "recommendation": "Use a build tool (like Webpack, Rollup) or an online tool to minify your JavaScript files before deploying to production."
    },
    "css_minification": {
        "feature_name": "CSS Minification", "category": "Performance",
        "description": "Minification removes unnecessary characters from CSS files (like whitespace and comments) to reduce their size.",
        "pros": "Smaller CSS files download faster, allowing the browser to render the page more quickly.",
        "pass_message": "CSS files appear to be minified.",
        "fail_messages": {
            "css_unminified": "Some CSS files are not minified, which can delay page rendering."
        },
        "recommendation": "Use a build tool (like PostCSS) or an online tool to minify your CSS files before deploying to production."
    },
    "cdn_usage": {
        "feature_name": "Content Delivery Network (CDN)", "category": "Performance",
        "description": "A CDN is a network of servers distributed globally that deliver content to users based on their geographic location.",
        "pros": "Dramatically improves page load times for users around the world and reduces the load on your origin server.",
        "pass_message": "Static resources appear to be served from a CDN.",
        "fail_messages": {"cdn_missing": "No CDN was detected. Serving resources directly from your server can be slow for international visitors."},
        "recommendation": "Use a CDN (like Cloudflare, Fastly, or AWS CloudFront) to serve your static assets (images, CSS, JS)."
    },
    "image_optimization": {
        "feature_name": "Image Optimization", "category": "Performance",
        "description": "Checks if images are served in modern formats and are appropriately sized.",
        "pros": "Optimized images load faster, consume less data, and contribute to better performance scores.",
        "pass_message": "Images are well-optimized, using modern formats and responsive techniques.",
        "fail_messages": {
            "image_modern_format_missing": "The page does not use modern image formats like WebP or AVIF, which offer better compression.",
            "images_too_heavy": "The total image payload is large, which can significantly slow down page load time.",
            "responsive_images_missing": "Images are not responsive; they lack `srcset` or `<picture>` elements to serve different sizes to different devices."
        },
        "recommendation": "Convert images to modern formats (WebP/AVIF), compress them, and use the `srcset` attribute to serve responsive images."
    },
    "resource_caching": {
        "feature_name": "Resource Caching", "category": "Performance",
        "description": "Checks if the browser is instructed to cache static resources (like CSS, JS, images) to speed up repeat visits.",
        "pros": "Effective caching dramatically speeds up load times for returning visitors by reducing the number of server requests.",
        "pass_message": "Static resources have effective caching policies.",
        "fail_messages": {"cache_missing_resources": "Many resources lack proper caching headers, forcing returning visitors to re-download them."},
        "recommendation": "Configure your server to send 'Cache-Control' or 'Expires' headers for all static assets."
    },

    "image_aspect_ratio": {
    "feature_name": "Image Aspect Ratio", "category": "Performance",
    "description": "Checks if image display dimensions match their natural aspect ratio to avoid distortion.",
    "pros": "Maintaining the correct aspect ratio ensures images are displayed clearly and professionally.",
    "pass_message": "All images appear to have the correct aspect ratio.",
    "fail_messages": {
        "image_ratio_issue": "Some images have distorted aspect ratios, which can harm visual quality and user experience."
    },
    "recommendation": "Ensure the CSS and HTML width/height attributes for your images are proportional to their actual dimensions."
    },
    "render_blocking": {
        "feature_name": "Render-Blocking Resources", "category": "Performance",
        "description": "Identifies scripts and stylesheets that block the browser from rendering the page until they are downloaded and processed.",
        "pros": "Minimizing render-blocking resources is key to achieving a fast First Contentful Paint (FCP).",
        "pass_message": "No significant render-blocking resources were found.",
        "fail_messages": {"render_blocking_resources": "Render-blocking resources were found, delaying how quickly users can see content."},
        "recommendation": "Defer non-critical JavaScript using `defer` or `async` attributes, and inline critical CSS needed for above-the-fold content."
    },
    "text_html_ratio": {
        "feature_name": "Text-to-HTML Ratio", "category": "Performance",
        "description": "This ratio compares the amount of actual text content to the amount of HTML code.",
        "pros": "A higher ratio can indicate a content-rich page with less code bloat, which can be crawled more efficiently.",
        "pass_message": "The page has a healthy text-to-HTML ratio.",
        "fail_messages": {"text_ratio_low": "The Text-to-HTML ratio is low, suggesting the page may have excessive code relative to its content."},
        "recommendation": "Aim for a ratio between 25-70%. Minify HTML, CSS, and JS, and remove unnecessary code or inline styles."
    },

    # --- Branding Category ---
    "favicon": {
        "feature_name": "Favicon", "category": "Branding",
        "description": "A favicon is a small icon that appears in browser tabs, bookmarks, and search results next to your site's name.",
        "pros": "Improves brand recognition and makes your site easily identifiable in a crowded browser tab bar.",
        "pass_message": "A favicon was found for the site.",
        "fail_messages": {"favicon_missing": "A favicon was not found. This is a small but important part of branding and user experience."},
        "recommendation": "Create a favicon and add the link tag for it in the `<head>` section of your site."
    },
    "open_graph": {
        "feature_name": "Open Graph (OG) Tags", "category": "Branding",
        "description": "OG tags are meta tags that control how your content appears when shared on social networks like Facebook, Twitter, and LinkedIn.",
        "pros": "Ensures your shared links look attractive and informative, which can dramatically increase click-through rates from social media.",
        "pass_message": "Open Graph tags are present on the page.",
        "fail_messages": {"open_graph_missing": "Open Graph tags are missing. This means your content may not display well when shared on social media."},
        "recommendation": "Add essential OG tags (`og:title`, `og:description`, `og:image`, `og:url`) to all shareable pages."
    },
     "google_analytics": {
        "feature_name": "Google Analytics", "category": "Branding",
        "description": "Checks for the presence of a Google Analytics tracking script.",
        "pros": "Google Analytics is a powerful tool for understanding your audience and measuring site performance.",
        "pass_message": "Google Analytics tracking code was detected.",
        "fail_messages": {"google_analytics_missing": "Google Analytics tracking code was not detected on the page."},
        "recommendation": "Add a Google Analytics tag to your site to gather valuable visitor data."
    },
    "media_query_test": {
    "feature_name": "Media Query Responsive Test", "category": "Technical",
    "description": "Checks for the presence of CSS media queries, which are essential for creating a responsive design.",
    "pros": "Media queries allow the page layout to adapt to different screen sizes, which is critical for mobile-friendliness.",
    "pass_message": "CSS media queries are being used, indicating a responsive design.",
    "fail_messages": {
        "media_queries_missing": "No CSS media queries were found. The page may not be properly responsive for mobile devices."
    },
    "recommendation": "Implement CSS media queries to ensure your website layout adapts correctly to all screen sizes, including tablets and smartphones."
    },
}

# Define impact levels for each specific check (fail message key)
# This allows for more granular scoring within a single feature.
IMPACT_LEVELS = {
    # Critical
    "title_missing": "Critical", "https_missing": "Critical", "viewport_missing": "Critical",
    "meta_robots_noindex": "Critical", "images_missing_alt_critical": "Critical",
    # High
    "meta_description_missing": "High", "h1_missing": "High", "canonical_missing": "High",
    "ttfb_slow": "High", "html_compression_missing": "High", "render_blocking_resources": "High",
    "certificate_expiring_soon": "High", "fcp_slow": "High", "lcp_slow": "High", "cls_bad": "High",
    "js_console_errors": "High", "keyword_missing_title": "High", "keyword_missing_h1": "High",
    "custom_404_status_issue": "High",
    "mixed_content_found": "High",
    # Medium
    # In analyzer.py, inside the IMPACT_LEVELS dictionary
    "media_queries_missing": "Medium",
    "hsts_missing": "Medium",
    "dom_size_large": "Medium",
    "html_page_size_large": "Medium",   
    "too_many_requests": "Medium",
    "title_too_long": "Medium",
    "js_unminified": "Medium", "css_unminified": "Medium",
    "multiple_h1s": "Medium", "word_count_low": "Medium",
    "images_missing_alt_warning": "Medium", "robots_txt_missing": "Medium", "sitemap_missing": "Medium",
    "cdn_missing": "Medium", "open_graph_missing": "Medium", "keyword_missing_meta": "Medium",
    "keyword_density_off": "Medium", "html_page_size_large": "Medium", "dom_size_large": "Medium",
    "too_many_requests": "Medium", "image_modern_format_missing": "Medium", "cache_missing_resources": "Medium",
    "images_too_heavy": "Medium", "responsive_images_missing": "Medium", "meta_refresh_found": "Medium",
    "custom_404_missing": "Medium",
    # Low
    "header_structure_issue": "Low", "readability_low": "Low", "images_low_quality_alts": "Low",
    "text_ratio_low": "Low", "favicon_missing": "Low", "google_analytics_missing": "Low",
    "deprecated_tags": "Low", "charset_missing": "Low", "spell_check_misspelled": "Low",
    "seo_friendly_url_fail": "Low",
    "snapshot_failed": "Low",
    "image_ratio_issue": "Low",
}

def extract_keywords_tfidf(text: str, num_keywords: int = 12) -> list:
    if not TfidfVectorizer or not text:
        return []
    try:
        stop_words = nltk.corpus.stopwords.words('english')
        words = nltk.word_tokenize(text.lower())
        clean_words = [word for word in words if word.isalpha() and word not in stop_words]
        if len(clean_words) < 2: 
            return []
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=num_keywords)
        vectorizer.fit_transform([" ".join(clean_words)])
        return vectorizer.get_feature_names_out().tolist()
    except Exception:
        return []


def generate_seo_report(seo_data: dict, target_keyword: str = "") -> dict:
    report = {
        "url": seo_data.get("url"),
        "overall_score": 100,
        "analysis_summary": {},
        "category_scores": {},
        "prioritized_suggestions": [],
        "detailed_feature_analysis": {}
    }
    findings = {}
    
    #checking for title 
    title = seo_data.get("title", "")
    if not title or title == "No Title Tag Found":
        findings["title_missing"] = {}
    elif len(title) > 60:
        findings["title_too_long"] = {"value": len(title)}

    #meta description check
    if not seo_data.get("meta_description", "") or seo_data.get("meta_description") == "No Meta Description Found":
        findings["meta_description_missing"] = {}

    #h1 check
    h1_list = seo_data.get("h1", [])
    if len(h1_list) == 0:
        findings["h1_missing"] = {}
    elif len(h1_list) > 1:
        findings["multiple_h1s"] = {}

    #header are properly structured or not 
    headers = seo_data.get("headers", {})
    if headers.get("h3") and not headers.get("h2"):
        findings["header_structure_issue"] = {}

    # Content Quality Checks and having low word count gets you flagged
    word_count = seo_data.get("word_count", 0)
    if 0 < word_count < 300:
        findings["word_count_low"] = {"value": word_count}

    #readibility check using flesh reading score 
    body_text = seo_data.get("body_text", "")
    flesch_score = None
    if body_text:
        try:
            flesch_score = textstat.flesch_reading_ease(body_text)
            if flesch_score < 50:
                findings["readability_low"] = {"value": f"{flesch_score:.2f}"}
        except Exception:
            pass # Ignore if textstat fails
    
    #missing alt text in images check
    image_data = seo_data.get("image_analysis", {})
    total_images, missing_alt = image_data.get("count", 0), image_data.get("missing_alt_count", 0)
    if total_images > 0:
        missing_ratio = missing_alt / total_images
        if missing_ratio > 0.25:
            findings["images_missing_alt_critical"] = {"value": f"{missing_ratio:.0%}"}
        elif missing_ratio > 0.05:
            findings["images_missing_alt_warning"] = {"value": f"{missing_ratio:.0%}"}
            
    #checking for low quality alt text
    low_quality_alts = 0
    generic_alts = ["image", "picture", "graphic", "photo", "alt text", "logo"]
    for text in image_data.get("alt_texts", []):
        if text.lower() in generic_alts or len(text) < 5 or len(text) > 125:
            low_quality_alts += 1
    if low_quality_alts > 0:
        findings["images_low_quality_alts"] = {"value": low_quality_alts}

    # Keyword-specific checks
    if target_keyword:
        tk_lower = target_keyword.lower()
        if tk_lower not in title.lower():
            findings["keyword_missing_title"] = {}
        if tk_lower not in seo_data.get("meta_description", "").lower():
            findings["keyword_missing_meta"] = {}
        if not any(tk_lower in h1.lower() for h1 in h1_list):
            findings["keyword_missing_h1"] = {}
        
        matches = re.findall(r'\b'+ re.escape(tk_lower) + r'\b',body_text.lower())   
        density = (len(matches)/ max(1, word_count) * 100)
        if not (0.5 <= density <= 2.5):
            findings["keyword_density_off"] = {"value": f"{density:.2f}%"}

    if seo_data.get("spell_check", {}).get("misspelled_count", 0) > 0:
        findings["spell_check_misspelled"] = {"value": seo_data["spell_check"]["misspelled_count"]}

    link_data = seo_data.get("link_analysis", {})
    broken_links_count = link_data.get("broken_links", {}).get("count", 0)
    external_links_count = link_data.get("external_links", {}).get("count", 0)
    
    if broken_links_count > 0:
        findings["broken_links_found"] = {"value": f"{broken_links_count} broken link(s)"}

    if external_links_count == 0:
        findings["no_external_links"] = {}

    structured_data = seo_data.get("structured_data", {})
    if not structured_data or structured_data.get("error"):
        findings["structured_data_missing"] = {}
    #checking for https 
    if not seo_data.get("performance", {}).get("is_https"):
        findings["https_missing"] = {}
    #checking for viewport   
    if not seo_data.get("performance", {}).get("has_viewport"):
        findings["viewport_missing"] = {}
    #robots_txt checking
    if not seo_data.get("site_files", {}).get("has_robots_txt"):
        findings["robots_txt_missing"] = {}
    #sitemap checkkkkk
    if not seo_data.get("site_files", {}).get("has_sitemap"):
        findings["sitemap_missing"] = {}
    #canonical check
    if not seo_data.get("canonical"):
        findings["canonical_missing"] = {}
    #meta robot checking 
    if "noindex" in seo_data.get("meta_robots", "").lower():
        findings["meta_robots_noindex"] = {}
    if seo_data.get("deprecated_tags"):
        findings["deprecated_tags"] = {"value": ", ".join(seo_data.get("deprecated_tags"))}
    if not seo_data.get("charset") or seo_data.get("charset") in ("unknown", ""):
        findings["charset_missing"] = {}
        
    canon_check_data = seo_data.get("canonicalization_check")
    if canon_check_data and canon_check_data.get("base_url_final") != canon_check_data.get("alt_url_final"):
        findings["canonicalization_issue"] = {
        "value": f"Base resolves to {canon_check_data.get('base_url_final')}, Alt resolves to {canon_check_data.get('alt_url_final')}"
    }
    #checking for the validation of the ssl certificate
    ssl_info = seo_data.get("ssl", {})
    if ssl_info and isinstance(ssl_info, dict) and ssl_info.get("days_to_expiry") is not None and ssl_info.get("days_to_expiry") <= 30:
        findings["certificate_expiring_soon"] = {"value": ssl_info.get("days_to_expiry")}
    
    #console error check js
    console_errors = seo_data.get("console_errors", [])
    if console_errors and len(console_errors) > 0:
        findings["js_console_errors"] = {"value": len(console_errors)}

    # External Test Findings
    seo_friendly_url_data = seo_data.get("seo_friendly_url")
    if seo_friendly_url_data and seo_friendly_url_data.get("issues"):
        findings["seo_friendly_url_fail"] = {}
    if not seo_data.get("error_page_test", {}).get("custom_404_detected"):
        findings["custom_404_missing"] = {}
    if seo_data.get("error_page_test",{}).get("status_code") not in [404, None]:
        findings["custom_404_status_issue"] = {}
    if seo_data.get("meta_refresh", {}).get("has_meta_refresh"):
        findings["meta_refresh_found"] = {}
    mixed_content_data = seo_data.get("mixed_content_test", {})
    if mixed_content_data.get("has_mixed_content"):
        findings["mixed_content_found"] = {"value": len(mixed_content_data.get("insecure_urls", []))}

    snapshot_data = seo_data.get("mobile_snapshot_test", {})
    if not snapshot_data or not snapshot_data.get("success"):
        findings["snapshot_failed"] = {"value": snapshot_data.get("error", "Unknown error")}

    minification_data = seo_data.get("minification_test", {})
    if minification_data:
        js_results = minification_data.get("js", {})
        if js_results.get("total", 0) > 0 and js_results.get("unminified_list"):
            findings["js_unminified"] = {"value": f"{len(js_results['unminified_list'])} file(s)"}

        css_results = minification_data.get("css", {})
        if css_results.get("total", 0) > 0 and css_results.get("unminified_list"):
            findings["css_unminified"] = {"value": f"{len(css_results['unminified_list'])} file(s)"}
            
    response_headers = {k.lower(): v for k, v in seo_data.get("response_headers", {}).items()}
    if "strict-transport-security" not in response_headers:
        findings["hsts_missing"] = {}
        
    #Performance Findings --->
    ttfb = seo_data.get("performance", {}).get("ttfb")
    if ttfb and ttfb > 0.8:
        findings["ttfb_slow"] = {"value": f"{ttfb:.2f}s"}

    text_ratio = seo_data.get("performance", {}).get("text_to_html_ratio", 0)
    if 0 < text_ratio < 25:
        findings["text_ratio_low"] = {"value": f"{text_ratio:.2f}%"}

    html_kb = seo_data.get("html_size_bytes", 0) / 1024
    if html_kb > 150:
        findings["html_page_size_large"] = {"value": f"{html_kb:.1f} KB"}
    if seo_data.get("dom_nodes", 0) > 1500:
        findings["dom_size_large"] = {"value": seo_data.get("dom_nodes")}

    content_encoding = (seo_data.get("response_headers", {}).get("content-encoding") or "").lower()
    if not ("gzip" in content_encoding or "br" in content_encoding):
        findings["html_compression_missing"] = {}
        
    total_requests = len(seo_data.get("resources", {}).get("items", []))
    if total_requests > 80: # Higher threshold for modern sites
        findings["too_many_requests"] = {"value": total_requests}

    if not seo_data.get("cdn_usage", False):
        findings["cdn_missing"] = {}

    link_data = seo_data.get("link_analysis", {})
    broken_links_count = link_data.get("broken_links", {}).get("count", 0)
    if broken_links_count > 0:
        findings["broken_links_found"] = {"value": f"{broken_links_count} broken link(s)"}
    
  
    if seo_data.get("image_ratio_test", {}).get("issues"):
        findings["image_ratio_issue"] = {"value": f"{len(seo_data['image_ratio_test']['issues'])} image(s) with issues"}

    if not seo_data.get("media_query_responsive_test", {}).get("has_media_queries"):
        findings["media_queries_missing"] = {}
    resources = seo_data.get("resources", {}).get("items", [])
    modern_found = any("webp" in (r.get("content_type") or "") or ".webp" in r.get("url", "") or ".avif" in r.get("url", "") for r in resources)
    if not modern_found and any(r.get("type") == "image" for r in resources):
        findings["image_modern_format_missing"] = {}

    missing_cache_count = sum(1 for r in resources if not r.get("cache_control"))
    if len(resources) > 0 and (missing_cache_count / len(resources)) > 0.4:
        findings["cache_missing_resources"] = {"value": missing_cache_count}

    image_payload_kb = seo_data.get("resources", {}).get("content_size_by_type", {}).get("image", 0) / 1024
    if image_payload_kb > 500:
        findings["images_too_heavy"] = {"value": f"{image_payload_kb:.1f} KB"}
    #render blocking resources check
    rb_count = len(seo_data.get("render_blocking_resources", {}).get("details", []))
    if rb_count > 0:
        findings["render_blocking_resources"] = {"value": rb_count}
    
    #disalliow directive test 
    disallow_data = seo_data.get("disallow_directive", {})
    disallow_rules= disallow_data.get("disallow_rules", [])
    if disallow_rules:
        current_path = urlparse(seo_data.get("url")).path or "/"
        for rule in disallow_rules:
            if rule !="/" and current_path.startswith(rule):
                findings["url_disallow"]={"value":f"Blocked by rule: '{rule}'"}
                break

    cwv = seo_data.get("core_web_vitals", {})
    if cwv:
        if cwv.get("fcp") and cwv.get("fcp") > 1800: findings["fcp_slow"] = {"value": cwv.get("fcp")}
        if cwv.get("lcp") and cwv.get("lcp") > 2500: findings["lcp_slow"] = {"value": cwv.get("lcp")}
        if cwv.get("cls") and cwv.get("cls") > 0.1: findings["cls_bad"] = {"value": cwv.get("cls")}

    if seo_data.get("responsive_image_test", {}).get("issues"):
         findings["responsive_images_missing"] = {"value": len(seo_data["responsive_image_test"]["issues"])}

    #Branding Findings ---
    if not seo_data.get("branding", {}).get("has_favicon"):
        findings["favicon_missing"] = {}
    if not seo_data.get("branding", {}).get("open_graph_tags"):
        findings["open_graph_missing"] = {}
    if not seo_data.get("has_google_analytics"):
        findings["google_analytics_missing"] = {}

    category_scores = {"Content": 100, "Technical": 100, "Performance": 100, "Branding": 100}
    point_deductions = {"Critical": 20, "High": 12, "Medium": 6, "Low": 2}

    for feature_key, info in FEATURE_ANALYSIS_MAP.items():
        pass_flag = True
        analysis_text = info["pass_message"]
        found_issue_key = None

        # Check if any of the failure conditions for this feature were met
        for issue_key in info["fail_messages"]:
            if issue_key in findings:
                pass_flag = False
                found_issue_key = issue_key
                analysis_text = info["fail_messages"][issue_key]
                # Add specific value to the message if available
                val = findings[issue_key].get("value")
                if val:
                    analysis_text = f"{analysis_text} (Detected Value: {val})"
                break # Only report the first issue found for a given feature

        # Build the analysis dictionary for this feature
        if pass_flag:
            report["detailed_feature_analysis"][feature_key] = {
                "feature_name": info["feature_name"], "category": info["category"],
                "status": "pass", "analysis": analysis_text,
                "description": info["description"], "pros": info["pros"]
            }
            if feature_key == "ssl_certificate" and pass_flag:
                ssl_info = seo_data.get("ssl", {})
                if ssl_info:
                    issuer = dict(ssl_info.get("issuer", [])[0]).get("organizationName", "N/A")
                    days_left = ssl_info.get("days_to_expiry", "N/A")
                    analysis_text = f"The SSL certificate is valid, issued by '{issuer}', and has {days_left} days remaining."
                report["detailed_feature_analysis"][feature_key]["analysis"] = analysis_text
        else:
            impact = IMPACT_LEVELS.get(found_issue_key, "Low")
            status = "fail" if impact in ["Critical", "High"] else "warning"

            report["detailed_feature_analysis"][feature_key] = {
                "feature_name": info["feature_name"], "category": info["category"],
                "status": status, "analysis": analysis_text, "issues": analysis_text,
                "description": info["description"], "pros": info["pros"],
                "recommendation": info["recommendation"]
            }
            # Deduct points from the relevant category
            category = info["category"]
            category_scores[category] -= point_deductions.get(impact, 0)

    #CALCULATE FINAL SCORE AND GATHER SUGGESTIONS
    category_weights = {"Content": 0.35, "Technical": 0.30, "Performance": 0.25, "Branding": 0.10}
    final_score = 0
    for cat, weight in category_weights.items():
        category_scores[cat] = max(0, category_scores[cat]) # Ensure score isn't negative
        final_score += category_scores[cat] * weight

    report["overall_score"] = round(final_score)
    report["category_scores"] = category_scores

    # Create prioritized suggestions list from failed/warning checks
    for key, value in report["detailed_feature_analysis"].items():
        if value["status"] in ["fail", "warning"]:
            report["prioritized_suggestions"].append({
                "feature": value["feature_name"],
                "suggestion": value.get("recommendation", "N/A")
            })
    extracted_keywords = extract_keywords_tfidf(body_text)
    keyword_cloud_result = generate_keyword_cloud(extracted_keywords, seo_data.get("url"))
    psi_data = seo_data.get("pagespeed_insights", {})
    
    
    
    resources_data = seo_data.get("resources", {})
    payload_by_type = resources_data.get("content_size_by_type", {})
    # --- Populate Analysis Summary with key metrics ---
    report["analysis_summary"] = {
    "title": title,
    "meta_description": seo_data.get("meta_description"),
    "word_count": word_count,
    "readability_score": flesch_score,
    "https": seo_data.get("performance", {}).get("is_https"),
    "cdn_usage": seo_data.get("cdn_usage", False),
    "compression": bool(content_encoding),
    "ttfb_seconds": ttfb,
    "internal_links": link_data.get("internal_links", {}).get("count", 0),
    "external_links": external_links_count,
    "broken_links": broken_links_count,
    "broken_link_urls": link_data.get("broken_links", {}).get("urls", []),
    "total_requests": total_requests,
    "requests_by_type": resources_data.get("requests_by_type", {}),
    "payload_by_type_kb": {k: round(v / 1024, 2) for k, v in payload_by_type.items()},
    "h1_tags": seo_data.get("h1", []),
    "h2_tags": seo_data.get("headers", {}).get("h2", []),
    "image_payload_kb": image_payload_kb,
    "extracted_keywords": extracted_keywords, # You already have a function for this
    "related_keywords_founds": seo_data.get("related_keywords_test",{}).get("related_keywords_found",[]),
    "keyword_cloud_path": keyword_cloud_result.get("cloud_image_path"),
    "pagespeed_score": psi_data.get("overall_score") if psi_data.get("success") else "N/A",
    "lcp": psi_data.get("lcp") if psi_data.get("success") else "N/A",
    "cls": psi_data.get("cls") if psi_data.get("success") else "N/A",
    "fcp": psi_data.get("fcp") if psi_data.get("success") else "N/A",
    "hsts_enabled": "strict-transport-security" in response_headers,
    # Safer way to access issuer to prevent errors
    "ssl_issuer": dict(seo_data.get("ssl", {}).get("issuer", [[]])[0]).get("organizationName", "N/A") if seo_data.get("ssl") else "N/A"
}

    return report


def export_to_json(report: dict, filename: str):
    """Exports the report dictionary to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"✅ Full JSON report exported to {filename}")


def export_to_markdown(report: dict,raw_data:dict, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# SEO Report for {report['url']}\n\n")
        f.write(f"## 💯 Overall Score: {report['overall_score']}/100\n\n")

        f.write("### 📊 Category Scores\n")
        for cat, score in report['category_scores'].items():
            f.write(f"- **{cat}:** {score}/100\n")
        f.write("\n")

        cloud_path = report.get("analysis_summary", {}).get("keyword_cloud_path")
        if cloud_path:
            f.write(f"### ☁️ Keyword Cloud\n\n")
            f.write(f"![Keyword Cloud for {report['url']}]({cloud_path})\n\n")
            
        snapshot_analysis = report.get("detailed_feature_analysis", {}).get("mobile_snapshot", {})
        
        if snapshot_analysis.get("status") == "pass":
            snapshot_path = raw_data.get("mobile_snapshot_test", {}).get("screenshot_path")
            if snapshot_path:
                f.write(f"### 📱 Mobile Snapshot\n\n")
                f.write(f"![Mobile Snapshot]({snapshot_path})\n\n")
        
        if report.get("prioritized_suggestions"):
            f.write("## 💡 Prioritized Suggestions\n\n")
            for item in report["prioritized_suggestions"]:
                f.write(f"- **{item['feature']}:** {item['suggestion']}\n")
            f.write("\n")

        f.write("## ⚙️ Detailed Feature Analysis\n\n")
        status_emoji = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
        for key, value in report["detailed_feature_analysis"].items():
            f.write(f"### {status_emoji.get(value['status'], '')} {value['feature_name']}\n\n")
            f.write(f"- **Category:** {value['category']}\n")
            f.write(f"- **Status:** {value['status'].title()}\n")
            f.write(f"- **Description:** {value['description']}\n")
            f.write(f"- **Pros:** {value['pros']}\n")
            f.write(f"- **Analysis:** {value['analysis']}\n")
            if value['status'] != 'pass':
                f.write(f"- **Recommendation:** {value['recommendation']}\n")
            f.write("\n---\n\n")
    print(f"✅ Markdown report exported to {filename}")

if __name__ == "__main__":
    target_keyword = ""
    use_playwright=False
    # Parse command line arguments for URL and optional keyword
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a URL.")
        sys.exit(1)

    test_url = sys.argv[1]

    # Check for optional arguments
    if len(sys.argv) > 2:
        # Check if the second argument is the playwright flag or a keyword
        if sys.argv[2] == "--playwright":
            use_playwright = True
        else:
            target_keyword = sys.argv[2]

    if len(sys.argv) > 3 and sys.argv[3] == "--playwright":
        use_playwright = True

    print(f"🚀 Starting SEO analysis for: {test_url}")
    if target_keyword:
        print(f"🎯 Target Keyword: {target_keyword}")
    if use_playwright:
        print("🖥️ Playwright mode enabled.")

    raw_data = extract_seo_data(test_url,target_keywords=[target_keyword] if target_keyword else None,run_playwright=use_playwright) 

    if raw_data:
        print("🧠 Generating comprehensive SEO report...")
        final_report = generate_seo_report(raw_data, target_keyword)

        domain_name = urlparse(test_url).netloc.replace(".", "_")
        json_filename = f"{domain_name}_seo_report.json"
        md_filename = f"{domain_name}_seo_report.md"

        export_to_json(final_report, json_filename)
        export_to_markdown(final_report, raw_data, md_filename)

        # This part prints the summary. It should only run once.
        print("\n--- 📝 Report Summary ---")
        print(f"Overall Score: {final_report['overall_score']}/100")
        print("Category Scores:", final_report['category_scores'])
        print("\nTop Suggestions:")
        pprint.pprint([item['suggestion'] for item in final_report['prioritized_suggestions'][:5]])
        print(f"\n✨ Analysis complete! Full reports saved as {json_filename} and {md_filename}")
    else:
        print("❌ Could not retrieve data to generate a report. Please check the URL and your connection.")