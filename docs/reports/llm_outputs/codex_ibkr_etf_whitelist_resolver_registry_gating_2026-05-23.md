# IBKR ETF Whitelist Resolver + Registry Gating — Codex Red-Team (2026-05-23)

## Objective
IBKR CP API 기반 `ibkr-etf-check`(read-only) / `ibkr-etf-approve`(append-only registry write) 설계/코드의 catastrophic 실패 모드(잘못된 conid, 권한/거래가능성 오판, 승인 우회)를 식별하고, 실행 전 보강안을 제시한다.

## Findings

1. **Wrong-instrument(잘못된 conid) 자동 확정 위험이 남아있다.**
   - `_pick_best_candidate()`가 `sectype == STK`도 가산점을 주고, `name_hint`를 전혀 쓰지 않아 “동일/유사 ticker” 충돌 시 ETF가 아닌 종목이 conf>=0.85로 확정될 수 있다.
   - 특히 EU/JP/KRX는 ticker 표기/거래소 코드가 IBKR에서 다르게 나오는 경우가 잦아 `exchange_hint`가 제대로 작동하지 않을 수 있다.

2. **Authenticated guard가 ‘missing key’ 케이스에 취약하다.**
   - `auth.get("authenticated") is False` 조건은 key가 없으면 통과한다(`None is False` → False).
   - CP API는 오류/제약 상황에서 shape이 흔들릴 수 있으므로 `authenticated is not True`로 막아야 한다.

3. **Confidence threshold는 “CEO가 낮출 수 있는” 옵션이면 안 된다.**
   - `--min-confidence`는 서버에서 하한을 강제(clamp)해야 한다.
   - 지금 상태에서는 실수/오조작으로 0.0 같은 값이 들어오면 대량의 conid가 자동 기록될 수 있다.

4. **‘registry 기록’은 downstream에서 tradable로 오해될 가능성이 높다.**
   - 현재 approve는 `secdef_search`만으로 기록한다.
   - 최소한 `permission_verified=false`, `tradable=unverified` 같은 필드로 “아직 거래가능성/권한 확인 안됨”을 강제 표기해야 한다.

5. **Ambiguous candidate 처리(“human confirm required”)가 부족하다.**
   - 현재는 conf threshold 미달이면 “skip”되고, 어떤 항목이 왜 스킵됐는지/후속 조치가 무엇인지가 약하다.
   - pending queue(예: `instrument_registry_pending.jsonl`)로 “확정 대기”를 남기는 게 안전하다.

## Risks

- **Catastrophic:** 잘못된 conid가 registry에 기록되고, 후속 자동매매(또는 사람이 registry를 신뢰)에서 엉뚱한 자산이 매매됨.
- **High:** `authenticated` shape 변동으로 mutation guard가 우회됨.
- **High:** CEO가 아닌 사용자가 approve intent를 만들려는 시도(현재는 `_authorize_structured_command`로 막히지만, Slack listener가 죽으면 운영자가 임시 우회할 유인이 생김).
- **Medium:** registry에 “permission checked”가 없는 상태에서 조직 내 오해로 운영 리스크 확대.

## Recommended Next Actions (Hardening)

1. `authenticated` guard를 다음으로 변경:
   - `if auth.get("authenticated") is not True: block`
2. `--min-confidence`를 bridge에서 `max(0.85, arg)`로 clamp (또는 플래그 제거).
3. `_pick_best_candidate()`에서 whitelist `type`과 candidate `sectype`를 강하게 연동:
   - 기본은 `sectype == ETF`만 auto-approve 가능
   - `STK`는 `name_hint` 강매칭 + 추가 검증(`secdef_info`)가 있을 때만 예외 허용
4. `name_hint`를 스코어링에 반영(필수 조건으로 격상).
5. `secdef_info(conid)`로 2차 검증 후 기록:
   - verify 결과를 `permission_verified=false/true`, `tradable=unverified` 등으로 분리 기록
6. pending queue 도입:
   - conf 미달/동률/거래소 불일치 등은 `instrument_registry_pending.jsonl`에 후보 전체를 남기고, per-item explicit approve만 허용.
7. approve 실행은 correlation-id(회의/AR/decision card) 필수로:
   - registry row에 `correlation_id`, `approved_by_slack_user_id`를 포함.

## Verdict
`red_team_block` (보강 1~4는 non-negotiable. 특히 authenticated guard + ETF/sectype gating 없이는 Phase-1 자동 확정/registry 기록을 진행하면 안 됨.)

