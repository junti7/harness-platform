# Weekly Business Review
# Version: 2.0
# Date: 2026-05-10

---

## 1. Cadence

매주 월요일 09:00 KST에 대표(President/CEO)에게 1페이지 creator business review를 보낸다.

매주 월요일 10:00 KST에는 별도의 **Weekly Multi-LLM Red Team**을 실행한다.

기본 모델 조합:

- Claude
- Gemini
- Codex

이 정례 red-team의 unresolved issue가 남아 있으면, 기본적으로 다음 단계 진행은 block이다.  
예외는 대표의 explicit `confirm`뿐이며, rejected issue와 rationale을 반드시 기록한다.

Slack route:

- decisions: `#exec-president-decisions`
- content review and reader empathy: `#vp-content-review`
- incidents: `#ops-incidents`

---

## 2. Metrics

| Metric | Target | Trigger if Missed |
| --- | --- | --- |
| Weekly issues published | 1/week | issue scope 축소 |
| Free subscribers | 50 in 30 days | distribution channel 변경 |
| Paid subscribers | 1 in 30 days | paid offer/value prop 재작성 |
| Open/reply/share signals | tracked weekly | title/lead 재작성 |
| Vice President reviews completed | 1/issue | review checklist 단순화 |
| Readability pass rate | 80%+ | jargon reduction |
| Paid tier impressions | 1+/week after first issue | pricing copy 노출 |
| Subscriber revenue | tracked weekly | positioning review |
| LLM cost per issue | under budget | model/batch review |

---

## 3. Review Template

```markdown
# Weekly Business Review

- Week:
- Issues published:
- Free subscribers:
- Paid subscribers:
- Subscriber revenue:
- Opens/clicks/replies/shares:
- Best-performing signal:
- Weakest section:
- Vice President readability notes:
- Paid hesitation:
- Distribution actions:
- President decisions needed:
- Next week commit:
```

---

## 4. Decision Rule

발행, 독자, paid 전환 지표가 미달이면 신규 인프라 작업을 중단하고 issue quality, title, distribution, paid value proposition을 먼저 해결한다.

추가 gate:

- Weekly Multi-LLM Red Team의 세 모델 지적사항이 모두 clear되지 않으면 다음 단계로 넘기지 않는다.
- 단, 대표가 특정 지적을 받아들이지 않기로 `confirm`하면 conditional proceed가 가능하다.
- conditional proceed가 발생한 주차에는 다음 주 review에서 해당 항목을 최우선 재검토한다.
