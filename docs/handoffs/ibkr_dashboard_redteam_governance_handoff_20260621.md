# Handoff — IBKR 대시보드 가시화 · 멀티-writer 안정화 · Red-Team 거버넌스 · 점수 통일 · Deploy 자동화

- 날짜: 2026-06-21
- 작성: Codex(Claude Code, MBP)
- 범위: 직전 세션(다중 태스크) 누적 결과. `/clear` 전 보존용.
- 결과 상태: **전 태스크 완료·배포·검증 끝.** 양쪽 머신 HEAD==origin/main, 추적 파일 clean.
- 최종 커밋(내 작업 범위): `c75a176` (그 이후 `ecd02ab`~`ca175ce` VP-training 커밋은 별도 작업, 내 범위 아님)

---

## 0. 반드시 기억할 거버넌스 (이번 세션에서 확정 — 영구 규칙)

**Red Team 은 CEO(junti7)가 명시적으로 주문할 때에만 호출한다.**
- 코드/문서/의사결정/외부발행/자본집행 등 *모든 영역*에서 자동·정례·의무 red-team 폐지.
- CEO 주문 없으면 `red_team_clear` 부재가 어떤 작업도 BLOCK 하지 않음.
- 단일 출처: `docs/governance/LLM_GROUND_RULES.md §2.7`. `CLAUDE.md` BASIC RULE, `RED_TEAM_PROTOCOL.md` 배너에도 반영.
- 메모리: `feedback_redteam_ceo_triggered_only.md`.
- (CEO 주문 시) cross-LLM = 서로 다른 신뢰 LLM 최소 2개. Gemini CLI 영구 불가(`project_gemini_cli_unavailable.md`) → Codex+Copilot 만, 2 clear 불가 시 CEO confirm. red-team 은 `scripts/redteam_review.sh` (read-only) 로만.

**공유 상태파일은 통째쓰기 금지 → `update_json_atomic` 으로만.** (아래 §2)

---

## 1. 태스크별 결과

### T1~T3. IBKR 대기주문(pending orders) 대시보드 가시화
- 문제: TSM/MU/SK Hynix `PreSubmitted` 주문이 대시보드에 안 보임. 처음엔 **죽은 컴포넌트** `IbkrTurtleMonitor.tsx`(import 안 됨)에 UI를 넣어 화면에 안 나타남.
- 조치: 실제 렌더되는 `TradingOpsCenter.tsx` 로 이동. pending order 카드 + `BrokerBadge` + 브로커 필터 칩 + 트레이드-플로우 테이블(브로커/방향/수량/가격/시스템/상태 컬럼).
- 백엔드: `scripts/ibkr_turtle_monitor.py` 에 `assess_pending_order` / `_collect_pending_orders`, `run()/run_offline()/fallback` 에 pending_orders 포함. `harness-os/backend/main.py` `_is_ibkr_monitor_result` 가 pending_orders 수용.
- 커밋: `de495c5`, `440aa51`(직전), 이번 정리 범위 내.

### T9. 트레이드-플로우 브로커 구분
- 문제: 이벤트 테이블이 IBKR vs Alpaca 구분 불가.
- 조치: `main.py` `_paper_trade_flow_payload` 가 이벤트별 `broker` 필드 부여(trading_diary/paper_trading_log=alpaca, `ibkr_tws_paper_log.jsonl`=ibkr) + `_flow_fields`(side/qty/price/system/status/scanned/breakout). 프론트는 브로커 배지/필터/컬럼. 커밋 `66932b2`.

### T10. 점수 게이트 통일 (IBKR/Alpaca)
- 문제: 동일 로직인데 IBKR=TSM+MU, Alpaca=TSM만. 원인 = IBKR 무문턱 vs Alpaca ≥7.
- 조치:
  - `core/trading_universe.py`: `HARNESS_MIN_SCORE = int(os.getenv("HARNESS_MIN_SCORE","6"))` 단일 출처. `load_trading_universe(broker, fallback, min_score=None)` 가 universe.json 경로에 점수 게이트 적용. HBM/DRAM → `005930`/`000660` 직접 alias 추가(MU 매칭처럼).
  - `configs/trading/theme_ticker_map.json`: HBM 0.7→0.85(+hbm4e), memory bandwidth 0.57→0.72.
  - 두 트레이더/모니터/스캔이 모두 `min_score=HARNESS_MIN_SCORE` 전달.
  - **CEO 최종 결정: 문턱 ≥6** (≥7은 MU/SK Hynix/Samsung=6 전부 탈락시킴). 커밋 `acedb7c`, `5113bad`.

### T7. 주문 라이프사이클 reconcile/purge
- `scripts/ibkr_tws_paper_trader.py` `reconcile_pending_orders(ib, state, paper_account)`: filled→positions 승격, live 유지, stale purge. run() scan 전에 wiring. dedup guard 에 `broker_open_symbols`.

