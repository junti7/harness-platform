#!/usr/bin/env python3
"""Read-only browser research helper for OpenClaw.

This script intentionally supports only public-page browsing, search, and
extraction. It must not log in, add to cart, purchase, submit forms, or mutate
remote state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup


BLOCKED_TERMS = (
    "구매",
    "결제",
    "주문",
    "장바구니",
    "바로구매",
    "checkout",
    "payment",
    "purchase",
    "buy now",
    "order",
    "cart",
    "login",
    "로그인",
    "sign in",
    "회원가입",
    "주소",
    "배송지",
)


@dataclass
class Product:
    title: str
    price: int | None
    url: str
    delivery: str
    ad: str


def _fail(message: str, code: int = 2) -> None:
    print(message)
    raise SystemExit(code)


def _check_read_only(*values: str | None) -> None:
    joined = " ".join(v or "" for v in values).lower()
    matched = [term for term in BLOCKED_TERMS if term in joined]
    if matched:
        _fail(
            "❌ browser_research 차단: 이 도구는 공개 페이지 read-only 탐색만 허용합니다.\n"
            f"차단 키워드: {', '.join(matched)}\n"
            "구매/결제/주문/장바구니/로그인/개인정보 입력은 실행하지 않습니다."
        )


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        _fail(
            "❌ Playwright가 설치되어 있지 않아 브라우저 자동화를 실행할 수 없습니다.\n"
            "필요 조치: `.venv/bin/pip install playwright` 후 `.venv/bin/python -m playwright install chromium`",
            code=3,
        )
    return sync_playwright


def _price_to_int(text: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else None


def _absolute_url(url: str, base: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    return url


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _extract_coupang_products(html: str, base_url: str, max_items: int) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []
    seen: set[str] = set()
    selectors = [
        "li.search-product",
        "li[data-sentry-component='SearchProductItem']",
        "a.search-product-link",
        "a[href*='/vp/products/']",
    ]
    nodes = []
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            break

    for node in nodes:
        link = node if getattr(node, "name", "") == "a" else node.select_one("a[href]")
        href = _absolute_url(link.get("href", "") if link else "", base_url)
        if not href or href in seen:
            continue
        seen.add(href)
        title = (
            _text(node.select_one(".name"))
            or _text(node.select_one("[class*='name']"))
            or (link.get("title", "") if link else "")
            or _text(link)
        )
        price_text = (
            _text(node.select_one(".price-value"))
            or _text(node.select_one("[class*='price']"))
            or ""
        )
        price = _price_to_int(price_text)
        if not title or price is None:
            continue
        delivery = (
            _text(node.select_one(".delivery"))
            or _text(node.select_one("[class*='delivery']"))
            or "미확인"
        )
        ad_text = _text(node)
        ad = "광고 가능" if "광고" in ad_text[:120] else "미확인"
        products.append(Product(title=title[:120], price=price, url=href, delivery=delivery[:80], ad=ad))
        if len(products) >= max_items * 3:
            break
    return sorted(products, key=lambda p: p.price if p.price is not None else 10**18)[:max_items]


def _render_products(query: str, products: list[Product], html: str = "") -> str:
    if not products:
        body_text = " ".join(BeautifulSoup(html or "", "html.parser").get_text(" ").split())[:500]
        if "Access Denied" in body_text or "permission to access" in body_text:
            return (
                f"❌ 쿠팡 접근 차단: 브라우저는 실행됐지만 쿠팡이 자동화 접근을 거부했습니다: {query}\n"
                f"- 감지 내용: {body_text}\n"
                "- 의미: 현재 방식으로는 `쿠팡에 등록된 상품 중 최저가`를 신뢰성 있게 산출할 수 없습니다.\n"
                "- 허용 가능한 대안: 공식/제휴 API, 사용자가 제공한 쿠팡 검색 URL/페이지 원문, 또는 일반 웹/가격검색 결과 기반 후보 비교."
            )
        return (
            f"❌ 쿠팡 검색 결과에서 가격이 있는 상품을 추출하지 못했습니다: {query}\n"
            "쿠팡의 봇 탐지/동적 렌더링/개인화 가격 때문에 결과가 제한될 수 있습니다."
        )
    lines = [
        f"✅ 브라우저 read-only 검색 완료: 쿠팡 `{query}`",
        "",
        "| 순위 | 상품 | 가격 | 배송 | 광고 | URL |",
        "|---|---|---:|---|---|---|",
    ]
    for idx, item in enumerate(products, 1):
        lines.append(
            f"| {idx} | {item.title} | {item.price:,}원 | {item.delivery} | {item.ad} | {item.url} |"
        )
    lines.extend([
        "",
        "주의: 구매/로그인/장바구니/결제는 실행하지 않았습니다. 배송비, 와우회원가, 쿠폰, 개인화 가격은 화면/계정 조건에 따라 달라질 수 있습니다.",
    ])
    return "\n".join(lines)


def _render_generic(url: str, html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else "(제목 없음)"
    links = []
    for link in soup.select("a[href]")[:20]:
        label = _text(link)[:80] or link.get("href", "")[:80]
        href = _absolute_url(link.get("href", ""), url)
        if href:
            links.append(f"- {label}: {href}")
    body = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return (
        f"✅ 브라우저 read-only 페이지 확인 완료\n"
        f"- URL: {url}\n"
        f"- TITLE: {title}\n\n"
        f"주요 링크:\n" + ("\n".join(links[:10]) if links else "(링크 없음)") + "\n\n"
        f"본문 미리보기:\n{body[:3000]}"
    )


def run(args: argparse.Namespace) -> str:
    _check_read_only(args.task, args.url, args.query, args.site)
    sync_playwright = _require_playwright()

    site = (args.site or "").lower().strip()
    if site == "coupang":
        if not args.query:
            _fail("❌ Coupang 검색에는 --query가 필요합니다.")
        url = f"https://www.coupang.com/np/search?q={quote_plus(args.query)}"
    elif args.url:
        url = args.url
    elif args.query:
        url = f"https://duckduckgo.com/?q={quote_plus(args.query)}"
    else:
        _fail("❌ --url 또는 --query 중 하나가 필요합니다.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        _fail(f"❌ 허용되지 않는 URL scheme: {parsed.scheme}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            locale="ko-KR",
            viewport={"width": 1440, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=min(args.timeout_ms, 8000))
        except Exception:
            pass
        html = page.content()
        final_url = page.url
        browser.close()

    if site == "coupang" or "coupang.com" in parsed.netloc:
        return _render_products(args.query or final_url, _extract_coupang_products(html, final_url, args.max_items), html)
    return _render_generic(final_url, html)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only browser research helper")
    parser.add_argument("--task", default="", help="Natural-language task description for audit/safety")
    parser.add_argument("--url", default="", help="Public URL to open")
    parser.add_argument("--query", default="", help="Search query")
    parser.add_argument("--site", default="", help="Known site adapter. Currently: coupang")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument("--headed", action="store_true", help="Open a visible browser window instead of headless mode")
    args = parser.parse_args()
    args.max_items = max(1, min(args.max_items, 10))
    try:
        print(run(args))
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
