# Handoff — Edu Query Engine 계획서 + gate_tracker sync 편입 (2026-06-14)

> 작성: 2026-06-14 / `/clear` 전 상태 보존. 맥락 없이도 다음 세션이 이어받도록 정리.
> 상태: **두 작업 모두 red_team_clear + commit + 배포 + MBP/Mac Mini 양쪽 청결 완료.**
> 직전 handoff: `docs/handoffs/ar044_checklist_handoff_20260614.md` (AR-044 체크리스트, 별개 라인)

---

## 0. 한 줄 요약

이번 세션은 **두 개의 독립 작업**을 끝냈다(둘 다 red_team_clear → commit → deploy → 양쪽 git clean):
1. **Edu Query Engine & Data Analysis Agent 개발 계획서** 작성 (commit `30136b4`) — 구현 미착수.
2. **gate_tracker.jsonl 결재기록 sync 편입 + 원자적 쓰기 버그 수정** (commit `5a6a44b`) — 배포·동작 검증 완료.

현재 HEAD = `5a6a44b`, MBP·Mac Mini 모두 `HEAD==origin/main`, tracked dirty 0.

---

## 1. 작업 ① — Edu Query Engine & Data Analysis Agent 개발 계획서

### 무엇/왜
대표 발의(2026-06-14): edu 응답을 "고객 발화마다 LLM이 매번 생성" → **"DB 즉답 우선, LLM은 꼭 필요할 때만"**
으로 전환. 비유료 익명 트래픽의 토큰 비용이 전부 손실비용으로 떨어지는 문제를 막는 게 목적.
**선행 조건 = robust Data Analysis Agent + query 효율 DB. 이게 완성도 보장된 뒤에만 다음 단계.**

### 산출물 (commit `30136b4`)
| 파일 | 내용 |
|---|---|
| `docs/education/EDU_QUERY_ENGINE_DEV_PLAN.md` | 핵심 계획서 (3-tier 라우터 + 선행 Data Analysis Agent) |
| `docs/reports/llm_outputs/edu_query_engine_plan_redteam_2026-06-14.md` | red-team 영속 기록(8라운드) |
| `docs/governance/RED_TEAM_LOG.md` | append |

### 아키텍처 핵심 (계획서 요지)
- **Tier 1** classifier(LLM 미호출): 결정형/사실형 질의 → 고정 resolver enum로 DB 즉답. 신뢰도 미달 시 Tier 2.
- **Tier 2** 저비용 LLM(로컬 우선): 자연어 → **고정 intent JSON만**(산문 생성 금지). resolver로 DB 재조회.
- **Tier 3** 기존 RAG(evidence_index **1,803항목/gemini-embedding-001/768d**) — **교체 아닌 래핑**. 여기만 고비용 허용.
- **누적 루프**: Tier3 답변을 `edu_rag_accumulation`에 적재하되 `provenance='generated'` 격리(즉답 인용 금지·자동 승격 금지).
- **중요 사실**: 대표가 그린 Tier 3는 이미 부분 구현됨(`main.py`의 `_retrieve_evidence_bundle` 등). 비어 있던 건 ① 항목화 DB ② Tier1 즉답 ③ Tier2 intent JSON ④ 누적 루프.

### red-team이 강제한 핵심 안전장치 (원안 대비 강화)
- **PII**: LLM이 테이블명/SQL 생성 불가(고정 resolver enum). `edu_cases`/대화원문은 인증 세션 `authed_case_id` 소유권 검증 경로만. → AR-044 PIPA 게이트 종속.
- **저작권**: 외부 소스 행단위 권리메타(`rights_class`/`reuse_scope`/`excerpt_max_chars`/`verbatim_allowed`) + canonical `servable` predicate 단일 정의.
- **자기증폭 환각**: generated 격리 + 기존 코퍼스(이미 섞인 pipeline 파생물) 소급 재라벨링(P1.5).
- **기존 RAG 보존**: `source_ref` crosswalk + 재빌드 회귀(top-3 100%/top-8 Jaccard≥0.95) 롤백.
- **provenance enum** = `collected|curated|generated` (DB CHECK 강제, `derived` 미사용).
- `api_cost_log`에 tier/token 컬럼 마이그레이션 필요(현재 없음).

### Phase 순서 (CEO 우선순위 — 어기지 말 것)
- **P1 (선행·BLOCKING)**: Data Analysis Agent + `edu_knowledge_items` 적재. §8 robust 수치 게이트(idempotent diff0, ingest≥95%, DLQ≤5%, 처리시간 ≤10분/임베딩포함≤30분, 샘플정확도≥98%) 전부 통과 전 **P1.5/P2 이후 착수 금지.**
- P1.5: 기존 코퍼스 provenance 소급 재라벨링·재빌드 + crosswalk.
- P2: intent JSON contract + Tier2 분류기. P3: Tier1 즉답 + 비용지표. P4: 라우터 통합 + baseline 대비 절감률. P5: 누적 루프(외부 트래픽 시 AR-044 종속).

### red-team 경과
8라운드. Gemini 전 라운드 clear, Codex가 매 라운드 실질 지적(r1 BLOCKER4/MAJOR6 PII·저작권·코퍼스오염·crosswalk·비용지표·robust임계값·resolver·인덱스·api_cost_log·shorthand → r8까지 enum/스키마 CHECK/servable predicate/DLQ재사용 등) → 전부 반영 → **r8 Gemini+Codex 동일본 clear = red_team_clear**. 잔여 비차단 MINOR: §2 `quality_score` 임계값 P3 baseline 후 확정.

