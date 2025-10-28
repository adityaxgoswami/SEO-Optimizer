import os
import logging
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from fastapi.concurrency import run_in_threadpool
import asyncio
import sys
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
from scraper import extract_seo_data
from analyzer import generate_seo_report
import asyncio
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Feature imports
from Features.seo_friendly import seo_friendly_url_test
from Features.DirectiveTest import disallow_directive_test
from Features.MetaRefreshTest import meta_refresh_test
from Features.ErrorPageTest import error_page_test
from Features.SpellCheckTest import spell_check_test
from Features.ResponsiveImageTest import responsive_image_test
from Features.ImageRatioTest import image_ratio_test
from Features.MediaQueryResponsiveTest import media_query_responsive_test
from Features.KeywordCloudTest import generate_keyword_cloud
from Features.MinificationTest import minification_test
from Features.MixedContentTest import mixed_content_test
from Features.MobileSnapTest import mobile_snapshot_test_sync
from Features.PageSpeedInsightsTest import pagespeed_insights_test
from Features.RelatedKeywordsTest import related_keywords_test
import uvicorn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(title="SEO Scraper/Analyzer API")

# Generic request models
class URLRequest(BaseModel):
    url: HttpUrl
    run_playwright: bool = False
    target_keyword: str | None = None
    validate_real_size: bool = False
    api_key: str | None = None

class TextRequest(BaseModel):
    text: str
    num_keywords: int | None = 12

class KeywordRequest(BaseModel):
    keyword: str
    limit: int | None = 10

@app.post("/analyze")
async def analyze(req: URLRequest):
    try:
        logging.info(f"Analysis started for: {req.url}")

        final_report = await run_in_threadpool(
            run_full_analysis,
            url=str(req.url),
            target_keyword=req.target_keyword,
            use_playwright=req.run_playwright
        )

        if not final_report:
            raise HTTPException(status_code=500, detail="Analysis failed. Scraper could not retrieve data.")

        logging.info(f"✨ Analysis complete for {req.url}!")
        return final_report

    except Exception as e:
        logging.exception("An internal error occurred during analysis.")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

def run_full_analysis(url: str, target_keyword: str | None, use_playwright: bool) -> dict:
    # Set the event loop policy *in this thread* before creating a new loop
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            # Policy might already be set or another issue, but try to continue
            pass
            
    raw_data = asyncio.run(
        extract_seo_data(
            url,
            target_keywords=[target_keyword] if target_keyword else None,
            run_playwright=use_playwright
        )
    )
    if not raw_data:
        return None

    final_report = generate_seo_report(raw_data, target_keyword or "")
    return final_report

@app.post("/check/seo_friendly")
async def check_seo_friendly(req: URLRequest):
    return await run_in_threadpool(seo_friendly_url_test, str(req.url), [req.target_keyword] if req.target_keyword else [])


@app.post("/check/robots_disallow")
async def check_robots(req: URLRequest):
    return await run_in_threadpool(disallow_directive_test, str(req.url))

@app.post("/check/meta_refresh")
async def check_meta_refresh(req: URLRequest):
    return await run_in_threadpool(meta_refresh_test, str(req.url))

@app.post("/check/error_page")
async def check_error_page(req: URLRequest):
    return await run_in_threadpool(error_page_test, str(req.url))

@app.post("/check/spell_check")
async def check_spell(req: TextRequest):
    return await run_in_threadpool(spell_check_test, req.text)

@app.post("/check/responsive_images")
async def check_responsive_images(req: URLRequest):
    return await run_in_threadpool(responsive_image_test, str(req.url))

@app.post("/check/image_ratio")
async def check_image_ratio(req: URLRequest):
    return await run_in_threadpool(image_ratio_test, str(req.url), req.validate_real_size)

@app.post("/check/media_queries")
async def check_media_queries(req: URLRequest):
    return await run_in_threadpool(media_query_responsive_test, str(req.url))

@app.post("/check/keyword_cloud")
async def check_keyword_cloud(req: TextRequest):
    return await run_in_threadpool(generate_keyword_cloud, req.text, req.num_keywords or 12)

@app.post("/check/minification")
async def check_minification(req: URLRequest):
    return await run_in_threadpool(minification_test, str(req.url))

@app.post("/check/mixed_content")
async def check_mixed_content(req: URLRequest):
    return await run_in_threadpool(mixed_content_test, str(req.url))

@app.post("/check/mobile_snap")
async def check_mobile_snap(req: URLRequest):
    return await run_in_threadpool(mobile_snapshot_test, str(req.url))

@app.post("/check/pagespeed")
async def check_pagespeed(req: URLRequest):
    return await run_in_threadpool(pagespeed_insights_test, str(req.url), req.api_key)

@app.post("/check/related_keywords")
async def check_related_keywords(req: KeywordRequest):
    return await run_in_threadpool(related_keywords_test, req.keyword, req.limit or 10)

@app.get("/")
def root():
    return {"message": "SEO Scraper / Analyzer API. Use POST /analyze or POST /check/<tool> to run individual tools."}

#directly running the main.py file 
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
