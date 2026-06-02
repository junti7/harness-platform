# Harness Engineering Ground Rules
# 최초 작성: 2026-05-28 | CEO 지시 기반

---

## 규칙 1 — Mac Mini가 항상 최종 프로덕션 환경이다

**[매우 중요]**

Harness의 모든 코드 변경, 스크립트 실행, 데이터 기록, 파이프라인 실행의 **최종 실행 환경은 Mac Mini**다.

| 환경 | 역할 | 주의 |
|------|------|------|
| MacBook Pro (MBP) | 개발·테스트·코드 작성 | 여기서만 실행하면 안 됨 |
| Mac Mini (100.97.175.44) | **프로덕션. 최종 실행처** | 항상 여기서 검증 완료해야 함 |

### 적용 범위

- Python 스크립트 실행 (데이터 수집, 거래, 리포트 생성 등)
- 파일 기록 (일기장, 로그, JSON 등)
- LaunchAgent / cron job
- 프론트엔드 빌드 결과물 서빙
- 백엔드 API 서빙

### 위반 사례 (이렇게 하면 안 됨)

```
❌ MBP에서 python scripts/trading_diary.py 실행 후 "기록 완료"라고 보고
   → Mac Mini Harness OS에는 반영이 안 됨

❌ MBP에서 npm run build 후 로컬에서 확인 후 "배포 완료"라고 보고
   → Mac Mini 프론트엔드는 여전히 구 버전

❌ MBP 터미널에서만 동작 확인 후 완료 처리
```

### 올바른 순서

```
1. MBP에서 코드 작성 + 테스트
2. git commit + git push
3. Mac Mini에서 git pull
4. Mac Mini에서 실행/빌드/배포
5. Mac Mini 기준으로 결과 확인 후 보고
```

### SSH 접근

```bash
ssh juntaepark@100.97.175.44
```

- 키 등록 완료 (2026-05-28 확인)
- Remote Login ON

### 자동화된 작업의 최종 확인

LaunchAgent, cron job, 스케줄러가 등록된 경우:
```bash
# Mac Mini에서 실행 중인지 확인
ssh juntaepark@100.97.175.44 "launchctl list | grep harness"
```

---

## 규칙 2 — 프론트엔드 빌드는 Mac Mini에서 완료해야 서빙된다

Harness OS 웹 화면은 Mac Mini의 FastAPI 백엔드가 `dist/` 폴더를 서빙한다.

MBP에서 빌드해도 Mac Mini `dist/`가 바뀌지 않으면 화면에 반영되지 않는다.

```bash
# Mac Mini 배포 원스텝
ssh juntaepark@100.97.175.44 "
  export PATH=/opt/homebrew/bin:\$PATH &&
  cd ~/projects/harness-platform &&
  git pull &&
  cd harness-os/frontend &&
  npm install --prefer-offline &&
  npm run build &&
  cd ../.. &&
  launchctl kickstart -k gui/\$(id -u)/com.harness.backend
"
```

---

## 규칙 3 — 환경 변수(.env)는 Mac Mini 기준이 원본이다

`.env`는 git에 커밋되지 않는다. MBP와 Mac Mini의 `.env`는 독립적이다.

코드에서 기본값을 바꿔도 Mac Mini `.env`에 같은 키가 설정돼 있으면 `.env`가 우선한다.

확인 방법:
```bash
ssh juntaepark@100.97.175.44 "grep '변경할키' ~/projects/harness-platform/.env"
```

---

## 규칙 4 — 파일 수정 전/후 항상 커밋 (즉시 롤백 보장)

AI Agent는 코드를 수정하거나 기능을 변경할 때, 예기치 않은 버그 발생 시 즉시 이전 상태로 되돌릴 수 있는 체계를 유지해야 한다.

1. **작업 전 베이스라인 확보**: 코드를 수정하기 **전**에 현재 작업 트리가 깨끗한지(또는 안전한지) 확인하고, 필요 시 커밋하여 롤백 가능한 기준점을 확보한다.
2. **작업 후 즉시 커밋**: 의미 있는 단위의 수정이 완료되면, 즉시 `git add <수정된 파일> && git commit -m "..."`을 실행해 새로운 롤백 지점을 만든다. 여러 파일을 수정하더라도 `dist` 같은 gitignore 파일 때문에 `git add .`이 막히지 않도록 수정된 소스 파일만 명시적으로 커밋한다.
3. **즉각적 롤백 (버그 발생 시)**: 수정한 코드가 오작동할 경우, 디버깅하며 시간을 끌지 말고 즉시 안전한 커밋 지점으로 되돌린다:
   - 특정 커밋으로 강제 복구: `git reset --hard <안전한_커밋해시>` (해시 확인: `git log --oneline -5`)
   - 방금 한 커밋만 취소(파일 되돌림): `git revert HEAD`
   - 아직 커밋하지 않은 작업 중단: `git checkout -- <파일>` 또는 `git reset --hard HEAD`

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-28 | 최초 작성. CEO 지시: "항상 Mac Mini가 최종이 되어야 한다" |

## 5. Rollback Policy (Fast Recovery)
- **Immediate Revert**: If any code change introduces a regression or visibility issue on production (e.g. `http://100.97.175.44:8000/`), the agent must prioritize reverting the problematic change using Git immediately before attempting deep debugging.
- **Data Integrity**: Database schema or state modifications must always provide a safe rollback command or mechanism. For unrecoverable data modifications, always create a snapshot or dump beforehand.
