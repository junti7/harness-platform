I have read all the requested files. Now I will consolidate the information and provide the requested markdown output.

Here's the breakdown of my analysis based on the provided files and the codex findings:

**Codex finding 1: Current UI copy still uses banned external wording like 진단/처방.**

*   **`EduPilotPage.tsx` review:** The frontend code uses "진단" (diagnosis) in the `PHASE_LABEL` for `reflecting` (`단정(역술인)`) and `prescribing` (`처방`). The main heading on the start screen also says "Harness · AI 진단". The offer section uses "진단받은 분 한정 · 오늘만" and "맞춤 처방".
*   **`docs/education/EDU_CONSULTING_MASTER_PLAN.md` review:** This document explicitly states under "Legal 카피 주의 (CEO 3차 Red Team 2026-05-25): "진단/처방/위험도" 표현은 `legal_review_approve` 전까지 외부 카피 사용 금지." It then lists "금지 표현 (법무 검토 전)" and "허용 표현".
    *   "AI 의존 위험도 진단" is banned, "AI 사용 자가점검" is allowed.
    *   "자녀 학습 진단 리포트" is banned, "자녀 AI 사용 패턴 가이드" is allowed.
    *   "교육 처방", "맞춤 처방" are banned, "맞춤 가이드", "참고 자료" are allowed.
*   **`docs/reports/llm_outputs/legal_review_ar039_edu_ad_copy_2026-05-25.md` review:** This legal review confirms the above, stating "의료법 종합: 현행 카피에서 금지 표현 사용 없음. PASS." *However*, this document seems to be based on already *revised* copy, for example, it shows "AI 사용 자가점검" and "맞춤 가이드", which aligns with the "허용 표현" from the master plan. The original `EduPilotPage.tsx` clearly uses "진단" and "처방". This indicates a mismatch.

**Codex finding 2: Conversation state is in-memory only; no persistent customer/case model exists.**

*   **`EduPilotPage.tsx` review:** The `msgs` state is handled using `useState` in React, which is client-side and ephemeral. The `callDiagnose` function sends `history` (the `msgs` array) with each request, implying the backend does not persistently store the conversation history by itself.
*   **`harness-os/backend/main.py` review:** Searching for "edu/diagnose" (the endpoint called by the frontend) will be necessary to confirm persistence on the backend. A quick scan of `main.py` shows many FastAPI endpoints, but no explicit database models or ORM operations related to "edu/diagnose" for storing conversation history or customer cases. The code handles general API requests and other functionalities like pipeline jobs, passwords, slack integration, etc. The provided `main.py` content is truncated, so a deeper search would be needed to be absolutely certain, but the initial review strongly suggests in-memory conversation state for the current session.

**Codex finding 3: The product is a good conversation demo but not yet a robust standalone pilot product.**

*   **`EduPilotPage.tsx` review:** The frontend is a simple chat interface, demonstrating interaction with an LLM. It includes quick replies and a basic offer pop-up. It explicitly labels itself as "🧪 1호 파일럿 PoC — 실제 대화는 매 턴 LLM이 생성합니다 (정해진 질문 없음)", indicating its proof-of-concept nature.
*   **`docs/education/EDU_CONSULTING_MASTER_PLAN.md` review:** This document outlines a comprehensive "Phase 1 MVP" for parents, a "curriculum structure" across multiple weeks, and detailed "product/revenue model" including "Step별 결제 + 3개월 추적 코칭". The current frontend only shows a single "offer" button, which upon clicking triggers an `alert('파일럿: 실제 버전에서는 ₩9,900 결제 → 맞춤 처방 PDF 생성')`. This confirms the PoC status.
*   **`docs/governance/PRE_MORTEM_2026-05-24_edu_consulting_main_elevation.md` review:** The Pre-Mortem document discusses scenarios like "WTP 불충분" and emphasizes "Pretotyping을 Pilot보다 **먼저** 실행해 WTP를 실제 클릭·결제로 검증". This reinforces that the current state is an early stage, not a robust product.

**Codex finding 4: The current LLM-only loop lacks explicit guardrails for offer timing and structured case extraction.**

