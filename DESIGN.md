---
name: Harness Platform
version: "0.1.0"
description: Design system for the Harness operating dashboard, tuned for trading-plan review, decision support, and risk-first operator workflows.
colors:
  ink-strong: "#0f172a"
  ink: "#111827"
  text-muted: "#475569"
  text-faint: "#64748b"
  accent: "#2563eb"
  accent-soft: "#dbeafe"
  accent-cyan: "#0ea5e9"
  background: "#f8fafc"
  background-elevated: "#f4f7fb"
  surface: "#ffffff"
  surface-muted: "#f8fafc"
  border: "#e2e8f0"
  border-strong: "#cbd5e1"
  gridline: "#e5edf5"
  success: "#059669"
  success-soft: "#d1fae5"
  warning: "#d97706"
  warning-soft: "#fef3c7"
  danger: "#dc2626"
  danger-soft: "#fee2e2"
  info-soft: "#eff6ff"
typography:
  h1:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "2rem"
    fontWeight: "700"
    lineHeight: "1.1"
    letterSpacing: "-0.02em"
  h2:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.25rem"
    fontWeight: "600"
    lineHeight: "1.25"
    letterSpacing: "-0.01em"
  h3:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.95rem"
    fontWeight: "600"
    lineHeight: "1.3"
  body-md:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: "400"
    lineHeight: "1.5"
  body-sm:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.875rem"
    fontWeight: "400"
    lineHeight: "1.45"
  label:
    fontFamily: "'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.75rem"
    fontWeight: "600"
    lineHeight: "1.2"
    letterSpacing: "0.02em"
  numeric:
    fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
    fontSize: "0.95rem"
    fontWeight: "600"
    lineHeight: "1.2"
    fontFeature: "'tnum' 1, 'cv05' 1"
rounded:
  sm: "4px"
  md: "10px"
  lg: "14px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  sm-md: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "40px"
components:
  shell:
    backgroundColor: "{colors.background}"
    textColor: "{colors.ink}"
  card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  decision-card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  kpi-card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    borderColor: "{colors.border-strong}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  status-chip:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.text-muted}"
    borderColor: "{colors.border}"
    rounded: "{rounded.pill}"
    padding: "6px 10px"
  risk-banner:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.ink}"
    borderColor: "{colors.warning}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm-md}"
  command-surface:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  data-table:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
  body-text:
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
  metadata:
    textColor: "{colors.text-muted}"
    typography: "{typography.body-sm}"
  numeric-text:
    textColor: "{colors.ink-strong}"
    typography: "{typography.numeric}"
  status-positive:
    textColor: "{colors.success}"
  status-caution:
    textColor: "{colors.warning}"
  status-negative:
    textColor: "{colors.danger}"
---

## Overview
Harness Platform의 운영 대시보드는 **"Calm Mission Control for High-Stakes Decisions"**를 지향합니다. 트레이딩 계획 수립 화면은 매수 충동을 자극하는 소비자형 투자 앱이 아니라, 계획, 리스크, 규율 위반 여부를 빠르게 판별하는 운영 콘솔이어야 합니다.

복잡한 데이터를 단순히 예쁘게 요약하지 말고, **무엇을 해야 하는지 / 하면 안 되는지 / 왜 그런지**가 즉시 드러나야 합니다. 수익 기대보다 리스크와 무효화 조건(invalidation)이 먼저 읽혀야 하며, 사용자는 5초 안에 오늘 계획의 실행 가능 여부를 파악할 수 있어야 합니다.

## Colors
팔레트는 현재 대시보드의 라이트 베이스와 블루/시안 기류를 유지하되, 더 정밀하고 운영적인 톤으로 정리합니다. 블루 계열은 브랜드와 인터랙션을 담당하고, 초록/빨강은 손익이나 상태 표현에만 제한적으로 사용합니다.

- **Ink Strong / Ink:** 주요 헤드라인, 숫자, 핵심 결론에 사용합니다.
- **Text Muted / Faint:** 메타데이터, 보조 설명, 조건문, timestamps에 사용합니다.
- **Accent / Accent Cyan:** 선택 상태, 인터랙션, 중요한 CTA, 제한적 데이터 강조에 사용합니다.
- **Warning / Danger:** 경고, 리스크 초과, invalidation 근접, 규율 위반에 사용합니다.
- **Success:** 계획 준수, 정상 범위, 리스크 통제 상태에 사용합니다.

