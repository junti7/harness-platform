# Handoff: Tier3 정제 적체 + 무료 티어 전환
**날짜**: 2026-07-04  
**작성**: Claude Sonnet 4.6  
**상태**: ⏳ 무료 API 키 입력 대기 중

---

## 문제 요약

Harness OS 대시보드에서 edu_consulting 정제 파이프라인이 **6,425건 적체, 처리율 0 건/시간** 상태로 표시됨.

운영 규칙: Codex CLI 사용 시 사용자가 별도 해제하기 전까지 `caveman ultra` 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.

**근본 원인**: `DAILY_COST_LIMIT_USD=2.00` 초과.  
오늘(2026-07-04) 자정~오전 6:31 사이에 tier3 정제가 Gemini 2.5 Flash를 378회 호출해 **$2.0613**를 소모. 이후 30분마다 job이 실행되지만 cost gate에 즉시 블록돼 0건 처리.

```
일일 비용 한도 도달: $2.0614 / $2.0   ← 매 실행마다 반복
pending 15019 → 15019, refined=0
```

---

## 원인 분석

| 항목 | 내용 |
|---|---|
| 소모 모델 | Gemini 2.5 Flash (`google` provider) |
| 총 호출 | 378회 |
| 토큰 | 입력 530,747 / 출력 760,837 |
| 비용 | $2.0613 (일일 한도 $2.00 초과) |
| 소모 시간대 | KST 00:17 ~ 06:31 (tier3 배치 30분 간격) |
| 기타 | 10:32~10:44 28회 $0.06 (edu_daily 추정) |

`DAILY_COST_LIMIT_USD` 는 `.env`에 고정돼 있고, `load_dotenv(override=True)` 로 로드되므로 **셸 환경변수로 오버라이드 불가**.

---

## 시도한 대안 및 결과

### gemma4:latest (Mac Mini Ollama, 9.6GB) — ❌ 탈락
- 건당 처리 시간: **5~10분**
- 6,425건 예상 소요: 22~44일
- 에러: `RuntimeError: ollama_fallback_unavailable: timed out`
- Mac Mini M4 24GB에서 통합 메모리 대역폭 병목. 실용 불가.

---

## 구현 완료 사항

### `scripts/run_edu_tier3_parallel.py` — `--free-tier` 플래그 추가

커밋: `8c82125`, `d5b6d1f` (completion evidence 포함)  
Mac Mini 배포: ✅ 완료 (`deploy_to_macmini.sh` 검증 통과)

**동작 방식**:
- `.env`의 `GEMINI_API_KEY_FREE` 값을 `GOOGLE_API_KEY`로 적용
- `DAILY_COST_LIMIT_USD=9999`로 비용 게이트 우회 (로컬 과금 없음)
- `workers`를 2 이하로 강제 (무료 티어 RPM 10 초과 방지)

### 2026-07-04 Codex 후속 진행

- `--free-tier` 실행 전 `DAILY_COST_LIMIT_USD=9999`만 설정하면 이미 import된 `DAILY_COST_LIMIT` 상수에는 반영되지 않는 문제를 확인함.
- `scripts/run_edu_tier3_parallel.py`에서 free-tier 진입 시 `globals()["DAILY_COST_LIMIT"] = 9999.0`도 함께 설정하도록 수정함.
- 로컬 검증: `.venv/bin/python -m py_compile scripts/run_edu_tier3_parallel.py`, `.venv/bin/python scripts/run_edu_tier3_parallel.py --help` 통과.
- Mac Mini 배포: `scripts/deploy_to_macmini.sh scripts/run_edu_tier3_parallel.py docs/handoffs/tier3_refine_backlog_free_tier_handoff_20260704.md docs/reports/completion_evidence/tier3_free_tier_cost_gate_fix_20260704.json` 검증 통과.
- Mac Mini 검증: `.venv/bin/python -m py_compile scripts/run_edu_tier3_parallel.py` 통과.
- Mac Mini 샘플 실행은 아직 `ERROR: --free-tier 사용 시 .env에 GEMINI_API_KEY_FREE 설정 필요`로 중단됨. `.env`의 `GEMINI_API_KEY_FREE=` 값이 비어 있어 Human step이 계속 필요함.

**실행 명령어**:
```bash
ssh macmini "cd /Users/juntaepark/projects/harness-platform && \
  .venv/bin/python scripts/run_edu_tier3_parallel.py \
  --free-tier --limit 500 2>&1"
```

---

## 잔여 작업 (다음 세션)

### Step 1 — 무료 API 키 등록 ⏳ HUMAN_REQUIRED

Google AI Studio(aistudio.google.com) → "Get API key" → **새 프로젝트** (결제 미연동)로 키 생성 후:

```bash
ssh macmini "sed -i '' 's|GEMINI_API_KEY_FREE=|GEMINI_API_KEY_FREE=<키>|' \
  /Users/juntaepark/projects/harness-platform/.env"
```

### Step 2 — 20건 샘플 품질 검증

```bash
ssh macmini "cd /Users/juntaepark/projects/harness-platform && \
  .venv/bin/python scripts/run_edu_tier3_parallel.py \
  --free-tier --limit 20 2>&1 | tail -20"
```

품질 확인 포인트:
- `정제 N / 스킵 M / 실패 0` 에서 스킵률이 50% 미만인지
- `final_title`이 한국어로 자연스러운지
- 타임아웃 없이 건당 30~60초 내 완료하는지

### Step 3 — launchd 잡 교체 (샘플 통과 시)

현재 `com.harness.tier3-filter.plist`는 유료 키 + `run_tier3_backlog_worker.py` 사용.  
샘플 품질 통과 시, 별도 잡(`com.harness.edu-tier3-free.plist`)으로 무료 키 기반 백로그 소진 잡 추가.

**무료 티어 처리 용량 예상**:
- Gemini 2.5 Flash 무료: 10 RPM, 1M TPD
- workers=2, 건당 ~45초 → 약 2~3 RPM → 하루 ~700~900건
- 6,425건 ÷ 800 ≈ **8~9일이면 백로그 소진**

### Step 4 — 재발 방지 (선택)

현재 구조적 문제: tier3 job이 30분마다 실행되면서 자정 이후 수 시간 내에 일일 예산 전부 소모.  
장기적으로는 `StartInterval`을 늘리거나 KST 시간대 제한을 추가해 낮 시간 비용 여유를 확보.

---

## 관련 파일

| 파일 | 용도 |
|---|---|
| `scripts/run_edu_tier3_parallel.py` | `--free-tier` 플래그 추가됨 |
| `adapters/content/refiner.py` | `DAILY_COST_LIMIT`, `get_today_cost` 로직 |
| `harness-os/launchd/com.harness.tier3-filter.plist` | 현재 실행 중인 배치 잡 |
| `.env` (Mac Mini) | `GEMINI_API_KEY_FREE=` 빈 값으로 추가됨 |
| `docs/reports/completion_evidence/edu_tier3_free_tier_flag_20260704.json` | completion evidence |
| `docs/reports/completion_evidence/tier3_free_tier_cost_gate_fix_20260704.json` | free-tier 비용 게이트 상수 보정 evidence |
