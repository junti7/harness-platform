# Handoff — 트레이딩 종목 선정의 "evidence→ticker 다리" 확장

- 작성일: 2026-06-09
- 작성자: Claude (Opus 4.8) — CEO 지시로 다른 LLM 개선작업용 핸드오프
- 대상 작업자: 차기 LLM/에이전트 (engineering)
- 우선순위: 中 (트레이딩 차단 상태라 당장은 백테스트용 — 아래 §6 참조)

---

## 1. 한 줄 요약

physical_ai 도메인에서 매일 대량 수집·정제하는 기술 evidence 중 **5.8%만 종목 선정에 도달하고 94%는 버려진다.** 원인은 수집 부족이 아니라 **evidence를 종목에 연결하는 alias 매핑이 좁아서**다. 이 "다리"를 넓혀 수집 투자 대비 선정 활용도를 끌어올리는 것이 이 작업의 목표다.

---

## 2. 측정된 문제 (2026-06-09 실측, Mac Mini prod DB)

`core.trading_universe._load_candidate_rows("physical_ai", 45)` 기준:

- 후보 evidence(45일 filtered_signals): **8,463건**
- 이 중 종목 1개 이상에 매칭: **489건 (5.8%)** → **94%가 선정에 미도달**
- 소스 분포: arXiv 71%(AI 2,919 / ML 2,068 / robotics 1,055), 공공데이터포털 585, google_news, 그리고 2026-06-09 신규 다양화 소스(openalex/hackernews/semantic_scholar/arxiv_api) = 563건(6.7%)

종목별 매칭(현재 universe seed = 12종목):

| 종목 | 매칭 evidence | 신규소스 기여 | 비고 |
|---|---|---|---|
| NVDA | 250 | 13 | google_news+arXiv 주력 |
| VRT | 78 | 16 | `liquid cooling` alias 작동 |
| MU | 69 | **31 (45%)** | `hbm` alias가 학술과 잘 붙음 — 다양화 효과 실재 |
| SYM | 51 | 12 | `warehouse automation` |
| TSM | 31 | 9 | `2nm/wafer` |
| AVGO/ANET/삼성/SK하이닉스/ROK/ISRG | 16·9·10·1·4·2 | 0 | 근거 빈약, 다양화 기여 0 |

**핵심 진단:** 선정 엔진은 수집 자료를 종목별 **하드코딩 alias**(회사명 + 소수 기술어)로만 본다. 논문/뉴스는 "silicon photonics·humanoid·AI accelerator·sim-to-real"처럼 **일반 기술어**로 쓰는데 대응 종목 alias가 없어, 그 evidence는 수집돼도 선정에서 안 보인다. (예: 2026-06-09에 의도적으로 넣은 휴머노이드·포토닉스·가속기 쿼리 결과물 대부분이 매칭 0. TSLA `optimus` alias조차 0 매칭.)

---

## 3. 코드 지도 (수정 대상)

파일: **`core/trading_universe.py`**

| 함수 | 위치 | 역할 |
|---|---|---|
| `_alias_map(symbol, name)` | L80 | 종목→매칭 키워드 dict. **여기가 다리의 핵심. 현재 ~12종목, 종목당 2~5개 키워드뿐.** |
| `_alias_patterns(symbol, name)` | L108 | alias→정규식 컴파일. 영숫자 alias는 단어경계, 그 외 substring. |
| `_load_candidate_rows(domain, lookback)` | L132 | `filtered_signals JOIN raw_signals` 45일치 텍스트 로드 |
| `build_trading_universe(domain, lookback, max_symbols)` | L219 | 종목별 매칭→가중합(score×reliability×recency)→`harness_score`(1~10). distinct_sources 가산. |
| `_load_seed_registry()` | L44 | 종목 시드. `UNIVERSE_PATH` 파일 있으면 그걸 사용(현재 12종목), 없으면 기본 20종목. |

관련 사실:
- Tier2 필터(`adapters/content/filter.py`)가 raw→filtered로 승급해야 universe 후보가 된다.
- 2026-06-09 `save_signal` 수정으로 학술 abstract가 summary/full_content에 매핑됨 → 학술 evidence 본문이 이제 매칭 텍스트에 포함됨(이 작업의 전제조건, commit `92aabb8` 이후).

---

## 4. 개선 과제

### 4-A. (핵심) 테마→종목 매핑 레이어 신설
일반 기술어 evidence를 노출 종목으로 연결한다. 제안 설계:

```
THEME_TO_TICKERS = {
  "silicon photonics":      ["COHR", "LITE", "AVGO", "NVDA"],
  "co-packaged optics":     ["AVGO", "MRVL", "COHR"],
  "high bandwidth memory":  ["MU", "000660", "005930"],   # 이미 부분 커버
  "humanoid":               ["TSLA", "6954", "SYM", "ISRG"],
  "ai accelerator|gpu|tpu": ["NVDA", "AVGO", "GOOG"],
  "liquid cooling|immersion cooling": ["VRT"],
  "sim-to-real|world model": ["NVDA", "GOOG", "TSLA"],
  "advanced packaging|cowos|chiplet": ["TSM", "042700", "AVGO"],
  ...
}
```
- `_alias_map`을 확장하거나, 별도 테마 매처를 `build_trading_universe` 매칭 루프에 추가.
- 테마 매칭은 **신뢰도 가중을 낮게**(예: 직접 회사명 매칭의 0.5배) 줘서 약한 신호임을 반영. 테마는 "관련 종목 후보 확대"용이지 회사 직접 언급과 동급이 아니다.
- 시드 종목에 없는 새 ticker(COHR/LITE/MRVL 등)를 추가하려면 `_load_seed_registry` / `UNIVERSE_PATH` 파일도 함께 갱신.

