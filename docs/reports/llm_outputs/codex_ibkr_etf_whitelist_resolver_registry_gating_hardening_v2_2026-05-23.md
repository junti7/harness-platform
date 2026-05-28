# IBKR ETF Whitelist Resolver + Registry Gating — Codex Red-Team (Hardening v2, 2026-05-23)

## Objective
하드닝(v2) 이후, 아래 체크가 실제로 코드로 강제되는지 재검증한다.
- authenticated==True가 아니면 approve 차단(키 누락 포함)
- min-confidence 하한(>=0.85) 서버측 강제
- ETF auto-approve에서 STK 오매칭이 registry로 절대 들어가지 않음
- ambiguous(top2 근접) → pending 큐로 강등
- correlation-id + approved_by 기록 강제
- TOCTOU 완화(체크 스냅샷 기반 approve) + secdef_info 2차 검증

## Findings

1. authenticated guard
   - `command_ibkr_etf_approve`: `auth.get("authenticated") is not True` → 키 누락/False/문자열 모두 차단.
   - `command_ibkr_etf_check`도 동일하게 authenticated가 아니면 “중단” 메시지로 끝나도록 변경됨.

2. min-confidence floor
   - `threshold = max(0.85, threshold)`로 caller가 낮춰도 무시됨.

3. ETF/sectype + name_hint
   - `_pick_best_candidate`에서 ETF item에 대해 `sectype != ETF` 페널티를 주는 것뿐 아니라,
   - approve 단계에서 `item_type in {etf, ucits_etf} and best.sectype != ETF`면 **명시적으로 pending(reason=sectype_mismatch)** 로 강등함(방어적 분기).

4. ambiguous → pending
   - `score_gap < 0.15`면 pending(reason=ambiguous_top2)로 강등.
   - conf 미달/후보 없음도 pending으로 남기며, 별도 파일 `instrument_registry_pending.jsonl`에 append-only 기록.

5. correlation_id + approved_by
   - approve에서 correlation-id 미지정은 즉시 차단.
   - approved_by 미지정도 즉시 차단(이전 “unknown” 허용 제거).
   - Slack 경로에서는 `_augment_bridge_args()`가 `--approved-by <slack_user_id>`를 자동 주입.

6. TOCTOU 완화 + secdef_info 2차 검증
   - check에서 `--snapshot-path`로 결과를 JSON으로 저장할 수 있고,
   - approve는 기본적으로 `--snapshot-path docs/reports/ibkr_etf_check_<corr>.json`을 소비하도록 Slack 파서가 설정됨.
   - approve는 registry write 직전에 `secdef_info(conid, sectype="ETF")`를 호출하고 실패 시 pending(reason=secdef_info_failed)로 강등.

## Risks (Residual)
- exchange_hint 표준화(예: KRX vs KSE, XETRA vs XETR)는 아직 단순 equality라, 정상 케이스가 pending으로 많이 쌓일 수 있음(안전하지만 운영 피로).
- `secdef_info`의 응답 shape이 다양할 수 있어(배열/딕트), 현재는 snapshot 저장만 하고 “정합성 검증”까지 강제하진 않음.

## Recommended Next Actions
- exchange code alias 테이블을 넣어 `exchange_hint` 매칭을 실사용 환경에 맞게 보정.
- `secdef_info`에서 확인 가능한 필드(sectype/currency/desc) 기반으로 name_hint 정합성 검증을 1단계 더 강화.

## Verdict
`red_team_clear` (Hardening v2 체크리스트 기준 충족. 첫 registry write 전에 요구된 방어 장치들이 코드 레벨에서 강제됨.)

