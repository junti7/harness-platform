# Notion Operating System (NOS)
# Version: 1.0
# Date: 2026-05-13
# Strategic Alignment: "From Page to System — Transforming Information into Assets"

---

## 1. Purpose

Notion은 Harness의 **'운영 뇌(Operating Brain)'**이자 **'지식 자산화 엔진'**이다. 
Slack이 실시간 명령과 휘발성 소통을 담당한다면, Notion은 모든 활동을 구조화된 데이터(Database)로 변환하여 팀의 운영 효율을 극대화한다.

본 문서는 유튜브 "노션으로 10배 더 똑똑하게 일하는 법"의 철학을 Harness 환경에 맞게 이식한 운영 가이드라인이다.

---

## 2. Core Philosophy: "Page is not enough, System is Data"

우리는 단순히 문서를 작성하기 위해 노션을 쓰지 않는다. **"정보가 데이터베이스에 담길 때만 비로소 관리 가능한 데이터가 된다"**는 원칙을 고수한다.

### 5대 운영 원칙 (The 5 Pillars)

1.  **명확한 책임 (Clear Accountability)**: 모든 Task와 의사결정 기록에는 `Owner(Person)` 속성을 필수 할당한다.
2.  **시각적 일정 관리 (Visual Schedule)**: 리스트 뷰가 아닌 `Timeline`과 `Calendar` 뷰를 통해 전체 발행 흐름과 병목을 한눈에 파악한다.
3.  **지식의 자산화 (Internal Wiki)**: 슬랙에서 오가는 단편적 정보, 회의록, VP의 정성적 피드백을 모두 데이터베이스에 축적하여 팀의 장기 자산으로 만든다.
4.  **극한의 개인화 (Personalized Dashboards)**: 하나의 Master DB를 사용하되, 대표(President)와 부대표(VP)는 각자에게 필요한 정보만 필터링된 개인용 대시보드를 사용한다.
5.  **AI 기반 운영 효율화 (AI-Powered Ops)**: LLM(Codex)이 노션 DB의 속성(요약, 카테고리, 액션 아이템 추출)을 자동으로 채우도록 설계한다.

---

## 3. Core Database Schemas

### 3.1 [DB] Master Action List (팀 액션 보드)
Harness의 모든 실행 과제를 관리한다.

*   **Properties**:
    *   `Name`: 과제명
    *   `Owner`: 담당자 (Person)
    *   `Status`: To-do, In Progress, Review, Done, Paused
    *   `Due Date`: 마감일
    *   `Priority`: High, Medium, Low
    *   `Linked Project`: 관련 프로젝트 (Physical AI Weekly 등)

### 3.2 [DB] Content Pipeline (콘텐츠 발행 파이프라인)
`Physical AI Weekly`의 기획부터 발행까지의 전 과정을 추적한다.

*   **Properties**:
    *   `Issue #`: 호수 (예: #001)
    *   `Status`: Evidence Collecting, Drafting, VP Review, QA/RedTeam, Publish Ready, Published
    *   `Publish Date`: 발행 예정일
    *   `Signals`: 수집된 핵심 신호 (Signal DB 연동)
    *   `VP Feedback`: 부대표의 가독성/공감도 체크 결과
    *   `URL`: 발행된 뉴스레터 링크

### 3.3 [DB] Knowledge Hub (지식 창고)
Harness의 SOP, 리서치 리포트, 의사결정 기록(Decision Cards)을 저장한다.

*   **Properties**:
    *   `Title`: 제목
    *   `Category`: SOP, Research, Legal, Decision, Manual
    *   `Last Updated`: 최종 수정일
    *   `Owner`: 문서 관리자
    *   `Tag`: 관련 키워드

### 3.4 [DB] Reader Memory & Feedback (독자 기억 저장소)
독자의 반응, 유료 전환 망설임 포인트(Paid Hesitation), 정성적 피드백을 자산화한다.

*   **Properties**:
    *   `Reader ID`: 익명 ID 또는 이메일
    *   `Sentiment`: Positive, Neutral, Negative, Hesitant
    *   `Feedback Note`: 피드백 내용
    *   `Product Upgrade`: 이 피드백이 상품 개선에 반영되었는지 여부
    *   `Interest Tags`: 독자 관심사

---

## 4. Team Dashboards

### 4.1 President's Decision Dashboard
대표가 '결정'에만 집중할 수 있는 뷰.
*   **Filter**: `Status = Publish Ready` 또는 `Priority = High` 인 항목.
*   **View**: `Timeline` 뷰를 통해 향후 4주간의 현금 흐름과 발행 일정 확인.

### 4.2 VP's Empathy Dashboard
부대표가 '독자 경험'과 '가독성'을 검토하는 뷰.
*   **Filter**: `Status = VP Review` 인 콘텐츠와 `New Feedback`인 독자 반응.
*   **View**: `Board` 뷰를 통해 검토 대기 중인 초안들을 직관적으로 관리.

---

## 5. Information Assetization Workflow

1.  **Slack Capture**: 슬랙에서 중요한 의사결정이나 아이디어가 나오면, Codex가 이를 요약하여 **Knowledge Hub** DB의 새 항목으로 등록한다.
2.  **Weekly Archive**: 매주 발행된 뉴스레터는 단순 텍스트가 아니라, 사용된 Signal과 독자 반응 데이터가 연결된 형태로 **Content Pipeline**에 아카이브된다.
3.  **Property First**: 새로운 페이지를 만들 때 내용을 먼저 쓰지 않고, 반드시 DB의 `Property`들을 먼저 채운다. (데이터의 분류와 검색 가능성 확보)

---

## 6. Implementation Roadmap

1.  **Phase 1 (Setup)**: 위 4대 핵심 DB 구조 생성 및 샘플 데이터 입력.
2.  **Phase 2 (Integration)**: Slack-Notion 연동 (Codex가 Slack 메시지를 Notion DB로 자동 전송).
3.  **Phase 3 (AI Enrichment)**: LLM이 Notion DB의 '요약' 및 '태깅' 속성을 자동 생성하도록 고도화.
