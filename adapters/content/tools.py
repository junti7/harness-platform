import os
import json
import re
import socket
import hmac
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, unquote, urlencode, urlparse
import ipaddress
import httpx
import logging
from typing import Any

from core.logger import HarnessLogger
from adapters.content.substack_publisher import fetch_draft_as_text

logger = logging.getLogger(__name__)

# 경로 및 상수 재정의 (순환 참조 방지)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = PROJECT_ROOT / ".venv/bin/python"

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

CHANNEL_MAP = {
    "exec-president-decisions": os.environ.get("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "C0B2TQV3RDG"),
    "president": os.environ.get("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "C0B2TQV3RDG"),
    "vp-content-review": os.environ.get("SLACK_CHANNEL_VP_CONTENT_REVIEW", "C0B2TQVV602"),
    "vp": os.environ.get("SLACK_CHANNEL_VP_CONTENT_REVIEW", "C0B2TQVV602"),
    "ops-incidents": os.environ.get("SLACK_CHANNEL_OPS_INCIDENTS", "C0B2MDYDE83"),
    "ops": os.environ.get("SLACK_CHANNEL_OPS_INCIDENTS", "C0B2MDYDE83"),
}

_ALLOWED_READ_ROOTS = [
    PROJECT_ROOT,
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "adapters",
    PROJECT_ROOT / "agents",
    PROJECT_ROOT / "configs",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "tests",
]

_ALLOWED_WRITE_ROOTS = [
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "adapters",
    PROJECT_ROOT / "agents",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "reports",
    PROJECT_ROOT / "runtime",
]


def _check_ssrf_url(url: str) -> None:
    """Raise ValueError if URL resolves to a private/reserved IP (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"허용되지 않는 URL 스킴: {parsed.scheme!r}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL에 hostname이 없습니다.")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"hostname 해석 실패: {hostname} — {exc}") from exc
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"SSRF 차단: {hostname} → {ip_str} (사설/예약 IP)")


def _resolve_path(path: str, write: bool = False) -> Path:
    p = Path(path)
    resolved = (p if p.is_absolute() else PROJECT_ROOT / p).resolve()
    roots = _ALLOWED_WRITE_ROOTS if write else _ALLOWED_READ_ROOTS
    if not any(resolved.is_relative_to(r.resolve()) for r in roots):
        raise PermissionError(f"경로 접근 거부: {resolved}")
    return resolved


def tool_read_file(path: str) -> str:
    try:
        fp = _resolve_path(path)
        if not fp.exists():
            return f"❌ 파일 없음: {fp}"
        
        # 이미지 및 바이너리 파일 차단 가드 (Fail-Fast)
        binary_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz",
            ".xlsx", ".xls", ".db", ".exe", ".dll", ".so", ".dylib", ".png"
        }
        if fp.suffix.lower() in binary_extensions:
            return f"❌ 읽기 실패: {fp.name}은(는) 텍스트 파일이 아닙니다. 바이너리/이미지 파일은 텍스트 뷰어로 읽을 수 없습니다."

        content = fp.read_text(encoding="utf-8")
        if fp.name == ".env":
            lines = []
            for line in content.splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    masked = val[:4] + "***" if len(val) > 4 else "***"
                    lines.append(f"{key}={masked}")
                else:
                    lines.append(line)
            content = "\n".join(lines)
        return content
    except Exception as e:
        return f"❌ 읽기 실패: {e}"


def tool_write_file(path: str, content: str, mode: str = "overwrite") -> str:
    try:
        fp = _resolve_path(path, write=True)
        fp.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with fp.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            fp.write_text(content, encoding="utf-8")
        return f"✅ 저장 완료: {fp} ({fp.stat().st_size} bytes)"
    except Exception as e:
        return f"❌ 쓰기 실패: {e}"


def tool_list_files(path: str) -> str:
    try:
        dp = _resolve_path(path)
        if not dp.exists():
            return f"❌ 디렉토리 없음: {dp}"
        items = sorted(dp.iterdir())
        lines = []
        for item in items:
            prefix = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{item.name}")
        return "\n".join(lines) or "(비어있음)"
    except Exception as e:
        return f"❌ 목록 조회 실패: {e}"


def tool_run_script(script: str, args: list | None = None) -> str:
    try:
        script_path = _resolve_path(script)
        cmd = [str(VENV_PYTHON), str(script_path)] + (args or [])
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT)
        )
        output = (result.stdout or "") + (result.stderr or "")
        status = "✅" if result.returncode == 0 else "❌"
        return f"{status} 종료코드: {result.returncode}\n{output[:1200]}"
    except subprocess.TimeoutExpired:
        return "❌ 시간 초과 (60초)"
    except Exception as e:
        return f"❌ 실행 오류: {e}"


def tool_send_slack(channel: str, message: str) -> str:
    channel_id = CHANNEL_MAP.get(channel.lower().lstrip("#"), channel)
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": channel_id, "text": message},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return f"✅ 전송 완료 → {channel} ({channel_id})"
        return f"❌ 전송 실패: {data.get('error')}"
    except Exception as e:
        return f"❌ Slack 전송 오류: {e}"


def tool_fetch_url(url: str) -> str:
    try:
        _check_ssrf_url(url)
        publication_url = os.environ.get("SUBSTACK_PUBLICATION_URL", "").rstrip("/")
        substack_session_token = os.environ.get("SUBSTACK_SESSION_TOKEN", "")
        is_substack_private = (
            publication_url
            and url.startswith(publication_url)
            and ("/publish/" in url or "/publish/post/" in url)
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        if is_substack_private:
            match = re.search(r"/publish/post/(\d+)", url)
            if match:
                draft = fetch_draft_as_text(match.group(1), logger=HarnessLogger(tier=4))
                title = draft.get("title") or "Untitled draft"
                subtitle = draft.get("subtitle") or ""
                body_text = (draft.get("body_text") or "").strip()
                parts = [f"✅ Substack draft fetch 완료: {url}", f"\nTITLE: {title}"]
                if subtitle:
                    parts.append(f"\nSUBTITLE: {subtitle}")
                if body_text:
                    parts.append(f"\n\n{body_text[:12000]}")
                else:
                    parts.append("\n\n(본문이 비어 있거나 추출되지 않았습니다.)")
                return "".join(parts)
        if publication_url and url.startswith(publication_url) and substack_session_token:
            headers["Cookie"] = f"substack.sid={substack_session_token}"
            headers["Referer"] = f"{publication_url}/publish/posts"
            headers["Origin"] = publication_url

        resp = httpx.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if "html" in content_type.lower():
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
                body_text = "\n".join(
                    line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
                )
                if title:
                    body_text = f"TITLE: {title}\n\n{body_text}"
                text = body_text
            except Exception:
                stripped = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
                stripped = re.sub(r"(?s)<[^>]+>", "\n", stripped)
                stripped = unescape(stripped)
                text = "\n".join(line.strip() for line in stripped.splitlines() if line.strip())

        text = text[:12000]
        return f"✅ URL fetch 완료: {url}\n\n{text}"
    except Exception as e:
        if is_substack_private and (
            "redirect" in str(e).lower() or "too many redirects" in str(e).lower()
        ):
            if not substack_session_token:
                return (
                    "❌ Substack draft 접근 실패: 이 URL은 로그인 세션이 필요한 private draft/publish 페이지입니다.\n"
                    "현재 `SUBSTACK_SESSION_TOKEN` 이 설정되어 있지 않아 내용을 가져올 수 없습니다.\n"
                    "권한이 생기면 같은 URL을 다시 읽을 수 있습니다."
                )
            return (
                "❌ Substack draft 접근 실패: 저장된 `SUBSTACK_SESSION_TOKEN` 이 만료되었거나 draft 접근 권한이 부족합니다.\n"
                "Substack 세션을 갱신한 뒤 다시 시도해야 합니다."
            )
        return f"❌ URL fetch 오류: {e}"


def _search_result_lines(provider: str, query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return f"검색 결과가 없습니다. provider={provider}, query={query!r}"
    lines = [f"✅ 웹 검색 완료: {query}", f"provider: {provider}", ""]
    for idx, item in enumerate(results, 1):
        title = item.get("title") or "(제목 없음)"
        url = item.get("url") or ""
        snippet = item.get("snippet") or ""
        published = item.get("published") or item.get("date") or item.get("age") or "미확인"
        lines.append(f"{idx}. {title}")
        if url:
            lines.append(f"   URL: {url}")
        lines.append(f"   게시일: {published}")
        if snippet:
            lines.append(f"   요약: {snippet[:500]}")
    return "\n".join(lines)


def _normalize_duckduckgo_url(href: str) -> str:
    if not href:
        return ""
    parsed = urlparse(href)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target) if target else href
    return href


def _web_search_brave_results(query: str, count: int) -> list[dict[str, str]]:
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY is not configured")
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": count, "text_decorations": "false"},
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
        timeout=12.0,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in (data.get("web") or {}).get("results", [])[:count]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
            "published": item.get("page_age") or item.get("age") or "",
        })
    return results


def _web_search_brave(query: str, count: int) -> str:
    return _search_result_lines("brave", query, _web_search_brave_results(query, count))


def _web_search_duckduckgo_results(query: str, count: int) -> list[dict[str, str]]:
    headers = {"User-Agent": "Mozilla/5.0"}

    def _parse_html_results(html: str) -> list[dict[str, str]]:
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html, "html.parser")
            parsed = []
            for node in soup.select(".result")[:count]:
                link = node.select_one(".result__a")
                if not link:
                    continue
                snippet_node = node.select_one(".result__snippet")
                parsed.append({
                    "title": link.get_text(" ", strip=True),
                    "url": _normalize_duckduckgo_url(link.get("href", "")),
                    "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
                })
            return parsed
        except Exception:
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
            parsed = []
            for href, title_html in links[:count]:
                title = unescape(re.sub(r"<[^>]+>", " ", title_html))
                parsed.append({"title": " ".join(title.split()), "url": _normalize_duckduckgo_url(unescape(href)), "snippet": ""})
            return parsed

    def _parse_lite_results(html: str) -> list[dict[str, str]]:
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html, "html.parser")
            parsed = []
            for link in soup.select(".result-link")[:count]:
                parsed.append({
                    "title": link.get_text(" ", strip=True),
                    "url": _normalize_duckduckgo_url(link.get("href", "")),
                    "snippet": "",
                })
            return parsed
        except Exception:
            return []

    resp = httpx.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=headers,
        timeout=15.0,
        follow_redirects=True,
    )
    resp.raise_for_status()
    results = _parse_html_results(resp.text)
    if not results:
        lite_resp = httpx.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers=headers,
            timeout=15.0,
            follow_redirects=True,
        )
        lite_resp.raise_for_status()
        results = _parse_lite_results(lite_resp.text)
    return results


def _web_search_duckduckgo(query: str, count: int) -> str:
    return _search_result_lines(
        "duckduckgo_html",
        query,
        _web_search_duckduckgo_results(query, count),
    )


def structured_web_search(query: str, count: int = 5) -> dict[str, Any]:
    """Return source URLs as structured data for read-only research workers."""
    count = max(1, min(int(count or 5), 10))
    provider = os.environ.get("OPENCLAW_WEB_SEARCH_PROVIDER", "auto").strip().lower()
    try:
        if provider == "brave":
            results = _web_search_brave_results(query, count)
            used_provider = "brave"
        elif provider in {"duckduckgo", "ddg"}:
            results = _web_search_duckduckgo_results(query, count)
            used_provider = "duckduckgo_html"
        elif os.environ.get("BRAVE_SEARCH_API_KEY", "").strip():
            results = _web_search_brave_results(query, count)
            used_provider = "brave"
        else:
            results = _web_search_duckduckgo_results(query, count)
            used_provider = "duckduckgo_html"
        return {
            "ok": bool(results),
            "query": query,
            "provider": used_provider,
            "results": results,
            **({} if results else {"error": "no search results returned"}),
        }
    except Exception as exc:
        return {
            "ok": False,
            "query": query,
            "provider": provider,
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def tool_web_search(query: str, count: int = 5) -> str:
    count = max(1, min(int(count or 5), 10))
    provider = os.environ.get("OPENCLAW_WEB_SEARCH_PROVIDER", "auto").strip().lower()
    try:
        if provider == "brave":
            return _web_search_brave(query, count)
        if provider in {"duckduckgo", "ddg"}:
            return _web_search_duckduckgo(query, count)
        if os.environ.get("BRAVE_SEARCH_API_KEY", "").strip():
            return _web_search_brave(query, count)
        return _web_search_duckduckgo(query, count)
    except Exception as exc:
        if provider == "auto" and os.environ.get("BRAVE_SEARCH_API_KEY", "").strip():
            try:
                return _web_search_duckduckgo(query, count)
            except Exception as fallback_exc:
                return f"❌ 웹 검색 실패: brave={type(exc).__name__}: {exc}; duckduckgo={type(fallback_exc).__name__}: {fallback_exc}"
        return f"❌ 웹 검색 실패: {type(exc).__name__}: {exc}"


def _browser_research_safety_error(*values: str | None) -> str | None:
    text = " ".join(value or "" for value in values).lower()
    blocked_terms = [
        "구매", "결제", "주문", "장바구니", "바로구매", "checkout", "payment", "purchase",
        "buy now", "order", "cart", "login", "로그인", "sign in", "회원가입", "주소", "배송지",
    ]
    matched = [term for term in blocked_terms if term in text]
    if not matched:
        return None
    return (
        "❌ browser_research 차단: 공개 페이지 read-only 탐색만 허용합니다.\n"
        f"차단 키워드: {', '.join(matched)}\n"
        "구매/결제/주문/장바구니/로그인/개인정보 입력은 실행하지 않습니다."
    )


def tool_browser_research(
    task: str,
    url: str = "",
    query: str = "",
    site: str = "",
    max_items: int = 5,
) -> str:
    safety_error = _browser_research_safety_error(task, url, query, site)
    if safety_error:
        return safety_error
    try:
        max_items = max(1, min(int(max_items or 5), 10))
        cmd = [
            str(VENV_PYTHON),
            str(PROJECT_ROOT / "scripts/browser_research.py"),
            "--task",
            task,
            "--max-items",
            str(max_items),
        ]
        if url:
            cmd.extend(["--url", url])
        if query:
            cmd.extend(["--query", query])
        if site:
            cmd.extend(["--site", site])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(PROJECT_ROOT),
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode == 0:
            return output[:12000]
        return f"❌ browser_research 실패 (code={result.returncode})\n{output[:3000]}"
    except subprocess.TimeoutExpired:
        return "❌ browser_research 시간 초과 (90초)"
    except Exception as exc:
        return f"❌ browser_research 오류: {type(exc).__name__}: {exc}"


def _coupang_product_search_safety_error(keyword: str) -> str | None:
    blocked_terms = [
        "구매", "결제", "주문", "장바구니", "바로구매", "checkout", "payment", "purchase",
        "buy now", "order", "cart", "login", "로그인", "sign in", "회원가입", "주소", "배송지",
    ]
    matched = [term for term in blocked_terms if term in (keyword or "").lower()]
    if not matched:
        return None
    return (
        "❌ coupang_product_search 차단: 상품 검색만 허용합니다.\n"
        f"차단 키워드: {', '.join(matched)}\n"
        "구매/결제/주문/장바구니/로그인/개인정보 입력은 실행하지 않습니다."
    )


def _coupang_hmac_headers(method: str, path_with_query: str) -> dict[str, str]:
    access_key = os.environ.get("COUPANG_PARTNERS_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("COUPANG_PARTNERS_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError(
            "COUPANG_PARTNERS_ACCESS_KEY / COUPANG_PARTNERS_SECRET_KEY 가 설정되지 않았습니다."
        )
    datetime_utc = datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
    parts = path_with_query.split("?", 1)
    path = parts[0]
    query = parts[1] if len(parts) == 2 else ""
    message = f"{datetime_utc}{method.upper()}{path}{query}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"CEA algorithm=HmacSHA256,access-key={access_key},"
        f"signed-date={datetime_utc},signature={signature}"
    )
    return {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8",
    }


def _format_coupang_products(keyword: str, products: list[dict[str, Any]]) -> str:
    if not products:
        return f"검색 결과가 없습니다: {keyword}"
    lines = [
        f"✅ 쿠팡 파트너스 API 상품 검색 완료: {keyword}",
        "",
        "| # | 상품 | 가격 | 링크 |",
        "|---|---|---:|---|",
    ]
    for idx, item in enumerate(products, 1):
        title = str(item.get("productName") or item.get("title") or "(제목 없음)").replace("\n", " ").strip()
        price = item.get("productPrice")
        product_url = item.get("productUrl") or item.get("url") or ""
        price_text = f"{int(price):,}원" if isinstance(price, (int, float)) else "미확인"
        lines.append(f"| {idx} | {title[:100]} | {price_text} | {product_url} |")
    lines.append("")
    lines.append("주의: 쿠팡 파트너스/Open API 응답 기준 read-only 검색 결과입니다. 주문/구매/장바구니 동작은 수행하지 않았습니다.")
    return "\n".join(lines)


def tool_coupang_product_search(keyword: str, limit: int = 5) -> str:
    safety_error = _coupang_product_search_safety_error(keyword)
    if safety_error:
        return safety_error
    access_key = os.environ.get("COUPANG_PARTNERS_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("COUPANG_PARTNERS_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        return (
            "❌ 쿠팡 파트너스/Open API 키가 설정되지 않았습니다.\n"
            "필요 환경변수: COUPANG_PARTNERS_ACCESS_KEY, COUPANG_PARTNERS_SECRET_KEY\n"
            "선택 환경변수: COUPANG_PARTNERS_BASE_URL, COUPANG_PARTNERS_PRODUCT_SEARCH_PATH"
        )
    try:
        limit = max(1, min(int(limit or 5), 10))
        base_url = os.environ.get("COUPANG_PARTNERS_BASE_URL", "https://api-gateway.coupang.com").rstrip("/")
        path = os.environ.get(
            "COUPANG_PARTNERS_PRODUCT_SEARCH_PATH",
            "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search",
        )
        query = urlencode({"keyword": keyword, "limit": limit})
        path_with_query = f"{path}?{query}"
        headers = _coupang_hmac_headers("GET", path_with_query)
        resp = httpx.get(
            f"{base_url}{path}",
            params={"keyword": keyword, "limit": limit},
            headers=headers,
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        products = (
            data.get("data", {}).get("productData")
            or data.get("data", [])
            or data.get("products", [])
            or []
        )
        if not isinstance(products, list):
            products = []
        return _format_coupang_products(keyword, products[:limit])
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        return f"❌ 쿠팡 파트너스 API 오류: HTTP {exc.response.status_code}\n{body}"
    except Exception as exc:
        return f"❌ 쿠팡 파트너스 API 오류: {type(exc).__name__}: {exc}"


def _slack_api(endpoint: str, payload: dict) -> dict:
    """Slack API 호출 — form-encoded"""
    resp = httpx.post(
        f"https://slack.com/api/{endpoint}",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _upload_file_to_slack(pdf_path: Path, title: str, channel_id: str) -> str:
    """3단계 Slack 파일 업로드"""
    file_size = pdf_path.stat().st_size
    r1 = _slack_api("files.getUploadURLExternal", {
        "filename": pdf_path.name,
        "length": str(file_size),
    })
    if not r1.get("ok"):
        return f"❌ URL 요청 실패: {r1.get('error')} / {r1}"

    upload_url = r1["upload_url"]
    file_id = r1["file_id"]

    with pdf_path.open("rb") as f:
        put_resp = httpx.post(upload_url, content=f.read(),
                              headers={"Content-Type": "application/octet-stream"},
                              timeout=60)
    if put_resp.status_code not in (200, 201):
        return f"❌ 파일 업로드 실패: HTTP {put_resp.status_code} / {put_resp.text[:200]}"

    r3 = _slack_api("files.completeUploadExternal", {
        "files": json.dumps([{"id": file_id, "title": title}]),
        "channel_id": channel_id,
        "initial_comment": f"📊 *{title}* — OpenClaw 생성 보고서",
    })
    if r3.get("ok"):
        return f"✅ PDF 전송 완료: {title}.pdf → {channel_id}"
    return f"❌ 업로드 완료 실패: {r3.get('error')} / {json.dumps(r3)[:300]}"


def tool_render_pdf(title: str, content: str, channel_id: str) -> str:
    try:
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        md_path = reports_dir / f"{safe_title}.md"
        pdf_path = reports_dir / f"{safe_title}.pdf"

        md_path.write_text(content, encoding="utf-8")
        logger.info(f"[render_pdf] MD 저장: {md_path}")

        result = subprocess.run(
            [str(VENV_PYTHON), str(PROJECT_ROOT / "scripts/render_markdown_pdf.py"),
             str(md_path), str(pdf_path)],
            capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT),
        )
        logger.info(f"[render_pdf] render rc={result.returncode} stdout={result.stdout[:200]}")
        if result.returncode != 0:
            return f"❌ PDF 생성 실패:\n{result.stderr[:500]}"

        logger.info(f"[render_pdf] PDF 크기: {pdf_path.stat().st_size} bytes")
        return _upload_file_to_slack(pdf_path, title, channel_id)
    except Exception as e:
        logger.exception("[render_pdf] 오류")
        return f"❌ render_pdf 오류: {e}"


def tool_gmail_search(query: str, limit: int = 10) -> str:
    try:
        limit = max(1, min(int(limit or 10), 25))
        cmd = [
            str(VENV_PYTHON),
            str(PROJECT_ROOT / "scripts/openclaw_codex_bridge.py"),
            "gmail-search",
            query,
            "--limit",
            str(limit),
            "--format",
            "text",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(PROJECT_ROOT),
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode == 0:
            return output
        return f"❌ Gmail 검색 실패 (code={result.returncode})\n{output}"
    except Exception as exc:
        return f"❌ Gmail 검색 중 오류 발생: {exc}"


def tool_gmail_get(message_id: str) -> str:
    try:
        cmd = [
            str(VENV_PYTHON),
            str(PROJECT_ROOT / "scripts/openclaw_codex_bridge.py"),
            "gmail-get",
            message_id,
            "--format",
            "text",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(PROJECT_ROOT),
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode == 0:
            return output
        return f"❌ Gmail 메일 본문 수집 실패 (code={result.returncode})\n{output}"
    except Exception as exc:
        return f"❌ Gmail 메일 수집 중 오류 발생: {exc}"


TOOL_EXECUTORS = {
    "read_file": lambda inp: tool_read_file(inp["path"]),
    "write_file": lambda inp: tool_write_file(inp["path"], inp["content"], inp.get("mode", "overwrite")),
    "list_files": lambda inp: tool_list_files(inp["path"]),
    "run_script": lambda inp: tool_run_script(inp["script"], inp.get("args")),
    "send_slack": lambda inp: tool_send_slack(inp["channel"], inp["message"]),
    "render_pdf": lambda inp: tool_render_pdf(inp["title"], inp["content"], inp["channel_id"]),
    "fetch_url": lambda inp: tool_fetch_url(inp["url"]),
    "web_search": lambda inp: tool_web_search(inp["query"], inp.get("count", 5)),
    "browser_research": lambda inp: tool_browser_research(
        inp["task"],
        inp.get("url", ""),
        inp.get("query", ""),
        inp.get("site", ""),
        inp.get("max_items", 5),
    ),
    "coupang_product_search": lambda inp: tool_coupang_product_search(
        inp["keyword"],
        inp.get("limit", 5),
    ),
    "gmail_search": lambda inp: tool_gmail_search(inp["query"], inp.get("limit", 10)),
    "gmail_get": lambda inp: tool_gmail_get(inp["message_id"]),
}
