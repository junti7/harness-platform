# EDU seeker-target 흐름 명세

> 작성일: 2026-06-13

---

## 1. 목적

`seeker / target_person / goal` 모델이 개념에 그치지 않고, 실제 화면과 케이스 흐름에서 어떻게 쓰이는지 정의한다.

---

## 2. 기본 흐름

1. seeker 정보 수집
2. target 종류 선택
3. target 수 1명/복수 여부 선택
4. 현재 가장 시급한 target 선택
5. 케이스 생성

---

## 3. 복수 target 처리

예:
- 중2 자녀
- 고1 자녀

원칙:
- seeker는 1명
- target은 여러 명 가능
- 같은 seeker가 target별로 별도 case를 열 수 있음
- 필요 시 상위 family overview를 둘 수 있음

초기 PoC에서는:
- 기본은 target 1명 기준
- 복수 target은 `추가 예정`이 아니라 별도 흐름 문서로 미리 정의

---

## 4. operator 관점

operator 화면에서 최소 보여야 하는 것:

- seeker
- target
- target 수
- 현재 active target
- selected_llm
- current device
- desktop target os
