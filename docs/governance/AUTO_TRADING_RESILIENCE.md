# 자동매매 복원력(Resilience) — 중단 방지 & IB Gateway 로그아웃 근본 대책

- 작성일: 2026-06-10
- 트리거: (1) 트레이더 launchd 잡이 언로드돼 자동 execute가 멈춤(2026-06-10 발견), (2) IB Gateway 로그아웃 시 거래불가
- 원칙: **알림만 하지 말고 자가복구(self-healing)한다.** + 명시적 kill-switch는 존중한다.

---

## 1. 관측된 두 장애 모드

| # | 장애 | 증상 | 근본 원인 |
|---|---|---|---|
| A | **자동매매 중단** | 트레이더 잡(`turtle-auto-trader`/`ibkr-auto-trader`)이 launchd에서 언로드 → 스케줄에 발화 안 함 | 리셋/수동 작업이 잡을 언로드한 뒤 아무도 재로드 안 함. 기존 watchdog·runtime-guard는 **탐지·알림만** 하고 복구 안 함 |
| B | **거래불가(게이트웨이)** | IB Gateway 로그아웃/프로세스 종료 → 포트 4002 미응답 → 모든 IBKR 주문 실패 | 일일 강제 로그아웃, 프로세스 크래시, Mac 재부팅. 기존 `start_ibgateway_ibc.sh`는 이름과 달리 **수동 `open`+2FA**라 무인 복구 불가 |

---

## 2. 다층 방어 (현재 적용)

### Layer 0 — 상시 로드 (기본)
- 트레이더 plist는 `~/Library/LaunchAgents`에 있어 **로그인 시 자동 로드**. plist에 `--execute` + `PAPER_TRADING_AUTO_EXECUTE=true`. 스케줄: 평일 Alpaca 13:30 / IBKR 13:35 UTC(미국장 개장).

### Layer 1 — 자가복구 watchdog (5분 주기, 핵심)
`scripts/pipeline_watchdog.py` (launchd `com.harness.ibkr-watchdog`, StartInterval 300s):
- **`ensure_trader_jobs_loaded()`**: 두 트레이더 잡이 언로드면 `launchctl load`로 **자동 재로드**. → 장애 A 자동 해결.
- **`ensure_gateway_up()`**: 포트 4002 미응답이면 **IBC 무인 런처(`~/IBC/gatewaystartmacos.sh`)로 자동 재시작**. → 장애 B 자동 해결.
- 모든 복구 동작은 `#exec-president-decisions` Slack로 통보(✅ 복구 / 🚨 실패+수동필요).

### Layer 2 — IBC 무인 로그인 (게이트웨이 근본 / 수동 로그인 제거)
`~/IBC/` (IBC.jar + `config.ini`): `IbLoginId`+`IbPassword` 저장, `ReloginAfterSecondFactorAuthenticationTimeout`(2FA 타임아웃 자동 재로그인), `AutoRestartTime`(일일 **무중단** 재시작 — 2FA 재입력 없이 세션 유지). → 일일 로그아웃이라는 **가장 흔한 원인을 무인 처리**.

**검증:** IBC 로그(2026-06-02) `Login attempt: 1 → Click button: Paper Log In → Login has completed`(~5초, **2FA 벽 없음**) — paper 계정 무인 로그인 실측 성공.

**수동 로그인의 근본 원인(2026-06-10 발견 & 해결):** 부팅 자동기동 잡 `com.harness.ibgateway`(RunAtLoad=true)가 실행하던 `scripts/start_ibgateway_ibc.sh`가 **이름과 달리 IBC를 안 쓰고 수동 `open`** 만 했다 → 매번 대표가 비밀번호+2FA를 직접 입력. **수정:** 이 스크립트를 **진짜 IBC 런처(`~/IBC/gatewaystartmacos.sh`) 호출로 교체**. 이제 부팅 잡과 watchdog 모두 IBC 무인 로그인을 사용 → **IBC가 설치된 prod에서는 대표 수동 로그인 불필요**.

> ⚠️ **단, IBC 미설치 시에는 수동 로그인이 남는다.** `~/IBC/gatewaystartmacos.sh`가 없으면 스크립트·watchdog 모두 **폴백으로 `open GW_APP`** 를 실행하며 이 경우 비밀번호+2FA 수동 승인이 필요하다(🚨 Slack 알림). prod에는 IBC가 설치돼 있어 정상 경로는 무인이지만, 무인 로그인 제거는 **IBC 설치를 전제**로 한다.
>
> IBC 런처의 raw stdout/stderr는 설정 파싱 진단·계정ID 등이 섞일 수 있어 사람용 로그(`docs/reports/ibgateway_ibc.log`)와 분리해 **gitignore 대상 `runtime/ibgateway_ibc_raw.log`** 로 보낸다(저장소 미추적).

