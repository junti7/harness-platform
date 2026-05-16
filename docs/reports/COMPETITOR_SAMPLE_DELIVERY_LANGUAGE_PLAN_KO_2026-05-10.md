# 경쟁사 샘플/전달방식/언어전략 보고서

작성일: 2026-05-10  
대상: 대표, 부대표  
작성: CEO 비서실장 기능 / 상품기획팀 / QA Team  

---

## 1. CEO 요약

| 항목 | 결론 |
| --- | --- |
| 공개 샘플 리포트 | 존재하지만 핵심 유료 구간은 제한적임 |
| 유료 구독 벤치마킹 | 필요 시 한시적으로 검토 가능. 단 대표 승인/법무/Pre-Mortem 필수 |
| 제품 전달 방식 | PDF만으로 부족. 웹 포털 + 이메일 + PDF + 고객 memory가 필요 |
| 유료 상품 언어 | 한국어 + 영어 필수 |
| 기타 언어 | 수요/QA/native review 확보 전에는 보류 |
| 가장 중요한 품질 허들 | 부대표 및 비전문가가 이해하고 “돈 낼 이유”를 느껴야 함 |
| 장기 자산 | 고객별 피드백, 질문, watchlist, product upgrade DB 누적 |

---

## 2. 공개 샘플 자료 위치

공개 샘플 후보는 다음 파일에 정리했다.

| Library | 위치 | 내용 |
| --- | --- | --- |
| 공개 샘플 리포트 목록 | `docs/library/competitor_intelligence/public_sample_reports.md` | 공개 PDF, 공개 sample, paywall preview, product page |
| 경쟁사별 요약 | `docs/library/competitor_intelligence/` | 회사별 포지셔닝, 가격, 제품 구조 |
| LLM 조사 결과 | `docs/reports/llm_outputs/` | Claude/Gemini/Copilot 원자료 요약 |

---

## 3. 실제 참고할 공개 샘플 후보

| 우선순위 | 자료 | 활용 목적 | 주의사항 |
| --- | --- | --- | --- |
| 1 | SemiAnalysis Sample Chipbook PDF | 데이터/표/모델 밀도 확인 | 공식 공개 PDF인지 재확인 |
| 2 | SemiAnalysis Robotics Part 1 preview | Physical AI와 가장 가까운 도메인 분석 구조 | 유료 구간 저장 금지 |
| 3 | Stratechery Daily Update Sample | 과거 유료 샘플의 글 구조와 전달 방식 확인 | 오래된 샘플이므로 최신 가격/UX 별도 확인 |
| 4 | CB Insights State of AI report page | chart-heavy 시장 리포트 구조 확인 | full report는 sign-in 가능성 |
| 5 | ARK Big Ideas | 일반 투자자용 테마 리포트 구조 확인 | 예측 과잉은 그대로 모방 금지 |
| 6 | McKinsey Technology Trends / Agents and Robots report | 컨설팅식 표/도표/so-what 구조 확인 | 무료 thought leadership 성격 |
| 7 | Deloitte Tech Trends / CEO Guide | executive packaging과 persona별 문서 확인 | PDF+웹 interactive 형태 참고 |
| 8 | Gartner Magic Quadrant methodology | matrix/scorecard 구조 확인 | 실제 MQ 전문은 라이선스 주의 |

---

## 4. 공개 샘플만으로 부족할 때

공개 샘플만으로는 유료 상품의 실제 품질을 충분히 보기 어려울 수 있다.

| 문제 | 설명 |
| --- | --- |
| Paywall 절단 | 핵심 표, 결론, 모델이 유료 구간에 있음 |
| UX 미확인 | 실제 이메일/RSS/앱/웹 포털 경험은 구독해야 확인 가능 |
| 유료/무료 경계 불명확 | 무엇을 무료로 주고 무엇을 유료로 남기는지 알기 어려움 |
| 품질 기준 낮아짐 | 실제 유료 artifact를 보지 않으면 우리 기준이 낮아질 위험 |

따라서 한시적 유료 구독은 검토할 수 있다.

승인 패킷:

`docs/reports/PAID_COMPETITOR_SUBSCRIPTION_APPROVAL_PACKET_2026-05-10.md`

---

## 5. 유료 벤치마킹 후보

| 후보 | 목적 | 비용/리스크 | 권고 |
| --- | --- | --- | --- |
| Stratechery 1개월 | free weekly와 paid daily 분리, email/RSS UX 확인 | 저비용 | 1순위 |
| SemiAnalysis | Physical AI/semiconductor deep dive, 표/모델/paywall 구조 확인 | 비용 큼 | 별도 승인 |
| The Information | premium journalism, database, app, newsletter bundle 확인 | 비용 큼 | 현 단계 보류 |
| Doomberg/Substack analyst | voice, metaphor lead, paid boundary 확인 | 중간 | 선택 |

유료 구독 후에도 유료 본문 전문 저장, 캡처 재배포, 문장 복제는 금지한다.

---

## 6. 경쟁사 제품 전달 방식

| 경쟁사/유형 | 전달 방식 | Harness 시사점 |
| --- | --- | --- |
| Stratechery | 이메일, 웹, RSS, podcast | paid는 PDF보다 inbox habit이 중요 |
| SemiAnalysis | 웹 article, 이메일, institutional model/data product | deep dive + data model 분리 가능 |
| The Information | 웹, 앱, newsletter, audio, database, org chart | 보고서 + 데이터베이스 + 앱 경험이 결합 |
| CB Insights | 웹 terminal, email personal briefing, homepage, watchlist, mobile, API/MCP | 개인화 briefing과 watchlist가 핵심 |
| PitchBook | web platform, mobile, Chrome extension, Excel plugin, API | 고객 workflow 안으로 들어가야 함 |
| Gartner | web portal, mobile app, analyst inquiry, PDF, notifications | 리포트+전문가 상담+모바일 피드 |
| AlphaSense | web search, saved search, email alerts, dashboards, executive brief | alert와 검색이 리포트보다 중요할 수 있음 |
| Deloitte/McKinsey/BCG | public web report, PDF, interactive report, client presentation | 표/도식/so-what 구조 학습 필요 |

