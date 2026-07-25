# Smartfarm Operations Dashboard 구현 계획

- 작성일: 2026-07-25
- 대상: Mac mini Harness OS
- 상태: RED TEAM 전 구현 계획
- 목표: Raspberry Pi, ESP8268266, ESP32 기반 스마트팜의 실시간 관측·이력·진단·안전 제어를 한 화면에서 운영

## 1. 성공 기준

1. 등록된 모든 Raspberry Pi/ESP8266/ESP32를 단일 inventory에서 확인한다.
2. 온도, 습도, 토양수분, raw ADC, 펌프 실제 상태가 2초 이내 UI에 반영된다.
3. 현재값과 SQLite 이력을 1시간/24시간/7일 범위로 조회한다.
4. `online`, `stale`, `offline`, `fault`, `unknown`을 구분하고 마지막 수신 시각과 근거를 표시한다.
5. 센서/모듈 self-test 요청, 진행, timeout, 결과를 command ID로 추적한다.
6. 펌프 OFF는 즉시 실행할 수 있고, ON은 CEO 인증·zone 확인·최대 동작시간·cooldown·watchdog 확인·감사로그를 모두 통과해야 한다.
7. MQTT 명령 발행만으로 성공 처리하지 않는다. 디바이스 ack와 실제 `pump/status`가 일치해야 성공이다.
8. DB/MQTT/브로커/허브/노드 중 끊긴 경로를 서로 구분한다.
9. 모바일과 데스크톱에서 핵심 경보, 현재값, 제어 확인창을 사용할 수 있다.
10. 로컬 테스트, API 테스트, 프런트 빌드, 브라우저 QA, Mac mini 실환경 검증을 통과한다.

## 2. 현재 기반과 gap

현재 자산:

- Raspberry Pi MQTT broker 및 `pi_hub/hub.py`
- `sensor_readings`, `pump_events` SQLite 이력
- ESP32/ESP8266 공용 `soil_node.ino`
- raw ADC 고장 감지, cooldown, 최대 급수시간, follower zone 안전장치
- Harness OS FastAPI 인증과 React 운영 콘솔

부족한 계약:

- 노드 inventory/firmware/board identity/boot ID/uptime/heartbeat
- Raspberry Pi hub heartbeat 및 broker 상태
- 명령 요청, ack, 실제 상태 확인, timeout 감사로그
- 센서 self-test 결과 계약
- 실시간 dashboard API와 추세 집계
- actuator ON을 위한 독립 watchdog 확인 정보

## 3. 아키텍처

```text
ESP32 / ESP8266
  telemetry + retained heartbeat + command ack
          |
          v
Raspberry Pi Mosquitto <-> pi_hub.py deterministic irrigation
          |
          v
Mac mini Harness OS smartfarm runtime
  MQTT subscriber/publisher
  SQLite operational store
  health/state reducer
  command safety gate + audit
          |
          v
FastAPI snapshot/history/command/test APIs
          |
          v
React Smartfarm Operations Dashboard (2 s refresh)
```

초기 구현은 SSE/WebSocket보다 장애 복구가 단순한 2초 conditional polling을 사용한다. MQTT 수신부터 DB 적재는 이벤트 기반이다. UI polling 실패는 마지막 정상 snapshot을 보존하고 stale로 표시한다.

## 4. MQTT 계약

- `farm/<zone>/telemetry/<metric>`: 신규 권장 토픽
- 기존 `farm/<zone>/{soil,soil_raw,temp,humidity}`: 계속 수용
- `farm/<zone>/device/status` retained JSON:
  `device_id`, `board`, `firmware`, `boot_id`, `uptime_s`, `ip`, `rssi_dbm`,
  `watchdog_max_run_ms`, `sensor_capabilities`, `actuator_capabilities`, `ts`
- `farm/system/pi-hub/status` retained JSON:
  `device_id`, `host`, `version`, `uptime_s`, `db_ok`, `config_ok`, `zones`, `ts`
- `farm/<zone>/command/request`: `command_id`, `kind`, `issued_at`, `expires_at`, `params`
- `farm/<zone>/command/ack`: `command_id`, `accepted`, `phase`, `reason`, `observed_state`, `ts`
- `farm/<zone>/diagnostic/result`: `command_id`, 센서별 pass/fail/value/reason

payload는 크기·필드·숫자 범위를 검증한다. 알 수 없는 zone과 만료 명령은 거부한다. retained command는 금지한다.