### Layer 3 — 재시작 폭주 방지 + 단일 실행 락
- **단일 실행 락:** `runtime/gateway_restart.lock`에 `flock(LOCK_EX|LOCK_NB)`. watchdog 실행이 겹쳐도(launchd 중첩) **런처는 단 한 번만** 기동(이중 실행 방지). 락 획득 후 포트 4002를 재확인해 그 사이 복구됐으면 중단.
- **쿨다운:** `runtime/gateway_restart_cooldown`로 재시작 **최소 10분 간격** 강제. 타임스탬프는 spawn **직전** 기록 → watchdog가 spawn 직후 죽어도 storm이 남지 않음. 단, `Popen` **자체가 예외로 실패**한 경우에만 쿨다운을 해제해 다음 주기 즉시 재시도(가용성 보호). 복구가 수렴 안 하면 CEO 알림(무한 재시작 금지).

### Layer 4 — 명시적 Kill-switch (자가복구보다 우선)
자가복구가 CEO의 의도적 정지를 덮어쓰지 못하게 하는 안전장치. **정지는 반드시 플래그로** 한다(단순 `launchctl unload`는 자가복구가 되살리도록 설계된 동작이므로 정지 수단이 아니다).
- `runtime/auto_trading_disabled` → `ensure_trader_jobs_loaded()`가 트레이더 잡 자동 reload 건너뜀(자동매매 정지).
- `runtime/ibgateway_disabled` → `ensure_gateway_up()`가 게이트웨이 자동 재시작 건너뜀(게이트웨이 의도적 다운).

| 동작 | 명령 |
|---|---|
| 자동매매 중단 | `touch runtime/auto_trading_disabled` (+ 필요시 트레이더 잡 unload) |
| 자동매매 재개 | `rm runtime/auto_trading_disabled` (다음 watchdog 주기에 자동 재로드) |
| 게이트웨이 중단 | `touch runtime/ibgateway_disabled` |
| 게이트웨이 재개 | `rm runtime/ibgateway_disabled` |

---

## 3. 안전성 — 자가복구가 위험을 만들지 않는가

- 잡 **재로드 ≠ 즉시 거래**. plist는 `RunAtLoad=false`라 로드해도 스케줄 시각에만 발화.
- 리셋 중(`reset_pending && not flat`)이면 `run_trading_cycle`이 진입을 **차단**하므로, 재로드돼도 리셋 도중 오발주 없음.
- 진입은 항상 Turtle 게이트(20/55일 브레이크아웃·ATR·손절·리스크≤1%) 통과 시에만.
- 실자본은 별개 차단 유지(`CAPITAL_ACTIONS_ENABLED=false`, AR-018). 본 체계는 **paper** 자동매매 연속성 보장용.

---

## 4. 잔여 리스크 & 다음 강화

| 리스크 | 현재 완화 | 추가 강화(권고) |
|---|---|---|
| IBC 미설치 환경 | 폴백 런처 + 🚨 2FA 수동 알림 | — (prod엔 IBC 설치됨) |
| 게이트웨이 프로세스가 KeepAlive 없이 죽음 | 5분 watchdog가 재시작 | **전용 launchd 잡(`com.harness.ibgateway`, KeepAlive=true)** 추가 시 즉시 재기동 |
| 신규 기기 2FA 푸시 | IBC 2FA 타임아웃 자동 재로그인 | IB Key 자동승인/디바이스 신뢰 등록 |
| watchdog 자체 중단 | launchd가 5분 주기 유지 | runtime-guard(10분)가 watchdog 잡 상태도 점검 |
| 게이트웨이 자체 AutoRestart 미설정 | IBC config `AutoRestartTime=05:00` | 실행 중 게이트웨이 GUI에서 Auto-Restart 활성 확인(분기 1회) |

---

## 5. 운영 점검(상시)
- 대시보드 트레이딩 패널 **스케줄러 칩**: `자동 execute 활성 / Alpaca ON · IBKR ON` 확인.
- `launchctl list | grep -E "turtle-auto|ibkr-auto|ibkr-watchdog"` — 세 잡 로드 확인.
- watchdog 로그: `logs/ibkr-watchdog.log`.
- 게이트웨이 상태: `docs/reports/ibkr_gateway_runtime_status.json`.
