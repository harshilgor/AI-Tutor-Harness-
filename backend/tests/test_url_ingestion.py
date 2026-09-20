import httpx
import pytest
from fastapi import HTTPException

from backend.app.url_ingestion import fetch_public_page, validate_public_url


def public_resolver(host):
    return [host] if host.replace(".", "").isdigit() else ["93.184.216.34"]


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://user:password@example.com",
    "http://example.com:8080/path",
    "http://127.0.0.1/admin",
    "http://169.254.169.254/latest/meta-data",
])
def test_url_validator_rejects_unsafe_targets(url):
    with pytest.raises(HTTPException):
        validate_public_url(url, public_resolver)


def test_fetch_extracts_readable_html_without_active_content():
    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text="""
          <html><head><title>Neural networks</title><script>secret()</script></head>
          <body><main><h1>Neural networks</h1><p>A network learns parameters from examples and uses them to make predictions.</p></main></body></html>
        """)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        page = fetch_public_page("https://example.com/lesson", resolver=public_resolver, client=client)
    assert page["title"] == "Neural networks"
    assert "learns parameters" in page["text"]
    assert "secret" not in page["text"]


def test_redirect_destination_is_revalidated_against_ssrf():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HTTPException) as exc:
            fetch_public_page("https://example.com/start", resolver=public_resolver, client=client)
    assert exc.value.status_code == 403


def test_fetch_rejects_binary_content():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, headers={"content-type": "application/octet-stream"}, content=b"binary"
    ))) as client:
        with pytest.raises(HTTPException) as exc:
            fetch_public_page("https://example.com/file", resolver=public_resolver, client=client)
    assert exc.value.status_code == 415
