# Content Operating Playbook
# Version: 2.0
# Date: 2026-05-10
# Based on: ARK Invest "Big Ideas" Quality Benchmark

---

## 1. Purpose

이 문서는 유료 구독을 이끌어낼 수 있는 수준의 고품질 `Physical AI Weekly` 및 심층 리포트를 매주 발행하기 위한 운영 절차 및 콘텐츠 품질 규약(Playbook)이다.

---

## 2. Premium Content Standards (ARK Benchmarks)

유료 구독자가 비용을 지불할 가치를 느끼게 하기 위해, Tier 3 (Refiner)에서 최종 생성되는 리포트는 다음 5가지 품질 기준을 반드시 충족해야 한다.

### 2.1. 데이터 시각화 및 추세 분석 (Data Visualization & Trends)
- 단순 텍스트 서술을 지양하고, 과거부터 현재까지의 시계열 데이터를 바탕으로 한 추세 분석을 포함한다.
- **Wright's Law(경험 곡선)** 등을 적용하여 기술의 생산량이 늘어날 때 비용이 어떻게 하락하는지 논리적/수치적으로 증명해야 한다.

### 2.2. 기술 융합적 통찰 (Technological Convergence)
- 단일 기술(예: AI, 배터리)의 단편적 소식이 아니라, 여러 기술이 결합하여 만들어내는 거시적 경제 효과(Macroeconomic Shift)를 분석한다.
- "A 기술의 발전이 B 산업에 미치는 연쇄 파급 효과"를 명확히 서술한다.

### 2.3. 학술적 엄밀성과 인용 (Academic Rigor & References)
- 리포트의 신뢰도를 확보하기 위해 주장의 근거를 명확히 제시한다.
- Tier 1에서 수집한 학술 논문(arXiv), 정부 공식 데이터(NHTSA, FDA 등), 기업 공시 자료를 반드시 본문과 하단 `Works Cited`에 명시한다.

### 2.4. 명확한 시장 규모 산정 (TAM: Total Addressable Market)
- 기술의 혁신성을 넘어, 해당 기술이 창출할 비즈니스 기회와 경제적 가치를 구체적인 숫자(예: 2030년 XX조 달러 규모)로 치환하여 독자에게 제공한다.

### 2.5. 용어 해설 의무화 (Mandatory Footnote Rule)
- 비전문가 독자(VP Review 통과 기준)를 배려하여, 본문에 등장하는 **모든 전문/어려운 용어에는 반드시 각주(Footnote)를 달아 상세히 설명**해야 한다. 
- 지식의 저주(Curse of Knowledge)에 빠지지 않도록 유의한다.

---

## 3. Weekly Issue Workflow

1. **월요일 (Collector):** arXiv, EDGAR, 정부 통계 등 고품질 학술/공시 데이터 집중 수집
2. **화요일 (Filter - Local LLM):** 노이즈 제거 및 데이터 가치(Score) 평가
3. **수요일 (Refiner - Multi-LLM Collab):** 
   - **Gemini:** 기술적 인과관계 구조화 및 코딩/데이터 스키마 처리
   - **Claude:** 긴 컨텍스트 융합, 임원급 논조(Executive Memo) 작성, TAM 추정치 도출
   - **Copilot:** 인용구 정리 및 서식 검증
4. **목요일 (Fact-Check):** 각주(Footnotes) 검증 및 레퍼런스(Works Cited) 크로스체크
5. **금요일 (VP Review):** 가독성, 한국어 자연스러움, 각주의 친절함 검토
6. **토요일 (CEO Review):** 최종 주장(Claim), 법률 리스크 확인 및 발행 승인
7. **일요일 (Publisher):** 유료/무료 티어 분리 발행 및 지표 측정

---

## 4. Premium Issue Template

```markdown
# [타이틀] A 기술과 B 기술의 융합이 만드는 [시장규모]의 기회

## 💡 Executive Summary
(ARK 수준의 거시적 요약: 현상 - 융합 - 경제적 파급효과)

## 📈 1. 데이터가 증명하는 비용 하락의 궤적 (Trend)
- Wright's Law 적용 분석
- 기술 보급률 및 비용 하락 수치 제시

## 융합: [기술A] x [기술B] = [혁신C] (Convergence)
- 기술 융합의 구조적 분석
- 산업별 연쇄 반응 예측

## 💰 경제적 파급효과 및 TAM 산정 (Market Sizing)
- 현행 산업의 비효율 비용
- 기술 도입 시 절감 비용 및 신규 창출 시장 규모 ($ 빌리언/트릴리언 단위)

## 🔒 유료 구독자 전용 Insight (Premium Note)
- 구체적 밸류체인 내 수혜/타격 예상 기업군
- 3~5년 내 핵심 마일스톤(Watchlist)

---
### 📚 Works Cited
- [1] 저자, "논문/보고서 제목", 출처, 연도.
- [2] 기관명, "통계 자료", 연도.

### 📝 주석 (Footnotes)
[^1]: 어려운 용어 1: 비전문가가 이해할 수 있는 쉬운 설명.
[^2]: 어려운 용어 2: 일상적인 비유를 곁들인 설명.
```

---

## 5. Notion Archive Field Updates
- `TAM_Calculated` (Boolean)
- `Convergence_Tags` (List)
- `Footnote_Count` (Number)
