import os
from urllib.parse import urlparse

# Conditional import for wordcloud
try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None

def generate_keyword_cloud(keywords: list, url: str) -> dict:
    """
    Generates a word cloud image from a list of keywords.

    Args:
        keywords (list): A list of keyword strings.
        url (str): The URL the keywords are from, used for naming the output file.

    Returns:
        dict: A dictionary indicating success or failure and providing the image path or an error message.
    """
    if not WordCloud:
        return {
            "success": False,
            "error": "WordCloud library not found. Please run 'pip install wordcloud matplotlib'."
        }
    
    if not keywords:
        return {
            "success": False,
            "error": "No keywords were provided to generate the cloud."
        }

    # Generate a safe filename from the URL's domain
    domain = urlparse(url).netloc.replace(".", "_")
    filename = f"{domain}_keyword_cloud.png"
    
    # Create a directory for reports if it doesn't exist
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    try:
        # Join the list of keywords into a single space-separated string
        text = " ".join(keywords)
        
        # Configure and generate the word cloud object
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color="white", 
            colormap="viridis", 
            collocations=False # Avoids grouping common word pairs
        ).generate(text)

        # Save the generated image to a file
        wordcloud.to_file(filepath)
        
        return {
            "success": True,
            "cloud_image_path": filepath
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate word cloud image: {str(e)}"
        }

# Standalone execution block for testing
if __name__ == '__main__':
    test_keywords = ["SEO", "python", "analysis", "web", "scraper", "report", "keywords", "cloud", "developer", "google", "search", "engine", "optimization", "python", "SEO", "analysis"]
    test_url = "https://example.com"
    print(f"Generating keyword cloud for '{test_url}'...")
    result = generate_keyword_cloud(test_keywords, test_url)
    
    if result["success"]:
        print(f"✅ Successfully generated keyword cloud: {result['cloud_image_path']}")
    else:
        print(f"❌ Error: {result['error']}")
