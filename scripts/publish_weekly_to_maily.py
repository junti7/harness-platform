"""
Weekly Newsletter -> Maily 운영용 패키지 생성 스크립트

기본 동작:
1) newsletter_issues(maily) 레코드 upsert
2) Maily 에디터에 붙여넣을 markdown 패키지 생성

주의:
- Maily 공개 발행은 현재 수동 단계다.
- --mark-published는 외부 발행 이후 DB 상태만 확정한다.

Usage:
  python scripts/publish_weekly_to_maily.py --issue 5
  python scripts/publish_weekly_to_maily.py --issue 5 --signal-ids 10 11 12
  python scripts/publish_weekly_to_maily.py --issue 5 --mark-published --public-url https://maily.so/...
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.content.qa_agent import has_qa_clear
from adapters.content.vp_review_card import check_vp_review_approved
from core.database import execute_query
from core.logger import HarnessLogger
from scripts.publish_weekly_to_substack import get_signals_by_ids, get_top_signals, parse_body


TOP_SIGNALS_LIMIT = 7
OUTPUT_ROOT = Path("runtime/maily")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _latest_gate_approved(target_type: str, target_id: int, approval_type: str) -> bool:
    rows = execute_query(
        """
        SELECT decision
        FROM ceo_decisions
        WHERE target_type = %s
          AND target_id = %s
          AND approval_type = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (target_type, target_id, approval_type),
        fetch=True,
    )
    return bool(rows and rows[0].get("decision") == "approved")


