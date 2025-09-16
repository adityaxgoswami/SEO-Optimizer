from bs4 import BeautifulSoup
from requests import Session, exceptions
from collections import defaultdict
import pprint

def extract_seo_data(url: str) -> dict | None:
    
    #for bypassing bot check
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }
    
    #sesssion for multiple requests if needed
    with Session() as session:
        session.headers.update(headers)
        
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            seo_data = {
                "url": url,
                "title": "",
                "meta_description": "",
                "h1": "No H1 Tag Found", # setting it as default
                "headers": defaultdict(list)
            }

            if soup.title and soup.title.string:
                seo_data["title"] = soup.title.string.strip()
            else:
                seo_data["title"] = "No Title Tag Found"

            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            if meta_desc_tag:
                seo_data["meta_description"] = meta_desc_tag.get("content", "").strip()
            else:
                seo_data["meta_description"] = "No Meta Description Found"

            h1_tag = soup.find("h1")
            if h1_tag:
                seo_data["h1"] = h1_tag.get_text(strip=True)

            for i in range(2, 7):
                header_tags = soup.find_all(f"h{i}")
                for tag in header_tags:
                    seo_data["headers"][f"h{i}"].append(tag.get_text(strip=True))
                    
            return seo_data
        except:
            pass
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
        
if __name__ == "__main__":
    test_url = "https://www.plex.tv/watch-free/"
    analysis_report = extract_seo_data(test_url)
    
    # if analysis_report:
    #     pprint.pprint(analysis_report)
        
    # title = analysis_report.get("title", "")
    # print(title)
    # title_text = title
    # print( title_text)
    # title_len = len(title_text)
    # print(title_len)
    
      
    # 2. Meta Description Analysis
    meta = analysis_report.get("meta_description", "")
    print(meta)
    meta_text = meta
    print(meta_text)
    meta_len = len(meta_text)
    print(meta_len)