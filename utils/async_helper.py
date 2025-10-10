import asyncio
import httpx

async def check_urls_async(urls_to_check: list, timeout: int = 8):
    results = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tasks = [client.head(url) for url in urls_to_check]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for url, response in zip(urls_to_check, responses):
            if isinstance(response, httpx.Response):
                results.append((url, response.status_code))
            else:
                results.append((url, None))
                
    return results

async def get_url_headers_async(urls_to_check: list, timeout: int = 8):
    """
    Performs an async HEAD request on each URL and returns detailed header info.
    """
    results = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        
        async def fetch_headers(url):
            try:
                response = await client.head(url)
                # Return a dictionary with the data we need
                return {
                    "url": url,
                    "status": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": int(response.headers.get("Content-Length", 0)),
                    "cache_control": response.headers.get("Cache-Control"),
                    "content_encoding": response.headers.get("Content-Encoding"),
                    "error": None
                }
            except Exception as e:
                # Return an error state if the request fails
                return {"url": url, "status": None, "error": str(e)}

        tasks = [fetch_headers(url) for url in urls_to_check]
        results = await asyncio.gather(*tasks)
        
    return results