### T8 / §2. 멀티-writer race 수정 (재발방지 강력 기록)
- 사고(2026-06-21): trader 가 `000660` 승격했는데 monitor 가 되돌림 — 둘 다 상태파일 통째쓰기.
- 조치: `core/atomic_io.py` `update_json_atomic(path, mutate, *, indent, ensure_ascii)` 신설 — `fcntl.flock` 배타락(`.lock`) + 디스크 fresh 재독 + 호출자 델타만 병합 + 원자 write.
  - `ibkr_turtle_monitor.py save_state` → `_monitor_persist`(델타: nav_history/signal_alerts/baseline/last_run + pop exited_positions, **pending_orders 절대 건드리지 않음**).
  - `ibkr_tws_paper_trader.py save_state` → `_trader_persist`(pending_orders 전적 소유, promoted positions만 추가).
  - 검증: monitor 실행 후에도 `000660` positions 유지 확인.
- 강한 기록: `update_json_atomic` docstring, `docs/governance/RED_TEAM_LOG.md` 2026-06-21 멀티-writer postmortem, 메모리 `project_state_file_multiwriter_lock.md`.
- 양쪽 `load_state` hardened: positions/pending_orders 가 dict 아니면 {} 로 강제.

### T11. Deploy [4d] 백엔드 reload 트리거 확장
- `scripts/deploy_to_macmini.sh` [4d] 가 `core/*|scripts/*` 변경에도 백엔드 launchd reload(bootout 대기 + bootstrap 재시도 + :8000 검증). 이전엔 백엔드가 stale in-memory 코드로 MU 미표시. 커밋 `bde864b`.
  - 관련 이전 수정: [4b] dist staging-swap 자동빌드(dist.tmp→dist, dist.prev 롤백, `.build_commit` 스탬프), [4c] serve-dist plist reload + legacy `com.harness.frontend` 잡 퇴역. `bf0224c`, `32dedad`.

### T12. 해외 ETF 확인 패널 — `[Errno 61]` → 중립 정보 톤
- 원인 1: CP 게이트웨이(:5001) 미가동 + 위장 fallback 이 죽은 포트 검색 강행 → raw errno 노출. 조치: 위장 제거, `cp_authenticated` 체크, `cp_gateway_required: true` + 명확 안내. `8d0433b`.
- 원인 2: `items_total: 0` = ETF 화이트리스트 상대경로가 백엔드 cwd(`harness-os/backend`)에서 안 풀림. 조치: `scripts/openclaw_codex_bridge.py` `ETF_WHITELIST_PATH` 절대경로화. `641d6a1`.
- 마무리(옵션1, 중립 톤): `TradingApiMonitor.tsx` 가 `cp_gateway_required` 분기 → `.etf-check-dormant` 회색 정보 카드(“CP 게이트웨이 필요 · 현재 비활성” 칩 + “자동매매와 무관, 매매 영향 없음” + “확인 대기 항목: N개 ETF”). `types.ts` 필드 추가, `App.css` 중립 CSS. `c75a176`.
- 결론: 이 패널은 실매매 무관 검증 유틸 → **현행 유지**. 추후 해외 ETF 분산매매 로드맵 진입 시 CP 게이트웨이(다지역) vs TWS(US) 택1 활성화.

---

## 2. 재발방지 인프라 (재사용)
- `core/atomic_io.py::update_json_atomic` — 공유 상태파일 멀티-writer 안전. **신규 공유 상태파일은 통째쓰기 금지, 반드시 이걸로.**
- deploy 자동빌드([4b]) + 자동 백엔드 reload([4d], core/scripts 포함).
- `scripts/check_code_drift.py` — 매일 08:00 드리프트 가드 + dist-freshness(`.build_commit` vs origin frontend-src commit).

---

## 3. 운영 메모 (변하지 않는 제약)
- 배포: commit→push→origin/main, **`scripts/deploy_to_macmini.sh` 로만**. Mac Mini 수동수정/scp 금지. 양쪽 끝 clean(dirty 0, HEAD==origin).
- Mac Mini SSH: alias `macmini`, 사용자명 `juntaepark`(점 없음). `juntae.park@`는 실패+훅 차단.
- 프로덕션 프론트 = `serve dist`(:5173, launchd `com.harness.harness-os-frontend`), vite dev 아님. 백엔드 uvicorn :8000.
- 트레이딩 capital_action = `turtle_gate_clear` + `CAPITAL_ACTIONS_ENABLED=true`(기본 false).
- IBKR 두 경로: TWS/IB Gateway(:4002, ib_insync, DUQ416334) = 자동매매. Client Portal API(:5001) = 별개, 미가동.

## 4. 내 범위 아님 (건드리지 말 것)
- `EduVpTrainingPage.tsx` 및 VP-training 커밋(`ecd02ab`~`ca175ce`), 미추적 edu_* 파일, `run_edu_pilot_simulations.py`, `test_edu_pilot_simulations.py` — 다른 작업 트랙.
- `data/harness.db` — 로컬 런타임 산출물(미추적, 무시).

## 5. 미결/후속 (현재 없음)
- 직전 세션 태스크는 전부 완료·검증. 새 지시 대기 상태.
