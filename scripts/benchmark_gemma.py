import ollama
import json
import time
import sys

# 벤치마크용 프롬프트 (기존 filter.py와 동일)
PROMPT = """너는 기술/경제 전문 분석가이다. 다음 기술 기사의 본문을 읽고, ARK Invest 스타일의 보고서 작성을 위해 필요한 핵심 수치 데이터를 추출하라.

필수 추출 항목:
1. 비용(Cost): 특정 기술이나 부품의 가격 하락치, 현재 가격 등
2. 성장률/성능(Growth/Performance): CAGR, 효율 개선 %, 벤치마크 점수 등
3. 시장규모(TAM): 조 달러($T) 또는 십억 달러($B) 단위의 시장 전망치
4. 주요 기업(Players): 언급된 핵심 기업명

출력 형식 (반드시 JSON 형식으로만 응답):
{
  "costs": [{"item": "이름", "value": "수치", "trend": "하락/상승"}],
  "performance": [{"metric": "항목", "value": "수치"}],
  "market_size": [{"segment": "분야", "value": "수치", "year": "2030"}],
  "key_players": ["기업1", "기업2"]
}

기사 본문:
"""

def test_model(model_name, text):
    print(f"\n--- Testing Model: {model_name} ---")
    start_time = time.time()
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": PROMPT + text}],
            options={"temperature": 0.1, "format": "json"}
        )
        elapsed = time.time() - start_time
        content = response['message']['content']
        # 마크다운 태그 제거
        content = content.replace("```json", "").replace("```", "").strip()
        print(f"Latency: {elapsed:.2f}s")
        print("Output:")
        print(content)
        # JSON 유효성 검사
        json.loads(content)
        return {"model": model_name, "latency": elapsed, "success": True, "output": content}
    except Exception as e:
        print(f"Error: {e}")
        return {"model": model_name, "success": False, "error": str(e)}

if __name__ == "__main__":
    sample_text = sys.stdin.read()
    results = []
    results.append(test_model("gemma4:latest", sample_text))
    results.append(test_model("gemma2:27b", sample_text))
    
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
