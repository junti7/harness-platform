# EDU UX RED TEAM Request Packet

> date: 2026-06-13  
> purpose: external LLM red-team review request for the current edu UX/service design  
> requested output language: Korean  
> reviewer role: adversarial product/UX/security reviewer

---

## 1. Review target

Review the following local design documents as the source of truth for the current direction:

1. `docs/education/EDU_UX_SERVICE_GUIDELINES.md`
2. `docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md`
3. `docs/education/EDU_SIMULATION_GATING.md`

If you cannot read local files directly, use the summarized context below as the review basis.

---

## 2. Product intent

This product is not meant to be a formal, textbook-like AI education chatbot.

The intended product should:

- feel realistic, current, and aggressive about recent AI trends
- create interest quickly
- help ordinary customers feel that if they learn with us for a few weeks, they can become a `semi-expert` who can lead a child, parent, spouse, or family member
- avoid dry, unrealistic advice such as telling an AI-naive parent to suddenly ask their child abstract questions about AI usage in schoolwork
- prioritize concrete, eye-opening early experiences where the customer uses an LLM to generate something visible and useful
- adapt training to the customer's chosen LLM/tool

We may recommend an LLM, but the customer must choose.  
If the customer chooses Gemini, education must be Gemini-specific.  
If the customer chooses Claude, education must be Claude-specific.  
Training the customer on a different LLM than the one they chose is considered a serious UX failure.

---

## 3. Entry and device model

Expected first entry is usually:

1. KakaoTalk message with a magic link
2. shared link from another person
3. SMS/email resume link
4. mobile landing CTA

Default assumption:

- first visit is smartphone-first, not desktop-first
- early intake should explicitly capture:
  - age band
  - gender
  - current device type (`iPhone` / `Android`)
  - browser context (`Kakao in-app` / normal browser)

Later, before deeper practice, the system should also capture:

- desktop target environment (`Windows` / `Mac`)
- managed device restrictions (company/school device)
- whether app installation is allowed
- whether someone nearby can help

Device/environment must never be inferred.  
Only explicit user-provided values should be used.

---

## 4. Core domain model

The service must distinguish:

- `seeker`: the person receiving guidance now
- `target_person`: the person the seeker wants to help/lead
- `goal`: the change the seeker wants

Examples:

- parent -> child
- adult child -> elderly parent
- worker -> self

The design direction introduces concepts such as:

- `seeker_role`
- `target_person_type`
- `selected_llm_for_training`
- `tool_readiness_state`
- `desktop_target_os`
- `helper_available_flag`

The design also proposes richer target modeling via a separate `edu_case_targets` structure.

---

## 5. Privacy, magic links, and session safety

The design direction currently requires:

- strict separation of `public share link` vs `private resume link`
- resume links must open a specific case, not latest-by-email
- sensitive resume links should require step-up verification on new devices
- recent case list, summary, resend flow, and explicit warning that the link opens personal history
- multi-device session control to avoid concurrent edits
- separation of payer vs actual participant when needed

Known risk already raised by Gemini red-team:

- IDOR-like privacy exposure if personal resume links are treated like share links
- race conditions / state corruption if the same case is edited from mobile and desktop simultaneously

---

## 6. Tool readiness and execution UX

The product assumes many users are novices.

Design principle:

- treat `install`, `launch`, `login`, and `first real task` as first-class UX stages
- never rely on dry instructions such as:
  - "Search the App Store and install it"
  - "Install Claude Desktop and run it"
  - "Open the browser and log in"

Instead:

- use guided step cards
- one action at a time
- show progress state
- confirm success before moving on
- branch by `iPhone / Android / Windows / Mac`
- track where users get blocked

The benchmark mindset is:

> build it as if teaching a 70-year-old person how to use a kiosk from scratch.

---

## 7. Realism rule for tasks

Early tasks must not feel like unrealistic school counseling scripts.

Bad example:

- asking an AI-naive parent to immediately ask their child,  
  "How are you using AI in your studies these days?"

This is considered too textbook-like and unrealistic.

Desired direction:

- start with trend-aware, reality-based framing
- make the customer feel "this is current, sharp, and useful"
- let the customer produce something visible with their own chosen LLM
- help the customer first become more capable before expecting them to lead someone else

The product should feel interesting, sticky, and easy to absorb.

---

## 8. Simulation and dark factory gate

Before large-scale real-world testing, the service should be tested via:

- evidence-grounded `digital twins`
- hidden `dark factory` full simulations
- multi-agent LLM-to-LLM dialogue runs
- score-based gating before final UX concretization

Simulation should be grounded in collected real voices from:

- mom cafes
- blogs
- YouTube
- RSS
- online communities

So digital twins should not be arbitrary fictional personas.  
They should reflect real expression patterns, anxieties, drop-off patterns, and wording.

Simulation should also test:

- latest LLM/tool trends
- current version differences
- current tutorials / clips / internet guidance
- whether the guidance matches the selected LLM
- whether the tasks feel realistic rather than textbook-like

Final UX should only be concretized or expanded after the simulation plus red-team score clears the gate.

---

## 9. Known implementation gaps already recognized

These gaps are already known internally:

- shadow customer is needed for pre-contact dropoff
- richer observability is needed for device/browser/link/tool-readiness failures
- target modeling is still evolving
- payer vs actual participant separation is not fully specified
- public app and internal test app are not fully unified

---

## 10. What we want from the reviewer

Please perform an adversarial red-team review of this design.

Focus especially on:

- mobile magic-link first entry
- Kakao/mobile browser failure modes
- cross-device handoff to PC/Mac
- seeker / target_person / goal model
- age / gender / device / environment intake
- privacy/security risk around resume links
- multi-device session/state corruption risk
- anti-textbook realism of customer tasks
- user-selected LLM specific training flow
- freshness of LLM/tool trend knowledge for simulation and guidance
- operator observability
- implementation ambiguity and migration risk

---

## 11. Required output format

Output in **Korean markdown** with exactly these sections:

1. `Verdict: clear / needs_work / block`
2. `Findings`
   - ordered by severity
   - each finding should include:
     - title
     - why it matters
     - recommendation
3. `Open questions`
4. `Brief summary`

Rules:

- be adversarial and specific
- do not praise
- do not rewrite the full design
- focus on risk, weakness, contradiction, ambiguity, and missing assumptions

