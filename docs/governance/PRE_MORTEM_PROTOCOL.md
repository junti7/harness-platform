# PRE-MORTEM PROTOCOL
**Version:** 1.0 | **Owner:** Chief of Staff (Codex) | **Gate:** `pre_mortem_approve`

---

## 1. 목적

High-impact 의사결정 전에 최악의 시나리오를 명시적으로 분석한다.
Pre-Mortem 없이 high-impact 결정을 실행하지 않는다 (CLAUDE.md §6 Never).

## 2. 적용 대상

다음 결정은 반드시 Pre-Mortem 작성 후 `pre_mortem_approve`를 기록해야 한다:

- `report_publish_approve` (외부 발행 / 유료 리포트)
- `monetization_experiment_approve` (paid 실험)
- `investment_thesis_approve` (투자 thesis)
- `capital_action_approve` (자본 집행)
- 외부 광고/마케팅 카피 발행
- 데이터 수집 정책 변경
- 가격 변경
- 다국어 launch

## 3. Pre-Mortem 작성 요건

최소 포함 항목:

| 항목 | 설명 |
|------|------|
| 의사결정 요약 | 무엇을 하려는가 |
| 최악 시나리오 (×3 이상) | "이 결정이 완전히 실패한다면" 가정 |
| 발생 확률 | 각 시나리오의 주관적 확률 (%) |
| 최대 손실 | 금전적/평판/운영 측면 |
| 회복 가능성 | 되돌릴 수 있는가, 얼마나 걸리는가 |
| Mitigation | 실패 가능성을 낮추는 사전 조치 |
| Detection Trigger | 실패를 언제 인지할 수 있는가 |

## 4. 프로세스

```
1. Codex 또는 Claude가 Pre-Mortem 문서 작성
2. 대표(CEO)가 검토 후 동의 여부 판단
3. 동의 시 bridge로 pre_mortem_approve 기록:
   python scripts/openclaw_codex_bridge.py record-decision \
     <target_type> <target_id> approved pre_mortem_approve \
     --reason "pre_mortem: docs/governance/PRE_MORTEM_<date>_<title>.md"
4. 이후 high-impact 결정 gate가 열림
```

## 5. 산출물 위치

`docs/governance/PRE_MORTEM_<YYYY-MM-DD>_<title>.md`

---

*이 문서가 없으면 `pre_mortem_approve` gate를 통과할 수 없다.*
