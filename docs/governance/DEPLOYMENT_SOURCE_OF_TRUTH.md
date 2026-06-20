# Deployment & Source of Truth 규약

- 버전: 1.0 | 제정: 2026-06-09
- 계기: 2026-06-09 트레이딩 로직 드리프트 사고 (아래 §5)
- 적용: 모든 사람·LLM·에이전트 (Claude, Codex, Gemini, OpenClaw 등)
- 상위 규약: `CLAUDE.md`, `docs/product/PLATFORM.md`

---

## 1. 단일 진실 공급원 (Single Source of Truth)

**`origin/main`(GitHub `junti7/harness-platform`)이 코드의 유일한 진실이다.**

- 어떤 머신의 로컬 상태도 SoT가 아니다. MBP도, Mac Mini도 origin/main의 *체크아웃*일 뿐이다.
- "내 머신에서는 된다"는 배포가 아니다. **origin/main에 들어가야 비로소 존재하는 코드**다.

## 2. Must (반드시)

- 모든 코드 변경은 **commit → push → origin/main 반영** 경로로만 흐른다.
- 프로덕션(Mac Mini)으로의 배포는 **`scripts/deploy_to_macmini.sh`**(origin/main에서 선택적 checkout)로만 한다.
- 배포 전, 배포 대상이 **origin/main에 push되어 있음**을 확인한다 (deploy 스크립트가 자동 검증).
- 코드 작업을 마치면 **그날 안에 commit+push**한다. 커밋했는데 push 안 한 코드는 "유실 예약" 상태다.
- 작업트리는 깨끗하게 유지한다. 런타임 산출물은 `.gitignore`에 등록해 추적 대상에서 뺀다.
- **OpenClaw main runtime 은 Mac Mini 에만 둔다.** Slack DM ingress(`adapters/content/slack_listener.py`), Socket Mode 연결,
  `ai.openclaw.gateway`, watchdog 는 Mac Mini 에서만 살아 있어야 하며, MBP 에서는 꺼진 상태가 정상이다.
- **MBP에서 추적 파일 commit이 발생한 작업은 그 시점에서 끝난 것이 아니다.** 같은 작업 안에서 반드시:
  1. `origin/main` push,
  2. `scripts/deploy_to_macmini.sh`로 Mac Mini 선택 배포,
  3. 필요 시 Mac Mini build/restart,
  4. MBP와 Mac Mini 양쪽에서 배포 대상 추적 파일의 `git status` 청결 검증
  까지 완료해야 한다.
- **양쪽 clean 검증 전에는 "완료", "배포됨", "반영됨"으로 보고하지 않는다.** dirty가 남으면 즉시 정리하거나 handoff에 잔여 사유/범위를 남긴다.

## 3. Never (절대 금지)

- **프로덕션(Mac Mini) 작업트리의 추적 코드 파일을 직접 편집하지 않는다.** 모든 변경은 SoT를 거친다.
- **커밋하지 않은 코드를 프로덕션에서 라이브로 운영하지 않는다.** (git에 안 보이면 다음 사람이 덮어쓴다 → 유실)
- 만성 dirty 트리 상태에서 **전체 `git pull` / `git checkout` / `git reset --hard`로 강제 동기화하지 않는다.** 미커밋 prod 작업을 파괴한다.
- 서버 간 파일을 **scp/수동 복사로 배포하지 않는다.** 드리프트의 근원이다.
- **프론트엔드를 `harness-os/frontend/` 루트에 빌드하지 않는다.** Vite 출력은 `dist/`만이며(`dist`는 gitignore됨). 루트에 `index.html`(빌드본)·`assets/`·`favicon.svg` 등이 생기면 잘못된 outDir 빌드의 잔재다 — 루트 `index.html`은 항상 dev 소스(`/src/main.tsx`)여야 한다.
- **[프론트 서빙·빌드 — 사실 정정 2026-06-20]** 프로덕션 프론트는 **백엔드가 아니라 전역 `serve` 가 빌드된 `dist/` 를 5173 에 정적 서빙**한다(launchd `com.harness.harness-os-frontend` = `/opt/homebrew/bin/serve …/dist -p 5173`; vite dev 서버 아님). 백엔드(8000)는 API 만 담당한다. **프론트 소스를 commit·push 만 하고 dist 를 재빌드하지 않으면 화면은 옛 번들 그대로다(2026-06-20 사고).** 그래서 `scripts/deploy_to_macmini.sh` 가 프론트 소스(`harness-os/frontend/src` 등) 변경을 감지하면 Mac Mini 에서 **자동으로 `npm run build`(staging dist.tmp → 원자 swap, 빌드 실패 시 기존 dist 보존)** 하고, plist 변경 시 launchd 재설치/reload 까지 수행한다. 즉 **프론트 갱신은 수동 빌드가 아니라 deploy 스크립트로 일원화**됐다. `serve` 전역 바이너리는 프론트 런타임 의존성이다(`npm i -g serve`; deploy·register_launchd 가 preflight 검증).
- MBP에서 commit만 하고 Mac Mini 선택 배포/청결 검증을 생략한 채 작업을 종료하지 않는다.
- MBP 또는 Mac Mini에서 추적 파일 dirty를 "원래 그런 상태"로 정상화하지 않는다. 반복 dirty는 출력 경로, 런타임 저장 위치, `.gitignore` 설계 문제로 간주하고 구조적으로 제거한다.
- **MBP 에서 OpenClaw 가 Slack DM 을 수신하게 두지 않는다.** MBP 에서 listener/gateway 를 수동 `nohup`, launchd, watchdog 로 살리는 행위는
  SoT 위반이자 운영 드리프트다. 발견 즉시 프로세스를 중지하고 Mac Mini 단일 runtime 으로 복귀한다.

