# Red Team 영속 기록 — Edu Query Engine & Data Analysis Agent 개발 계획서

- 일자: 2026-06-14
- 대상 문서: `docs/education/EDU_QUERY_ENGINE_DEV_PLAN.md`
- 저자: Claude (self-review 불가)
- 검토자(비저자): Gemini, Codex — `scripts/redteam_review.sh`(read-only 강제)
- 결과: **✅ red_team_clear** (r8에서 Gemini + Codex 동일 최종본 clear)
- AGENTS.md 요건 충족: 모델명 + context path + round별 verdict 기록.

## 라운드별 verdict

| R | context snapshot | Gemini | Codex | Codex 주요 지적 (전부 반영) |
|---|---|---|---|---|
| r1 | /tmp/edu_query_plan.md | clear (MINOR1) | **block** | PII 직접노출 경로(edu_cases LLM 조회)·기존 코퍼스 오염(refined_outputs→evidence_index)·신구 RAG crosswalk 부재·행단위 저작권 메타 부재·비용지표 단일(즉답률)·robust 임계값 주관·resolver 테이블 화이트리스트 불충분·인덱스 약함(한국어 FTS)·api_cost_log tier/token 컬럼 부재·`red_team` shorthand (BLOCKER4/MAJOR6/MINOR3) |
| r2 | /tmp/edu_query_plan_r2.md | clear | block | r1 10건 반영 확인. 잔여: derived/generated 이원화·§8 처리시간 공란·§7.1 회귀 정량화 (MAJOR2/MINOR1) |
| r3 | /tmp/edu_query_plan_r3.md | clear | block | §6.1 derived 1줄 (MAJOR1) |
| r4 | /tmp/edu_query_plan_r4.md | clear | block | §1 SoT 단락 derived 1줄 |
| r5 | /tmp/edu_query_plan_r5.md | clear | block | §3.2 한글 provenance 라벨 불일치 |
| r6 | /tmp/edu_query_plan_r6.md | clear | block | §5 스키마 CHECK 제약 부재(DB enum 강제 누락) |
| r7 | /tmp/edu_query_plan_r7.md | clear | block | dead_letter_queue/pipeline_runs 재사용 미명시(BLOCKER)·servable predicate 미고정(MAJOR)·source_url nullable 불일치(MINOR) |
| **r8** | /tmp/edu_query_plan_r8.md | **clear** | **clear** | r7 3건 폐쇄 확인. 잔여 비차단 MINOR: §2 quality_score 임계값 P3 baseline 후 확정 |

## non-negotiable finding 처리 (단순 다수결 불가 항목)

CLAUDE.md상 factual/legal/regulatory/PII/저작권은 2-of-N 다수결로 넘기지 않는다. 해당 r1 지적은 전부 구조적으로 반영:
- **PII**: §2 데이터 2등급 분리 + LLM이 테이블명 생성 불가(고정 resolver enum) + case는 인증 세션 `authed_case_id` 소유권 검증. AR-044 hold 종속 명시.
- **저작권/ToS**: 행단위 `rights_class`/`reuse_scope`/`excerpt_max_chars`/`verbatim_allowed` + canonical servable predicate + legal_review_approve 게이트.
- **자기증폭 환각**: §6 provenance 격리(generated 즉답 인용 금지·자동 승격 금지) + §6.1 기존 코퍼스 소급 재라벨링.

## 최종 산출물 핵심 (red_team_clear 시점)

- 3-tier 비용효율 응답 라우터(Tier1 classifier 즉답 / Tier2 intent JSON / Tier3 기존 RAG), 선행 BLOCKING = robust Data Analysis Agent(§8 수치 게이트).
- provenance enum `collected|curated|generated` (DB CHECK 강제), `derived` 미사용.
- 기존 evidence_index(1,803항목/gemini-embedding-001/768d) 교체 아닌 래핑 + source_ref crosswalk + 회귀(top-3 100%/top-8 Jaccard≥0.95) 롤백.
- AR-044 PIPA 게이트와 P5 누적 루프 정렬(외부 트래픽 활성화 차단).

## 비고

- 본 검토는 계획 문서(구현 전) 대상이다. 실제 코드(P1~) 착수 시 코드 변경분에 대한 별도 red_team_clear가 필요하다.
- red-team caller는 read-only(`scripts/redteam_review.sh`). git 쓰기권한 없음.
