# Handoff: Tier3 정제 적체 + 무료 티어 전환
**날짜**: 2026-07-04  
**작성**: Claude Sonnet 4.6  
**상태**: ✅ Gemini free-tier 기반 운영으로 전환. rule triage로 backlog 청소 후 high-precision 후보만 정제

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

### 2026-07-04 Codex 후속 진행 2

- 무료 키 등록 확인: `GEMINI_API_KEY_FREE` present=true, length=39.
- 20건 샘플 1차: `정제 0 / 스킵 17 / 실패 3`. 실패 원인은 irrelevant 후보의 `evidence_posture.classification`이 `None/not_applicable`인 schema mismatch.
- 수정: `is_relevant=false` 결과는 evidence posture와 title을 안전하게 정규화하고 `refined_outputs`에 `gemini-2.5-flash:irrelevant`로 저장하게 함. 기존에는 스킵만 카운트하고 저장하지 않아 같은 후보를 계속 재처리했음.
- 20건 샘플 2차: `정제 0 / 스킵 20 / 실패 0`. DB 확인 결과 샘플 20개 모두 `refined_outputs`에 저장됨.
- 5건 smoke 중 `JSONDecodeError` 1건이 반복 위험으로 확인되어 no-fallback parse/validation 오류도 `gemini-2.5-flash:error-skip`으로 저장하게 보완.
- 최종 5건 smoke: `정제 0 / 스킵 5 / 실패 0`.
- 현재 pending: 6,395건. 상위 pending source는 `Naver_블로그`, `Naver_카페글`, 일반 교육뉴스가 많아 source quality가 낮음.
- 결론: 무료 키와 스킵 저장은 작동. 다만 샘플 품질이 `정제 0 / 스킵 25`라 `com.harness.edu-tier3-free.plist` 자동 launchd 전환은 아직 보류.

### 2026-07-04 Codex 후속 진행 3

- AI/디지털 교육 text gate 추가 후 10건 샘플: `정제 3 / 스킵 7 / 실패 0`.
- institution PR deny gate 추가 후 10건 샘플: `정제 6 / 스킵 4 / 실패 0`로 일시 통과.
- 보수적 LaunchAgent `com.harness.edu-tier3-free` 추가 및 설치. 설정: `--free-tier --limit 40`, `StartInterval=3600`, workers는 스크립트에서 2로 강제.
- 첫 RunAtLoad 40건 실측: `정제 16 / 스킵 24 / 실패 0`. 안전하게 저장/진행됐지만 스킵률 60%로 품질 기준 미달.
- LaunchAgent는 `bootout` 완료. 현재 plist는 설치돼 있으나 `launchctl list`에는 로드되어 있지 않음.
- K-12/학부모/학생 audience gate 추가 후 10건 샘플: `정제 3 / 스킵 7 / 실패 0`. 여전히 자동화 기준 미달.
- 결론: 무료 tier3 자동 잡은 설치되어 있지만 intentionally unloaded. 다음 작업은 stricter source allowlist 또는 stronger positive audience policy 적용 후 재샘플.

### 2026-07-05 Codex 후속 진행 4

- curated source allowlist 추가 후 10건 샘플: `정제 10 / 스킵 0 / 실패 0`.
- 이 결과를 근거로 `com.harness.edu-tier3-free.plist`를 재등록했으나 RunAtLoad는 남은 후보 32건을 처리하며 `정제 13 / 스킵 19 / 실패 0`로 종료. 스킵률 59.4%라 자동화 기준 미달.
- 즉시 `launchctl bootout gui/$(id -u)/com.harness.edu-tier3-free`로 다시 unload 완료. 현재 plist는 설치되어 있지만 로드되어 있지 않음.
- source별 진단:
  - `GoogleNews_디지털의존`: 4 refined / 11 skipped
  - `The74Million`: 2 refined / 4 skipped
  - `Chalkbeat`: 0 refined / 2 skipped
- 위 3개 source를 allowlist에서 제거함. 배포 후 pruned allowlist로 `--free-tier --limit 10` 실행 결과 `정제 대상 없음`.
- 운영 방향 결정: Local LLM 정제는 실용 속도 미달이므로 Tier3 본정제는 Gemini free-tier가 owner. Local LLM은 필요 시 Tier2 필터/분류 보조로만 사용.
- `com.harness.edu-tier3-free.plist`의 batch size를 `--limit 40`에서 `--limit 10`으로 낮추고 `--cost-every 10`으로 조정. 새 eligible batch가 들어와도 한 번에 크게 번지지 않도록 보수적으로 운영.
- Mac Mini LaunchAgent 재설치/로드 완료. `launchctl print`에서 `--free-tier --limit 10 --cost-every 10` 확인. RunAtLoad는 `GEMINI_API_KEY_FREE`를 적용했고 `정제 대상 없음`으로 exit 0.
- 대시보드의 6,283건 backlog는 high-quality 정제 후보가 아니라 Tier2 통과 후 아직 refined_outputs 기록이 없는 전체 미처리 풀임을 확인. `--no-text-gate --limit 10` 실제 실행 결과 `정제 2 / 스킵 8 / 실패 0`, pending `6,283 → 6,273`.
- 현실 운영 방식으로 전환:
  - 명백한 noise는 LLM 호출 없이 `edu-triage:rule-skip`으로 `refined_outputs`에 저장해 backlog에서 제거.
  - Gemini free-tier는 pruned allowlist + topic/audience gate를 통과한 high-precision 후보만 정제.
  - `com.harness.edu-tier3-free.plist`는 매시간 `--triage-limit 50 --limit 10`으로 운영.
