"""
Price Drop Monitor — 포지션 급락 실시간 감지 → Claude 브리핑 → CEO Slack 긴급 보고
AR-018 Paper Trading 모니터링 확장
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALERTS_PATH = PROJECT_ROOT / "docs" / "reports" / "price_drop_alerts.jsonl"

# ── 설정 ──────────────────────────────────────────────────────────────────────
DROP_RAPID_THRESHOLD = float(os.getenv("PRICE_DROP_RAPID_PCT", "-3.0"))   # 단기 -3%
DROP_DAY_THRESHOLD = float(os.getenv("PRICE_DROP_DAY_PCT", "-5.0"))       # 진입가 대비 -5%
MONITOR_INTERVAL_SEC = int(os.getenv("PRICE_DROP_INTERVAL_SEC", "60"))    # 폴링 주기
COOLDOWN_SEC = int(os.getenv("PRICE_DROP_COOLDOWN_SEC", "3600"))          # 급속(rapid) 알림 쿨다운 1h
# 누적 낙폭(진입가 대비)은 손실 포지션이 계속 떠 있는 한 매 쿨다운마다 영구 재알림되어
# Slack 폭주의 주원인이다. 별도로 대폭 긴 쿨다운(기본 24h)을 적용한다.
DAY_COOLDOWN_SEC = int(os.getenv("PRICE_DROP_DAY_COOLDOWN_SEC", "86400")) # 누적 낙폭 알림 쿨다운 24h
# 쿨다운 타임스탬프를 파일로 영속화 — 백엔드(KeepAlive) 재시작 시 in-memory 초기화로
# 인한 재폭주를 방지한다.
_ALERT_STATE_PATH = PROJECT_ROOT / "runtime" / "price_drop_alert_state.json"

_prev_prices: dict[str, float] = {}
_last_alert_ts: dict[str, float] = {}  # key = "symbol:trigger_type"
_lock = threading.Lock()


def _load_alert_state() -> None:
    try:
        data = json.loads(_ALERT_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            with _lock:
                _last_alert_ts.update({str(k): float(v) for k, v in data.items()})
    except Exception:
        pass


def _save_alert_state() -> None:
    try:
        _ALERT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            snap = dict(_last_alert_ts)
        _ALERT_STATE_PATH.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
_monitor_thread: threading.Thread | None = None


# ── Alpaca 데이터 ─────────────────────────────────────────────────────────────

def _get_current_positions() -> list[dict[str, Any]]:
    try:
        import sys
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.alpaca_paper_trading import get_positions
        raw = get_positions()
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _fetch_alpaca_news(symbol: str, limit: int = 5) -> list[str]:
    """Alpaca News API로 최근 뉴스 헤드라인 가져오기"""
    try:
        import requests
        key = os.getenv("ALPACA_API_KEY", "")
        secret = os.getenv("ALPACA_SECRET_KEY", "")
        if not key or not secret:
            return []
        resp = requests.get(
            "https://data.alpaca.markets/v1beta1/news",
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
            params={"symbols": symbol, "limit": limit, "sort": "desc"},
            timeout=10,
        )
        if not resp.ok:
            return []
        items = resp.json().get("news") or []
        return [
            str(item.get("headline") or item.get("summary") or "")
            for item in items
            if item.get("headline") or item.get("summary")
        ]
    except Exception:
        return []


def _generate_briefing(
    symbol: str,
    drop_pct: float,
    current: float,
    prev: float,
    trigger: str,
    news: list[str],
) -> str:
    """Claude Haiku로 급락 원인 분석 브리핑 생성"""
    try:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 미설정")

        client = anthropic.Anthropic(api_key=api_key)
        news_block = "\n".join(f"- {h}" for h in news[:5]) if news else "- 관련 뉴스 없음"
        trigger_label = "급속 낙폭(단기)" if trigger == "rapid" else "누적 낙폭(진입가 대비)"

        prompt = (
            f"Paper Trading 모니터링 알림: 종목 {symbol}에서 {trigger_label} {drop_pct:.1f}%가 감지되었습니다.\n"
            f"가격: ${prev:.2f} → ${current:.2f}\n\n"
            f"최근 관련 뉴스:\n{news_block}\n\n"
            "위 정보를 바탕으로 낙폭 원인을 2~3문장으로 한국어로 요약하세요.\n"
            "근거가 불충분하면 '추가 확인 필요'를 명시하고 가능한 원인을 짧게 적어주세요.\n"
            "투자 조언은 제공하지 마세요."
        )

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        if news:
            return f"AI 분석 불가({type(e).__name__}). 최근 뉴스: {'; '.join(news[:2])}"
        return f"AI 분석 불가({type(e).__name__}). 수동 확인 필요."


def _post_slack(alert: dict[str, Any]) -> None:
    """CEO에게 Slack 긴급 보고"""
    try:
        import httpx

        symbol = alert["symbol"]
        drop_pct = alert["drop_pct"]
        trigger = alert["trigger"]
        trigger_label = "급속 낙폭(단기)" if trigger == "rapid" else "누적 낙폭(진입가 대비)"
        ts_str = alert["detected_at"][:19].replace("T", " ")

        text = (
            f"🚨 *[긴급] Paper Trading 급락 감지 — {symbol}*\n"
            f"유형: {trigger_label} | 낙폭: *{drop_pct:.1f}%* "
            f"(${alert['prev_price']:.2f} → ${alert['current_price']:.2f})\n"
            f"감지 시각: {ts_str} UTC\n\n"
            f"*OpenClaw 자동 브리핑:*\n{alert['briefing']}\n\n"
            "_Paper Trading Monitor | Harness B2I_"
        )

        bot_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
        channel_id = (
            os.getenv("SLACK_CHANNEL_TRADING_ALERTS", "").strip()
            or os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "").strip()
        )
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()

        if bot_token and channel_id:
            httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {bot_token}",
                    "Content-Type": "application/json",
                },
                json={"channel": channel_id, "text": text},
                timeout=10,
            )
        elif webhook_url:
            httpx.post(webhook_url, json={"text": text}, timeout=10)
    except Exception:
        pass


def _save_alert(alert: dict[str, Any]) -> None:
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(alert, ensure_ascii=False) + "\n")


def check_once() -> list[dict[str, Any]]:
    """한 번 포지션 체크 → 급락 감지 → 알림. 새 알림 목록 반환."""
    positions = _get_current_positions()
    new_alerts: list[dict[str, Any]] = []
    now_ts = time.time()

    for pos in positions:
        if pos.get("error"):
            continue
        symbol = str(pos.get("symbol") or "")
        current = float(pos.get("current_price") or 0)
        if not symbol or not current:
            continue

        with _lock:
            prev = _prev_prices.get(symbol)

        if prev is None:
            with _lock:
                _prev_prices[symbol] = current
            continue

        fires: list[dict] = []

        # ① 급속 낙폭: 이전 폴링 대비
        rapid_drop = (current - prev) / prev * 100 if prev > 0 else 0.0
        if rapid_drop <= DROP_RAPID_THRESHOLD:
            ck = f"{symbol}:rapid"
            with _lock:
                last = _last_alert_ts.get(ck, 0)
            if now_ts - last >= COOLDOWN_SEC:
                fires.append({"trigger": "rapid", "drop_pct": round(rapid_drop, 2), "ref_price": prev})

        # ② 누적 낙폭: 진입가 대비
        day_drop = float(pos.get("unrealized_pnl_pct") or 0)
        if day_drop <= DROP_DAY_THRESHOLD:
            entry = float(pos.get("entry_price") or current)
            ck = f"{symbol}:day"
            with _lock:
                last = _last_alert_ts.get(ck, 0)
            if now_ts - last >= DAY_COOLDOWN_SEC:
                fires.append({"trigger": "day", "drop_pct": round(day_drop, 2), "ref_price": entry})

        for f in fires:
            news = _fetch_alpaca_news(symbol)
            briefing = _generate_briefing(symbol, f["drop_pct"], current, f["ref_price"], f["trigger"], news)
            alert: dict[str, Any] = {
                "id": f"drop-{symbol}-{f['trigger']}-{int(now_ts)}",
                "symbol": symbol,
                "trigger": f["trigger"],
                "drop_pct": f["drop_pct"],
                "current_price": round(current, 4),
                "prev_price": round(f["ref_price"], 4),
                "news_titles": news,
                "briefing": briefing,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False,
            }
            _save_alert(alert)
            _post_slack(alert)
            new_alerts.append(alert)

            ck = f"{symbol}:{f['trigger']}"
            with _lock:
                _last_alert_ts[ck] = now_ts
            _save_alert_state()  # 영속화 — 재시작에도 쿨다운 유지

        with _lock:
            _prev_prices[symbol] = current

    return new_alerts


def get_recent_alerts(limit: int = 20) -> list[dict[str, Any]]:
    """최근 알림 로드 (최신순)"""
    if not ALERTS_PATH.exists():
        return []
    rows: list[dict] = []
    with ALERTS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except Exception:
                pass
    return list(reversed(rows[-limit:]))


def ack_alert(alert_id: str) -> bool:
    """알림 확인 처리 (acknowledged=True)"""
    if not ALERTS_PATH.exists():
        return False
    rows: list[dict] = []
    found = False
    with ALERTS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
                if row.get("id") == alert_id:
                    row["acknowledged"] = True
                    found = True
                rows.append(row)
            except Exception:
                pass
    if found:
        with ALERTS_PATH.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return found


def _monitor_loop() -> None:
    while True:
        try:
            check_once()
        except Exception:
            pass
        time.sleep(MONITOR_INTERVAL_SEC)


def start_monitor() -> threading.Thread:
    global _monitor_thread
    _load_alert_state()  # 재시작에도 쿨다운 유지 — 영속 상태 복원
    with _lock:
        if _monitor_thread and _monitor_thread.is_alive():
            return _monitor_thread
        t = threading.Thread(target=_monitor_loop, daemon=True, name="price-drop-monitor")
        t.start()
        _monitor_thread = t
    return t