### 4-B. (보조) 기존 회사 alias 보강
NVDA에 `gpu/accelerator/cuda` 없음, 다수 종목이 회사명만 있음. 종목별 제품·기술어 alias를 늘린다. (예: ISRG `surgical robot`, ROK `industrial automation`, GOOG `tpu/gemini`.)

### 4-C. (선택) 매핑을 코드 하드코딩이 아닌 설정 파일로
`configs/trading/theme_ticker_map.json` 등으로 분리해 코드 변경 없이 확장 가능하게. (유지보수성)

---

## 5. 성공 기준 (측정 가능)

베이스라인(2026-06-09): 매칭율 **5.8%**, 신규소스 기여 6.7%.

- [ ] 매칭율(≥1종목 매칭 evidence 비율) **5.8% → 20%+**
- [ ] 매칭 evidence 0~극소(<5건) 종목 수 감소
- [ ] silicon photonics/humanoid/accelerator 등 테마 evidence가 실제로 종목에 귀속되는지 케이스 확인
- [ ] harness_score 분포가 noise(1~2건 근거로 점수)에서 개선 — 종목당 최소 distinct_source 근거 확보
- [ ] **Turtle 게이트·점수 상한(1~10)·`harness_score≥7` 기준은 변경 금지** (아래 §6)

검증 스크립트(그대로 재실행해 전후 비교):
```python
# /tmp/match_rate.py — 매칭율
import sys; sys.path.insert(0,'.')
from core import trading_universe as TU
rows=TU._load_candidate_rows("physical_ai",45)
seeds=TU._load_seed_registry()
pats={s["symbol"]:TU._alias_patterns(s["symbol"],s.get("name","")) for s in seeds}
matched=sum(1 for r in rows if any(any(p.search(r.text) for p in ps) for ps in pats.values()))
print(f"{matched}/{len(rows)} = {100*matched/len(rows):.1f}%")
```
(종목별 소스 분해 진단 스크립트는 commit 히스토리/이 핸드오프 작성자 세션 참조, 또는 위를 종목별 loop로 확장.)

실행: Mac Mini(prod, 100.97.175.44) `cd ~/projects/harness-platform && source .venv/bin/activate && python3 - < script.py`. **Mac Mini가 프로덕션 DB**(MBP는 테스트).

---

## 6. 제약·게이트 (반드시 준수)

- **[트레이딩 차단 중]** AR-018 red_team_block + `CAPITAL_ACTIONS_ENABLED=false`. 이 작업은 **선정 로직 개선이며 실제 자본을 움직이지 않는다.** 해제 전까지는 백테스트/시뮬레이션 용도. 트레이딩을 "활성화"하는 작업이 아님을 명심.
- **[Turtle 불변]** `docs/trading/TURTLE_TRADING_PRINCIPLES.md`의 5대 원칙(종목선정·포지션사이징·진입·손절·청산)과 `turtle_gate_*` 로직은 **건드리지 않는다.** 이 작업은 "후보 evidence→종목 매핑" 단계만 손댄다.
- **[Red Team 필수]** 코드 변경은 서로 다른 LLM 2개 이상 cross-LLM red_team_clear 후 반영(CLAUDE.md §5). 참고: 현재 Gemini 선불크레딧 소진(429), Claude API 미과금 → 가용 조합은 **Claude(오케스트레이터)+Codex(`/opt/homebrew/bin/codex`)**. (오늘 Wave 2도 이 조합으로 검증함.)
- **[데이터 정책]** 새 ticker/소스 추가가 수반되면 `legal_review_approve`도 검토(공개 시세/메타데이터는 저위험).
- **[배포]** 로컬 수정→커밋·푸시→Mac Mini는 `git checkout origin/main -- <file>` 단일파일 배포(전체 pull은 드리프트 위험, `docs/handoffs/`·memory `project_macmini_git_drift` 참조). 다른 LLM 미커밋 작업 파일은 건드리지 말 것.

---

## 7. 참고

- 오늘 관련 커밋: `92aabb8`(edu 다양화), `6b3d198`(physical 다양화+abstract fix), `5e8ba8d`(RSS 복구), `4e5fd8a`(대시보드 실시간), `271ed4f`(대시보드 모바일).
- 관련 문서: `docs/operations/COLLECTION_DIVERSIFICATION_PLAN.md`, `docs/governance/wave2_collection_gate_2026-06-09.md`, `docs/trading/TURTLE_TRADING_PRINCIPLES.md`, `core/trading_universe.py`.
- 냉정한 현실: 이 작업은 "수집→선정" 활용도를 높이지만, **트레이딩이 차단된 동안은 매출/자본 효과 0**이다. 우선순위는 교육 컨설팅 수익화(Pretotyping CTR·첫 유료 구독자)가 여전히 위다. 이 핸드오프는 "수집 자료가 선정에서 낭비되고 있다"는 기술 부채를 다른 LLM이 정리하도록 넘기는 것이지, 트레이딩을 메인으로 올리자는 게 아니다.
