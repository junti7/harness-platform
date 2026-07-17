#!/usr/bin/env python3
"""자료 수집 주기 성능검사 + 자동복구 + Slack 에스컬레이션.

launchd로 주기 실행(기본 6시간)되어 수집 파이프라인의 건강도를 점검하고,
문제가 감지되면 스스로 복구를 시도한 뒤, 끝내 복구되지 않으면 Slack으로 보고한다.

단계
  1) 활성 소스별 건강도 점검: liveness, 피드 entries(RSS류), 최신 적재 경과시간
  2) 도메인 freshness: physical_ai / edu_consulting 최근 적재 경과
  3) 자동복구: 적재 지연(DEGRADED) 또는 도메인 정체 시 해당 수집기를 재실행 후 재점검
       - physical_ai → adapters.content.collector.collect()
       - edu_consulting → scripts/run_edu_deep_research.py --sources rss,arxiv,scholar
  4) 에스컬레이션: 피드 죽음/liveness 실패(DOWN) 또는 복구 실패가 임계 횟수 이상
       지속되면 source_catalog.failure_count를 올리고 Slack(ops_incidents)에 보고
  5) 회복 시 failure_count 리셋, 매 실행 상태를 JSON으로 저장

이 스크립트는 LLM/Anthropic에 의존하지 않으며, 안전하게 반복 실행 가능하다.

  python scripts/collection_health_check.py            # 점검+자동복구+(필요시)Slack
  python scripts/collection_health_check.py --no-recover  # 점검만(복구 안 함)
  python scripts/collection_health_check.py --dry-run     # Slack 발송 안 함
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
# launchd/production environment must remain authoritative; .env only fills gaps.
load_dotenv(PROJECT_ROOT / ".env", override=False)

import os  # noqa: E402
import feedparser  # noqa: E402

from core.database import execute_query  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402

# 임계값 (env로 조정 가능)
STALE_HOURS = float(os.getenv("COLLECTION_STALE_HOURS", "30"))          # 이 시간 넘게 신규 적재 없으면 정체
EDU_STALE_HOURS = float(os.getenv("COLLECTION_EDU_STALE_HOURS", "30"))  # edu 채널 정체 기준
FAIL_THRESHOLD = int(os.getenv("COLLECTION_FAIL_THRESHOLD", "2"))       # 연속 N회 실패 시 Slack
RECOVER_TIMEOUT_S = int(os.getenv("COLLECTION_RECOVER_TIMEOUT_S", "600"))
STATUS_PATH = PROJECT_ROOT / "data" / "collection_health_status.json"
# edu 핵심 채널만 건강 대상으로 본다. 간헐 수집되는 youtube 보조 채널
# (Khan/Edutopia/TED 등)은 매일 돌지 않으므로 stale이 정상 → 오탐 방지 위해 제외.
EDU_CORE_CHANNELS = ("Naver_블로그", "Naver_카페글", "Naver_지식iN", "youtube_topic_search")


def _hours_ago(ts) -> float | None:
    if not ts:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except Exception:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0


def _recency_by_source() -> dict[str, dict]:
    rows = execute_query(
        "SELECT source, COUNT(*) n, MAX(ingested_at) last_at FROM raw_signals GROUP BY source",
        fetch=True,
    ) or []
    out = {}
    for r in rows:
        out[r["source"]] = {"count": int(r["n"]), "hours": _hours_ago(r["last_at"])}
    return out


def _is_feed(src: dict) -> bool:
    url = (src.get("url") or src.get("base_url") or "").lower()
    st = (src.get("source_type") or "").lower()
    return st == "rss" or any(k in url for k in ("rss", "feed", "arxiv", "/api/query", ".xml"))


def _assess_physical(logger: HarnessLogger, recency: dict[str, dict]) -> list[dict]:
    """physical_ai 활성 소스별 상태 평가."""
    from adapters.content.collector import get_active_sources, check_liveness

    results = []
    for src in get_active_sources(logger):
        name = src.get("name") or src.get("source_name") or "?"
        url = src.get("url") or src.get("base_url") or ""
        rec = recency.get(name, {})
        hours = rec.get("hours")
        status, reason = "ok", ""

        if _is_feed(src) and url:
            try:
                live = check_liveness(url)
            except Exception as e:
                live = False
                reason = f"liveness 예외: {e}"
            if not live:
                status, reason = "down", reason or "liveness 실패(사이트 미응답)"
            else:
                try:
                    entries = len(feedparser.parse(url).entries)
                except Exception as e:
                    entries = -1
                    reason = f"피드 파싱 예외: {e}"
                if entries == 0:
                    # 피드가 비었는데 적재도 오래됐으면 죽은 피드(arXiv RSS형 장애)
                    if hours is None or hours > STALE_HOURS:
                        status, reason = "down", "피드 entries=0 (죽은 피드 의심)"
                    # 피드 0이지만 최근 적재 있으면 일시적 — ok로 둠
                elif hours is None:
                    status, reason = "degraded", "수집 이력 없음(피드는 정상)"
                elif hours > STALE_HOURS:
                    status, reason = "degraded", f"적재 지연 {hours:.0f}h (피드는 정상)"
        else:
            # 비(非)피드 소스: 최신성만으로 판단
            if hours is None:
                status, reason = "degraded", "수집 이력 없음"
            elif hours > STALE_HOURS:
                status, reason = "degraded", f"적재 지연 {hours:.0f}h"

        results.append({
            "domain": "physical_ai", "source": name, "status": status,
            "reason": reason, "hours_ago": round(hours, 1) if hours is not None else None,
            "enabled": bool(src.get("enabled", True)),
        })
    return results


def _assess_edu(recency: dict[str, dict]) -> list[dict]:
    """edu 핵심 채널(Naver 3종 + youtube_topic_search)만 최신성 평가."""
    results = []
    for name in EDU_CORE_CHANNELS:
        hours = recency.get(name, {}).get("hours")
        if hours is None:
            status, reason = "degraded", "수집 이력 없음"
        elif hours > EDU_STALE_HOURS:
            status, reason = "degraded", f"적재 지연 {hours:.0f}h"
        else:
            status, reason = "ok", ""
        results.append({
            "domain": "edu_consulting", "source": name, "status": status,
            "reason": reason, "hours_ago": round(hours, 1) if hours is not None else None,
            "enabled": True,
        })
    return results


def _recover(domain: str, logger: HarnessLogger) -> str:
    """도메인별 수집기 재실행(자동복구)."""
    py = str(PROJECT_ROOT / ".venv" / "bin" / "python3")
    if not Path(py).exists():
        py = sys.executable
    if domain == "physical_ai":
        cmd = [py, "-c", "from adapters.content.collector import collect; collect(correlation_id='health-recover')"]
    else:  # edu_consulting
        cmd = [py, str(PROJECT_ROOT / "scripts" / "run_edu_deep_research.py"),
               "--sources", "rss,arxiv,scholar"]
    logger.info(f"[복구] {domain} 수집기 재실행: {' '.join(cmd[-2:])}")
    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                       timeout=RECOVER_TIMEOUT_S, check=False)
        return "executed"
    except subprocess.TimeoutExpired:
        logger.warning(f"[복구] {domain} 재실행 타임아웃({RECOVER_TIMEOUT_S}s)")
        return "timeout"
    except Exception as e:
        logger.warning(f"[복구] {domain} 재실행 예외: {e}")
        return f"error:{e}"


def _bump_failure(source: str, delta: int = 1) -> int:
    row = execute_query(
        "UPDATE source_catalog SET failure_count = COALESCE(failure_count,0) + %s, updated_at = NOW() "
        "WHERE source_name = %s RETURNING failure_count",
        (delta, source), fetch=True,
    )
    return int(row[0]["failure_count"]) if row else delta


def _reset_failure(source: str) -> None:
    execute_query(
        "UPDATE source_catalog SET failure_count = 0, updated_at = NOW() "
        "WHERE source_name = %s AND COALESCE(failure_count,0) <> 0",
        (source,),
    )


def _send_slack(escalations: list[dict], summary: dict, logger: HarnessLogger) -> None:
    from adapters.content.slack_router import send_slack_route

    lines = [f":rotating_light: *[수집 장애]* 자동복구 실패 {len(escalations)}개 소스 — 수동 점검 필요\n"]
    for e in escalations:
        lines.append(f"• `{e['source']}` ({e['domain']}) — {e['reason']} | 연속실패 {e['failure_count']}회")
    lines.append(
        f"\n점검 요약: OK {summary['ok']} / DEGRADED {summary['degraded']} / DOWN {summary['down']} "
        f"(복구시도 {summary['recovered_attempts']}회)"
    )
    text = "\n".join(lines)
    payload = {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "context", "elements": [
                {"type": "mrkdwn", "text": f"collection_health_check @ {datetime.now().isoformat(timespec='seconds')}"},
            ]},
        ],
    }
    try:
        send_slack_route("ops_incidents", payload)
        logger.info(f"[Slack] ops_incidents 보고 발송 ({len(escalations)}건)")
    except Exception as e:
        logger.error(f"[Slack] 발송 실패: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="자료 수집 성능검사 + 자동복구 + Slack")
    ap.add_argument("--no-recover", action="store_true", help="복구 시도 안 함(점검만)")
    ap.add_argument("--dry-run", action="store_true", help="Slack 발송 안 함")
    args = ap.parse_args()

    logger = HarnessLogger(tier=1, correlation_id="collection-health")
    logger.info("=== 수집 성능검사 시작 ===")

    recency = _recency_by_source()
    assessed = _assess_physical(logger, recency) + _assess_edu(recency)

    bad = [a for a in assessed if a["status"] in ("degraded", "down")]
    recovered_attempts = 0

    if bad and not args.no_recover:
        # 문제 도메인만 복구 실행
        for domain in sorted({a["domain"] for a in bad}):
            _recover(domain, logger)
            recovered_attempts += 1
        # 복구 후 재평가
        recency = _recency_by_source()
        assessed = _assess_physical(logger, recency) + _assess_edu(recency)

    # 도메인 전체 정체 여부(모든 소스가 STALE_HOURS 넘게 신규 없음) — 진짜 파이프라인 장애
    domain_stalled = {}
    for dom in ("physical_ai", "edu_consulting"):
        hrs = [a["hours_ago"] for a in assessed if a["domain"] == dom and a["hours_ago"] is not None]
        # 가장 최근 적재가 STALE_HOURS를 넘으면 그 도메인은 통째로 멈춘 것
        domain_stalled[dom] = (not hrs) or (min(hrs) > STALE_HOURS)

    # 직전 실행의 연속 실패 카운트(JSON 영속 — edu 채널처럼 source_catalog에 없는 소스도 추적)
    prev_fail: dict[str, int] = {}
    try:
        prev = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        prev_fail = {s["source"]: int(s.get("failure_count") or 0) for s in prev.get("sources", [])}
    except Exception:
        prev_fail = {}

    # 에스컬레이션은 "진짜 복구 불가"만: ① DOWN(죽은 피드/미응답) ② 도메인 전체 정체.
    # DEGRADED인데 도메인은 신선(다른 소스가 수집 중, 교차게재 dedup 등)이면 오탐이라 제외.
    escalations = []
    for a in assessed:
        real_problem = a["status"] == "down" or (
            a["status"] == "degraded" and domain_stalled.get(a["domain"])
        )
        if not real_problem:
            a["failure_count"] = 0
            _reset_failure(a["source"])  # 카탈로그 소스면 0으로 리셋
            continue
        fc = prev_fail.get(a["source"], 0) + 1
        a["failure_count"] = fc
        _bump_failure(a["source"])  # 카탈로그 소스면 대시보드용으로도 누적
        if fc >= FAIL_THRESHOLD:
            escalations.append(a)

    summary = {
        "ok": sum(1 for a in assessed if a["status"] == "ok"),
        "degraded": sum(1 for a in assessed if a["status"] == "degraded"),
        "down": sum(1 for a in assessed if a["status"] == "down"),
        "recovered_attempts": recovered_attempts,
        "escalations": len(escalations),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    # 상태 저장
    try:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(
            {"summary": summary, "sources": assessed}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"상태 저장 실패: {e}")

    logger.info(f"점검 결과: OK {summary['ok']} / DEGRADED {summary['degraded']} / "
                f"DOWN {summary['down']} / 에스컬레이션 {summary['escalations']}")

    if escalations and not args.dry_run:
        _send_slack(escalations, summary, logger)

    logger.info("=== 수집 성능검사 종료 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
