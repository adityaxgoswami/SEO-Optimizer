# Python SEO Analyzer 🐍📊

A command-line tool to scrape and analyze on-page and technical SEO factors for any given URL. This script provides a detailed report with an overall score, a list of issues, and a breakdown of key SEO metrics.

## ✨ Key Features

This tool analyzes the following SEO elements:

* **Title Tag:** Checks for presence, length (under 60 characters), and provides the text.
* **Meta Description:** Checks for presence and length (under 160 characters).
* **H1 Tag:** Ensures one and only one H1 tag exists.
* **Header Structure:** Verifies a logical heading hierarchy (e.g., no H3s without H2s).
* **Word Count:** Checks for "thin content" by ensuring a word count of at least 300 words.
* **Image SEO:**
    * Calculates the ratio of images missing `alt` attributes.
    * Performs quality checks on existing `alt` text (e.g., not generic, too long, or too short).
* **Link Analysis:**
    * Classifies links as **internal** or **external**.
    * Checks a sample of links for **broken status** (4xx/5xx errors).
* **Canonical Tag:** Verifies the presence of a `rel="canonical"` link.

---

## ⚙️ Installation & Setup

Follow these steps to get the project running on your local machine.

#### **1. Prerequisites**
Ensure you have Python 3.8 or higher installed.

#### **2. Clone the Repository**
```bash
git clone <your-repository-url>
cd <your-repository-directory>
````

#### **3. Create a Virtual Environment**

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### **4. Install Dependencies**

Create a `requirements.txt` file in your project directory with the following content:

**`requirements.txt`**

```
requests
beautifulsoup4
lxml
```

Then, install the packages using pip:

```bash
pip install -r requirements.txt
```

-----

## 🚀 Usage

To make the tool more flexible, pass the URL as a command-line argument.

First, update your `analyzer.py` file to accept arguments. Replace the `if __name__ == "__main__":` block at the bottom with this code:

```python
# In analyzer.py

import sys # Add this import at the top of the file

# ... (rest of your code) ...

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        print("Error: Please provide a URL as an argument.")
        sys.exit(1)
    
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
```

Now, you can run the analyzer from your terminal like this:

```bash
python analyzer.py "[https://www.example.com](https://www.example.com)"
```

-----

## 📄 Output

The tool will generate two report files in the project directory:

1.  **`www_example_com_report.json`**: A JSON file with the full, detailed analysis.
2.  **`www_example_com_report.md`**: A clean, human-readable Markdown report.

#### **Sample Markdown Report:**

````markdown
# SEO Report for [https://www.example.com](https://www.example.com)

## 💯 Overall Score: 85/100

### Issues Found:
- (-5 pts) Warning: Title is too long (over 60 characters).
- (-10 pts) Critical: 2/15 (13%) of images are missing alt attributes.

---

### Detailed Analysis:
- **Title:**
```json
{
  "text": "This is a Very Long Example Title for a Website Page",
  "length": 57
}
````

  - **H1 Tags:**

<!-- end list -->

```json
{
  "count": 1,
  "tags": [
    "Main Heading of the Page"
  ]
}
```

```


## ⚖️ License

This project is licensed under the MIT License. See the `LICENSE` file for details.

```
