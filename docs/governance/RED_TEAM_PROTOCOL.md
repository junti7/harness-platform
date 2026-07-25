# Red Team Protocol
# Version: 1.2
# Date: 2026-07-25
# Owner: Chief of Staff / Red Team

---

> **[BASIC RULE — 최상위 우선, 2026-06-20 CEO 지시]**
> cross-LLM Red Team 은 **CEO(junti7)가 명시적으로 주문할 때에만** 수행한다. 코드/MD/의사결정/외부발행/
> 자본집행 등 *모든 영역*에서 자동·정례·의무 red-team 을 돌리지 않는다. **정례(주 1회) red-team 은 폐지.**
> 아래 절차는 CEO 가 red-team 을 주문한 경우에만 적용된다. 단일 출처: `docs/governance/LLM_GROUND_RULES.md`.

---

## 1. Purpose

이 문서는 Harness의 CEO 주문형 Multi-LLM Red Team 운영 규약이다.

목표는 다음 둘이다.

1. 고객이 돈을 낼 가치가 없는 산출물을 내부 착시로 통과시키지 않는다.
2. 코드, 문서, 리포트, 의사결정의 약한 고리를 매주 강제로 드러낸다.

Harness에서 Red Team은 선택적 리뷰가 아니라 **다음 단계 진입 게이트**다.

---

## 2. Invocation And Cost Boundary

- 자동·정례·주간 Red Team은 폐지한다.
- `--ceo-order-id` 없는 호출은 실패해야 한다.
- 기본 조합은 서로 다른 두 모델 `Codex + Antigravity Gemini Flash Low`다.
- artifact hash와 모델 조합이 같으면 저장된 결과를 재사용한다.
- 대표가 재검증을 명시하면 `--force-revalidate`로 캐시를 우회하며, 자동 재시도는 하지 않는다.
- 기본 paid API budget은 `$0`; quota 불명 시 유료 fallback하지 않는다.
- 세 번째 모델은 두 reviewer 충돌 또는 non-negotiable finding이 있을 때 대표가 별도 주문한다.
- Copilot은 기본 Red Team 경로에서 제외하고 개발 보조로만 사용한다.

---

## 3. Decision Rule

### 3.1 Default Rule

다음 단계로 넘어가기 위한 기본 조건:

- 서로 다른 두 모델이 모두 clear해야 `red_team_clear`다.
- 충돌하면 자동으로 세 번째 모델을 호출하지 않고 대표에게 escalate한다.

다만 아래 항목은 단순 다수결로 넘기지 않는다.

- factual error
- fabricated source
- missing disclaimer
- legal / regulatory risk
- 투자 권유성 표현
- 독립 검증이 없는 self-report를 사실처럼 단정한 경우

이런 항목은 1개 모델만 지적해도 기본적으로 수정 후 재검토 또는 President confirm이 필요하다.

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

- **2-of-2 clear -> proceed**
- **1개 이상 material block -> block 또는 대표 escalation**
- **non-negotiable finding 존재 -> fix or President confirm**
- **모델 충돌 but President confirm -> conditional proceed**

---

## 4. Required Output

주문형 red-team이 끝나면 아래 산출물을 남긴다.

1. `red_team_memo`
2. model-by-model findings table
3. unresolved issues list
4. clear / block / conditional proceed verdict
5. President confirmation 필요 여부

권장 섹션:

```markdown
# Red Team Memo

- Week:
- Artifact(s) reviewed:
- Model set: Codex / Antigravity Gemini Flash Low
- Approval rule: 2-of-2 clear unless non-negotiable finding exists
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

이런 항목은 기본적으로 수정 후 재검토가 원칙이다. 두 reviewer가 clear여도 그대로 자동 통과시키지 않는다.

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

- 주간 정례 red-team을 실행하지 않는다.
- CEO 주문 ID 없는 red-team을 실행하지 않는다.
- 기본 reviewer 수는 2개로 제한한다.
- 기본 paid API budget은 `$0`이다.
- 모델 하나만 통과해서는 `clear`로 쓰지 않는다.
- 최소 2개 모델의 approve/clear가 있어야 기본 통과다.
- non-negotiable finding은 두 reviewer 승인만으로 자동 무시하지 않는다.
- 대표 중재가 발생하면 반드시 `왜 override했는지`를 남긴다.
