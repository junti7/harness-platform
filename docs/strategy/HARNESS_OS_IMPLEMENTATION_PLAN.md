# Harness-OS 상세 구현 계획서

- **Version:** 1.1 (Red-Team 검증 조건 반영)
- **Date:** 2026년 5월 23일
- **Owner:** Jarvis (Chief of Staff)
- **Status:** **APPROVED**. 즉시 실행 가능.

---

### 1. 목적 및 비전 (Purpose & Vision)

Harness-OS는 `NOTION_OPERATING_SYSTEM.md`의 한계를 넘어, `AGENTIC_ORCHESTRATION_CHARTER.md`의 비전을 지원하기 위한 harness-platform의 공식 사내 ERP다.

**v1.1의 목표:** 1주일 내에 **웹 MVP(Minimum Viable Product)**를 구축하여, 대표와 부대표가 가장 핵심적인 비즈니스 현황을 실시간으로 파악하고 AI 에이전트와 상호작용할 수 있는 '통합 지휘 대시보드'를 제공한다.

### 2. 핵심 설계 원칙 (Core Principles)

1.  **신속한 가치 제공 (Rapid Value Delivery):** 1주일 내에 실질적인 가치를 제공하는 MVP 개발을 최우선으로 하며, 장기적인 목표는 후속 버전으로 계획한다.
2.  **Notion 확장, 비(非) 대체 (Notion as a Backend):** Harness-OS는 Notion을 대체하는 시스템이 아니라, Notion DB API 위에 구축된 **'스마트 인터페이스'** 역할을 수행한다. 데이터의 원천(Source of Truth)은 Notion에 유지하여 데이터 마이그레이션 리스크를 원천 배제한다.
3.  **단일 코드베이스 (Single Codebase):** 웹 MVP는 React(Vite) 프레임워크를 사용하여 신속하게 개발한다. (모바일 앱은 MVP 성공 후 Flutter 전환 검토)
4.  **에이전트 중심 아키텍처:** 모든 기능은 인간 사용자와 AI 에이전트(`Jarvis` 등)가 상호작용하는 것을 전제로 설계된다.

### 3. 제안 아키텍처 (MVP Architecture)

| 계층 | 기술 | 선정 사유 |
| :--- | :--- | :--- |
| **프론트엔드** | **React (Vite)** | 웹 전용 MVP를 가장 신속하게 개발할 수 있으며, LLM 에이전트의 코드 생성 지원이 가장 활발함. |
| **백엔드** | **Python (FastAPI)** | Notion API 호출을 위한 보안 프록시 및 캐싱 레이어 역할. 기존 Python 자산과 완벽 호환. |
| **데이터베이스** | **Notion API** | 기존 `NOTION_OPERATING_SYSTEM`의 DB들을 직접 백엔드로 활용. |

```
[ React Web App ] <---> [ Python (FastAPI) Proxy ] <---> [ Notion API / AI Agents ]
```

### 4. MVP 기능 레이아웃: 통합 지휘 대시보드

1주일 안에 개발할 MVP는 아래 두 핵심 기능을 통합한 단일 페이지 애플리케이션이다.

#### **기능 1: 지휘 대시보드 (Command Dashboard)**
-   `KILL_CRITERIA.md` 목표 실시간 추적 (유료 구독자: 0/1, 무료 구독자: 0/50).
-   LLM API 일일 누적 비용.
-   승인 대기 중인 `Red-Team` 리뷰 항목 수.

#### **기능 2: 자비스 콘솔 (Jarvis Console)**
-   `CEO_SLACK_COMMAND_PATTERNS.md`의 GUI 버전.
-   간단한 텍스트 입력창을 통해 `Jarvis`에게 직접 명령을 하달하고, 그 결과를 바로 아래에 텍스트로 표시.

**※ 후순위 모듈:** 독자 기억장치, 프로젝트 관리, 재무, 정규 아카이브 등 나머지 모듈은 MVP 성공 후 2단계에서 구현한다.

### 5. 1주일 MVP 스프린트 계획 (1-Week MVP Sprint Plan)

| 일자 | 목표 | 핵심 과업 |
| :--- | :--- | :--- |
| **Day 1-2** | **프로젝트 설정 및 백엔드 구축** | - React(Vite) 및 FastAPI 프로젝트 생성.<br>- Notion API 키를 사용하여 KPI 데이터를 읽어오는 FastAPI 엔드포인트(`/api/dashboard`) 구현.<br>- `Jarvis` 에이전트 스크립트를 호출하는 엔드포인트(`/api/jarvis/invoke`) 구현. |
| **Day 3-4** | **프론트엔드 UI 개발** | - `DESIGN.md` 토큰을 참고하여 대시보드 및 콘솔 UI 컴포넌트 개발.<br>- 백엔드 API와 연동하여 KPI 데이터를 화면에 표시. |
| **Day 5-6** | **통합 및 테스트** | - '자비스 콘솔' 입력창과 `invoke` API를 연동하여 실제 명령-응답 테스트.<br>- 전체 워크플로우(데이터 표시, 명령 전송)에 대한 End-to-End 테스트. |
| **Day 7** | **배포 및 안정화** | - FastAPI 백엔드를 로컬 서버 또는 클라우드에 배포.<br>- React 프론트엔드를 Vercel/Netlify 등 플랫폼에 배포하여 즉시 사용 가능한 URL 확보. |

### 6. 개발 리소스 및 책임 (Resource & Responsibility)

-   **총괄 리드:** CEO
-   **개발팀:** CEO 주도 하에, Codex, Copilot 등 다양한 LLM 에이전트와 협업하여 개발 진행.
-   **개발 기간:** 1주일 (7일)

### 7. 사전 위험 분석 (Pre-Mortem for MVP)

| 시나리오 (1주일 후 실패했다면?) | 발생 가능성 | 최대 손실 | 사전 완화 전략 (Mitigation) |
| :--- | :--- | :--- | :--- |
| **1. Notion API 성능 문제:** Notion API의 속도 제한(Rate Limit) 또는 응답 지연으로 인해 대시보드가 느리게 로딩됨. | **Medium** | 사용성 저하 | FastAPI 백엔드에 1분 단위의 간단한 인메모리 캐시(In-memory Cache)를 구현하여 API 호출 최소화. |
| **2. MVP 범위 확장:** 1주일 안에 너무 많은 기능을 추가하려다 핵심 기능조차 완성하지 못함. | **High** | 일정 지연, 미완성 결과물 | 본 계획서의 MVP 기능(대시보드 KPI 3개 + 자비스 콘솔) 외 모든 아이디어는 'Post-MVP' 백로그로 기록하고, 이번 스프린트에서는 절대 구현하지 않음. |
| **3. 인증 복잡성:** 복잡한 사용자 로그인 시스템을 구현하려다 시간을 낭비함. | **Medium** | 개발 시간 지연 | MVP 버전은 별도의 로그인 기능 없이, 사내 네트워크 IP 주소로만 접근을 제한하거나 간단한 환경변수 기반의 Secret Key로 인증을 대체하여 복잡성 제거. |

### 8. 다음 단계 (Next Steps)

본 계획서는 Red-Team의 조건부 승인 사항을 모두 반영하여 수립된 최종 실행 계획이다.

즉시 **'1주일 MVP 스프린트 계획'**의 **Day 1** 과업에 착수할 수 있다.
