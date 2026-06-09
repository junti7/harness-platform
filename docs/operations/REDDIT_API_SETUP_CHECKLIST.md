# Reddit API Setup Checklist

목적:

- `edu_consulting` / `physical_ai` 수집 파이프라인에서 Reddit 수집을 정상 가동
- `.env`와 Mac Mini runtime에 같은 credential을 반영
- dry-run으로 인증/토큰 교환까지 확인

---

## 1. Reddit 앱 생성

1. `https://www.reddit.com/prefs/apps` 접속
2. 하단 `are you a developer? create an app...` 클릭
3. 앱 타입은 반드시 `script` 선택
4. 추천 입력값:
   - name: `harness-edu-research`
   - description: `Harness edu/community signal collection`
   - about url: 비워도 됨
   - redirect uri: `http://localhost:8080`
5. 저장 후 아래 두 값을 확보
   - `client_id`
   - `client_secret`

주의:

- 현재 collector는 `client_credentials` grant만 쓰므로 user login flow는 필요 없다.
- `script` 타입이 아니면 현재 코드 경로와 안 맞는다.

---

## 2. 로컬 `.env` 반영

로컬 개발 머신 `.env`에 아래 3개를 넣는다.

```env
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=harness-edu-research/0.1
```

원칙:

- secret은 git에 커밋하지 않는다
- `.env.example`만 스키마 기준으로 유지한다

---

## 3. 로컬 검증

### 3-1. credential 유무 확인

```bash
PYTHONPATH=. .venv/bin/python scripts/check_reddit_runtime.py
```

기대 결과:

- `REDDIT_CLIENT_ID=SET`
- `REDDIT_CLIENT_SECRET=SET`
- `REDDIT_USER_AGENT=SET`

### 3-2. token 교환 / collector dry-run

```bash
PYTHONPATH=. .venv/bin/python scripts/check_reddit_runtime.py --token-only
PYTHONPATH=. .venv/bin/python scripts/run_edu_deep_research.py --sources reddit --dry-run
```

정상 시:

- token endpoint `200`
- `Reddit API credentials missing`가 아니라 실제 subreddit query 로그가 나와야 한다

---

## 4. Mac Mini runtime 반영

1. Mac Mini `.env`에도 동일한 3개를 반영
2. 코드 변경이 있다면 반드시 `commit -> push -> scripts/deploy_to_macmini.sh` 경로 사용
3. Mac Mini에서 검증

```bash
ssh juntaepark@100.97.175.44
cd ~/projects/harness-platform
PYTHONPATH=. .venv/bin/python scripts/check_reddit_runtime.py
PYTHONPATH=. .venv/bin/python scripts/run_edu_deep_research.py --sources reddit --dry-run
```

---

## 5. 완료 기준

- 로컬 `.env` 3개 값 존재
- Mac Mini `.env` 3개 값 존재
- 로컬 token 교환 성공
- Mac Mini token 교환 성공
- Mac Mini dry-run에서 subreddit query가 실제 실행됨

---

## 6. 현재 상태 (2026-06-09)

현재 확인값:

- 로컬 `.env`: `REDDIT_CLIENT_ID/SECRET/USER_AGENT` 없음
- Mac Mini `.env`: `REDDIT_CLIENT_ID/SECRET/USER_AGENT` 없음
- Mac Mini dry-run 결과: `Reddit API credentials missing; skipping reddit collector.`

즉, 코드가 멈춘 게 아니라 credential 입력 단계가 미완료다.
