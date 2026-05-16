# LLM CLI Auth Runbook
# Version: 1.0
# Date: 2026-05-10

---

## 1. Purpose

Harness는 고강도 자동화를 위해 Claude, Gemini, GitHub Copilot 등 외부 LLM을 CLI 환경에서 호출한다.

다만 최초 로그인/OAuth 승인은 사람이 직접 수행해야 한다. Codex는 API key, OAuth code, browser login credential을 대신 입력하거나 출력하지 않는다.

---

## 2. Current Required Logins

### 2.1 Claude CLI

Status command:

```bash
claude auth status
```

Login command:

```bash
claude auth login
```

성공 확인:

```bash
claude auth status
```

Expected:

```json
{
  "loggedIn": true
}
```

---

### 2.2 Gemini CLI

Gemini CLI는 별도 `auth` subcommand가 없고, 첫 실행 시 브라우저 인증을 요구한다.

Login/init command:

```bash
gemini
```

또는:

```bash
gemini -p "auth smoke test" --approval-mode plan
```

브라우저 인증 페이지가 뜨면 Google 계정으로 로그인한다.

성공 확인:

```bash
gemini -p "Return only: gemini_ok" --approval-mode plan
```

Expected:

```text
gemini_ok
```

---

### 2.3 GitHub Copilot CLI

Login command:

```bash
copilot login
```

Copilot CLI는 OAuth device flow를 사용한다. 브라우저에서 GitHub 계정으로 승인한다.

성공 확인:

```bash
copilot -p "Return only: copilot_ok" --no-ask-user --silent
```

Expected:

```text
copilot_ok
```

Alternative for automation:

```bash
export COPILOT_GITHUB_TOKEN=github_pat_...
```

주의:

- classic `ghp_` token은 지원하지 않는다.
- fine-grained PAT는 `Copilot Requests` permission이 필요하다.
- token 값은 `.env`, Slack, logs, markdown 문서에 출력하지 않는다.

---

## 3. Post-Auth Cross-LLM Review

인증 완료 후 Codex가 다음 역할 분담으로 issue review를 실행한다.

| CLI | Role |
| --- | --- |
| Claude | Legal / reputation review |
| Gemini | Red Team / factual adversarial review |
| GitHub Copilot | QA / format / structure review |

`Physical AI Weekly #001` 기준 대상 파일:

- `docs/issues/physical_ai_weekly_001_2026-05-10.md`
- `docs/reviews/physical_ai_weekly_001_gate_review_2026-05-10.md`

완료 전까지 다음 approval은 기록하지 않는다:

- `legal_review_approve`
- `red_team_clear`
- `qa_clear`

---

## 4. Security Rules

- CLI 인증 토큰을 채팅에 붙여 넣지 않는다.
- `.env` 내용을 출력하지 않는다.
- OAuth code는 사람이 브라우저에서 직접 처리한다.
- 인증 후 smoke test 결과만 공유한다.
