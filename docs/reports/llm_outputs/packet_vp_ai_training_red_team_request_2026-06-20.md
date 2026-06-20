# Packet — VP AI 교육 프로그램 Cross-LLM Red Team Request (2026-06-20)

> 용도: Claude / Gemini에 그대로 붙여넣어 독립 red-team 검토를 요청하기 위한 패킷
> 중요: 두 모델은 **서로의 분석을 보면 안 된다.**
> 목적: `VP 대상 내부 AI 교육 프로그램` 계획서를 formal `red_team_clear` 기준으로 검증

---

## 0. 검토 대상

주 문서:

- `docs/education/VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md`

참고 문서:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/education/EDU_CONSULTING_MASTER_PLAN.md`
- `docs/education/EDU_UX_SERVICE_GUIDELINES.md`
- `docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md`
- `docs/education/EDU_DB_TRANSPARENCY_PLAN.md`

검토자는 위 문서들을 바탕으로, 아래 계획이 구조적으로 타당한지 독립적으로 판정해야 한다.

---

## 1. 무엇을 만들려는가

Harness는 현재 mac mini의 Harness OS 안에 `부모 AI 진단 (1호 파일럿)` 메뉴를 가지고 있다.
하지만 외부 서비스 완성도, 내부 숙련 데이터, 고객 friction 이해, device handoff, grounded training asset 측면에서 아직 미완성 요소가 많다.

이번 계획은 `VP(부대표)`를 첫 번째 실제 교육 대상자로 삼아:

1. VP 본인의 AI 숙련을 키우고
2. 그 과정에서 생기는 막힘, 오해, 공감 포인트, 쉬운 한국어 표현, device/tool friction을 수집하고
3. 그 결과를 외부 부모 서비스에 재사용하는

내부 first-party AI 교육 프로그램을 만들려는 것이다.

이 프로그램은 단순 내부 OJT 문서가 아니라, 외부 서비스와 같은 완성도로 설계된다.

---

## 2. VP 배경

VP의 현재 강점:

- EQ
- 시장 촉
- 독자 공감
- 한국어 자연스러움 판단
- 가족/교육/가정 운영 맥락의 현실 감각
- paid hesitation 감지

VP의 현재 약점 또는 보강 필요 영역:

- AI 기본 개념 체계화
- 도구 설치/로그인/첫 실행 경험
- 결과 검토 기준
- selected-LLM별 차이 이해
- 외부 고객 가이드의 난이도/허세/실전성 판단을 위한 실제 hands-on 경험

중요한 목표:

- 단기: `AI 초보 → guided independent user`
- 중기: `internal quality lead`
- 장기 북극성: `CEO의 AI handling 수준에 최대한 근접`

중요한 설계 철학:

- 교육은 이론보다 실습이 중심이어야 한다.
- 설명자료는 초등학생도 이해 가능한 수준이어야 한다.
- 예시는 VP가 감성적으로 공감할 수 있어야 한다.
- 가능하면 Harness가 이미 쌓은 edu RAG 자료를 적극 활용해야 한다.
- 장기적으로는 Harness 작업 환경의 축약 미러, operator 환경, device/tool handoff까지 다뤄야 한다.

---

## 3. 이 계획의 핵심 주장

현재 계획서는 대략 아래를 주장한다.

1. 6주 실습형 프로그램으로 VP의 기본 AI 숙련을 끌어올린다.
2. 실습은 selected-LLM, mobile→PC/Mac handoff, artifact 저장을 포함한다.
3. 교육 자료는 쉬운 한국어와 감성 공감형 예시를 사용한다.
4. Harness RAG 자료를 적극 활용해 grounded training material을 만든다.
5. 6주 본과정 이후에는 Harness 미러 환경, operator 환경, CEO parity 추격 심화 트랙으로 이어진다.
6. 이 프로그램에서 얻은 산출물은 외부 부모 서비스 자산으로 재사용된다.

---

## 4. 당신이 반드시 검토해야 할 질문

### A. 제품/교육 구조

1. 이 계획은 실제로 `교육 제품`인가, 아니면 문서만 많은 내부 프로젝트인가?
2. 6주 구조가 실제 행동 변화를 만들 수 있는가?
3. 이론보다 실습을 우선한다는 주장이 계획서에 충분히 강하게 반영되어 있는가?
4. `CEO parity`를 북극성으로 둔 방식이 현실적인가, 아니면 과도한가?

### B. 사용자/난이도

5. VP를 사실상 `완전 초보자`로 놓고 설계해야 한다는 관점이 충분히 반영되어 있는가?
6. 설명자료를 `초등학생도 이해 가능한 수준`으로 만든다는 기준이 실제로 운영 가능한가?
7. 감성 공감형 예시가 학습 동기를 올리는 구조로 충분히 설계되어 있는가?
8. VP에게 과부하가 걸릴 가능성은 없는가?

### C. 운영/제품화

9. 이 프로그램이 외부 부모 서비스와 분리된 별도 장난감이 될 위험은 없는가?
10. selected-LLM / 디바이스 / mobile→PC/Mac handoff가 충분히 반영되어 있는가?
11. Harness 미러 환경, Tailscale/venv/secret 분리 같은 operator 요소를 포함시키는 방향이 적절한가?
12. 그 operator 요소를 너무 빨리 열어 보안 리스크를 키우지는 않는가?

### D. 지식/근거

13. 교육 자료에 Harness의 edu RAG 자료를 적극 활용한다는 방향이 타당한가?
14. live DB schema drift, customer-facing safety boundary, rights 경계 문제를 감안할 때 어떤 guardrail이 더 필요한가?
15. grounded material을 쓴다고 해도 허세형/교과서형 설명으로 다시 흐를 위험은 없는가?

### E. 외부 전이

16. 이 프로그램에서 나온 자산을 외부 부모 서비스로 재사용할 때 어떤 구조적 리스크가 있는가?
17. 법무/QA/red-team gate가 충분히 분리되어 있는가?

---

## 5. Non-Negotiable Blocker 기준

아래 중 하나라도 해당하면 `block` 또는 최소 `conditional_block`로 보라.

1. 교육이 실제 실습 없이 문서/설명 위주로 끝날 가능성이 높다.
2. 외부 서비스 자산으로 재사용된다는 주장에 비해 데이터 구조/운영 구조가 분리되어 있다.
3. 초보자 관점 friction, selected-LLM 차이, device handoff가 얕게 다뤄진다.
4. CEO parity를 이유로 VP에게 비현실적인 난이도와 책임이 한꺼번에 실린다.
5. Harness 미러/operator 환경을 다루면서도 보안 경계가 부실하다.
6. RAG 활용을 주장하지만 rights, safety, customer-facing boundary가 불명확하다.
7. 설명자료가 쉬운 언어 원칙을 주장만 하고 실제 평가/운영 방식에 안 박혀 있다.

---

## 6. 특별히 보고 싶은 리스크

다음 리스크는 적극적으로 찾아달라.

- `좋은 말은 많지만 실제 구현/운영이 안 되는 계획`
- `VP 혼자 너무 많은 역할을 떠안는 계획`
- `내부용 훈련과 외부용 제품이 자연스럽게 이어지지 않는 계획`
- `실습 중심이라면서 실제로는 설명 비중이 높은 계획`
- `초등학생도 이해 가능`이라는 기준이 허울뿐인 계획
- `RAG를 쓴다`면서 사실상 generic AI 상식으로 흐르는 계획
- `CEO parity`를 내세우지만 실제 operator 체험이 약한 계획

---

## 7. 원하는 출력 형식

아래 형식으로 답해달라.

```md
# Red Team Review — VP AI Training Program

