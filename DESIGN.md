---
name: Harness Platform
version: "0.1.0"
description: Design system for Physical AI / AGI market intelligence platform.
colors:
  primary: "#111827"
  secondary: "#4b5563"
  accent: "#2563eb"
  background: "#ffffff"
  surface: "#f9fafb"
  border: "#e5e7eb"
  callout-bg: "#eff6ff"
  callout-border: "#2563eb"
  success: "#059669"
  warning: "#d97706"
  error: "#dc2626"
typography:
  h1:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Apple SD Gothic Neo', sans-serif"
    fontSize: "2.25rem"
    fontWeight: "700"
    lineHeight: "1.2"
  h2:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Apple SD Gothic Neo', sans-serif"
    fontSize: "1.5rem"
    fontWeight: "600"
    lineHeight: "1.3"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Apple SD Gothic Neo', sans-serif"
    fontSize: "1rem"
    fontWeight: "400"
    lineHeight: "1.55"
  mono:
    fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
    fontSize: "0.875rem"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  callout:
    backgroundColor: "{colors.callout-bg}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  body-text:
    textColor: "{colors.primary}"
    typography: "{typography.body}"
  metadata:
    textColor: "{colors.secondary}"
    typography: "{typography.mono}"
  status-success:
    textColor: "{colors.success}"
  status-warning:
    textColor: "{colors.warning}"
  status-error:
    textColor: "{colors.error}"
---

## Overview
Harness Platform의 디자인은 **"Industrial Precision meets High-Signal Intelligence"**를 지향합니다. Physical AI, 로보틱스, AGI 분야의 고난도 정보를 다루는 만큼, 신뢰감 있고 정교하며 정제된 시각적 경험을 제공해야 합니다.

복잡한 데이터를 단순하게 보여주기보다는, 데이터의 층위(Hierarchy)를 명확히 하여 독자가 핵심 신호(Signal)를 빠르게 포착할 수 있도록 돕습니다.

## Colors
팔레트는 차분한 무채색 베이스에 신뢰감을 주는 디지털 블루(`accent`)를 포인트로 사용합니다.

- **Primary (#111827):** 깊은 잉크색으로 헤드라인과 핵심 텍스트에 사용됩니다.
- **Secondary (#4b5563):** 슬레이트 그레이로 메타데이터, 보조 설명, 캡션에 사용됩니다.
- **Accent (#2563eb):** 인터랙션, 링크, 강조 사항(Callout)에 사용되는 핵심 액센트 컬러입니다.
- **Surface (#f9fafb):** 카드 배경이나 보조 영역에 사용되어 레이어 구분을 돕습니다.

## Typography
가독성이 뛰어난 산세리프 글꼴(`Inter` 권장)을 기본으로 하며, 한글 환경에서는 `Apple SD Gothic Neo`를 우선 적용합니다. 기술적 데이터나 코드 스니펫에는 일관된 고정폭 글꼴(`mono`)을 사용합니다.

- **Headings:** 굵고(Bold/Semi-bold) 자간을 약간 좁혀 단단한 느낌을 줍니다.
- **Body:** 충분한 행간(1.55)을 확보하여 장문의 분석 리포트도 편안하게 읽힐 수 있도록 합니다.

## Layout & Spacing
8px 그리드 시스템을 기반으로 하며, 정보 밀도가 높은 리포트 특성상 여백을 전략적으로 사용하여 시각적 피로도를 낮춥니다.

## Components
- **Card:** 정보의 단위를 구분하는 기본 컨테이너입니다. 부드러운 라운딩(`rounded.md`)과 미세한 테두리를 가집니다.
- **Callout:** 주의 깊게 읽어야 할 핵심 통찰(Insight)이나 요약을 담습니다. 좌측 액센트 보더를 통해 시선을 유도합니다.

## Do's and Don'ts
- **Do:** 핵심 신호(Signal)와 소음(Noise)을 시각적으로 명확히 분리하세요.
- **Do:** 계층 구조를 위해 일관된 타이포그래피 토큰을 사용하세요.
- **Don't:** 너무 많은 원색을 사용하여 시선을 분산시키지 마세요.
- **Don't:** 행간을 너무 좁게 설정하여 가독성을 해치지 마세요.