초록과 빨강을 브랜드 색처럼 넓게 사용하지 마세요. 전체 화면이 손익 색에 지배되면 도박성 트레이딩 UI처럼 보입니다.

## Typography
타이포는 짧고 단단해야 합니다. 설명문은 간결해야 하며, 숫자는 한눈에 비교 가능해야 합니다.

- **H1:** 현재 화면의 운영 헤더. 짧고 단단하게.
- **H2/H3:** 카드 타이틀과 섹션 타이틀. 기능적이며 과장되지 않게.
- **Body MD / SM:** 설명과 상태 요약용.
- **Numeric:** 가격, 비율, 손익, exposure, risk multiple, conviction score에 우선 사용합니다.

가능하면 숫자 영역에는 tabular numerals를 적용해 열 정렬 안정성을 확보하세요.

## Layout
레이아웃은 일반적인 SaaS 카드 그리드에서 끝나면 안 됩니다. 화면은 **상단 판단 레이어 → 계획 레이어 → 로그/보조 레이어**로 읽혀야 합니다.

- 첫 스캔 구역에는 `오늘의 시장 상태`, `전략 준비도`, `리스크 경고`, `실행 가능 여부`를 배치합니다.
- KPI 카드는 단순 수치 박스가 아니라 판단 카드여야 합니다. 값만이 아니라 변화, 맥락, 위험 신호를 함께 보여주세요.
- Watchlist, setup, trigger, invalidation, position sizing, scenario A/B/C, do nothing 상태를 구조적으로 노출하세요.
- 데스크톱은 운영자 workflow 우선입니다. 모바일에서는 카드 수를 줄이되 리스크, 실행 가능 여부, 핵심 시나리오는 항상 남겨둡니다.

## Elevation & Depth
깊이는 강한 그림자 대신 **밝기 차이, 얇은 보더, 구획 분리**로 만듭니다. 금융 운영 UI처럼 정교하고 절제된 계층감을 유지하세요.

- 기본 카드는 흰색 surface 위 얕은 보더를 사용합니다.
- 강조 구역은 더 진한 그림자가 아니라 배경 톤 변화 또는 accent border로 구분합니다.
- 위험 상태는 shadow가 아니라 semantic color와 concise label로 전달합니다.

## Shapes
형태는 현재보다 약간 더 타이트한 방향이 적절합니다. 지나치게 둥근 consumer-fintech 인상은 피합니다.

- 일반 카드와 버튼은 `10px` 전후 라운드
- 상태 칩은 pill 가능
- 데이터 표와 콘솔은 박스 구조를 명확히 유지
- 입력창은 친절해 보이는 것보다 정확해 보이는 쪽이 우선

## Components
- **KPI Card:** 값 + 상태 + 변화 방향 + 기준선 중 최소 2개 이상을 담습니다.
- **Decision Card:** thesis, trigger, invalidation, stop, target, confidence를 요약하는 핵심 모듈입니다.
- **Risk Banner:** 규율 위반, 손실 한도 초과 위험, 미승인 전략, 데이터 결손을 즉시 드러냅니다.
- **Scenario Panel:** bull/base/bear 혹은 scenario A/B/C별 행동을 명확히 분기합니다.
- **Command Surface:** 일반 챗 UI보다 operator console처럼 보여야 합니다. 명령, 결과, 상태, 로그 구분이 명확해야 합니다.
- **Dense Table:** watchlist, pending review, execution criteria, event calendar를 빠르게 스캔할 수 있어야 합니다.

## Do's and Don'ts
- **Do:** 리스크, invalidation, do nothing 상태를 수익 기대보다 먼저 배치하세요.
- **Do:** 정보의 중요도에 따라 시각적 무게를 분명히 차등하세요.
- **Do:** 현재의 밝은 배경과 블루 계열 DNA를 유지한 채 더 날카로운 운영 콘솔 톤으로 발전시키세요.
- **Do:** 차트는 아름다움보다 해석 속도를 우선하세요.
- **Don't:** generic Tailwind dashboard처럼 보이게 만들지 마세요.
- **Don't:** crypto casino 같은 neon, glow, 과포화 red/green, 블랙 배경 중심 연출을 사용하지 마세요.
- **Don't:** 차트를 과대 확대해 계획과 리스크 레이어를 주변화하지 마세요.
- **Don't:** 모든 카드를 같은 시각적 무게로 다루지 마세요.