추가 전송 규칙:

- telemetry/status는 QoS 1, command/ack/diagnostic은 QoS 1 + 애플리케이션 상태머신을 사용한다.
  저사양 ESP에서 QoS 2만 믿지 않고 `command_id`, boot-scoped monotonic `sequence`,
  `issued_at`, `expires_at`으로 중복·역순·재부팅 replay를 거부한다.
- node와 Pi hub는 LWT로 `state=offline`을 retained publish한다. 정상 status는 retained이지만
  backend는 broker 수신시각이 아니라 payload timestamp, boot ID, heartbeat deadline으로 freshness를 판정한다.
- edge node는 command payload의 MQTT retained flag가 참이면 실행하지 않는다. 부팅 직후 command
  subscription 전에 retained request를 명시적으로 삭제하고, Mosquitto ACL은 dashboard service identity만
  command publish 가능하게 제한한다.
- broker ACL은 telemetry writer, hub controller, dashboard command publisher를 분리한다. 운영망에서는
  계정별 credential과 TLS를 사용하고 anonymous publish를 금지한다. 비밀은 로그/DB/UI에 저장하지 않는다.
- clock skew를 health 항목으로 측정한다. 명령 만료는 edge monotonic receive-time deadline과
  wall-clock expiry를 함께 사용하며 허용 skew를 넘으면 ON을 거부한다.

## 5. DB

Mac mini operational SQLite 기본 경로를 환경변수로 설정한다.

- `smartfarm_devices`: identity, kind, zone, capabilities, firmware, last_seen, last payload
- `smartfarm_readings`: device/zone/metric/value/quality/source timestamp/ingest timestamp
- `smartfarm_commands`: request, actor, safety decision, publish, ack, observed result, timeout
- `smartfarm_alerts`: severity, code, lifecycle, evidence
- `smartfarm_runtime_events`: broker connect/disconnect, parse errors, config changes

단일 전용 writer queue, WAL, busy timeout, bounded retry, read-only connection을 적용한다. API handler가
MQTT callback에서 직접 DB write하지 않는다. 기존 Pi DB는 source-of-truth 급수 이력으로 유지하고 Mac mini
DB는 관제·감사 저장소다. 중복 telemetry는 `(device_id, metric, source_ts, boot_id)`로 멱등 처리한다.
raw telemetry는 기본 30일, 시간 집계는 1년 보존하며 purge job, DB size 경보, 일일 online backup,
월 1회 restore drill을 둔다. 보존값은 환경변수로 조정한다.

## 6. API

- `GET /api/smartfarm/overview`: 전체 상태, zones, devices, active alerts, runtime health
- `GET /api/smartfarm/history`: zone/device/metric/range/downsample
- `GET /api/smartfarm/devices/{id}`: identity, health evidence, capabilities, recent diagnostics
- `POST /api/smartfarm/devices/{id}/test`: read-only self-test 요청
- `POST /api/smartfarm/zones/{zone}/pump`: `off` 또는 guarded `on`
- `GET /api/smartfarm/commands/{id}`: ack/observed/timeout 상태

모든 endpoint는 Harness 인증을 사용한다. 읽기와 test는 CEO/VP, actuator는 CEO 전용이다. 입력은 Pydantic allowlist와 명시적 범위로 제한한다.

## 7. 제어 안전

펌프 OFF:

- fail-safe 우선
- 네트워크 API는 CEO 인증을 유지해 임의 OFF 공격을 막음
- 짧은 expiry
- ack 및 실제 OFF 확인
- 인증/API/Mac mini 장애와 독립된 Raspberry Pi 로컬 emergency-stop 명령과 물리 전원 차단 절차 제공
- node watchdog은 control plane 전체 장애 시 최종 OFF 수행

펌프 ON:

- `HARNESS_SMARTFARM_ACTUATION_ENABLED=true`
- CEO 인증 + 최근 5분 이내 비밀번호 재확인으로 발급된 1회용 actuation nonce
- 정확한 zone과 최대 duration 재확인
- device online, heartbeat fresh, boot ID 존재
- firmware가 watchdog duration을 보고
- 요청 duration < node watchdog
- cooldown 충족
- sensor fault 없음
- 이미 실행 중인 명령 없음
- command expiry, idempotency key
- ack 후 `pump/status=on` 관측
- timeout이면 성공 아닌 `unknown`/`failed`
- backend 재시작 시 미완료 command를 DB에서 복구해 재발행하지 않고 상태 조회만 재개
- OFF보다 낮은 sequence의 ON, 이미 처리한 command ID, 이전 boot ID 대상 명령은 edge에서 거부

