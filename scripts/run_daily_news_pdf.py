"""
Daily News PDF — 매일 오전 6시 신규 refined_outputs → CEO Slack 발송

- 이미 발송한 article ID는 docs/reports/news_pdf_sent_ids.json에 기록
- 신규 기사만 포함 (중복 발송 없음)
- PDF 구조:
    [1] Executive Summary Box — 오늘의 핵심 인사이트 (Claude 생성)
    [2] 채널별 기사 (hook + 한국 전략 맥락)
- SLACK_BOT_TOKEN으로 files.getUploadURLExternal 방식 업로드
"""

from __future__ import annotations

import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

SENT_IDS_PATH = ROOT / "docs" / "reports" / "news_pdf_sent_ids.json"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── DB 조회 ──────────────────────────────────────────────────────────────────

def _get_new_articles(sent_ids: set[int]) -> list[dict]:
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT ro.id, ro.final_title, ro.final_body, ro.tags, ro.created_at,
               fs.source, fs.score,
               rs.raw_data->>'url' AS url
        FROM refined_outputs ro
        LEFT JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        ORDER BY ro.created_at DESC
        LIMIT 200
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    new_rows = [r for r in rows if r["id"] not in sent_ids]
    return new_rows


# ── 채널 분류 ─────────────────────────────────────────────────────────────────

_CHANNEL_KW = {
    "policy_reg":    {"regulation","policy","regulatory","compliance","audit","govtech","ai act","legislation","law","rule","certified","korea ai policy","governance","online safety","regtech"},
    "edu_business":  {"education","edtech","learning","teaching","school","curriculum","training","talent","education pipeline","special needs education","pedagogy","upskilling"},
    "market_invest": {"venture capital","investment","market","economics","startup ecosystem","hard tech","creator economy","data licensing","ipo","equity","revenue","monetization","supply chain","llm economics"},
}
_CHANNEL_LABELS = {
    "tech_ai":       "🤖 AI·테크",
    "edu_business":  "📚 교육·사업",
    "market_invest": "📈 시장·투자",
    "policy_reg":    "⚖️ 정책·규제",
}

def _infer_channel(tags) -> str:
    if not isinstance(tags, list):
        return "tech_ai"
    tag_lower = {str(t).lower() for t in tags}
    scores = {ch: sum(1 for kw in kws for t in tag_lower if kw in t)
              for ch, kws in _CHANNEL_KW.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "tech_ai"


# ── Claude로 핵심 인사이트 생성 ───────────────────────────────────────────────

def _generate_insights(articles: list[dict]) -> str:
    """최신 기사 기반으로 오늘의 핵심 인사이트 3-5개를 Claude로 생성."""
    if not articles:
        return "오늘은 신규 분석 기사가 없습니다."
    summaries = []
    for a in articles[:15]:
        body = a.get("final_body") or {}
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except Exception:
                body = {}
        hook = (body.get("hook") or "")[:150]
        title = a.get("final_title") or ""
        summaries.append(f"- {title}: {hook}")

    prompt = (
        "당신은 Harness의 최고 인텔리전스 분석가입니다.\n"
        "아래는 오늘 수집된 주요 기사 목록입니다.\n\n"
        + "\n".join(summaries) +
        "\n\n"
        "CEO가 오늘 아침 30초 안에 핵심을 파악할 수 있도록, "
        "가장 중요한 인사이트 3~5개를 한국어로 작성하세요.\n"
        "각 인사이트는 '• '으로 시작하고, 1~2문장 이내로 간결하게 씁니다.\n"
        "전문용어에는 반드시 괄호로 쉬운 설명을 붙이세요.\n"
        "결론만 씁니다. 서론이나 인사말 없이 바로 bullet으로 시작합니다."
    )
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/claude", "-p", prompt],
            capture_output=True, text=True, timeout=60,
            env={**os.environ,
                 "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
                 "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")},
        )
        text = (result.stdout or "").strip()
        if text and result.returncode == 0:
            return text
    except Exception:
        pass
    # fallback: 상위 기사 제목 나열
    lines = [f"• {a.get('final_title','')[:80]}" for a in articles[:5] if a.get("final_title")]
    return "\n".join(lines) if lines else "오늘의 신규 기사를 확인하세요."


