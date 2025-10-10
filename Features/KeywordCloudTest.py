# Features/KeywordCloudTest.py
import os
from urllib.parse import urlparse

try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None

def generate_keyword_cloud(keywords: list, url: str) -> dict:
    if not WordCloud:
        return {
            "success": False,
            "error": "WordCloud library not found. Please run 'pip install wordcloud matplotlib'."
        }
    
    if not keywords:
        return {
            "success": False,
            "error": "No keywords provided to generate a cloud."
        }

    # Generate a safe filename from the URL
    domain = urlparse(url).netloc.replace(".", "_")
    filename = f"{domain}_keyword_cloud.png"
    
    # Create a directory for reports if it doesn't exist
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    try:
        # Join the list of keywords into a single string
        text = " ".join(keywords)
        
        # Generate the word cloud object
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color="white", 
            colormap="viridis", 
            collocations=False
        ).generate(text)

        # Save the image file
        wordcloud.to_file(filepath)
        
        return {
            "success": True,
            "cloud_image_path": filepath
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate word cloud: {str(e)}"
        }
        
# print(generate_keyword_cloud(["example", "test", "font", "literature", "graphic"], "https://www.dafont.com/"))