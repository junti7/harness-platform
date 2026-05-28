"""
browser_control.py — OpenClaw 웹 브라우저 컨트롤 모듈
Playwright Chromium (headless) 기반.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCREENSHOT_DIR = Path("docs/browser_screenshots")
DEFAULT_TIMEOUT_MS = 15_000          # 페이지 로드 타임아웃
DEFAULT_VIEWPORT = {"width": 1280, "height": 900}
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _make_browser(headless: bool = True):
    """Playwright 브라우저 인스턴스 생성 (Chromium)."""
    from playwright.sync_api import sync_playwright  # lazy import

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context(
        viewport=DEFAULT_VIEWPORT,
        user_agent=USER_AGENT,
        java_script_enabled=True,
    )
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    return pw, browser, context, page


def _safe_text(page, max_chars: int = 4000) -> str:
    """페이지에서 가독성 있는 텍스트 추출 (노이즈 제거)."""
    try:
        # <main>, <article>, <body> 순으로 시도
        for selector in ["main", "article", "#content", "body"]:
            try:
                el = page.query_selector(selector)
                if el:
                    text = el.inner_text()
                    if text and len(text.strip()) > 100:
                        break
            except Exception:
                continue
        else:
            text = page.inner_text("body")
    except Exception:
        text = ""

    # 연속 공백/개행 정리
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r" {3,}", " ", text)
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def browser_open(url: str, extract_text: bool = True) -> dict[str, Any]:
    """
    URL을 열고 페이지 제목 + 텍스트를 반환한다.
    Returns: {"ok": bool, "url": str, "title": str, "text": str, "error": str}
    """
    pw = browser = context = page = None
    try:
        pw, browser, context, page = _make_browser()
        page.goto(url, wait_until="domcontentloaded")
        title = page.title()
        text = _safe_text(page) if extract_text else ""
        return {"ok": True, "url": page.url, "title": title, "text": text}
    except Exception as exc:
        return {"ok": False, "url": url, "title": "", "text": "", "error": str(exc)}
    finally:
        if page: page.close()
        if context: context.close()
        if browser: browser.close()
        if pw: pw.stop()


def browser_screenshot(url: str, filename: str | None = None) -> dict[str, Any]:
    """
    URL 스크린샷을 파일로 저장.
    Returns: {"ok": bool, "path": str, "error": str}
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename:
        safe = re.sub(r"[^\w]", "_", url)[:60]
        filename = f"{safe}_{int(time.time())}.png"
    out_path = SCREENSHOT_DIR / filename

    pw = browser = context = page = None
    try:
        pw, browser, context, page = _make_browser()
        page.goto(url, wait_until="domcontentloaded")
        page.screenshot(path=str(out_path), full_page=True)
        return {"ok": True, "path": str(out_path), "url": page.url}
    except Exception as exc:
        return {"ok": False, "path": "", "error": str(exc)}
    finally:
        if page: page.close()
        if context: context.close()
        if browser: browser.close()
        if pw: pw.stop()


