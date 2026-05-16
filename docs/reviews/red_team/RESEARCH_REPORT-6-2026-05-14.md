# Red Team Memo — research_report#6

- Artifact: Physical AI Decision Brief #001
- Path: docs/issues/physical_ai_decision_brief_001_2026-05-13.md
- Provider A: codex / codex
- Provider B: claude / claude-opus-4-7

## Codex Findings
- The brief makes named-entity judgments about Figure, DeepMind, NVIDIA, Genesis AI, and Meta/ARI without providing any citations, links, dates, or quoted source context. That makes the evidence scorecard unauditable and raises hallucination risk because the reader cannot verify whether the referenced posts, blogs, press releases, or media reports actually support the stated takeaways. (high)
- The document labels Figure, DeepMind, and NVIDIA as 'strong signals' and says they are worth acting on now, but its own scorecard rates them only medium or medium-low and explicitly notes self-reporting, speculative posture, and no deployment economics proof. That is a claim-strength mismatch and risks overstating weak evidence as decision-grade signal. (high)
- The Figure section appears to launder company narrative into market inference: 'operable quantity,' 'field management loop,' and an investor-facing shift toward operations may be true as messaging posture, but the brief does not show the underlying metrics or wording. Without source excerpts, it is hard to separate what Figure actually said from the author's interpretation. (medium)
- The Korea-specific interpretation is too thinly supported. The brief says Korean readers should focus on operating repeatability, reasoning quality, and infrastructure control, but it offers no Korea-specific deployment data, buyer behavior, factory constraints, or local counterexamples. That creates a false sense of localized precision from mostly global PR and research material. (medium)
- The industry-direction claim that Physical AI competition is shifting toward software/infrastructure/validation is presented as a repeated message, but the brief does not seriously engage counterarguments such as hardware reliability, safety certification, integration labor, customer ROI, or the possibility that vendor stack framing is just PR. Missing these counterarguments makes the thesis look cleaner than the evidence warrants. (medium)

## Claude Findings
- Headline asserts three 'strong signals' (Figure 운영 지표, DeepMind embodied reasoning, NVIDIA 인프라 포지셔닝) without summary-level evidence of independent verification — claim posture flag is present but the artifact summary itself does not disclose whether each claim is `verified`, `company-self-report`, or `speculative`. Figure 운영 지표 in particular is almost certainly company self-report and should be labeled as such at headline level. (high)
- `DeepMind의 embodied reasoning 서사` is described as a strong actionable signal, but a corporate narrative/서사 is by definition marketing posture, not a structural signal. Treating narrative as actionable risks confusing reader between thesis-grade evidence and PR framing. (medium)
- No counterargument or bear case visible in the summary — e.g., Figure 양산 주장에 대한 반대 증거(공급망, 인력, 실패 사례), NVIDIA 인프라 narrative에 대한 경쟁/대체(AMD, custom ASIC, 중국 대체재) 미언급. CLAUDE.md는 high-impact 의사결정에 bear case와 pre-mortem을 요구. (high)
- Korea context flag is true but the headline/summary contains no Korea-specific 해석 또는 수혜/위험 매핑. 한국어 독자 대상 매체에서 'Korea context present'를 자동 true로 기록하면 향후 QA에서 거짓 양성을 만든다. (medium)
- Genesis AI, Meta/ARI를 'watchlist note'로 분류한 근거가 summary에 없다. 분류 기준(데이터 부족, 검증 불가, 시기 이름) 없이 watch vs defer를 표시하면 reader가 분류 자체를 신호로 오해할 수 있다. (low)

## Consensus Issues
- None

## Split Issues
- codex: The brief makes named-entity judgments about Figure, DeepMind, NVIDIA, Genesis AI, and Meta/ARI without providing any citations, links, dates, or quoted source context. That makes the evidence scorecard unauditable and raises hallucination risk because the reader cannot verify whether the referenced posts, blogs, press releases, or media reports actually support the stated takeaways. (high)
- codex: The document labels Figure, DeepMind, and NVIDIA as 'strong signals' and says they are worth acting on now, but its own scorecard rates them only medium or medium-low and explicitly notes self-reporting, speculative posture, and no deployment economics proof. That is a claim-strength mismatch and risks overstating weak evidence as decision-grade signal. (high)
- codex: The Figure section appears to launder company narrative into market inference: 'operable quantity,' 'field management loop,' and an investor-facing shift toward operations may be true as messaging posture, but the brief does not show the underlying metrics or wording. Without source excerpts, it is hard to separate what Figure actually said from the author's interpretation. (medium)
- codex: The Korea-specific interpretation is too thinly supported. The brief says Korean readers should focus on operating repeatability, reasoning quality, and infrastructure control, but it offers no Korea-specific deployment data, buyer behavior, factory constraints, or local counterexamples. That creates a false sense of localized precision from mostly global PR and research material. (medium)
- codex: The industry-direction claim that Physical AI competition is shifting toward software/infrastructure/validation is presented as a repeated message, but the brief does not seriously engage counterarguments such as hardware reliability, safety certification, integration labor, customer ROI, or the possibility that vendor stack framing is just PR. Missing these counterarguments makes the thesis look cleaner than the evidence warrants. (medium)
- claude: Headline asserts three 'strong signals' (Figure 운영 지표, DeepMind embodied reasoning, NVIDIA 인프라 포지셔닝) without summary-level evidence of independent verification — claim posture flag is present but the artifact summary itself does not disclose whether each claim is `verified`, `company-self-report`, or `speculative`. Figure 운영 지표 in particular is almost certainly company self-report and should be labeled as such at headline level. (high)
- claude: `DeepMind의 embodied reasoning 서사` is described as a strong actionable signal, but a corporate narrative/서사 is by definition marketing posture, not a structural signal. Treating narrative as actionable risks confusing reader between thesis-grade evidence and PR framing. (medium)
- claude: No counterargument or bear case visible in the summary — e.g., Figure 양산 주장에 대한 반대 증거(공급망, 인력, 실패 사례), NVIDIA 인프라 narrative에 대한 경쟁/대체(AMD, custom ASIC, 중국 대체재) 미언급. CLAUDE.md는 high-impact 의사결정에 bear case와 pre-mortem을 요구. (high)
- claude: Korea context flag is true but the headline/summary contains no Korea-specific 해석 또는 수혜/위험 매핑. 한국어 독자 대상 매체에서 'Korea context present'를 자동 true로 기록하면 향후 QA에서 거짓 양성을 만든다. (medium)
- claude: Genesis AI, Meta/ARI를 'watchlist note'로 분류한 근거가 summary에 없다. 분류 기준(데이터 부족, 검증 불가, 시기 이름) 없이 watch vs defer를 표시하면 reader가 분류 자체를 신호로 오해할 수 있다. (low)

## Decision
- red_team_block
