import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import execute_query

CLUSTER_LABELS = {
    "parenting_ai": "보호자 · 자녀 AI",
    "worker_ai": "직장인 AI",
    "military_ai": "군 복무 · 입대 준비",
    "career_major": "진로 · 전공 선택",
    "digital_dependence": "디지털 의존 · 스마트폰 갈등",
    "general_ai_education": "일반 AI 교육",
    "embodiment_robotics": "로봇 본체 · 자동화",
    "compute_models": "반도체 · 연산 칩",
    "memory_packaging": "메모리 · 패키징",
    "networking_optics": "네트워킹 · 광통신",
    "power_cooling": "전력 · 냉각",
    "simulation_software": "시뮬레이션 · 산업 소프트웨어",
    "warehouse_deployment": "물류 · 배포",
    "edge_realtime": "엣지 · 실시간 추론",
    "general_physical_ai": "일반 Physical AI",
}


def _label(cluster: str) -> str:
    return CLUSTER_LABELS.get(cluster, cluster.replace("_", " "))


def _cluster_rows(domain: str, limit: int = 5) -> list[dict[str, Any]]:
    where = "coalesce(raw_data->>'domain', 'physical_ai') = %s" if domain == "physical_ai" else "coalesce(domain, raw_data->>'domain', '') = %s"
    return execute_query(
        "SELECT raw_data->>'topic_cluster' AS cluster, count(*) AS cnt, max(ingested_at) AS last_at "
        "FROM raw_signals "
        f"WHERE {where} AND coalesce(raw_data->>'topic_cluster', '') <> '' "
        "GROUP BY raw_data->>'topic_cluster' "
        "ORDER BY count(*) DESC, max(ingested_at) DESC LIMIT %s",
        (domain, limit),
        fetch=True,
    )


def _push_rows(domain: str, limit: int = 20) -> list[dict[str, Any]]:
    where = "coalesce(raw_data->>'domain', 'physical_ai') = %s" if domain == "physical_ai" else "coalesce(domain, raw_data->>'domain', '') = %s"
    rows = execute_query(
        "SELECT raw_data->>'topic_cluster' AS cluster, raw_data->>'title' AS title, raw_data->>'url' AS url, "
        "raw_data->>'query' AS query, source, ingested_at "
        "FROM raw_signals "
        f"WHERE {where} AND coalesce(raw_data->>'topic_cluster', '') <> '' "
        "ORDER BY ingested_at DESC LIMIT %s",
        (domain, limit),
        fetch=True,
    )
    def is_kr_or_en(value: str) -> bool:
        return bool(re.search(r"[가-힣]{2,}", value) or re.search(r"[A-Za-z]{4,}", value))

    picks: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        cluster = str(row.get("cluster") or "")
        title = str(row.get("title") or "")
        if not cluster or not title:
            continue
        if domain == "edu_consulting" and not is_kr_or_en(title):
            continue
        if domain == "edu_consulting" and cluster == "general_ai_education":
            continue
        if domain == "physical_ai" and cluster == "general_physical_ai":
            continue
        if domain == "physical_ai" and any(term in title for term in ["공원현황", "시설현황", "민원", "행정", "통계연보", "가구에너지패널조사"]):
            continue
        key = (cluster, title)
        if key in seen:
            continue
        seen.add(key)
        picks.append(row)
        if len(picks) >= 5:
            break
    return picks


def _build_text() -> str:
    lines = ["*자료수집 Push 후보 브리프*", f"- generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    for domain, label in [("physical_ai", "기술"), ("edu_consulting", "교육")]:
        lines.append(f"\n*{label}*")
        clusters = _cluster_rows(domain, limit=5)
        if clusters:
            lines.append("- top clusters:")
            for row in clusters:
                lines.append(f"  - {_label(str(row.get('cluster') or ''))}: {int(row.get('cnt') or 0)}건")
        pushes = _push_rows(domain, limit=20)
        if pushes:
            lines.append("- push candidates:")
            for row in pushes[:3]:
                cluster = _label(str(row.get("cluster") or ""))
                title = str(row.get("title") or "")[:110]
                lines.append(f"  - [{cluster}] {title}")
        else:
            lines.append("- push candidates: none")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize topic-cluster push candidates for education and physical AI.")
    parser.add_argument("--to-slack", action="store_true")
    parser.add_argument("--route", default="exec_president_decisions")
    args = parser.parse_args()

    text = _build_text()
    print(text)
    if args.to_slack:
        from adapters.content.slack_router import send_slack_route

        send_slack_route(args.route, {"text": text})


if __name__ == "__main__":
    main()