## 4. 자동 감시 (강제 조치)

- **`scripts/check_code_drift.py`** 가 라이브 작업트리를 origin/main과 비교해 critical 코드 경로(`core/`, `adapters/`, `scripts/`, `configs/`, `harness-os/backend/`, `harness-os/frontend/src/`, `run_pipeline.py`, `CLAUDE.md`)의 드리프트를 감지한다.
- Mac Mini에서 **매일 08:00(KST) 자동 실행**되며, 드리프트 발견 시 `#exec-president-decisions`(또는 `SLACK_WEBHOOK_URL`)로 경보한다.
  - launchd: `com.harness.code-drift-check` (`scripts/install_drift_check_macmini.sh`로 설치)
- 드리프트 경보가 뜨면:
  1. 의도된 변경이면 → 즉시 commit + push (SoT 반영)
  2. 의도치 않은/실험 잔여물이면 → `git checkout origin/main -- <path>`로 정합
  3. prod에만 있는 미커밋 가치 작업이면 → 백업 후 dev로 가져와 commit + push

## 5. 무엇이 잘못됐었나 (2026-06-09 사고 기록)

- 한 LLM이 트레이딩 로직 보강을 **Mac Mini 작업트리에 직접 편집하고 커밋하지 않음** → git에 안 보임.
- 다른 LLM(Claude/MBP)은 같은 작업을 **commit 했지만 push 안 함** → 프로덕션에 도달 못 함.
- 결과: MBP와 Mac Mini가 **조용히 분기**, 양쪽 다 "내 작업이 사라졌다"고 인식.
- 추가로 Mac Mini는 **11,656개 dirty + origin 대비 17커밋 뒤처짐** → 안전한 git 동기화 불가 → 수동 파일 복사 유혹 → 드리프트 악순환.
- 다행히 유실은 없었다(트레이딩 config는 양쪽 동일, 코드는 MBP본이 더 정밀한 완성본이었음). 본 규약은 이 운(運)에 기대지 않기 위함이다.

## 6. 미해결 / 후속 (AR)

- [x] Mac Mini dirty 트리 정리: 생성형/런타임 산출물 `.gitignore` 등록 + 미커밋 prod 가치 작업 식별·SoT 반영 완료. **11,656 → ~40** (잔여는 HEAD-behind staged + 런타임 churn, prod 가치 위험 0). 드리프트 가드 green = 작업트리 코드 ≡ origin/main.
- [x] 프론트 build 정리: 빌드 아키텍처는 정상(`dist/` gitignore·백엔드 dist/ 서빙)이었고, 문제는 루트에 쏟아진 stray 빌드물. 루트 `index.html` dev소스 원복 + stray 제거 완료. §3에 재발방지 규칙 추가.
- [ ] Mac Mini HEAD를 origin/main으로 완전 정합(현재 origin보다 뒤). 두 구조적 선결: (a) read-critical 런타임 파일(`evidence_bank.json` 등) gitignore+rm--cached 시 sync 중 삭제 위험 처리, (b) 백엔드 deploy 엔드포인트의 `git stash -u && git pull`(전체 pull)을 SoT 규약(선택적 동기화)에 맞게 정비. 라이브 정비창에서 수행.
- [x] CLAUDE.md Must/Never에 본 규약 핵심 1줄 반영 (red_team_clear 후).
