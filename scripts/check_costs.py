import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "postgresql://localhost/harness_dev")
print("Connecting to:", db_url)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # 5월 이후의 모든 비용 계산
    query = """
        SELECT 
            created_at::date as day,
            provider,
            model,
            input_tokens,
            output_tokens,
            CASE provider
                WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                WHEN 'google'    THEN (input_tokens::float/1000000*3.5) + (output_tokens::float/1000000*10.5)
                WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                ELSE 0
            END as cost
        FROM api_cost_log
        WHERE created_at >= '2026-05-01'
        ORDER BY created_at ASC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    total_cost = 0.0
    daily_costs = {}
    provider_costs = {}
    model_costs = {}
    
    for day, provider, model, input_tokens, output_tokens, cost in rows:
        total_cost += cost
        day_str = str(day)
        daily_costs[day_str] = daily_costs.get(day_str, 0.0) + cost
        provider_costs[provider] = provider_costs.get(provider, 0.0) + cost
        model_key = f"{provider} | {model}"
        model_costs[model_key] = model_costs.get(model_key, 0.0) + cost
        
    print(f"\n================ 5월 이후 LLM 지출 보고서 ================")
    print(f"총 소요 비용: ${total_cost:.4f}")
    
    print("\n[제공업체(Provider)별 비용]")
    for p, c in sorted(provider_costs.items(), key=lambda x: x[1], reverse=True):
        print(f"- {p}: ${c:.4f} ({c/total_cost*100:.1f}%)")
        
    print("\n[모델(Model)별 비용]")
    for m, c in sorted(model_costs.items(), key=lambda x: x[1], reverse=True):
        print(f"- {m}: ${c:.4f} ({c/total_cost*100:.1f}%)")
        
    print("\n[일별(Daily) 비용]")
    for d, c in sorted(daily_costs.items(), key=lambda x: x[0]):
        print(f"- {d}: ${c:.4f}")
        
except Exception as e:
    print("Error:", e)
