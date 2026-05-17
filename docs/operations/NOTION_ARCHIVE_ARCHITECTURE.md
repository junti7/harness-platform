# Notion Archive Architecture
# Version: 2.0
# Date: 2026-05-17

---

## 1. Purpose

Notion은 단순한 문서 저장소가 아니라 Harness의 **회사 기록관**이어야 한다.

즉, 나중에 LLM이 다음 질문에 답할 수 있어야 한다.

- 왜 이 전략을 채택했는가
- 누가 어떤 반론을 냈는가
- 어떤 실패를 반복하면 안 되는가
- 어떤 프로젝트가 어떤 goal에 연결됐는가
- 어떤 결정이 매출, 품질, 속도에 실제 영향을 줬는가

---

## 2. Design Principle

LLM이 이해하기 쉬운 Notion 구조의 핵심은 **예쁜 페이지**가 아니라 **일관된 metadata + 표준 본문 구조**다.

따라서 모든 Notion archive entry는 아래 2층 구조를 갖는다.

1. `Properties`
2. `Canonical Body Sections`

---

## 3. Archive Model

현재 Harness는 단일 Notion database를 사용한다.

이 database는 앞으로 **Universal Operating Archive**로 간주한다.

즉, 아래 artifact를 모두 한 곳에 저장한다.

- project
- goal
- meeting_note
- strategy_memo
- decision_card
- experiment
- success_case
- failure_case
- issue_archive
- research_report
- sop
- ops_brief

여러 DB를 relation으로 잘게 나누는 방식은 나중에 가능하지만, 현재 단계에서는 **하나의 canonical archive DB + 강한 taxonomy**가 LLM retrieval에 더 유리하다.

---

## 4. Required Properties

모든 archive entry는 가능한 한 아래 property를 채운다.

- `제목`
- `Artifact Type`
- `Team`
- `Project`
- `Goal ID`
- `Goal Metric`
- `Project Status`
- `Outcome`
- `Source Channel`
- `Event Date`
- `Last Reviewed`
- `Reminder Date`
- `Canonical Key`
- `Summary`
- `Decision Summary`
- `Action Items`
- `Lessons Learned`
- `Failure Pattern`
- `Parent Ref`
- `DB Record Ref`
- `URL`
- `LLM Ready`
- `Historical Value`
- `Confidentiality`

---

## 5. Canonical Body Template

모든 핵심 기록은 본문을 다음 순서로 작성한다.

1. `Context`
2. `Objective`
3. `What Happened`
4. `Decision`
5. `Evidence`
6. `Action Items`
7. `Outcome`
8. `Failure / Success Pattern`
9. `Lessons Learned`
10. `Next Reminder`

이 순서는 검색성과 회고성을 동시에 높인다.

---

## 6. Entry Types

### 6.1 Project

의미:

- 하나의 지속적 실행 단위

예:

- `Physical AI Weekly launch`
- `Goal loop rollout`
- `Notion archive upgrade`

### 6.2 Goal

의미:

- 기간, metric, target을 가진 운영 목표

규칙:

- `/goal` 시스템과 연결
- snapshot, diagnosis, revision의 상위 anchor

### 6.3 Meeting Note

의미:

- 팀 간 회의록

규칙:

- 참석 팀과 결정사항, 미결 이슈, 액션 아이템을 property와 body에 모두 남긴다.

### 6.4 Strategy Memo

의미:

- 어떤 방향성을 채택/수정한 이유

규칙:

- 반대 가설과 폐기한 대안도 반드시 기록

### 6.5 Success / Failure Case

의미:

- 재사용 가능한 패턴

규칙:

- 단순 결과가 아니라 조건, 메커니즘, 재현 가능성 기록

---

## 7. Retrieval Philosophy

LLM이 나중에 잘 찾으려면 다음 기준이 중요하다.

- artifact type이 명확할 것
- project와 goal anchor가 있을 것
- outcome / lessons가 분리돼 있을 것
- decision과 evidence가 섞이지 않을 것
- failure pattern이 독립 property로 남을 것

즉, "잘 쓴 장문 문서"보다 "잘 구조화된 회고 기록"이 더 중요하다.

---

## 8. Operating Rules

- Slack에서 나온 중요한 논의는 Notion으로 승격한다.
- 회의가 끝나면 회의록만 남기지 말고 action item과 decision을 분리 저장한다.
- 실패는 숨기지 말고 `failure_case`로 명시한다.
- 같은 실패가 2회 이상 반복되면 `Failure Pattern` property를 같은 키로 맞춘다.
- reminder가 필요한 기록은 `Reminder Date`를 채운다.
- 장기 가치가 높은 기록은 `Historical Value = high`로 남긴다.

---

## 9. Immediate Upgrade

현재 DB는 `제목/본문/태그/소스/발행일` 수준이라 archive로는 너무 얕다.

따라서 즉시 보강해야 할 것은:

1. artifact taxonomy
2. goal/project anchor
3. outcome / lessons / action item 분리
4. reminder / review date
5. confidentiality / historical value

