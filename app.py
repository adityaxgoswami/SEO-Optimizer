# app.py (Streamlit frontend - upgraded)
import streamlit as st
import time
import json
from collections import defaultdict
from urllib.parse import urlparse

from scraper import extract_seo_data
from analyzer import generate_seo_report, SUGGESTIONS_KNOWLEDGE_BASE

st.set_page_config(
    page_title="Python SEO Analyzer",
    page_icon="🐍",
    layout="wide"
)

st.title("🐍 Python SEO Analyzer")
st.caption("A comprehensive on-page SEO analysis tool built with Python.")

col1, col2 = st.columns([3, 1])
with col1:
    url_to_analyze = st.text_input("Enter the URL to analyze", placeholder="https://example.com")
    target_keyword = st.text_input("Enter a target keyword (optional)", placeholder="your keyword")
with col2:
    st.write("Advanced options")
    run_deep = st.checkbox("Run advanced browser checks (Playwright)", value=False, help="Runs optional Playwright-based metrics (FCP/LCP/CLS, console errors). Requires Playwright to be installed.")
    export_json = st.checkbox("Show raw JSON download", value=True)

if 'report' not in st.session_state:
    st.session_state.report = None

if st.button("Analyze Website", type="primary"):
    if not url_to_analyze:
        st.warning("Please enter a URL to analyze.")
    else:
        with st.spinner("Running SEO analysis... This may take a moment."):
            # pass run_deep into scraper
            raw_data = extract_seo_data(url_to_analyze, run_playwright=run_deep)
            if raw_data:
                st.session_state.report = generate_seo_report(raw_data, target_keyword)
            else:
                st.session_state.report = None
                st.error("Could not fetch data from the URL. Please check the URL and try again.")

if st.session_state.report:
    report = st.session_state.report

    st.divider()
    st.header("📊 SEO Report Summary")

    score = report.get("overall_score", 0)
    checklist = report.get("suggestions", [])
    passed_count = max(0, 100 - len(checklist))  # heuristic display
    failed_count = len(checklist)

    summary_cols = st.columns(4)
    summary_cols[0].metric(label="Overall Score", value=f"{score}/100")
    summary_cols[1].metric(label="Checks Failed", value=failed_count)
    summary_cols[2].metric(label="Checks Passed (heuristic)", value=passed_count)
    summary_cols[3].metric(label="Warnings", value="0")

    st.subheader("SEO Checklist Results (Prioritized Suggestions)")
    if report["suggestions"]:
        for item in report["suggestions"]:
            st.markdown(f"**Impact: {item['impact']} | Effort: {item['effort']} | Priority: {item['priority_score']}**")
            st.write(item['suggestion'])
            st.markdown("---")
    else:
        st.success("No suggestions — great job!")

    st.subheader("Detailed Analysis Snapshot")
    analysis = report.get("analysis", {})

    # Basic fields
    left, right = st.columns(2)
    with left:
        st.markdown("**Title**")
        st.write(analysis.get("title", {}))
        st.markdown("**Meta Description**")
        st.write(analysis.get("meta_description", {}))
        st.markdown("**H1 Tags**")
        st.write(analysis.get("h1_tags", {}))
    with right:
        st.markdown("**Performance**")
        st.write(analysis.get("performance", {}))
        st.markdown("**Readability**")
        st.write(analysis.get("readability", {}))
        st.markdown("**Word Count**")
        st.write(analysis.get("word_count", {}))

    # Resources summary and table
    st.subheader("Resources & Asset Summary")
    resources_summary = analysis.get("resources_summary", {})
    st.write("Requests by type:", resources_summary.get("requests_by_type"))
    st.write("Content size by type (bytes):", resources_summary.get("content_size_by_type"))
    st.write("Total requests:", resources_summary.get("total_requests"))


    # Visualize content size by type (if available)
    if resources_summary.get("content_size_by_type"):
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.DataFrame(
            list(resources_summary["content_size_by_type"].items()),
            columns=["Resource Type", "Size (bytes)"]
        )
        df["Size (KB)"] = df["Size (bytes)"] / 1024

        st.markdown("**Content Size Breakdown**")
        fig, ax = plt.subplots()
        ax.bar(df["Resource Type"], df["Size (KB)"])
        ax.set_ylabel("Size (KB)")
        ax.set_xlabel("Resource Type")
        ax.set_title("Content Size Breakdown by Resource Type")
        st.pyplot(fig)

    # Show resource table (if present)
    from_aggr = report.get("analysis", {}).get("raw_seo_data_snapshot", {})
    st.write("HTML size (KB):", from_aggr.get("html_size_kb"))
    resources = report.get("analysis", {}).get("raw_seo_data_snapshot", {})
    # We kept the full resources under the raw seo_data snapshot in analyzer; show full raw if present
    if "raw_seo_data_snapshot" in analysis:
        st.markdown("**Raw SEO Data Snapshot**")
        st.json(analysis["raw_seo_data_snapshot"])

    # Core Web Vitals (if available)
    st.subheader("Core Web Vitals & Console Errors (browser-run only)")
    cwv = analysis.get("core_web_vitals")
    if cwv:
        st.write("FCP (ms):", cwv.get("fcp"))
        st.write("LCP (ms):", cwv.get("lcp"))
        st.write("CLS:", cwv.get("cls"))
    else:
        st.info("Core Web Vitals not available. Enable 'Run advanced browser checks' and install Playwright for FCP/LCP/CLS.")

    console_errors = analysis.get("console_errors")
    if console_errors:
        st.warning(f"Console errors detected: {len(console_errors)}")
        for e in console_errors[:10]:
            st.write(e)
    else:
        st.write("No console errors captured (or not run).")

    # SSL info
    st.subheader("SSL / Certificate Info")
    ssl_info = analysis.get("ssl")
    if ssl_info:
        st.write(ssl_info)
    else:
        st.info("SSL info not available.")

    # Download JSON
    if export_json:
        st.download_button("Download full report JSON", data=json.dumps(report, indent=2), file_name="seo_report.json", mime="application/json")

    st.divider()
    with st.expander("Show Full Raw Data JSON"):
        st.json(report)
