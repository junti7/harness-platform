# 교육 상담사 근거 신선도 루프 (Evidence Freshness Loop)

작성일: 2026-06-03
목적: 부모 상담 앱(`/api/edu/diagnose`)이 **같은 말만 반복하지 않고** 최신 트렌드를 계속 반영하도록 하는 자동 갱신 구조.

## 문제

상담사는 대화 중 실제 근거(연구·사례·발언)를 자연스럽게 흘려 "진짜 사람" 신뢰감을 만든다.
이 근거는 `data/edu_research/evidence_bank.json`에서 프롬프트로 주입(`__EVIDENCE__`)된다.
초기 뱅크는 2026-06-01에 **수작업**으로 한 번 만든 정적 파일이라, 방치하면 고객이 금세 "맨날 같은 소리"임을 알아챈다.

## 해결 — 3단

### 1. 에버그린 앵커 (`data/edu_research/evidence_anchors.json`)
시간이 지나도 낡지 않는 랜드마크 근거를 사람이 큐레이션한 정본.
- 부모 초안(2026-06)의 강력한 실제 사례: Haidt(WEF) "지름길" 발언, 1851 유치원 금지, 1930s 모험 놀이터, 2026 코펜하겐 Common Sense Summit
- 2026-06-01 수작업 정제한 ERIC/Semantic Scholar/Reddit 연구 12건
- 모두 `evergreen: true` — 만료되지 않음.

### 2. 파이프라인 신선분 (자동)
`scripts/refresh_edu_evidence_bank.py`가 DB의 최신 `edu_consulting` `refined_outputs`(Tier 3 산출물)를
구어체 cite로 변환해 뱅크에 합친다. **(현재 9건 채워짐 — 2026-06-03 기준)**
- recency window(기본 45일) — 오래된 자동 항목은 자동 탈락.
- cite 추출 우선순위: `parent_insight.what_changed`(실제 인사이트) → `action_now`(구체 행동)
  → `hook` → `final_title`. **알맹이 없는 일반 공감문("걱정되시죠")과 메타 발화("원문은…")는 제외**,
  마크다운 서식·소제목·해시태그 제거.
- 출처 라벨은 `raw_data`의 실제 영상 제목·채널로 구성(예: `YouTube · Parent Squad — '…'`),
  HTML 엔티티 디코드. 수치를 새로 지어내지 않음.
- 첫머리 18자 유사 cite는 중복 제외, `provenance: "pipeline"` 태그 → 상담 시 **우선 노출**.

### 3. 반복 방지 전달 (`_load_evidence`)
매 대화마다 최신분을 먼저 채우고 앵커/관찰을 섞어 **회전 샘플링**(최대 8개).
같은 첫 인용이 고정되지 않게 순서까지 셔플.

## 자동 실행

별도 cron 없음. `run_pipeline.py` 말미에서 매 파이프라인 실행(Mac Mini 일 1회)마다
`build_bank()`를 호출해 `evidence_bank.json`을 재생성한다. (실패해도 파이프라인 성공에 무영향)

수동 실행:
```bash
python scripts/refresh_edu_evidence_bank.py            # 재생성
python scripts/refresh_edu_evidence_bank.py --dry-run  # 미리보기
python scripts/refresh_edu_evidence_bank.py --window-days 30 --max-fresh 15
```

## 흐름 요약

```
Tier1 수집 → Tier2 필터 → Tier3 정제(edu_consulting) → refined_outputs(DB)
                                                            │
                              evidence_anchors.json(앵커) ──┤
                                                            ▼
                              refresh_edu_evidence_bank.py → evidence_bank.json
                                                            ▼
                              _load_evidence(회전 샘플) → 상담사 프롬프트 __EVIDENCE__
                                                            ▼
                              고객 대화에서 최신 근거 자연 인용
```

## edu 전용 정제 러너

기본 `refine()`은 score DESC라 physical_ai(0.8대)가 배치를 먼저 채워 edu(0.1~0.4)가 정제되지 않는다.
edu만 골라 정제하려면:
```bash
python scripts/run_edu_tier3.py --limit 10            # 상위 10건 정제 후 뱅크 자동 갱신
python scripts/run_edu_tier3.py --limit 5 --min-score 0.2
```
정제가 끝나면 자동으로 `refresh_edu_evidence_bank`를 호출해 뱅크를 갱신한다.

## 더 신선하게 하려면 (다음 단계)

- `edu_consulting` 필터 통과분은 663건 — 현재 8건만 Tier 3 정제됨. 나머지를 점진 정제하면 신선분이 더 쌓인다.
- 수집 소스가 현재 YouTube 위주 → RSS/논문/뉴스 소스를 늘리면 cite 다양성이 올라간다.
- 신선분이 충분히 쌓이면 window/max 파라미터를 조여 최신성을 더 높일 수 있다.
- 장기적으로 동일 고객 재방문 시 직전 대화에서 쓴 cite를 제외하는 per-case 중복 회피도 가능.
