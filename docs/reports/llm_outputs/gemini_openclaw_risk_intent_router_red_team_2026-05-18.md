# OpenClaw Risk/Intent Router Red-Team Response

Date: 2026-05-18

## Verdict

`conditional_approve`

## Top Findings Ordered by Severity

1.  **Over-reliance on "High-Risk Trigger Scan" for comprehensive safety:** While a high-risk trigger list is crucial, it's inherently incomplete and reactive. New attack vectors or nuanced phrasing could bypass keyword-based triggers. The document acknowledges this as "dangerous low-risk misclassification" but doesn't fully mitigate the implications of such a bypass. A single missed keyword or semantic interpretation could lead to significant damage (e.g., accidental publication, erroneous financial transactions, data mutation).

2.  **Ambiguity in "Preflight gate" implementation:** The description states it "independently re-check whether the action mutates data, publishes externally, affects pricing/legal/capital/brand, or needs approval." The critical question is *how* independently this re-check is performed. If it relies on the same classification mechanisms or underlying LLMs that made the initial decision, it introduces a single point of failure and reduces its effectiveness as a true independent gate. It needs to be a truly separate and robust deterministic check or human-in-the-loop process.

3.  **Potential for "Cheap Router" (Haiku) to introduce subtle misclassification leading to inappropriate escalation/de-escalation:** The "Ambiguous natural-language command router" (Haiku) maps ambiguous messages to bridge commands. If confidence is low, it escalates to clarification or Sonnet. However, a misclassified message that appears *unambiguous* to Haiku but has critical underlying context (e.g., a seemingly innocuous request that subtly implies a policy violation) could be routed to a less-secure "Local LLM" or an incorrect "Premium LLM" path, bypassing necessary human oversight or higher-tier checks.

4.  **Inadequate scope definition for "Local LLM route":** The limitations for local LLMs are well-stated ("Outputs are not allowed to publish, mutate files, spend money, approve decisions, or represent legal/QA/Red-Team clearances."). However, "non-customer-facing drafts" and "cheap summarization" can still carry brand risk or propagate incorrect information internally if the local LLM hallucinates or misinterprets. The risk here is less direct financial/operational damage but more reputational or internal inefficiency.

5.  **Lack of explicit human oversight integration:** While "escalate to clarification" is mentioned, the architecture doesn't explicitly detail where and how human review and intervention are *mandated* for high-risk or ambiguous situations, especially before any action is taken. The "Preflight gate" hints at it, but direct human gatekeepers for specific operations are not clearly articulated as a required step.

## Required Changes Before Production Trust

1.  **Enhance High-Risk Trigger with Semantic Analysis and Human-in-the-Loop:**
    *   **Implement a secondary, more sophisticated semantic analysis layer** for high-risk keywords/phrases, possibly using a more powerful LLM (Sonnet) or a dedicated classification model, to catch nuanced or disguised high-risk intents.
    *   **Mandatory human review** for *any* message flagged by the high-risk trigger, regardless of subsequent LLM classification. This should be a hard gate.
    *   **Regular, proactive red-teaming** specifically targeting the high-risk trigger list and its semantic interpretation capabilities to identify and patch bypasses.

2.  **Strengthen "Preflight Gate" Independence and Determinism:**
    *   The preflight gate *must* be completely decoupled from the intent classification models. It should ideally be a **deterministic rule-based system** or a **human review step** that re-evaluates the *proposed action's characteristics* (e.g., does this action modify a database? does it send an external email?) against a whitelist/blacklist of safe operations.
    *   The preflight gate should explicitly reference a **"risk manifest"** that categorizes actions by their potential impact, ensuring any action falling into a critical category triggers a mandatory human approval.

3.  **Refine "Ambiguous Natural-Language Command Router" (Haiku) Confidence Thresholds and Escalation Paths:**
    *   **Define clear, auditable confidence thresholds** for Haiku. Messages below a certain confidence score (e.g., 80%) for *any* intent should automatically escalate to a higher-tier LLM (Sonnet) for re-evaluation *or* a human for clarification, rather than attempting to pick the "least bad" option.
    *   **Implement explicit "clarification loops"** for the user when Haiku's confidence is low or multiple intents conflict, rather than just escalating to Sonnet which might still misinterpret.

4.  **Stricter Output Filtering and Vetting for "Local LLM route":**
    *   Implement **deterministic content filters** (keyword, regex) on *all* local LLM outputs to prevent accidental inclusion of sensitive terms, brand-inappropriate language, or internal jargon in "non-customer-facing drafts" that might later be exposed.
    *   **Human review/approval for *any* output from a local LLM that is intended for wider internal distribution or could influence external communications**, even if it's "just a draft."

5.  **Explicit Human Approval Workflow for Critical Actions:**
    *   Clearly define and integrate a **formal human approval step** for all actions that involve:
        *   Financial transactions (spending, refunds).
        *   External publications or communications (marketing, legal, press releases).
        *   Data mutation or deletion in critical systems.
        *   Changes to core business logic or operational parameters.
    *   This approval workflow should be auditable and clearly indicate the human approver.

## Residual Risks

1.  **Evolving Attack Vectors/Prompt Injection:** Even with robust preflight and high-risk triggers, sophisticated prompt injection techniques could trick LLMs into generating or enabling actions that appear low-risk but have high-risk consequences, especially as LLM capabilities evolve. This requires continuous monitoring and adaptation.

2.  **Semantic Drift and Misinterpretation:** LLMs can exhibit semantic drift, where their understanding of terms changes over time or across contexts. A seemingly safe phrase today might, through subtle shifts in model weights or training data, be misinterpreted as a high-risk command tomorrow, bypassing static triggers.

3.  **Configuration Complexity and Error:** The layered architecture introduces significant configuration complexity (allowlists, denylists, confidence thresholds, routing rules). A misconfiguration at any layer could introduce vulnerabilities, allowing dangerous actions to proceed unnoticed.

4.  **"Death by a Thousand Cuts" via Low-Risk Misclassifications:** While individual low-risk misclassifications from local LLMs might not be catastrophic, a consistent pattern of minor errors, incorrect summaries, or misleading internal drafts could degrade decision-making, erode trust, and lead to cumulative negative impacts over time.

5.  **Scalability and Performance Bottlenecks with Human-in-the-Loop:** Introducing mandatory human review steps for high-risk actions will add latency and potentially create bottlenecks, especially if the volume of such requests is higher than anticipated. This needs to be factored into operational planning.
