# Red Team Protocol
# Version: 1.0
# Date: 2026-05-14
# Owner: Chief of Staff / Red Team

---

## 1. Purpose

이 문서는 Harness의 정례 Multi-LLM Red Team 운영 규약이다.

목표는 다음 둘이다.

1. 고객이 돈을 낼 가치가 없는 산출물을 내부 착시로 통과시키지 않는다.
2. 코드, 문서, 리포트, 의사결정의 약한 고리를 매주 강제로 드러낸다.

Harness에서 Red Team은 선택적 리뷰가 아니라 **다음 단계 진입 게이트**다.

---

## 2. Weekly Cadence

### Weekly Multi-LLM Red Team

- cadence: **매주 1회 정례**
- time: **매주 월요일 10:00 KST**
- owner: Chief of Staff
- participants:
  - Claude
  - Gemini
  - Codex

정례 red-team의 기본 리뷰 범위:

1. 대표용 핵심 artifact 1건
2. 현재 발행 직전인 고객-facing 산출물 1건
3. 지난주 수정된 운영 규약/전략 문서
4. 운영 취약성 및 미해결 gate 항목

---

## 3. Decision Rule

### 3.1 Default Rule

다음 단계로 넘어가기 위한 기본 조건:

- **Claude, Gemini, Codex 세 모델의 지적사항이 모두 clear**
- unresolved issue = 0

즉, 한 모델이라도 material issue를 남기면 기본값은 **block**이다.

### 3.2 President Mediation Rule

단, 아래 경우에는 대표(President/CEO)가 중재할 수 있다.

- 특정 지적이 사업적으로 받아들일 수 없다고 판단되는 경우
- 모델 오류, 과잉 보수성, 도메인 미스리드가 명백한 경우
- 일정/전략/법률/제품 tradeoff 상 인간 판단이 우선해야 하는 경우

이 경우 다음 조건이 필요하다.

1. unresolved issue가 무엇인지 명시
2. 왜 받아들이지 않는지 서면 이유 작성
3. 남는 리스크와 추후 재검토 시점을 적음
4. 대표가 **confirm**하면 다음 단계 진행 가능

즉, 원칙은:

- **all clear -> proceed**
- **not all clear -> block**
- **not all clear but President confirm -> conditional proceed**

---

## 4. Required Output

정례 red-team이 끝나면 아래 산출물을 남긴다.

1. `weekly_red_team_memo`
2. model-by-model findings table
3. unresolved issues list
4. clear / block / conditional proceed verdict
5. President confirmation 필요 여부

권장 섹션:

```markdown
# Weekly Red Team Memo

- Week:
- Artifact(s) reviewed:
- Model set: Claude / Gemini / Codex
- Overall verdict: clear | block | conditional_proceed

## Findings by Model
- Claude:
- Gemini:
- Codex:

## Consolidated Issues
- issue
- severity
- owner
- fix status

## President Mediation
- required: yes/no
- rejected issue(s):
- rationale:
- confirm status:

## Next Step
- proceed / revise / hold
```

---

## 5. What Counts As Clear

clear는 단순히 "문제가 적다"가 아니다.

다음을 모두 만족해야 한다.

- hallucination risk 없음
- weak evidence issue 해소
- hype / overclaim 해소
- Korea-specific decision utility 존재
- claim posture (`verified / company-self-report / speculative`) 적절
- customer가 돈을 낼 이유가 artifact 안에서 설명됨

---

## 6. What Cannot Be Overridden Casually

다음은 대표 중재로도 쉽게 무시하면 안 된다.

- factual error
- fabricated source
- missing disclaimer
- legal / regulatory risk
- 투자 권유성 표현
- 독립 검증이 없는 self-report를 사실처럼 단정한 경우

이런 항목은 기본적으로 수정 후 재검토가 원칙이다.

---

## 7. Relationship To Other Gates

Red Team은 QA와 다르다.

- Red Team: 약한 주장, 과장, 반론 부재, 해석 리스크
- QA: 사실, 형식, 링크, 스키마, 용어, 렌더링
- Legal: 규제, 약관, 개인정보, 저작권

고객-facing 산출물은 아래 순서를 따른다.

1. Vice President review
2. Red Team
3. Legal review
4. QA
5. President decision

---

## 8. Non-Negotiables

- 주간 정례 red-team은 생략하지 않는다.
- Claude, Gemini, Codex 세 모델을 기본 조합으로 사용한다.
- 모델 하나만 통과해도 `clear`로 쓰지 않는다.
- unresolved issue가 남아 있으면 기본값은 block이다.
- 대표 중재가 발생하면 반드시 `왜 override했는지`를 남긴다.
