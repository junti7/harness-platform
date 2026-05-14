"""
T-12: Multi-LLM Orchestrator

Claude API (primary) + Gemini CLI (independent critique) + GPT (arbitration).
All Claude costs tracked in api_cost_log with provider column.
Gemini/GPT tracked as 0-token entries (external billing).
"""
import os
import subprocess
from typing import Optional

import anthropic

from core.database import execute_query
from core.logger import HarnessLogger

_GEMINI_CLI = "/opt/homebrew/bin/gemini"
_SUBPROCESS_ENV = {
    **os.environ,
    "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}",
}


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
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        _log_cost("anthropic", model, resp.usage.input_tokens, resp.usage.output_tokens)

        from core.cost_alerts import check_and_alert
        from adapters.content.refiner import get_today_cost, DAILY_COST_LIMIT
        check_and_alert(get_today_cost(self.logger), DAILY_COST_LIMIT, self.logger)

        return {
            "output": resp.content[0].text if resp.content else "",
            "model": model,
            "provider": "anthropic",
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }

    def gemini_critique(
        self,
        prompt: str,
        primary_output: str = "",
        timeout: int = 120,
    ) -> dict:
        """Gemini CLI independent review. Falls back gracefully if CLI absent."""
        full_prompt = prompt
        if primary_output:
            full_prompt += f"\n\n[1차 분석 참고 (비판적으로 검토하세요)]\n{primary_output[:2000]}"

        try:
            result = subprocess.run(
                [_GEMINI_CLI, "-p", full_prompt],
                capture_output=True, text=True,
                timeout=timeout, env=_SUBPROCESS_ENV,
            )
            if result.returncode != 0 and self.logger:
                self.logger.warning(f"Gemini CLI returncode={result.returncode}: {result.stderr[:200]}")
            _log_cost("google", "gemini", 0, 0)
            return {
                "output": result.stdout.strip(),
                "model": "gemini",
                "provider": "google",
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            if self.logger:
                self.logger.warning("Gemini CLI 없음 — claude fallback으로 대체")
            return self._claude_fallback_critique(prompt, primary_output)
        except subprocess.TimeoutExpired:
            if self.logger:
                self.logger.warning(f"Gemini CLI timeout ({timeout}s)")
            return {"output": "", "model": "gemini-timeout", "provider": "google", "error": "timeout"}

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
        """GPT reasoning 중재 — API 키 미설정 시 경고 반환."""
        if self.logger:
            self.logger.warning("GPT 중재 미설정 (OPENAI_API_KEY) — 수동 검토 필요")
        return {
            "output": "GPT_ARBITRATION_NOT_CONFIGURED",
            "provider": "openai",
            "note": "Split decision requires manual review",
        }
