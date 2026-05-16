# Vice President Feedback Template
# Version: 1.0
# Date: 2026-05-10

---

## Purpose

부대표가 `Physical AI Weekly` 초안을 검토할 때 사용하는 고정 피드백 양식이다.

부대표는 기술 전문가처럼 평가하지 않는다. Phase 1의 핵심 역할은 **일반 한국어 독자가 읽을 수 있는지, 신뢰가 가는지, 공유하고 싶은지, 결제 저항이 어디서 생기는지**를 판단하는 것이다.

---

## Slack Reply Template

아래 양식을 `#vp-content-review`에 그대로 복사해서 작성한다.

```text
[VP REVIEW]
Issue: Physical AI Weekly #001
Target: newsletter_issue#1

1. Readability:
좋음 / 보통 / 어려움

2. 가장 이해하기 쉬운 부분:

3. 가장 어렵거나 지루한 부분:

4. 일반 독자가 공유하고 싶을 문장 또는 제목 후보:

5. 신뢰가 떨어지는 표현:

6. 너무 기술자처럼 느껴지는 단어:

7. Paid teaser 결제 욕구:
강함 / 보통 / 약함

8. 결제를 망설이게 하는 이유:

9. 감각적 판단:
hot / unclear / weak

10. 대표에게 요청:
approve / revise / more_research / reject

11. 추가 메모:
```

---

## Interpretation Rule

부대표 피드백은 다음 기준으로 DB에 기록한다.

| Slack field | DB field |
| --- | --- |
| 감각적 판단 hot / unclear / weak | `market_read` |
| Paid teaser 결제 욕구 | `emotional_resonance` |
| 결제를 망설이게 하는 이유 | `buyer_hesitation` |
| 추가 메모 + 어려운 부분 + 신뢰 저하 표현 | `analog_notes` |
| 대표에게 요청 | `requested_action` |

---

## DB Recording Command

부대표가 Slack에 피드백을 남긴 뒤 Codex가 아래 형태로 기록한다.

```bash
.venv/bin/python scripts/partner_feedback.py newsletter_issue 1 hot \
  --emotional-resonance strong \
  --buyer-hesitation "전문용어가 많아 paid teaser 가치를 바로 이해하기 어려움" \
  --analog-notes "Figure/Fleet 부분은 좋지만 VLA, sim-to-real 설명 필요" \
  --requested-action ceo_review \
  --human-review-required
```