## Verdict
- clear / conditional_clear / conditional_block / block

## Executive Summary
- 3~6문장으로 가장 중요한 판단 요약

## Findings
1. [severity: critical/high/medium/low] 제목
   - 문제 설명
   - 왜 위험한지
   - 계획서의 어느 부분이 약한지

## Required Changes Before Clear
1. ...

## Residual Risks After Fix
1. ...

## Specific Questions For CEO
1. ...
```

가능하면 severity를 명확히 나눠달라.
특히 `critical`과 `high`는 반드시 수정 전 clear를 주지 말아달라.

---

## 8. Claude용 독립 요청문

아래 내용을 Claude에 그대로 붙여넣어 사용한다.

```text
당신은 Harness라는 한국 AI 교육/서비스 회사의 VP 대상 내부 AI 교육 프로그램을 독립적으로 검토하는 Red Team 전문가입니다.

다른 모델의 분석을 절대 참고하지 말고, 아래 설명과 대상 문서만 바탕으로 독립적으로 판단해주세요.

검토 목적은 칭찬이 아니라 구조적 약점, 과한 가정, 운영 리스크, 보안 리스크, 제품화 실패 가능성을 찾는 것입니다.

[검토 대상]
- docs/education/VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md

[참고 대상]
- AGENTS.md
- CLAUDE.md
- docs/education/EDU_CONSULTING_MASTER_PLAN.md
- docs/education/EDU_UX_SERVICE_GUIDELINES.md
- docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md
- docs/education/EDU_DB_TRANSPARENCY_PLAN.md

