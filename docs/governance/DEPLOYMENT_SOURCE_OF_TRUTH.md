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

## 3. Never (절대 금지)

- **프로덕션(Mac Mini) 작업트리의 추적 코드 파일을 직접 편집하지 않는다.** 모든 변경은 SoT를 거친다.
- **커밋하지 않은 코드를 프로덕션에서 라이브로 운영하지 않는다.** (git에 안 보이면 다음 사람이 덮어쓴다 → 유실)
- 만성 dirty 트리 상태에서 **전체 `git pull` / `git checkout` / `git reset --hard`로 강제 동기화하지 않는다.** 미커밋 prod 작업을 파괴한다.
- 서버 간 파일을 **scp/수동 복사로 배포하지 않는다.** 드리프트의 근원이다.

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

- [ ] Mac Mini의 11,656 dirty 트리 정리: 런타임 산출물 `.gitignore` 등록 + 미커밋 prod 가치 작업(`TradingOpsCenter.tsx`, `evidence_bank.json` 등) 식별·SoT 반영 → 안전한 전체 동기화 복원.
- [ ] Mac Mini HEAD를 origin/main으로 정합(현재 17커밋 뒤) — 위 dirty 정리 선행 필요.
- [ ] CLAUDE.md Must/Never에 본 규약 핵심 1줄 반영 (red_team_clear 후).