- 실측:
  - 수동 triage sample: `edu-triage:rule-skip` 5건 저장, high-precision Gemini 정제 대상 없음.
  - launchd RunAtLoad: `edu-triage:rule-skip` 50건 저장, high-precision Gemini 정제 대상 없음, exit 0.
  - 최근 저장 합계: `edu-triage:rule-skip 55`, `gemini-2.5-flash 2`, `gemini-2.5-flash:irrelevant 8`.
  - pending은 `6,283 → 6,273 → 6,218`.
- 최신 커밋:
  - `2eb53a6` `fix: restrict edu tier3 candidates to curated sources`
  - `3b84f03` `fix: prune noisy edu tier3 sources`
- Mac Mini 배포: `scripts/deploy_to_macmini.sh` 검증 통과. 대상 diff 0 확인.

**실행 명령어**:
```bash
ssh macmini "cd /Users/juntaepark/projects/harness-platform && \
  .venv/bin/python scripts/run_edu_tier3_parallel.py \
  --free-tier --limit 500 2>&1"
```

---

## 잔여 작업 (다음 세션)

### Step 1 — 다음 eligible batch 품질 검증

```bash
ssh macmini "cd /Users/juntaepark/projects/harness-platform && \
  .venv/bin/python scripts/run_edu_tier3_parallel.py \
  --free-tier --limit 20 2>&1 | tail -20"
```

품질 확인 포인트:
- `정제 N / 스킵 M / 실패 0` 에서 스킵률이 50% 미만인지
- `final_title`이 한국어로 자연스러운지
- 타임아웃 없이 건당 30~60초 내 완료하는지

현재는 pruned allowlist 적용 후 남은 후보가 없어 `정제 대상 없음`이 정상이다. 새 eligible batch가 들어오면 위 명령으로 다시 품질 검증한다.

### Step 2 — launchd 운영/모니터링

현재 `com.harness.tier3-filter.plist`는 유료 키 + `run_tier3_backlog_worker.py` 사용.  
별도 잡(`com.harness.edu-tier3-free.plist`)이 Gemini free-tier 기반 백로그 소진을 담당한다.

2026-07-05 현재 판정: Gemini free-tier 기반으로 운영. `com.harness.edu-tier3-free.plist`는 시간당 rule-skip 50건 + Gemini 정제 10건 제한으로 로드한다. 향후 실행에서 rule-skip 오분류가 보이거나 Gemini 스킵률이 50%를 넘으면 즉시 `bootout` 후 원인 source/pattern을 조정한다.

**무료 티어 처리 용량 예상**:
- Gemini 2.5 Flash 무료: 10 RPM, 1M TPD
- 현재 launchd: 시간당 rule-skip 최대 50건 + Gemini 정제 최대 10건, workers=2
- 처리량보다 품질/비용 안정성을 우선한다. source 품질이 더 검증되면 `--limit`를 20, 40 순으로 올린다.

### Step 3 — 재발 방지 (선택)

현재 구조적 문제: tier3 job이 30분마다 실행되면서 자정 이후 수 시간 내에 일일 예산 전부 소모.  
장기적으로는 `StartInterval`을 늘리거나 KST 시간대 제한을 추가해 낮 시간 비용 여유를 확보.

---

## 관련 파일

| 파일 | 용도 |
|---|---|
| `scripts/run_edu_tier3_parallel.py` | `--free-tier` 플래그 추가됨 |
| `adapters/content/refiner.py` | `DAILY_COST_LIMIT`, `get_today_cost` 로직 |
| `harness-os/launchd/com.harness.tier3-filter.plist` | 현재 실행 중인 배치 잡 |
| `harness-os/launchd/com.harness.edu-tier3-free.plist` | Gemini free-tier 자동 정제 잡, 시간당 10건 제한 |
| `.env` (Mac Mini) | `GEMINI_API_KEY_FREE` 등록 완료 |
| `docs/reports/completion_evidence/edu_tier3_free_tier_flag_20260704.json` | completion evidence |
| `docs/reports/completion_evidence/tier3_free_tier_cost_gate_fix_20260704.json` | free-tier 비용 게이트 상수 보정 evidence |
| `docs/reports/completion_evidence/edu_tier3_text_gate_20260704.json` | text/audience/source gate와 launchd hold evidence |