[배경]
- VP는 EQ, 독자 공감, 한국어 자연스러움, 가족/교육 맥락 감각은 강하지만 AI 도구 숙련은 아직 체계화되지 않은 상태다.
- 이 프로그램은 VP를 개발자로 만드는 것이 아니라, 장기적으로 CEO 수준의 AI handling에 근접하도록 키우는 internal-first training product다.
- 교육은 실습 중심이어야 하고, 설명자료는 초등학생도 이해 가능한 수준이어야 하며, Harness의 edu RAG 자료를 적극 활용해야 한다.
- 장기적으로는 Harness 작업 환경의 축약 미러, operator 환경, mobile→PC/Mac handoff까지 포함한다.

[당신이 봐야 할 것]
1. 이 계획이 실제 교육 제품인지, 아니면 문서 과잉 프로젝트인지
2. 6주 구조와 심화 트랙이 현실적인지
3. 실습 우선 원칙이 충분히 강한지
4. 초보자/초등학생 설명 기준이 실제 운영 가능한지
5. VP 과부하, operator 보안 경계, RAG safety 경계가 충분한지
6. 외부 부모 서비스 자산으로 재사용 가능한 구조인지

[Non-negotiable blocker 예시]
- 실습보다 설명 비중이 높다
- 외부 서비스와 분리된 장난감 트랙이 될 위험이 높다
- operator 환경을 다루면서도 보안 경계가 약하다
- RAG 활용을 말하지만 rights/safety/customer-facing 경계가 약하다
- CEO parity를 구실로 비현실적인 난이도를 준다

[출력 형식]
# Red Team Review — VP AI Training Program

## Verdict
- clear / conditional_clear / conditional_block / block

## Executive Summary

## Findings
1. [severity: critical/high/medium/low] ...

## Required Changes Before Clear
1. ...

## Residual Risks After Fix
1. ...

## Specific Questions For CEO
1. ...
```

---

## 9. Gemini용 독립 요청문

아래 내용을 Gemini에 그대로 붙여넣어 사용한다.

```text
당신은 한국 AI 교육 서비스 회사의 VP 대상 내부 AI 교육 프로그램을 독립적으로 검토하는 Red Team 전문가입니다.
다른 AI의 분석을 절대 참고하지 말고, 아래 정보와 대상 문서만 바탕으로 독립적으로 판단해주세요.

[검토 대상 문서]
- docs/education/VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md

[참고 문서]
- AGENTS.md
- CLAUDE.md
- docs/education/EDU_CONSULTING_MASTER_PLAN.md
- docs/education/EDU_UX_SERVICE_GUIDELINES.md
- docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md
- docs/education/EDU_DB_TRANSPARENCY_PLAN.md

[배경 요약]
- VP는 reader empathy, 한국어 자연스러움, 가족/교육 맥락 감각은 강하지만 AI 도구 숙련은 아직 충분히 체계화되지 않았다.
- 계획의 목적은 VP를 장기적으로 CEO 수준의 AI handling에 근접하게 만드는 것이다.
- 교육은 이론보다 실습이 중심이어야 한다.
- 설명자료는 초등학생도 이해 가능한 수준이어야 한다.
- Harness가 모은 edu RAG 자료를 교육 자료에 적극 활용하려 한다.
- 장기적으로는 Harness 작업 환경의 축약 미러와 operator 환경도 다루려 한다.

[핵심 검토 질문]
1. 이 계획은 실제 행동 변화를 만드는 교육 구조인가?
2. VP에게 너무 많은 역할과 난이도를 너무 빨리 싣고 있지 않은가?
3. 초보자 관점 friction, selected-LLM 차이, device handoff가 충분히 반영되었는가?
4. RAG 활용이 grounded value를 만들 수 있는가, 아니면 generic한 자료로 흐를 위험이 큰가?
5. operator 환경과 보안 경계의 설계가 충분히 신중한가?
6. 외부 부모 서비스로 재사용 가능한 제품 구조인가?

[blocker 예시]
- 설명이 실습보다 많다
- 외부 서비스와 분리된 내부용 장난감이 될 위험
- CEO parity 목표가 비현실적인 압박으로 작동
- rights/safety/customer-facing 경계가 약한 RAG 활용
- operator 환경을 열면서 보안 완화가 부족함

[출력 형식]
# Red Team Review — VP AI Training Program

## Verdict
- clear / conditional_clear / conditional_block / block

## Executive Summary

## Findings
1. [severity: critical/high/medium/low] ...

## Required Changes Before Clear
1. ...

## Residual Risks After Fix
1. ...

## Specific Questions For CEO
1. ...
```

---

## 10. 실행 메모

검토 완료 후 결과를 아래 같은 이름으로 저장하는 것을 권장한다.

- `docs/reports/llm_outputs/claude_vp_ai_training_red_team_YYYY-MM-DD.md`
- `docs/reports/llm_outputs/gemini_vp_ai_training_red_team_YYYY-MM-DD.md`

이후:

1. 두 결과를 비교
2. `critical/high` 수정 반영
3. 필요 시 third opinion
4. 그 후에만 formal `red_team_clear` 검토

