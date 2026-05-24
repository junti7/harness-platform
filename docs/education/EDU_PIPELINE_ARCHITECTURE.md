# 파이프라인 도메인 분리 아키텍처 (Physical AI vs 교육 컨설팅)

> 작성: 2026-05-24 | AR-029 Red Team 조건 C 해소 | correlation_id: edu-consulting-20260524
> 목적: Physical AI(B2I 투자신호) 파이프라인과 교육 컨설팅 파이프라인의 충돌 없는 공존 설계

---

## 1. 문제 정의 (Claude Red Team 지적)

현재 Harness 파이프라인은 단일 수집기 구조다.
- **Physical AI 파이프라인**: arXiv 로보틱스·ETF·반도체 신호 → B2I 투자 인텔리전스
- **교육 컨설팅 파이프라인**: AI 교육 학술·미디어·유튜브 → 학부모 자문 콘텐츠

소스 도메인, 분석 목적, 출력 포맷이 완전히 다름. 혼재 시:
1. 투자 신호에 교육 콘텐츠가 섞여 노이즈 증가
2. 교육 분석에 로보틱스 논문이 들어가 품질 저하
3. LLM 비용 계산 불투명 (도메인별 분리 불가)

---

## 2. 분리 설계 원칙

### Domain Registry 분리 (이미 구현됨)

```
configs/sources/
├── edu_consulting.json     ← 교육 도메인 소스 (AR-028 완료)
└── physical_ai.json        ← Physical AI/ETF 소스 (기존)
```

두 JSON 파일은 `domain` 필드로 구분:
```json
// edu_consulting.json
{"_meta": {"domain": "edu_consulting", ...}}

// physical_ai.json  
{"_meta": {"domain": "physical_ai", ...}}
```

### 수집기 분리 (구현 예정)

```
scripts/
├── run_edu_deep_research.py    ← 교육 전용 수집기 (AR-026, Red Team clear 후)
└── run_physical_ai_pipeline.py ← 기존 Physical AI 파이프라인
```

두 스크립트는 서로 다른 `domain` 파라미터로 기동:
```bash
# 교육 도메인 실행
.venv/bin/python scripts/run_edu_deep_research.py \
  --sources configs/sources/edu_consulting.json \
  --domain edu_consulting --tier 1

# Physical AI 도메인 실행  
.venv/bin/python scripts/run_physical_ai_pipeline.py \
  --sources configs/sources/physical_ai.json \
  --domain physical_ai --tier 1
```

---

## 3. DB 스키마 분리 (제안)

기존 `signals` 테이블에 `domain` 컬럼을 추가해 도메인별 격리:

```sql
ALTER TABLE signals ADD COLUMN domain VARCHAR(50) DEFAULT 'physical_ai';
CREATE INDEX idx_signals_domain ON signals(domain);
```

쿼리 시 도메인 필터 강제:
```sql
-- 교육 도메인 신호만 조회
SELECT * FROM signals WHERE domain = 'edu_consulting' ORDER BY created_at DESC;

-- Physical AI 신호만 조회
SELECT * FROM signals WHERE domain = 'physical_ai' ORDER BY created_at DESC;
```

---

## 4. LLM 비용 계정 분리

각 파이프라인 실행 시 비용 태그 추가:
```python
# 교육 파이프라인 호출 시
response = anthropic.messages.create(
    ...,
    metadata={"domain": "edu_consulting", "correlation_id": "edu-consulting-20260524"}
)
```

월별 비용 리포트 시:
- `domain=edu_consulting` 비용 → 교육사업 예산 ($100/월)에서 차감
- `domain=physical_ai` 비용 → B2I 예산에서 차감 (별도 예산 필요 시 CEO 승인)

---

## 5. 뉴스레터 파이프라인 역할 재정의

CEO 결정(2026-05-24): 뉴스레터 외부 발행 중단 → **B2I 투자 정보 수집 Backend**

```
현재 아키텍처 (명확화):
┌─────────────────────────────────────────────────────┐
│ Physical AI 파이프라인 (domain: physical_ai)          │
│  Tier 1: arXiv/로보틱스/ETF RSS 수집                 │
│  Tier 2: Ollama 필터                                  │
│  Tier 3: Claude/Gemini 투자 신호 분석                 │
│  Tier 4: → [B2I 투자 인텔리전스 내부 보고]            │
│          → [뉴스레터 외부 발행 ❌ BLOCKED]            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 교육 컨설팅 파이프라인 (domain: edu_consulting)       │
│  Tier 1: 교육 RSS/YouTube/논문 수집                   │
│  Tier 2: Ollama 교육 관련성 필터                      │
│  Tier 3: Claude/Gemini 학부모 자문 콘텐츠 분석        │
│  Tier 4: → [부대표 검토 → 유료 구독 발행 ✅]          │
└─────────────────────────────────────────────────────┘
```

두 파이프라인은 **인프라(Mac Mini, .venv, Ollama)를 공유**하되 **소스·DB·LLM 비용 계정은 분리**.

---

## 6. 구현 순서 (Red Team clear 후)

1. `signals` 테이블에 `domain` 컬럼 추가 (스키마 마이그레이션)
2. `run_edu_deep_research.py` 스켈레톤 작성 (AR-026)
3. 기존 `collector.py`에 `--domain` 파라미터 추가
4. 비용 태그 메타데이터 표준화

---

> 리스크 C 해소: 두 파이프라인은 `configs/sources/` 레지스트리 분리, `domain` 파라미터 격리, DB 컬럼 필터로 충돌 없이 공존 가능. 인프라 재사용 효율은 유지하면서 도메인 혼선은 방지됨. 구현 선행 조건: AR-029 red_team_clear.

---

*생성: 2026-05-24 | Jarvis (Red Team 조건 C 해소) | AR-029 | correlation_id: edu-consulting-20260524*
