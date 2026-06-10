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
- **`ensure_gateway_up()`**: 포트 4002 미응답이면 **`scripts/start_ibgateway_ibc.sh`를 트리거**(단일 진입점). 이 스크립트가 GUI 세션 확인 → IBC `-inline` 무인 로그인 → 실패 시 `open` 폴백까지 처리. → 장애 B 자동 해결.
- 모든 복구 동작은 `#exec-president-decisions` Slack로 통보(✅ 복구 / 🚨 실패+수동필요).

### Layer 2 — IBC 무인 로그인 (게이트웨이 근본 / 수동 로그인 제거)
`~/IBC/` (IBC.jar + `config.ini`): `IbLoginId`+`IbPassword` 저장, `ReloginAfterSecondFactorAuthenticationTimeout`(2FA 타임아웃 자동 재로그인), `AutoRestartTime`(일일 **무중단** 재시작 — 2FA 재입력 없이 세션 유지). → 일일 로그아웃이라는 **가장 흔한 원인을 무인 처리**.

**수동 로그인의 근본 원인 2가지(2026-06-10 라이브 테스트로 규명):**

1. **IBC 런처의 Terminal 자동화 타임아웃** — `gatewaystartmacos.sh`(인자 없이)는 `osascript`로 Terminal을 조종해 `$0 -inline`을 새 창에서 실행하는데, 비대화형/launchd 컨텍스트에선 AppleEvent가 타임아웃(`-1712`)된다. **해결: `-inline` 인자로 직접 호출** → `displaybannerandlaunch.sh`를 곧장 `exec`(Terminal/osascript 우회). 기존 `start_ibgateway_ibc.sh`가 이름과 달리 수동 `open`만 했던 것을, **`gatewaystartmacos.sh -inline` 호출로 교체**.

2. **`java.awt.HeadlessException`(GUI 세션 필수)** — IB Gateway는 GUI(Aqua) 데스크톱 세션이 **반드시** 필요하다. SSH로 띄운 프로세스는 GUI 세션 밖이라 `getScreenSize`에서 HeadlessException으로 즉시 종료(exit 1107). **해결: 게이트웨이 기동은 항상 launchd LaunchAgent(`domain=gui/<uid>`)가 수행**한다 — `com.harness.ibgateway`(부팅)·`com.harness.ibkr-watchdog`(자가복구) 모두 gui 도메인이라 스크립트·Popen 자식이 GUI 세션을 상속한다. (수동 SSH 실행은 운영 경로가 아니다. `launchctl asuser`는 root 필요라 미사용.)

**검증:** IBC 로그(2026-06-02) `Login attempt: 1 → Click button: Paper Log In → Login has completed`(~5초, **2FA 벽 없음**) — paper 계정 무인 로그인 자체는 실측 성공. (단 GUI 세션 안에서 실행됐을 때 한정.)

**복구 동작(`start_ibgateway_ibc.sh`):** ① 콘솔 GUI 세션이 juntaepark인지 확인(아니면 즉시 🚨 알림 — Aqua 세션 없으면 어떤 방법으로도 불가) → ② IBC `-inline` 무인 로그인(최대 90s 대기) → ③ 실패 시 `open` 폴백(60s) → ④ 그래도 미연결이면 수동 2FA 알림.

> ⚠️ **구조적 한계 — 재부팅 시 GUI 세션 부재 (CEO 결정: FileVault 유지):** Mac Mini는 **FileVault ON**이라 macOS GUI 자동 로그인을 켤 수 없다(자동 로그인은 FileVault와 상호 배타). 따라서 **재부팅 시 화면에서 FileVault 잠금해제 + GUI 로그인 1회**가 필요하며, 그 전까지 Aqua 세션이 없어 게이트웨이를 못 띄운다.
> - **2026-06-10 CEO 결정: FileVault 유지(보안 우선).** 디스크에 IB 비밀번호(IBC config.ini)·secret이 있어 암호화를 유지한다. 재부팅은 드문 일(정전·OS 업데이트·크래시)이고, **평상시(재부팅 없을 때) 자동매매 무중단은 이미 달성**(게이트웨이 로그아웃·트레이더 잡 언로드 모두 watchdog 무인 자가복구). reboot-proof(FileVault OFF + 자동 로그인 ON)는 채택하지 않음.
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
| **재부팅 시 Aqua 세션 없음(FileVault ON)** | 스크립트가 GUI 세션 부재 감지 시 🚨 알림 | CEO 결정으로 FileVault 유지(보안 우선) — 재부팅 시 화면에서 잠금해제 1회 수용. reboot-proof 미채택 |
| ~~IBC `-inline` 무인 로그인 prod 미검증~~ | ✅ **2026-06-10 실측 검증 완료** (Login completed ~6초, 2FA 없음, setsid 분리로 생존) | — |
| IBC 미설치 환경 | 폴백 `open` + 🚨 2FA 수동 알림 | — (prod엔 IBC 설치됨) |
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
