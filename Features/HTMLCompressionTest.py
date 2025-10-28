def html_compression_test(headers: dict, original_size_bytes: int) -> dict:
    """
    Checks if the HTML response is compressed (Gzip or Brotli).

    Args:
        headers: A dictionary of response headers.
        original_size_bytes: The size of the HTML in bytes.

    Returns:
        A dictionary with the test status and analysis.
    """
    content_encoding = headers.get("content-encoding", "").lower()

    if "gzip" in content_encoding or "br" in content_encoding:
        # Note: Calculating exact savings without the compressed size is complex.
        # We'll just confirm that compression is active. A more advanced
        # version could compare compressed vs uncompressed sizes.
        return {
            "status": "pass",
            "analysis": f"The HTML is compressed using '{content_encoding}'.",
            "savings_percent": "N/A" 
        }
    else:
        return {
            "status": "fail",
            "analysis": "The HTML response is not compressed. Enabling GZIP or Brotli can significantly reduce page size and improve load times."
        }