진단:

- 기본 self-test는 read-only sensor sampling, bus probe, connectivity 확인만 허용
- GPIO toggle/relay test는 actuator test로 별도 분류하고 CEO 재인증 및 동일 ON gate 적용
- pump ON 또는 cooldown 중에는 bus/GPIO에 영향을 줄 수 있는 진단을 거부

대시보드는 명령 발행·ack·실제 상태 3단계를 따로 표시한다.

## 8. 화면

1. Operations header: MQTT, DB, Pi hub, online devices, critical alert, last update
2. Zone cards: 작물/zone, soil/temp/humidity, freshness, sparkline, pump state
3. Fleet table: Raspberry Pi/ESP32/ESP8266, firmware, IP, RSSI, uptime, last seen, fault
4. Live telemetry panel: 선택 metric 추세, 품질 gap, raw/processed 동시 보기
5. Alerts timeline: open/acknowledged/resolved
6. Diagnostics drawer: capability별 self-test, command progress, raw result
7. Pump control drawer: safety checklist, duration, explicit confirmation, observed outcome
8. Audit log: actor, request, safety rejection, ack, observed result

색만으로 상태를 전달하지 않고 아이콘/문구/시간을 함께 표시한다. stale data를 정상처럼 보간하지 않는다.

## 9. 구현 순서

1. smartfarm runtime 모듈, schema, MQTT payload reducer와 unit tests
2. Pi hub heartbeat 및 node heartbeat/ack/diagnostic firmware 계약
3. FastAPI read/history/test/control endpoints와 auth/safety tests
4. React page, navigation, responsive styles, loading/error/stale states
5. fixture MQTT replay로 end-to-end API 검증
6. Codex + Antigravity Gemini Flash Low 코드 RED TEAM
7. 브라우저 desktop/mobile QA
8. scoped commit/push, `scripts/deploy_to_macmini.sh`
9. Mac mini API/UI, Pi MQTT, SQLite writes, 실제 device heartbeat 검증
10. actuator는 watchdog 실증 전 OFF/test만 검증하고 ON은 차단 상태로 정직하게 보고
11. Mosquitto ACL/TLS 설정 백업, DB backup/restore, 기존 release로 rollback rehearsal

## 10. 검증

- Python: reducer/schema/history/downsample/auth/validation/idempotency/timeout/safety gate
- Firmware: ESP32 및 ESP8266 compile
- Integration: local Mosquitto 또는 fake client로 telemetry → DB → API → command ack replay
- Frontend: TypeScript build, lint, API error/stale/empty/large fleet 상태
- Browser: 1440px, 390px; 제어 confirmation과 keyboard focus
- Production:
  - Mac mini service/API health
  - MQTT broker connect와 실제 retained heartbeat
  - 실제 telemetry 수신 후 operational DB row 증가
  - Raspberry Pi/ESP device identity와 freshness
  - diagnostic request/ack/result
  - OFF 명령의 ack + observed state
  - retained ON 주입이 edge에서 거부되는지 확인
  - ESP 강제 전원 차단 후 LWT/offline 전환 확인
  - ON/OFF 역순·중복·backend 재시작 replay 확인
  - 만료 auth 상태에서도 Pi 로컬 emergency stop과 node watchdog OFF 확인
  - SQLite 동시 ingest/read 부하, purge, backup/restore 확인

## 11. 범위와 정직한 완료 조건

서버/UI 배포만으로 “모든 기기 실시간 연결 완료”라 하지 않는다. 구형 firmware 또는 미연결 센서는 `unknown`/`offline`으로 표시한다. ESP8266 DHT22 NaN은 해결된 것으로 간주하지 않는다. 릴레이/펌프 ON은 독립 watchdog과 실제 상태 경로가 검증되기 전까지 차단한다.

## 12. RED TEAM 통과 기준

- Codex와 Antigravity Gemini Flash Low가 각각 독립 review
- 둘 다 material blocker 없음
- security, actuator safety, false-green health, DB concurrency, message ordering,
  offline behavior, mobile operability, deploy/rollback 검토
- 한 모델이라도 material block이면 계획 수정 후 두 모델 재검토
- 최종 상태: `red_team_clear` 또는 `red_team_block`

## 운영 규칙

Codex CLI 사용 시 `caveman ultra` 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.
