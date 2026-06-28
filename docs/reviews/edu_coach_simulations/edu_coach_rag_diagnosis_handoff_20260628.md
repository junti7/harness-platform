# EDU AI Coach RAG 진단 Hand-off 문서

작성일: 2026-06-28
작성자: Claude (진단 세션)
대상: 다음 구현 담당자 (Claude / Codex / CEO)

---

## 한 줄 요약

EDU AI Coach의 RAG가 사실상 전혀 작동하지 않고 있다. 1차 DB 경로는 테이블 미존재로 100% 실패, 2차 인덱스 경로는 embedding mismatch + score 기준 버그로 모든 후보가 rejected된다.

---

## 진단 근거 파일

| 파일 | 역할 |
|---|---|
| `harness-os/backend/main.py` | 구현 전체. 진단 대상 함수 라인 번호 아래 명시 |
| `data/edu_research/evidence_index.json` | 2차 RAG 인덱스. 1803개 항목, provider=None |
| `runtime/edu_pilot_runtime_events.jsonl` | 런타임 이벤트 로그. 진단 시점 총 2421건 |
| `.env` | `EMBEDDING_PROVIDER_MODE=auto`, `OLLAMA_EMBED_MODEL=nomic-embed-text`, `OLLAMA_EMBED_DIM=768` |
| `docs/reviews/edu_coach_simulations/edu_coach_external_llm_evaluation_guide_20260628.md` | 외부 LLM 평가 가이드 (이 문서의 배경) |

---

## 결함 목록 (P0~P2)

### [P0-1] DB 1차 경로 100% 실패

- **위치**: `main.py:12073` `_edu_db_customer_facing_bundle`
- **증상**: `event_type: edu_customer_facing_db_query_failed` / `error_type: UndefinedTable`
- **빈도**: 최근 500 이벤트 중 365건 (73%)
- **원인**: `edu_knowledge_items_customer_facing` 테이블이 DB에 존재하지 않음
- **영향**: 1차 경로가 예외를 던지고 2차로 fall-through. 불필요한 DB 예외 누적

**수정 방법 A (단기)**: 함수 진입부에 테이블 존재 여부 캐시 guard 추가

```python
# main.py:12072 직후 삽입
_EDU_CF_TABLE_READY: bool | None = None

def _edu_db_customer_facing_bundle(query: str, segment: str, k: int = 8) -> dict[str, Any] | None:
    global _EDU_CF_TABLE_READY
    if _EDU_CF_TABLE_READY is False:
        return None
    try:
        rows = execute_query(...)
        _EDU_CF_TABLE_READY = True
        ...
    except Exception as exc:
        if "UndefinedTable" in type(exc).__name__ or "does not exist" in str(exc):
            _EDU_CF_TABLE_READY = False
        ...
        return None
```

**수정 방법 B (정식)**: `edu_knowledge_items_customer_facing` 테이블 생성 마이그레이션 작성. 스키마는 `main.py:12073-12096` SELECT 절 참고.

---

### [P0-2] Score 검증 기준 버그 — 코사인 유사도 범위 오해

- **위치**: `main.py:9996`
- **코드**:
  ```python
  if score and score < 2.0:
      reasons.append("low_retrieval_score")
  ```
- **원인**: 코사인 유사도는 0~1 범위. `score < 2.0`은 score가 0이 아닌 한 **항상 True** → 모든 후보 rejected
- **증거**: 런타임 이벤트에 `skip_reason: "no_candidates"` 또는 `"all_candidates_rejected"` 반복
- **수정**:
  ```python
  _RAG_MIN_COSINE_SCORE = float(os.getenv("EDU_RAG_MIN_SCORE", "0.30"))
  if score and score < _RAG_MIN_COSINE_SCORE:
      reasons.append("low_retrieval_score")
  ```

---

### [P0-3] Embedding Provider Mismatch — 인덱스 벡터 공간 불일치

- **위치**: `main.py:12128-12147` (`_edu_ranked_matches`)
- **원인**: 인덱스가 `gemini-embedding-001`로 구축됐으나 (provider 필드=None), 런타임은 `OLLAMA_EMBED_MODEL=nomic-embed-text` 사용. provider=None이면 mismatch 체크가 스킵(`if idx.get("provider") and ...` 조건 불충족)되어 다른 벡터 공간으로 검색
- **영향**: 코사인 유사도가 무작위 수준으로 낮아짐 → keyword validation도 통과 못 함

**수정 옵션 (셋 중 하나 선택)**:

1. **인덱스 재구축** (권장): `EMBEDDING_PROVIDER_MODE`가 실제 선택하는 모델을 확인한 뒤 동일 모델로 인덱스 재빌드
   ```bash
   .venv/bin/python scripts/build_edu_pattern_intelligence.py
   ```

2. **런타임 provider 고정**: `.env`에 명시적 설정 추가
   ```
   EMBEDDING_PROVIDER=gemini
   GEMINI_API_KEY=<기존 키>
   ```

3. **인덱스에 provider 기록**: 인덱스 생성 스크립트에서 `"provider": "gemini"`, `"model": "gemini-embedding-001"` 필드를 저장하도록 수정 → mismatch 체크 활성화

---

### [P1-1] Structured Packet 모드 비활성화