결론:

PDF는 premium artifact이지만 단독 상품으로는 약하다. 고객 경험은 웹 포털, 이메일, PDF, watchlist, 알림, 고객 memory가 결합되어야 한다.

---

## 7. Harness 권장 전달 구조

| 채널 | 역할 |
| --- | --- |
| Web portal | 고객별 archive, watchlist, 질문 이력, 과거 리포트 |
| Email | 매주 요약과 링크 전달 |
| PDF | premium deep report, 보관/공유용 artifact |
| Slack/Notion | 내부 검토와 승인용. 고객 전달용 아님 |
| Signed link | 유료 PDF 보안 다운로드 |
| Customer memory DB | 다음 리포트 개인화의 근거 |

---

## 8. 언어 전략

| 언어 | 상태 | 정책 |
| --- | --- | --- |
| 한국어 | 필수 | master edition. 부대표/비전문가 허들 통과 필수 |
| 영어 | 유료 상품 필수 | 영어 executive summary 또는 full edition 포함 |
| 일본어 | 후보 | Phase 2 이후 native review 확보 시 검토 |
| 중국어 | 보류 | 법률/검열/운영 리스크 큼 |
| 기타 언어 | 보류 | 수요와 QA capacity 확인 전 금지 |

유료 상품은 한국어와 영어를 반드시 포함한다.

단, 영어는 단순 자동번역이 아니라 별도 QA/Legal/Red Team을 통과한 edition이어야 한다.

---

## 9. 부대표/비전문가 허들

| 기준 | 통과 조건 |
| --- | --- |
| 이해 가능성 | 부대표가 핵심 thesis를 1문장으로 설명 가능 |
| 용어 장벽 | 어려운 용어마다 쉬운 설명 존재 |
| 투자 관련 의미 | buy/sell 없이 company/technology watchlist와 시나리오 제공 |
| 돈 낼 이유 | 무료 글과 유료 상품 차이가 명확 |
| 신뢰감 | 과장, 허세, 사기성 표현 없음 |
| 개인화 느낌 | 고객 관심사 또는 질문이 반영됨 |

부대표가 `block`하면 유료 발행 금지다.

---

## 10. 고객 피드백/업그레이드 누적 구조

| 데이터 | DB 테이블 | 목적 |
| --- | --- | --- |
| 고객 profile | `customer_profiles` | 언어, 지식수준, tier, consent |
| 고객 feedback/event | `customer_memory_events` | 클릭, 답장, 혼란, hesitation, 요청 누적 |
| 관심사 | `customer_interest_tags` | topic weight 관리 |
| Watchlist | `customer_watchlists` | 고객별 회사/기술/지표 추적 |
| 질문 | `customer_questions` | 다음 리포트에서 답변할 질문 |
| 상품 개선 | `product_upgrade_events` | feedback이 상품에 어떻게 반영됐는지 기록 |
| 산출물 참조 이력 | `artifact_memory_usage` | 특정 report가 어떤 memory를 참조했는지 QA 증빙 |

QA는 개인화 상품이 위 데이터를 실제로 참조했는지 확인해야 한다.

---

## 11. QA 신규 차단 기준

| 차단 조건 | 의미 |
| --- | --- |
| memory usage record 없음 | 개인화라고 주장하지만 DB 근거 없음 |
| 고객 질문 미반영 | open/high-priority 질문을 무시 |
| watchlist 미반영 | 고객이 추적하는 기업/기술이 반영되지 않음 |
| consent 없는 개인화 | 개인정보/동의 리스크 |
| 민감 투자정보 사용 | 보유종목, 매매의도, 자산규모 사용 금지 |
| 다른 상품 재사용 미검토 | 반복 feedback이 상품 개선으로 연결되지 않음 |

---

## 12. 대표 의사결정 요청

| 번호 | 결정 요청 | 권고 |
| --- | --- | --- |
| 1 | 공개 샘플 Library 확장 계속 진행 | 승인 |
| 2 | 유료 구독 벤치마킹 승인 패킷 검토 | 승인 검토 |
| 3 | Stratechery 1개월 구독부터 테스트 | 승인 권고 |
| 4 | SemiAnalysis 구독은 별도 capital action으로 검토 | 보류 후 별도 승인 |
| 5 | 유료 상품은 한국어+영어 필수 | 승인 |
| 6 | 기타 언어는 Phase 2 이후 검토 | 승인 |
| 7 | 고객 memory/watchlist DB를 상품 핵심 자산으로 지정 | 승인 |

---

## 13. 최종 권고

Harness가 팔아야 할 것은 PDF 한 장이 아니다.

팔아야 할 것은:

| 자산 | 설명 |
| --- | --- |
| 쉬운 한국어 해설 | 부대표/비전문가도 이해 |
| 영어 edition | 글로벌 자료성과 신뢰 확보 |
| 고객별 watchlist | 어떤 회사/기술을 계속 볼지 제시 |
| 고객 memory | 피드백이 다음 상품에 반영 |
| Library | 경쟁사와 시장 자료 누적 |
| Scorecard | 유료 품질을 객관적으로 검증 |
| Web/email/PDF delivery | 고객이 원하는 방식으로 전달 |

다음 단계는 공개 샘플 Library를 확장하면서, 승인된 경우 낮은 비용의 유료 구독 벤치마킹을 1개월만 진행하는 것이다.
