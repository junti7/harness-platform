#!/usr/bin/env python3
"""
Physical AI DEEP RESEARCH 수집 (Wave 2, 2026-06-09)

physical_ai 도메인은 그동안 RSS(arXiv 카테고리 피드/IEEE/MIT/TechCrunch) + data.go.kr
API만 수집했다. edu 도메인이 이미 보유한 학술(semantic scholar/openalex)·커뮤니티
(hackernews)·키워드 arXiv 콜렉터를 physical_ai 주제로 재사용해 기술 도메인의 수집
다양성을 끌어올린다. 이 수집은 트레이딩 유니버스(arXiv/학술 evidence) 강화에도 직결된다.

설계 원칙:
- 검증된 edu 콜렉터(run_edu_deep_research)를 **무수정 재사용**한다. 모듈 전역 DOMAIN을
  'physical_ai'로 오버라이드하면 save_signal이 physical_ai로 적재한다.
- 키 불필요 공개 API만 사용(openalex/hackernews/arXiv export). semantic scholar는 키
  있으면 사용. 신규 ToS 리스크 = arXiv/openalex와 동일 클래스(저위험).
- 채널 상한으로 정제 백로그 폭주 방지(수집 ≤ 정제 capacity 원칙).

게이트: 이 러너의 스케줄 활성화는 red_team_clear + legal_review_approve + pre_mortem
통과 후에만 한다(데이터 수집 정책 변경). 본 파일은 수동/dry-run 실행만으로는 게이트 불요.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.run_edu_deep_research as R  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402

DOMAIN = "physical_ai"

# physical_ai 주제 쿼리 — 핸드오프 테마(embodiment/memory·packaging/networking·optics/
# power·cooling/simulation/warehouse) + 반도체·가속기·휴머노이드·자율주행
PHYS_ACADEMIC_QUERIES = [
    "humanoid robot learning",
    "embodied AI manipulation policy",
    "robot foundation model",
    "vision language action model robotics",
    "dexterous manipulation reinforcement learning",
    "legged locomotion control",
    "sim-to-real transfer robotics",
    "high bandwidth memory packaging",
    "chiplet heterogeneous integration",
    "silicon photonics interconnect datacenter",
    "AI accelerator dataflow architecture",
    "datacenter liquid cooling thermal",
    "autonomous driving end-to-end perception",
    "warehouse automation mobile robot",
]

PHYS_HN_QUERIES = [
    "humanoid robot",
    "robotics foundation model",
    "embodied AI",
    "semiconductor HBM",
    "AI accelerator GPU",
    "silicon photonics",
    "datacenter cooling power",
    "autonomous driving",
    "warehouse robotics",
]

# 카테고리 RSS(cs.RO/cs.AI/cs.LG)로 안 잡히는 테마 키워드 arXiv 검색
PHYS_ARXIV_QUERIES = [
    "all:humanoid+robot",
    "all:vision+language+action+manipulation",
    "all:high+bandwidth+memory",
    "all:silicon+photonics+interconnect",
    "all:liquid+cooling+datacenter",
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Physical AI DEEP RESEARCH 수집")
    ap.add_argument("--sources", default="scholar,openalex,hackernews,arxiv",
                    help="scholar,openalex,hackernews,arxiv (콤마구분)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    # 모듈 전역 오버라이드 — 검증된 콜렉터를 physical_ai로 재사용
    R.DOMAIN = DOMAIN
    enabled = {s.strip() for s in args.sources.split(",")}
    logger = HarnessLogger(tier=1, correlation_id="physical-deep-research")
    tracker = R.SaturationTracker()
    dry = args.dry_run
    results: dict[str, dict] = {}

    logger.info(f"=== Physical AI DEEP RESEARCH 시작 | sources={sorted(enabled)} | dry_run={dry} ===")

    if "scholar" in enabled:
        # semantic scholar는 모듈 SCHOLAR_QUERIES_EN_ONLY 전역을 사용 → physical 쿼리로 교체
        R.SCHOLAR_QUERIES_EN_ONLY = PHYS_ACADEMIC_QUERIES
        results["scholar"] = R.collect_semantic_scholar(logger, tracker, dry, scholar_mode="en_only")

    if "openalex" in enabled:
        results["openalex"] = R.collect_openalex(PHYS_ACADEMIC_QUERIES, logger, tracker, dry)

    if "hackernews" in enabled:
        results["hackernews"] = R.collect_hackernews(PHYS_HN_QUERIES, logger, tracker, dry)

    if "arxiv" in enabled:
        R.ARXIV_QUERIES = PHYS_ARXIV_QUERIES
        results["arxiv"] = R.collect_arxiv(logger, tracker, dry)

    total = sum(r.get("new", 0) for r in results.values())
    logger.info(f"=== Physical AI DEEP RESEARCH 완료 | 총 신규 {total}개 ===")
    for k, v in results.items():
        logger.info(f"  {k}: {v}")
    if dry:
        logger.info("[dry-run] DB 미저장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
