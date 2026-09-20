"""Bounded public-web ingestion with SSRF-resistant redirect validation."""
from __future__ import annotations

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from .material_service import problem

MAX_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "text/markdown"}


def _system_resolver(host: str) -> list[str]:
    return list({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


def validate_public_url(value: str, resolver=_system_resolver) -> str:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        problem("invalid_url", "Enter a valid public HTTP or HTTPS URL.")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        problem("invalid_url", "Only public HTTP and HTTPS URLs without embedded credentials are supported.")
    try:
        port = parsed.port
    except ValueError:
        problem("invalid_url", "Enter a valid public HTTP or HTTPS URL.")
    if port not in {None, 80, 443}:
        problem("url_port_forbidden", "Only standard HTTP and HTTPS ports are supported.")
    try:
        addresses = resolver(parsed.hostname)
    except (OSError, socket.gaierror):
        problem("url_resolution_failed", "The page address could not be resolved.")
    if not addresses:
        problem("url_resolution_failed", "The page address could not be resolved.")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address.split("%")[0])
        except ValueError:
            problem("url_resolution_failed", "The page address could not be resolved.")
        if not ip.is_global:
            problem("url_private_address", "Local and private-network pages cannot be imported.", 403)
    return parsed.geturl()


class _ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.title = ""
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}: self.hidden += 1
        if tag == "title": self.in_title = True
        if tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li", "br"}: self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.hidden: self.hidden -= 1
        if tag == "title": self.in_title = False

    def handle_data(self, data):
        if self.hidden: return
        text = " ".join(data.split())
        if not text: return
        if self.in_title: self.title = f"{self.title} {text}".strip()
        self.parts.append(text)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in " ".join(self.parts).splitlines()]
        return "\n\n".join(line for line in lines if line).strip()


def extract_readable(content: bytes, content_type: str) -> tuple[str, str]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        problem("url_encoding_unsupported", "The page is not readable UTF-8 text.")
    if content_type in {"text/plain", "text/markdown"}:
        text = decoded.strip()
        if not text: problem("url_extraction_failed", "The page did not contain readable text.")
        return "Imported page", text
    parser = _ReadableHTML(); parser.feed(decoded)
    text = parser.text()
    if len(text) < 40:
        problem("url_extraction_failed", "The page did not contain enough readable text.")
    return parser.title or "Imported page", text


def fetch_public_page(value: str, *, resolver=_system_resolver, client: httpx.Client | None = None) -> dict:
    current = validate_public_url(value, resolver)
    owned = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=False, trust_env=False,
        headers={"User-Agent": "Forma-Learning-Importer/1.0", "Accept": "text/html,text/plain,text/markdown"})
    try:
        for _ in range(4):
            validate_public_url(current, resolver)
            with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location: problem("url_redirect_invalid", "The page returned an invalid redirect.")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in ALLOWED_CONTENT_TYPES:
                    problem("url_content_type_unsupported", "Only HTML, plain text, and Markdown pages can be imported.", 415)
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES: problem("url_response_too_large", "The page exceeds the 2 MB import limit.", 413)
                title, text = extract_readable(bytes(data), content_type)
                return {"url": current, "title": title[:300], "text": text[:100000], "contentType": content_type}
        problem("url_redirect_limit", "The page redirected too many times.")
    except httpx.TimeoutException:
        problem("url_timeout", "The page took too long to respond.", 504)
    except httpx.HTTPStatusError as exc:
        problem("url_fetch_failed", f"The page returned HTTP {exc.response.status_code}.", 422)
    except httpx.HTTPError:
        problem("url_fetch_failed", "The page could not be downloaded.", 422)
    finally:
        if owned: client.close()