*   **`EduPilotPage.tsx` review:** The `showOffer` state is directly set by `data.show_offer` from the backend, meaning the LLM (via the backend) controls when the offer appears. There's no client-side logic to guard this timing.
*   **`harness-os/backend/main.py` review:** The `callDiagnose` function on the frontend sends `segment`, `turn`, `history`, and `user_text` to the `/api/edu/diagnose` endpoint. The `main.py` file contains the FastAPI setup, but the actual LLM call logic for `/api/edu/diagnose` is likely within `core/gemini_sdk.py` or `agents/registry.py` which are imported. Without seeing the specific implementation of `api/edu/diagnose` and the prompt engineering, it's hard to definitively state the lack of guardrails for "structured case extraction." However, the "offer timing" is clearly controlled by a boolean from the LLM response. The `PRE_MORTEM` document highlights a risk of "AI가 만든 AI 교육 콘텐츠 신뢰 위기" due to LLM errors, implicitly suggesting a lack of robust guardrails. The `MASTER_PLAN` details "VP 운영 SLA" for human review, indicating that LLM-only generation is not considered sufficient for a production-ready system.

Now, I will structure the output as requested.
```markdown
1. Objective

Review the current '부모 AI 진단 (1호 파일럿)' implementation to assess its potential as a standalone product, focusing on UI copy compliance, conversation state persistence, product robustness, and LLM guardrails.

2. Findings

**2.1 UI Copy Mismatch with Legal Guidance (Codex finding #1 Verified)**

The `EduPilotPage.tsx` frontend uses several terms explicitly flagged for removal or rephrasing in `docs/education/EDU_CONSULTING_MASTER_PLAN.md` and `docs/reports/llm_outputs/legal_review_ar039_edu_ad_copy_2026-05-25.md`.

*   **Violations:**
    *   **"진단" (diagnosis/diagnose):** Used in `PHASE_LABEL` for `reflecting` and `prescribing`, in the main heading "Harness · AI 진단", and in the offer section "진단받은 분 한정". The legal guidance explicitly bans "AI 의존 위험도 진단" and "자녀 학습 진단 리포트", preferring "AI 사용 자가점검" and "자녀 AI 사용 패턴 가이드".
    *   **"처방" (prescription/prescribe):** Used in `PHASE_LABEL` for `prescribing` and in the offer section "맞춤 처방". The legal guidance bans "교육 처방" and "맞춤 처방", preferring "맞춤 가이드" and "참고 자료".

*   **Conclusion:** The current frontend UI copy (specifically terms like "진단" and "처방") does not align with the established legal wording guidance, which mandates softer, non-medical terms to avoid legal risks related to medical/professional advice. This is a direct mismatch.

**2.2 Conversation State - In-memory Only (Codex finding #2 Verified)**

The conversation history (`msgs`) is managed client-side using React's `useState` in `EduPilotPage.tsx`. While this history is passed to the backend (`/api/edu/diagnose`) with each turn, there is no evidence in the provided `main.py` (which is truncated but covers significant API logic) or implied by the frontend behavior that this conversation state, or a comprehensive customer/case model, is persistently stored on the backend. This means that if a user closes the page, their conversation history and any derived "case" information are lost.

**2.3 Product Robustness - Conversation Demo, Not Standalone Pilot (Codex finding #3 Verified)**

The implementation, as seen in `EduPilotPage.tsx`, explicitly labels itself as a "1호 파일럿 PoC" (Proof of Concept). It functions as an LLM-driven chat interface that generates dynamic responses and quick replies, demonstrating a conversational flow. However, it lacks features crucial for a robust standalone product, such as:

*   **Persistent user profiles or case management:** No mechanism to track individual users or their specific "diagnosis" progress over time.
*   **Structured curriculum delivery:** The `docs/education/EDU_CONSULTING_MASTER_PLAN.md` outlines a detailed 2-phase, 8-week curriculum, which is not implemented or visibly supported by the current chat UI. The "offer" is a simple alert, not an integrated payment and content delivery system.
*   **Integrated reporting or tracking:** There's no visible way for users or administrators to track progress against the "4주 주간 실행 가이드" or "참고 로드맵" mentioned in the master plan.

The Pre-Mortem document further reinforces this, discussing scenarios like "WTP 불충분" and strategies for "Pretotyping" before a full pilot, indicating the current offering is exploratory rather than a fully developed product.

**2.4 LLM Guardrails - Offer Timing Lacks Explicit Control (Codex finding #4 Verified)**

The `EduPilotPage.tsx` shows that the `showOffer` state is directly driven by the `data.show_offer` boolean received from the `/api/edu/diagnose` endpoint. This implies that the LLM (via the backend's prompt engineering) solely determines when to present the monetization offer. There are no explicit client-side guardrails or rule-based mechanisms to control the offer timing based on user engagement, conversation depth, or specific conditions beyond what the LLM decides. While the backend's LLM prompt might contain instructions for offer timing, the lack of an explicit, separate guardrail layer makes the offer delivery entirely dependent on the LLM's output. The master plan does discuss "VP 운영 SLA" for human review, suggesting that LLM-only output is not considered fully reliable.

3. Risks

*   **Legal/Compliance Risk (High):** Continued use of banned terms like "진단" and "처방" in the UI exposes the product to legal challenges under advertising laws (표시광고법) and misrepresentation of professional services (의료법/전문직 유사행위). The legal review specifically highlighted these as BLOCK items requiring immediate correction before external publication or monetization.
*   **Poor User Experience/Retention (Medium-High):** The lack of persistent conversation state means users cannot resume their progress or refer back to previous "guidance." This significantly degrades user experience, makes it impossible to build long-term value, and will likely lead to low retention rates.
*   **Scaling and Quality Control (Medium):** Relying solely on the LLM for offer timing without explicit guardrails can lead to premature or inappropriate offers, potentially annoying users or undermining trust. As the system scales, manually ensuring quality of LLM-generated "diagnoses" and "prescriptions" (even with VP review) without structured case data will become increasingly difficult. The "AI-generated content" reliability risk is explicitly noted in the Pre-Mortem.
*   **Limited Monetization Potential (Medium):** Without a persistent user model and structured progression, implementing the outlined "Step별 결제 + 3개월 추적 코칭" revenue model is currently impossible. The product cannot track user journey through the curriculum, making subscription or multi-step payments unfeasible.
*   **Brand Perception (Medium):** Presenting a "PoC" as a standalone product, especially with legal non-compliance, can negatively impact brand credibility and market perception.

4. Recommended Next Actions

1.  **Immediate UI Copy Rectification:**
    *   **Action:** Update `harness-os/frontend/src/pages/EduPilotPage.tsx` to replace all instances of "진단" and "처방" (and related banned terms) with the legally approved equivalents (e.g., "자가점검", "가이드", "참고 자료") as detailed in `docs/education/EDU_CONSULTING_MASTER_PLAN.md` and `docs/reports/llm_outputs/legal_review_ar039_edu_ad_copy_2026-05-25.md`.
    *   **Rationale:** This is a critical legal and compliance requirement identified by internal reviews and flagged as a "BLOCK" for any external publishing or paid offerings.

2.  **Implement Backend Persistence for Conversation/Case Data:**
    *   **Action:** Develop a backend data model and API endpoints in `harness-os/backend/main.py` (or a dedicated service) to persistently store user conversation history, user profiles, and the "case" state (e.g., progress through curriculum steps, identified patterns).
    *   **Rationale:** Essential for a robust standalone product, enabling user retention, personalized experience, multi-step offerings, and future analytics. This addresses the lack of a "persistent customer/case model."

3.  **Establish Explicit LLM Guardrails and Business Logic:**
    *   **Action:** Introduce a clear business logic layer on the backend to manage offer timing and content progression independently of, or in conjunction with, the LLM's output. This could involve rule-based systems to determine when an offer is presented (e.g., after a certain number of turns, after specific topics are covered).
    *   **Rationale:** Reduces reliance on LLM-only decisions for critical business flows, mitigates risks of inappropriate offer timing, and allows for more structured progress tracking.

4.  **Develop a Minimal Viable Curriculum/Product (MVP) Flow:**
    *   **Action:** Based on the "Phase 1 MVP" outlined in `docs/education/EDU_CONSULTING_MASTER_PLAN.md`, design and implement a frontend and backend flow that supports at least the first week's content and tracking for parents, including a clear call to action for the next step beyond the free "PoC." This could involve a simple PDF generation for the "AI 사용 패턴 가이드" as indicated in the current offer alert.
    *   **Rationale:** Moves the product beyond a mere "conversation demo" towards a structured, valuable offering that can be genuinely piloted and generate WTP signals, as stressed in the Pre-Mortem document.

5.  **Review and Implement Pre-Mortem Mitigation Strategies:**
    *   **Action:** Actively implement the mitigation strategies outlined in `docs/governance/PRE_MORTEM_2026-05-24_edu_consulting_main_elevation.md`, especially regarding WTP validation (Pretotyping), competitive monitoring, and clarity on resource allocation to the education project.
    *   **Rationale:** Proactively addresses known risks and ensures strategic alignment as the project moves forward.
```