def browser_search(query: str, engine: str = "naver", limit: int = 5) -> dict[str, Any]:
    """
    검색엔진에서 검색 후 결과 목록을 반환.
    engine: "naver" | "google" | "duckduckgo"
    Returns: {"ok": bool, "query": str, "results": [{"title", "url", "snippet"}]}
    """
    import urllib.parse

    q_enc = urllib.parse.quote(query)

    if engine == "google":
        search_url = f"https://www.google.com/search?q={q_enc}&hl=ko&num={limit}"
    elif engine == "duckduckgo":
        search_url = f"https://html.duckduckgo.com/html/?q={q_enc}"
    else:  # naver (default)
        search_url = f"https://search.naver.com/search.naver?query={q_enc}"

    pw = browser = context = page = None
    try:
        pw, browser, context, page = _make_browser()
        page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(1.5)

        results: list[dict] = []

        if engine == "naver":
            # Naver: li.bx 안에서 a 링크 + 텍스트 추출
            items = page.query_selector_all("li.bx")
            for item in items[:limit * 2]:
                try:
                    title_el = item.query_selector("a.title_link, a.news_tit, .title a, h2 a, h3 a")
                    if not title_el:
                        continue
                    title = title_el.inner_text().strip()
                    href = title_el.get_attribute("href") or ""
                    snippet_el = item.query_selector(".dsc_txt, .total_dsc_wrap, .news_dsc, p")
                    snippet = snippet_el.inner_text().strip() if snippet_el else ""
                    if title and len(title) > 2:
                        results.append({"title": title, "url": href, "snippet": snippet[:200]})
                        if len(results) >= limit:
                            break
                except Exception:
                    continue
            # fallback: 텍스트 파싱
            if not results:
                text = _safe_text(page, max_chars=3000)
                results = [{"title": f"Naver 검색: {query}", "url": search_url, "snippet": text[:500]}]

        else:
            # Google / DuckDuckGo: 봇 차단 가능성 있으므로 텍스트 fallback 우선
            text = _safe_text(page, max_chars=3000)
            if text and len(text) > 100:
                results = [{"title": f"{engine.capitalize()} 검색: {query}", "url": search_url, "snippet": text[:800]}]
            else:
                results = [{"title": f"{engine.capitalize()} 검색: {query}", "url": search_url, "snippet": "(결과 없음 — 봇 차단 가능)"}]

        return {"ok": True, "query": query, "engine": engine, "results": results}
    except Exception as exc:
        return {"ok": False, "query": query, "engine": engine, "results": [], "error": str(exc)}
    finally:
        if page: page.close()
        if context: context.close()
        if browser: browser.close()
        if pw: pw.stop()


def browser_extract(url: str, selector: str) -> dict[str, Any]:
    """
    CSS selector로 특정 요소의 텍스트를 추출.
    Returns: {"ok": bool, "url": str, "selector": str, "texts": [str]}
    """
    pw = browser = context = page = None
    try:
        pw, browser, context, page = _make_browser()
        page.goto(url, wait_until="domcontentloaded")
        elements = page.query_selector_all(selector)
        texts = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
        return {"ok": True, "url": url, "selector": selector, "texts": texts[:20]}
    except Exception as exc:
        return {"ok": False, "url": url, "selector": selector, "texts": [], "error": str(exc)}
    finally:
        if page: page.close()
        if context: context.close()
        if browser: browser.close()
        if pw: pw.stop()


def browser_fill(url: str, actions: list[dict]) -> dict[str, Any]:
    """
    폼 입력 및 클릭 자동화.
    actions: [{"type": "fill"|"click"|"wait", "selector": str, "value": str}]
    Returns: {"ok": bool, "url": str, "final_url": str, "text": str, "error": str}

    Example actions:
      [
        {"type": "fill",  "selector": "input[name=q]", "value": "검색어"},
        {"type": "click", "selector": "input[type=submit]"},
        {"type": "wait",  "selector": ".results"}
      ]
    """
    pw = browser = context = page = None
    try:
        pw, browser, context, page = _make_browser()
        page.goto(url, wait_until="domcontentloaded")

        for action in actions:
            atype = action.get("type", "")
            sel = action.get("selector", "")
            val = action.get("value", "")
            if atype == "fill":
                page.fill(sel, val)
            elif atype == "click":
                page.click(sel)
                time.sleep(0.5)
            elif atype == "wait":
                page.wait_for_selector(sel, timeout=DEFAULT_TIMEOUT_MS)
            elif atype == "goto":
                page.goto(val, wait_until="domcontentloaded")

        final_url = page.url
        text = _safe_text(page)
        return {"ok": True, "url": url, "final_url": final_url, "text": text}
    except Exception as exc:
        return {"ok": False, "url": url, "final_url": "", "text": "", "error": str(exc)}
    finally:
        if page: page.close()
        if context: context.close()
        if browser: browser.close()
        if pw: pw.stop()