- **위치**: `main.py:11064`
- **현황**: `EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED` 미설정 → False
- **영향**: RAG를 `rag_synthesis` 구조로 답변에 통합하는 경로(prompt: `main.py:9669-9715`)가 사용되지 않음. 대신 base_prompt(`main.py:11149`)에서 RAG 근거를 단순 텍스트 블록으로 주입
- **수정**: `.env`에 추가
  ```
  EDU_SAFETY_COACH_STRUCTURED_PACKET_ENABLED=true
  ```
- **주의**: 구조화 패킷은 JSON 출력을 파싱하므로 `max_output_tokens=760` 제한 내 응답이 잘리지 않는지 초기 테스트 필요

---

### [P1-2] Evidence 검색 limit=1 + Fast RAG timeout 0.6초 과소

- **위치**: `main.py:11018` (limit), `main.py:11012` (timeout)
- **현황**: limit=1로 최대 1개 근거만 검색. fast_answer 경로 RAG timeout 0.6초
- **수정**: `.env`에 추가
  ```
  EDU_SAFETY_COACH_RAG_TIMEOUT_SECONDS=2.5
  EDU_SAFETY_COACH_FAST_RAG_TIMEOUT_SECONDS=1.5
  ```
  limit 변경은 코드 수정 필요 (`limit=1` → `limit=3`, `main.py:11018`)

---

### [P2-1] Evidence Index 콘텐츠 편향

- **현황**: 1803개 중 1784개(99%)가 `최신 동향` 타입. `worker` 세그먼트 3개뿐
- **문제**: 학부모 질문의 주요 패턴(감정·관계·비용 장벽·개인정보·안전)과 매칭되는 `커뮤니티 목소리`, `연구·정책`, `미디어 사례` 항목이 부족
- **수정**: `configs/education/edu_coach_corpus_scenarios.json`의 실제 질문 패턴을 분석해 부족한 유형의 evidence를 `anchor` 방식으로 추가 큐레이션. anchor 항목 19개(Jonathan Haidt 등)는 품질 우수 — 동일 방식으로 확장

---

### [P2-2] Keyword 정규화 부재

- **위치**: `main.py:9981-9993` (`_edu_vp_validate_safety_coach_evidence`)
- **현황**: `"AI한테"`, `"AI와"` 등 조사 결합 형태가 별개 토큰으로 처리 → keyword overlap 낮음
- **수정**: 간단히 `min_hits=2` → `min_hits=1`로 완화하거나, 키워드 정규화에서 2글자 이상 한글/영문 추출 시 조사 제거 추가

---

## 수정 우선순위 및 예상 효과

| 순서 | 항목 | 변경 위치 | 예상 효과 |
|---|---|---|---|
| 1 | P0-2: score < 2.0 → < 0.30 | `main.py:9996` 1줄 | all_candidates_rejected 즉시 해소 |
| 2 | P0-3: embedding provider 일치 | `.env` 또는 인덱스 재구축 | 2차 경로 검색 품질 복원 |
| 3 | P0-1: DB guard 또는 테이블 생성 | `main.py:12072` 또는 migration | 73% 불필요 예외 제거 |
| 4 | P1-1: STRUCTURED_PACKET=true | `.env` 1줄 | RAG→답변 통합 품질 대폭 향상 |
| 5 | P1-2: limit 1→3, timeout 완화 | `main.py:11018` + `.env` | 근거 다양성 확보 |
| 6 | P2-1: 인덱스 콘텐츠 확장 | 콘텐츠 큐레이션 | 장기 hit rate 개선 |
| 7 | P2-2: keyword min_hits 완화 | `main.py:9993` 1줄 | validation pass율 개선 |

P0 세 가지 수정만으로도 `evidence_used=false` 비율이 대폭 줄어들 것으로 예상.

---

## 평가 가이드 연동

이 진단은 `edu_coach_external_llm_evaluation_guide_20260628.md`의 F(RAG Decision Quality)·G(RAG Fit)·H(RAG Faithfulness) 차원을 근거로 한다.

수정 후 검증 기준:
- `used_weak_or_mismatched_evidence + fabricated_or_unfaithful_evidence` 비율 < 1%
- `should_have_used_available_evidence` 비율 < 2%
- `evidence_used=true` 비율이 전체의 최소 20% 이상 (현재 추정 <5%)

평가 실행:
```bash
# 평가 입력 JSONL 생성 (guide 문서 참고)
.venv/bin/python - <<'PY' > docs/reviews/edu_coach_simulations/edu_coach_questions_for_external_eval_20260628.jsonl
# ... (guide 문서의 추출 명령 사용)
PY
```

---

## 관련 파일 전체 경로

```
진단 보고서 (이 문서):
  /Users/juntae.park/projects/harness-platform/docs/reviews/edu_coach_simulations/edu_coach_rag_diagnosis_handoff_20260628.md

평가 가이드:
  /Users/juntae.park/projects/harness-platform/docs/reviews/edu_coach_simulations/edu_coach_external_llm_evaluation_guide_20260628.md

구현 파일:
  /Users/juntae.park/projects/harness-platform/harness-os/backend/main.py

RAG 인덱스:
  /Users/juntae.park/projects/harness-platform/data/edu_research/evidence_index.json

런타임 이벤트 로그:
  /Users/juntae.park/projects/harness-platform/runtime/edu_pilot_runtime_events.jsonl

환경 변수:
  /Users/juntae.park/projects/harness-platform/.env
```
