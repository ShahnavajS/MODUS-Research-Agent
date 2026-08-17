from app.core.security import is_safe_external_url


def test_ssrf_blocking_localhost_and_internal_ips():
    """Verify SSRF protection blocks localhost, internal IPs, and non-HTTP schemes."""
    # Unsafe URLs
    unsafe_urls = [
        "http://localhost:8000/api/v1/health",
        "http://127.0.0.1/admin",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/secret",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]

    for url in unsafe_urls:
        is_safe, reason = is_safe_external_url(url)
        assert not is_safe, f"Expected URL '{url}' to be blocked, but passed: {reason}"


def test_safe_external_urls():
    """Verify safe external HTTP/HTTPS domain URLs pass security checks."""
    safe_urls = [
        "https://www.google.com/search",
        "http://example.com/article/123",
        "https://research.mit.edu/paper.pdf",
        "https://www.reuters.com/business",
    ]

    for url in safe_urls:
        is_safe, reason = is_safe_external_url(url)
        assert is_safe, f"Expected URL '{url}' to be allowed, but blocked: {reason}"