def _render_signal_block(signal: dict, idx: int) -> str:
    watchlist = signal.get("watchlist") or []
    watchlist_lines = "\n".join(
        f"- {item.get('item', '').strip()} | 트리거: {item.get('trigger', '').strip()}"
        for item in watchlist
        if isinstance(item, dict)
    ).strip()
    decision_block = signal.get("decision_block") or {}

    lines = [
        f"## {idx}. {signal.get('final_title', '').strip()}",
        "",
        f"> {signal.get('hook', '').strip()}",
        "",
        "### What happened",
        signal.get("what_happened", "").strip(),
        "",
        "### Why it matters",
        signal.get("why_it_matters", "").strip(),
        "",
        "### Korea implication",
        signal.get("korea_implication", "").strip(),
        "",
        "### Risk / Counterargument",
        signal.get("risk_counterargument", "").strip(),
        "",
    ]

    if watchlist_lines:
        lines.extend(["### Watchlist", watchlist_lines, ""])

    if decision_block:
        lines.extend(
            [
                "### Action summary",
                f"- What to track: {decision_block.get('what_to_track', '').strip()}",
                f"- Who benefits: {decision_block.get('who_benefits', '').strip()}",
                f"- Who is exposed: {decision_block.get('who_is_exposed', '').strip()}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def build_maily_markdown(issue_number: int, issue_date: str, signals: list[dict]) -> str:
    head = [
        f"# Physical AI Weekly #{issue_number:03d}",
        "",
        f"- Issue Date: {issue_date}",
        "- Publishing Platform: Maily",
        "- Format: Free Weekly Issue",
        "",
        "---",
        "",
    ]
    body_blocks = [_render_signal_block(signal, idx) for idx, signal in enumerate(signals, start=1)]
    outro = [
        "",
        "---",
        "",
        "### Disclaimer",
        "본 콘텐츠는 정보 제공 목적이며 투자 자문이 아닙니다.",
    ]
    return "\n".join(head + body_blocks + outro).strip() + "\n"


def _esc(value: str | None) -> str:
    return html.escape((value or "").strip())


def _resolve_image_src(raw: str) -> str:
    value = raw.strip()
    if value.startswith("http://") or value.startswith("https://") or value.startswith("data:"):
        return value
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    if path.suffix.lower() == ".b64":
        payload = path.read_text(encoding="utf-8").strip()
        if not payload:
            raise ValueError(f"empty base64 payload: {path}")
        return f"data:image/png;base64,{payload}"
    mime_type, _ = mimetypes.guess_type(path.name)
    mime = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _render_image_gallery(image_inputs: list[str]) -> tuple[str, list[str]]:
    if not image_inputs:
        return "", []
    parts = [
        '<section style="margin:28px 0 34px 0;">',
        '<h2 style="font-size:20px;line-height:1.35;color:#0f172a;margin:0 0 14px 0;">Charts &amp; Figures</h2>',
    ]
    skipped: list[str] = []
    for raw in image_inputs:
        try:
            src = _resolve_image_src(raw)
            caption = Path(raw).name.replace("_", " ").replace("-", " ")
            parts.append(
                '<figure style="margin:0 0 20px 0;padding:14px 14px 12px 14px;border:1px solid #e2e8f0;'
                'border-radius:12px;background:#f8fafc;">'
                f'<img src="{src}" alt="{html.escape(caption)}" '
                'style="display:block;width:100%;max-width:640px;height:auto;max-height:420px;'
                'object-fit:contain;border-radius:10px;margin:0 auto;"/>'
                f'<figcaption style="margin-top:9px;font-size:13px;color:#64748b;text-align:center;">'
                f"{html.escape(caption)}</figcaption>"
                "</figure>"
            )
        except Exception:
            skipped.append(raw)
    if len(parts) == 2:
        return "", skipped
    parts.append("</section>")
    return "\n".join(parts), skipped


def _render_signal_html(signal: dict, idx: int) -> str:
    title = _esc(signal.get("final_title"))
    hook = _esc(signal.get("hook"))
    what_happened = _esc(signal.get("what_happened"))
    why_it_matters = _esc(signal.get("why_it_matters"))
    korea_implication = _esc(signal.get("korea_implication"))
    risk_counterargument = _esc(signal.get("risk_counterargument"))
    watchlist = signal.get("watchlist") or []
    decision_block = signal.get("decision_block") or {}

    parts = ['<section style="margin:0 0 32px 0;padding:0 0 26px 0;border-bottom:1px solid #e2e8f0;">']
    parts.append(
        f'<h2 style="font-size:28px;line-height:1.32;color:#0f172a;margin:0 0 14px 0;font-weight:800;">'
        f"{idx}. {title}</h2>"
    )
    if hook:
        parts.append(
            '<blockquote style="margin:0 0 18px 0;padding:12px 14px;border-left:3px solid #0ea5e9;'
            'background:#f0f9ff;border-radius:8px;">'
            f'<p style="margin:0;font-size:15px;line-height:1.65;color:#0f172a;">{hook}</p></blockquote>'
        )
    if what_happened:
        parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">What happened</h3>')
        parts.append(f'<p style="font-size:16px;line-height:1.75;color:#1e293b;margin:0;">{what_happened}</p>')
    if why_it_matters:
        parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">Why it matters</h3>')
        parts.append(f'<p style="font-size:16px;line-height:1.75;color:#1e293b;margin:0;">{why_it_matters}</p>')
    if korea_implication:
        parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">Korea implication</h3>')
        parts.append(f'<p style="font-size:16px;line-height:1.75;color:#1e293b;margin:0;">{korea_implication}</p>')
    if risk_counterargument:
        parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">Risk / Counterargument</h3>')
        parts.append(f'<p style="font-size:16px;line-height:1.75;color:#1e293b;margin:0;">{risk_counterargument}</p>')

    if watchlist:
        items = []
        for item in watchlist:
            if not isinstance(item, dict):
                continue
            main = _esc(item.get("item"))
            trigger = _esc(item.get("trigger"))
            if main:
                items.append(f"<li>{main} (트리거: {trigger})</li>" if trigger else f"<li>{main}</li>")
        if items:
            parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">Watchlist</h3>')
            parts.append(
                '<ul style="margin:0;padding-left:20px;color:#1e293b;font-size:15px;line-height:1.75;">'
                + "".join(items)
                + "</ul>"
            )

    if decision_block:
        what_to_track = _esc(decision_block.get("what_to_track"))
        who_benefits = _esc(decision_block.get("who_benefits"))
        who_exposed = _esc(decision_block.get("who_is_exposed"))
        lines = []
        if what_to_track:
            lines.append(f"<li>What to track: {what_to_track}</li>")
        if who_benefits:
            lines.append(f"<li>Who benefits: {who_benefits}</li>")
        if who_exposed:
            lines.append(f"<li>Who is exposed: {who_exposed}</li>")
        if lines:
            parts.append('<h3 style="font-size:18px;line-height:1.4;color:#0f172a;margin:18px 0 8px 0;">Action summary</h3>')
            parts.append(
                '<ul style="margin:0;padding-left:20px;color:#1e293b;font-size:15px;line-height:1.75;">'
                + "".join(lines)
                + "</ul>"
            )
    parts.append("</section>")
    return "\n".join(parts)


def build_maily_html(
    issue_number: int,
    issue_date: str,
    signals: list[dict],
    image_inputs: list[str] | None = None,
) -> tuple[str, list[str]]:
    image_inputs = image_inputs or []
    signal_blocks = "\n<hr/>\n".join(
        _render_signal_html(signal, idx) for idx, signal in enumerate(signals, start=1)
    )
    gallery, skipped_images = _render_image_gallery(image_inputs)
    gallery_block = f"{gallery}\n" if gallery else ""
    html_body = (
        '<article style="max-width:760px;margin:0 auto;padding:28px 20px;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,\'Noto Sans KR\',sans-serif;'
        'color:#0f172a;background:#ffffff;">'
        f'<h1 style="font-size:42px;line-height:1.16;letter-spacing:-0.02em;'
        'margin:0 0 16px 0;color:#0b132f;">Physical AI Weekly '
        f"#{issue_number:03d}</h1>\n"
        f'<p style="margin:0 0 20px 0;font-size:14px;line-height:1.7;color:#64748b;">'
        f"<strong>Issue Date:</strong> {html.escape(issue_date)} · "
        "<strong>Platform:</strong> Maily · "
        "<strong>Format:</strong> Free Weekly Issue</p>\n"
        '<hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 24px 0;"/>\n'
        f"{gallery_block}"
        f"{signal_blocks}\n"
        '<hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0 12px 0;"/>\n'
        '<h3 style="font-size:16px;line-height:1.4;margin:0 0 6px 0;color:#0f172a;">Disclaimer</h3>\n'
        '<p style="font-size:14px;line-height:1.7;margin:0;color:#64748b;">'
        "본 콘텐츠는 정보 제공 목적이며 투자 자문이 아닙니다.</p>\n"
        "</article>"
    )
    return html_body, skipped_images


def upsert_issue_to_db(
    *,
    issue_number: int,
    issue_date: str,
    signal_ids: list[int],
    free_body: str,
    status: str,
    public_url: str = "",
) -> int:
    title = f"Physical AI Weekly #{issue_number:03d}"
    existing = execute_query(
        """
        SELECT id
        FROM newsletter_issues
        WHERE title = %s
          AND LOWER(COALESCE(publishing_platform, '')) = 'maily'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (title,),
        fetch=True,
    )

    params = (
        issue_date,
        status,
        free_body,
        json.dumps(signal_ids),
        "maily",
        public_url,
    )

    if existing:
        result = execute_query(
            """
            UPDATE newsletter_issues
            SET issue_date = %s,
                status = %s,
                free_body = %s,
                source_signal_ids = %s,
                publishing_platform = %s,
                public_url = %s,
                published_at = CASE WHEN %s = 'published' THEN NOW() ELSE published_at END,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id
            """,
            (*params, status, existing[0]["id"]),
            fetch=True,
        )
        return int(result[0]["id"])

    result = execute_query(
        """
        INSERT INTO newsletter_issues
            (issue_date, title, status, free_body, source_signal_ids, publishing_platform, public_url, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CASE WHEN %s = 'published' THEN NOW() ELSE NULL END)
        RETURNING id
        """,
        (
            issue_date,
            title,
            status,
            free_body,
            json.dumps(signal_ids),
            "maily",
            public_url,
            status,
        ),
        fetch=True,
    )
    if not result:
        raise RuntimeError("newsletter_issues insert failed")
    return int(result[0]["id"])


def _write_artifacts(
    *,
    output_dir: Path,
    issue_number: int,
    issue_date: str,
    issue_id: int,
    signal_ids: list[int],
    markdown: str,
    html_body: str,
    image_inputs: list[str],
    skipped_images: list[str],
) -> tuple[Path, Path, Path]:
    _ensure_dir(output_dir)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"issue-{issue_number:03d}-{issue_date}-{ts}"
    md_path = output_dir / f"{stem}.md"
    html_path = output_dir / f"{stem}.html"
    meta_path = output_dir / f"{stem}.json"

    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_body, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "issue_id": issue_id,
                "issue_number": issue_number,
                "issue_date": issue_date,
                "publishing_platform": "maily",
                "signal_ids": signal_ids,
                "image_inputs": image_inputs,
                "skipped_images": skipped_images,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return md_path, html_path, meta_path


def _assert_publish_gates(issue_id: int) -> None:
    errors: list[str] = []
    if not check_vp_review_approved(issue_id):
        errors.append("VP review 미승인")
    if not has_qa_clear(issue_id):
        errors.append("qa_clear 미승인")
    if not _latest_gate_approved("newsletter_issue", issue_id, "legal_review_approve"):
        errors.append("legal_review_approve 미확인")
    if not _latest_gate_approved("newsletter_issue", issue_id, "red_team_clear"):
        errors.append("red_team_clear 미확인")
    if errors:
        raise RuntimeError("Maily publish gate 미통과: " + ", ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare weekly issue package for Maily")
    parser.add_argument("--issue", type=int, required=True, help="issue number (e.g. 5)")
    parser.add_argument("--date", type=str, default=str(date.today()), help="issue date YYYY-MM-DD")
    parser.add_argument("--signal-ids", type=int, nargs="+", help="specific refined_output IDs")
    parser.add_argument("--top", type=int, default=TOP_SIGNALS_LIMIT, help="top-N signal selection")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help="artifact output directory (default: runtime/maily)",
    )
    parser.add_argument(
        "--mark-published",
        action="store_true",
        help="after external publish, enforce gates and mark issue status=published",
    )
    parser.add_argument("--public-url", type=str, default="", help="public URL for published issue")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="image/chart path or URL (repeatable). local file is embedded as data URI in html.",
    )
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id=f"maily-{args.issue:03d}")

    rows = get_signals_by_ids(args.signal_ids) if args.signal_ids else get_top_signals(args.top)
    if not rows:
        raise RuntimeError("발행할 signal이 없습니다. 파이프라인 실행 후 재시도하세요.")

    signals = [parse_body(row) for row in rows]
    signal_ids = [int(row["id"]) for row in rows]
    markdown = build_maily_markdown(args.issue, args.date, signals)
    html_body, skipped_images = build_maily_html(args.issue, args.date, signals, image_inputs=args.image)

    issue_id = upsert_issue_to_db(
        issue_number=args.issue,
        issue_date=args.date,
        signal_ids=signal_ids,
        free_body=markdown,
        status="draft",
    )

    md_path, html_path, meta_path = _write_artifacts(
        output_dir=args.output_dir,
        issue_number=args.issue,
        issue_date=args.date,
        issue_id=issue_id,
        signal_ids=signal_ids,
        markdown=markdown,
        html_body=html_body,
        image_inputs=args.image,
        skipped_images=skipped_images,
    )
    logger.info(f"Maily issue package generated: issue_id={issue_id} markdown={md_path} html={html_path}")
    if skipped_images:
        logger.warning(f"Maily image inputs skipped (not found/invalid): {skipped_images}")

    if args.mark_published:
        if not args.public_url.strip():
            raise RuntimeError("--mark-published 사용 시 --public-url이 필요합니다.")
        _assert_publish_gates(issue_id)
        issue_id = upsert_issue_to_db(
            issue_number=args.issue,
            issue_date=args.date,
            signal_ids=signal_ids,
            free_body=markdown,
            status="published",
            public_url=args.public_url.strip(),
        )
        logger.info(f"Maily issue marked published: issue_id={issue_id} url={args.public_url.strip()}")

    print(json.dumps(
        {
            "issue_id": issue_id,
            "issue_number": args.issue,
            "platform": "maily",
            "status": "published" if args.mark_published else "draft",
            "markdown_path": str(md_path),
            "html_path": str(html_path),
            "metadata_path": str(meta_path),
            "signal_ids": signal_ids,
            "image_inputs": args.image,
            "skipped_images": skipped_images,
            "next_step": "Open html_path in browser, copy rendered content, and paste into Maily editor."
            if not args.mark_published
            else "Issue status recorded as published.",
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
