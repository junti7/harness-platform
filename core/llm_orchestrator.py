"""
T-12: Multi-LLM Orchestrator

Claude API (primary) + Gemini API (independent critique) + GPT (arbitration).
All costs tracked in api_cost_log with provider column.
"""
import os
from typing import Optional

import anthropic

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.refiner import _price_for_model


def _log_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
    execute_query(
        """INSERT INTO api_cost_log (provider, model, input_tokens, output_tokens)
           VALUES (%s, %s, %s, %s)""",
        (provider, model, input_tokens, output_tokens),
    )


class LLMOrchestrator:
    def __init__(self, logger: Optional[HarnessLogger] = None):
        self.logger = logger
        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def claude_primary(
        self,
        system: str,
        user: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ) -> dict:
        """Claude API primary analysis. Logs cost + fires threshold alerts."""
        from core.cost_alerts import check_and_alert
        from adapters.content.refiner import get_today_cost, DAILY_COST_LIMIT
        today = get_today_cost(self.logger)
        if today >= DAILY_COST_LIMIT:
            raise RuntimeError(
                f"[LLMOrchestrator] 일일 비용 한도 도달 (${today:.4f} / ${DAILY_COST_LIMIT}) — Claude API 호출 차단"
            )
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        _log_cost("anthropic", model, resp.usage.input_tokens, resp.usage.output_tokens)

        check_and_alert(get_today_cost(self.logger), DAILY_COST_LIMIT, self.logger)

        return {
            "output": resp.content[0].text if resp.content else "",
            "model": model,
            "provider": "anthropic",
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }

    def estimate_claude_cost(self, text_length: int, model: str = "claude-sonnet-4-6") -> float:
        """단순 토큰 추정치로 예상 비용 계산 (실제 호출 없음)."""
        # 아주 대략적인 추정: 1 char ~= 2 tokens
        # 실제로는 토크나이저를 써야 정확함
        input_tokens = text_length * 2 
        output_tokens = 2048 # 일반적인 최대 출력값으로 가정
        
        input_price, output_price = _price_for_model(model)
        return (input_tokens / 1000 * input_price +
                output_tokens / 1000 * output_price)

    def gemini_critique(
        self,
        prompt: str,
        primary_output: str = "",
        timeout: int = 120,
    ) -> dict:
        """Gemini API를 사용한 독립적 Critique 검토. API 키 미설정 시 Claude Fallback."""
        import google.generativeai as genai
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            if self.logger:
                self.logger.warning("GOOGLE_API_KEY 없음 — claude fallback으로 대체")
            return self._claude_fallback_critique(prompt, primary_output)

        full_prompt = prompt
        if primary_output:
            full_prompt += f"\n\n[1차 분석 참고 (비판적으로 검토하세요)]\n{primary_output[:2000]}"

        try:
            genai.configure(api_key=google_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            model = genai.GenerativeModel(model_name)
            
            # API 호출
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048,
                )
            )
            
            # 토큰 메트릭 추출
            input_tokens = 0
            output_tokens = 0
            try:
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens = response.usage_metadata.prompt_token_count
                    output_tokens = response.usage_metadata.candidates_token_count
            except Exception:
                pass

            _log_cost("google", model_name, input_tokens, output_tokens)
            
            return {
                "output": response.text.strip(),
                "model": model_name,
                "provider": "google",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Gemini API 에러: {str(e)} — claude fallback으로 대체")
            return self._claude_fallback_critique(prompt, primary_output)

    def _claude_fallback_critique(self, prompt: str, primary_output: str) -> dict:
        """Gemini 불가 시 동일 모델 재호출로 fallback. 로그에 명시."""
        if self.logger:
            self.logger.warning("⚠️ Gemini 불가 — Claude 동일 모델 fallback (cross-LLM 미충족, 수동 검토 권장)")
        system = "당신은 비판적 검토자입니다. 다른 AI의 분석을 독립적으로 검토하고 약점, 과장, 누락을 지적하세요."
        user = prompt
        if primary_output:
            user += f"\n\n검토 대상:\n{primary_output[:2000]}"
        result = self.claude_primary(system=system, user=user, model="claude-haiku-4-5", max_tokens=2048)
        result["provider"] = "anthropic_fallback"
        return result

    def gpt_arbitrate(self, prompt: str, primary: str, critique: str) -> dict:
        """GPT-4o를 사용한 상위 중재 — API 키 미설정 시 Fallback."""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            if self.logger:
                self.logger.warning("GPT 중재 미설정 (OPENAI_API_KEY) — 수동 검토 필요")
            return {
                "output": "GPT_ARBITRATION_NOT_CONFIGURED",
                "provider": "openai",
                "note": "Split decision requires manual review",
            }
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            model_name = "gpt-4o-mini"
            
            system_prompt = "당신은 고도로 지능적인 수석 중재자입니다. 1차 분석과 2차 비판 분석을 검토하여 최선의 중재 결론을 내리세요."
            user_prompt = f"질문/프롬프트:\n{prompt}\n\n1차 분석:\n{primary}\n\n2차 비판:\n{critique}\n\n두 의견을 종합적으로 판단하여 최선의 결론 및 실행 계획을 수립하세요."
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2048,
            )
            
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            _log_cost("openai", model_name, input_tokens, output_tokens)
            
            return {
                "output": response.choices[0].message.content.strip(),
                "model": model_name,
                "provider": "openai",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"GPT 중재 API 에러: {str(e)} — 수동 검토 필요")
            return {
                "output": f"GPT_ARBITRATION_ERROR: {str(e)}",
                "provider": "openai",
                "note": "API error. Split decision requires manual review",
            }