# ── PDF 생성 ──────────────────────────────────────────────────────────────────

def _build_pdf(articles: list[dict], insights: str, date_str: str) -> bytes:
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
        Table, TableStyle, KeepTogether,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    # 한글 폰트
    font = "Helvetica"
    for fp in [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf",
    ]:
        try:
            if "KDailyNews" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("KDailyNews", fp))
            font = "KDailyNews"
            break
        except Exception:
            continue

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], fontName=font, **kw)

    title_s  = ps("dt", fontSize=20, leading=26, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    sub_s    = ps("ds", fontSize=9,  textColor=colors.HexColor("#94a3b8"), spaceAfter=12)
    box_s    = ps("db", fontSize=10, leading=16, textColor=colors.HexColor("#1e3a5f"), spaceAfter=4)
    ch_s     = ps("dc", fontSize=12, leading=16, textColor=colors.HexColor("#1e40af"), spaceBefore=16, spaceAfter=4)
    art_h_s  = ps("dah", fontSize=11, leading=15, textColor=colors.HexColor("#1e293b"), spaceBefore=8, spaceAfter=3)
    art_b_s  = ps("dab", fontSize=9,  leading=14, textColor=colors.HexColor("#475569"), spaceAfter=3)
    art_k_s  = ps("dak", fontSize=9,  leading=14, textColor=colors.HexColor("#7c3aed"), spaceAfter=2)

    def esc(s):
        return (str(s) or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story: list = []

    # ── 헤더 ──
    story += [
        Paragraph("Harness News Center", title_s),
        Paragraph(f"CEO Daily Intelligence Brief · {date_str}  |  신규 기사 {len(articles)}건", sub_s),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb")),
        Spacer(1, 0.3*cm),
    ]

    # ── 핵심 인사이트 박스 ──
    insight_lines = [Paragraph(esc(line), box_s)
                     for line in insights.splitlines() if line.strip()]
    if not insight_lines:
        insight_lines = [Paragraph("신규 분석 기사를 확인하세요.", box_s)]

    box_header = Paragraph("📌  오늘의 핵심 인사이트", ps("bh", fontSize=11,
                           textColor=colors.HexColor("#1e3a5f"), spaceAfter=6))
    box_content = [box_header] + insight_lines
    box_table = Table(
        [[box_content]],
        colWidths=[doc.width],
    )
    box_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ("LEFTPADDING",  (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("BOX",          (0,0), (-1,-1), 1.5, colors.HexColor("#2563eb")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story += [box_table, Spacer(1, 0.5*cm)]

    # ── 채널별 기사 ──
    from itertools import groupby
    articles_with_ch = [(a, _infer_channel(a.get("tags"))) for a in articles]
    ch_order = ["tech_ai", "market_invest", "policy_reg", "edu_business"]
    ch_groups: dict[str, list] = {ch: [] for ch in ch_order}
    for a, ch in articles_with_ch:
        ch_groups.setdefault(ch, []).append(a)

    for ch in ch_order:
        group = ch_groups.get(ch, [])
        if not group:
            continue
        story.append(Paragraph(
            f"{_CHANNEL_LABELS.get(ch, ch)}  ({len(group)}건)", ch_s))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#dbeafe")))

        for a in group:
            body = a.get("final_body") or {}
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except Exception:
                    body = {}
            hook  = body.get("hook") or ""
            korea = body.get("korea_strategic_context") or ""
            exec_b = body.get("executive_decision_block") or {}
            buy = ""
            if isinstance(exec_b, dict):
                buy = exec_b.get("buy_signal") or exec_b.get("action") or ""
            elif isinstance(exec_b, str):
                buy = exec_b

            block = [
                Paragraph(esc(a.get("final_title") or "(제목 없음)"), art_h_s),
            ]
            if hook:
                block.append(Paragraph(esc(hook[:400]), art_b_s))
            if korea:
                block.append(Paragraph(f"▸ {esc(korea[:300])}", art_k_s))
            if buy:
                block.append(Paragraph(f"→ CEO 액션: {esc(str(buy)[:200])}", art_b_s))
            story.append(KeepTogether(block))

    doc.build(story)
    return buf.getvalue()


# ── Slack 업로드 ──────────────────────────────────────────────────────────────

def _slack_upload_pdf(pdf_bytes: bytes, filename: str, message: str) -> bool:
    import httpx
    try:
        # Step 1: get upload URL
        r1 = httpx.post(
            "https://slack.com/api/files.getUploadURLExternal",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            data={"filename": filename, "length": len(pdf_bytes)},
            timeout=15,
        ).json()
        if not r1.get("ok"):
            print(f"[ERROR] upload URL 실패: {r1.get('error')}")
            return False
        # Step 2: upload binary
        httpx.post(r1["upload_url"], content=pdf_bytes,
                   headers={"Content-Type": "application/octet-stream"}, timeout=60)
        # Step 3: complete
        r3 = httpx.post(
            "https://slack.com/api/files.completeUploadExternal",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                     "Content-Type": "application/json"},
            json={"files": [{"id": r1["file_id"]}],
                  "channel_id": SLACK_CHANNEL,
                  "initial_comment": message},
            timeout=15,
        ).json()
        if not r3.get("ok"):
            print(f"[ERROR] complete 실패: {r3.get('error')}")
            return False
        return True
    except Exception as exc:
        print(f"[ERROR] Slack 업로드 예외: {exc}")
        return False


# ── 발송 기록 ──────────────────────────────────────────────────────────────────

def _load_sent_ids() -> set[int]:
    if SENT_IDS_PATH.exists():
        try:
            data = json.loads(SENT_IDS_PATH.read_text())
            return set(data.get("sent_ids", []))
        except Exception:
            pass
    return set()


def _save_sent_ids(sent_ids: set[int]) -> None:
    SENT_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SENT_IDS_PATH.write_text(
        json.dumps({"sent_ids": sorted(sent_ids), "updated_at": datetime.now(timezone.utc).isoformat()},
                   ensure_ascii=False, indent=2)
    )


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    date_str = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")  # KST
    print(f"[{date_str}] Daily News PDF 시작")

    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
        print("[ERROR] SLACK_BOT_TOKEN 또는 SLACK_CHANNEL 미설정")
        sys.exit(1)

    sent_ids = _load_sent_ids()
    articles = _get_new_articles(sent_ids)

    if not articles:
        print("[INFO] 신규 기사 없음 — 발송 생략")
        return

    print(f"[INFO] 신규 기사 {len(articles)}건 발견")

    # 핵심 인사이트 생성 (Claude)
    print("[INFO] 핵심 인사이트 생성 중...")
    insights = _generate_insights(articles)

    # PDF 생성
    print("[INFO] PDF 생성 중...")
    pdf_bytes = _build_pdf(articles, insights, date_str)
    filename = f"harness-news-{date_str}.pdf"
    print(f"[INFO] PDF 크기: {len(pdf_bytes):,} bytes")

    # Slack 발송
    article_count = len(articles)
    ch_counts = {}
    for a in articles:
        ch = _infer_channel(a.get("tags"))
        ch_counts[ch] = ch_counts.get(ch, 0) + 1
    ch_summary = " · ".join(
        f"{_CHANNEL_LABELS.get(ch, ch).split(' ')[1]} {cnt}건"
        for ch, cnt in sorted(ch_counts.items(), key=lambda x: -x[1])
    )
    message = (
        f"📰 *Harness News Center* — {date_str} CEO 데일리 브리프\n"
        f"신규 기사 *{article_count}건* | {ch_summary}\n"
        f"_📌 핵심 인사이트 및 채널별 분석이 PDF에 포함되어 있습니다._"
    )

    print("[INFO] Slack 발송 중...")
    ok = _slack_upload_pdf(pdf_bytes, filename, message)
    if ok:
        new_sent = sent_ids | {a["id"] for a in articles}
        _save_sent_ids(new_sent)
        print(f"[OK] 발송 완료 — {article_count}건, sent_ids 업데이트")
    else:
        print("[ERROR] 발송 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