### 다음 할 일 (미착수 — CEO 우선순위 확인 후)
- **P1 구현**: Data Analysis Agent(소스별 어댑터 ETL → `edu_knowledge_items` 적재 + `tests/test_edu_data_agent.py` + `api_cog_log` 마이그레이션). **코드는 별도 red_team_clear 필요.**
- 그 전에 대표가 계획서 방향 확인하면 좋음.

---

## 2. 작업 ② — gate_tracker.jsonl sync 편입 + 원자적 쓰기 (commit `5a6a44b`)

### 배경
작업 ① 배포 중 발견: `docs/reports/gate_tracker.jsonl`(게이트 상태 원장)은 **추적 파일인데 sync 주인이 없어**,
매일 점검기(08:00/09:00)가 status(pending→overdue)·last_checked_at를 갱신할 때마다 Mac Mini에 dirty 누적 → ff/배포 방해.
대표 결정(B안): gitignore(감사이력 휘발) 대신 **origin 환원**(`com.harness.decision-record-sync` 화이트리스트 편입).

### 변경 (commit `5a6a44b`)
- `scripts/sync_decision_records.py`: `EXACT_FILES`에 `docs/reports/gate_tracker.jsonl` 추가 + bootstrap 주석.
- `scripts/gate_tracker.py`: `_rewrite_gates` 비원자적 `open("w")` → **`tempfile.mkstemp(같은 디렉터리)+fsync+os.replace` 원자적 교체**.
- `.gitignore`: `docs/reports/.gate_tracker_*.tmp`.
- `docs/governance/RED_TEAM_LOG.md`: append.

### red-team이 막은 것 (중요)
단순 화이트리스트 추가만 했으면 **torn-write 버그**를 켤 뻔함. Codex r1 BLOCKER: `gate_tracker.py`가 파일을
비원자적으로 전체 재작성 → sync의 `_is_stable()`이 "쓰는 도중의 유효 JSONL prefix"를 정상으로 오인 →
**절단된 원장 커밋** 가능. 원자적 교체로 근원 차단. (r1 block → r2 Gemini+Codex clear)

### 배포 시 수반된 운영 조치 (재현 필요시 참고)
- **bootstrap 마커 seed**: 기존 추적 파일을 화이트리스트에 새로 넣을 때, 첫 sync 회차가 "마커 없음→prod 무조건 채택"
  하므로, **`origin:path == 워킹 blob` 확인 후** `runtime/decision_record_sync_state.json`에 마커를 seed해야 blind-adopt를 막는다.
  이번엔 `469310e`로 seed 완료. `sync --dry-run` = no-op 확인.

---

## 3. 현재 git 상태 (양쪽 청결)

| | HEAD | origin 동기 | tracked dirty |
|---|---|---|---|
| MBP | `5a6a44b` | ✅ ==origin/main | 0 |
| Mac Mini | `5a6a44b` | ✅ ==origin/main | 0 |

- 세션 시작 시점의 Slack 관련 dirty(slack_listener/slack_runtime_guard 등)는 **이미 별도로 commit/push 처리됨**(이번 세션과 무관 라인). 현재 작업트리엔 없음.
- Mac Mini는 selective checkout 모델이라 deploy 후 HEAD가 뒤처지면 `git merge --ff-only origin/main`(ancestor+staged diff0+백업 선행)로 전진시켜 청결화함.

---

## 4. 운영 규약 리마인더 (CLAUDE.md MUST)

- 배포: commit→push→origin/main만. Mac Mini 수동수정·scp 금지. `scripts/deploy_to_macmini.sh`로만(선택 checkout). 양쪽 종료 시 dirty 0 + HEAD==origin.
- Mac Mini: ssh alias `macmini`, user `juntaepark`(점 없음).
- 코드/MD/high-impact 변경 = 비저자 cross-LLM 2개 이상 `red_team_clear`. 동일 LLM self-review 금지. red-team caller는 read-only(`scripts/redteam_review.sh <gemini|codex|copilot> <ctx>`, git 쓰기권한 금지). 저자=Claude는 self-review 불가.
- 큰 계획은 실행 전 red_team_clear 먼저(BLOCK 원칙).
- 응답: 한국어 존댓말 + 'OO님', 간결, 영어용어 괄호 설명.

---

## 5. 관련 파일 빠른 참조

- 계획서: `docs/education/EDU_QUERY_ENGINE_DEV_PLAN.md`
- 계획서 red-team 기록: `docs/reports/llm_outputs/edu_query_engine_plan_redteam_2026-06-14.md`
- sync 잡: `scripts/sync_decision_records.py` (화이트리스트 EXACT_FILES/DIR_PREFIXES)
- 게이트 원장 생성기: `scripts/gate_tracker.py` (`_rewrite_gates` 원자적)
- 기존 RAG 검색: `harness-os/backend/main.py` `_retrieve_evidence_bundle`/`_edu_ranked_matches`/`_load_rag_index`
- red-team 로그: `docs/governance/RED_TEAM_LOG.md`
