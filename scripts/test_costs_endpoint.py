import requests
import os
from dotenv import load_dotenv

load_dotenv()

secret_key = os.getenv("HARNESS_OS_SECRET_KEY")
print("Using secret:", secret_key)

url = "http://127.0.0.1:8001/api/costs/summary"
headers = {"X-Harness-Secret": secret_key}

try:
    print(f"Requesting GET {url}...")
    res = requests.get(url, headers=headers)
    print("Status Code:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("\n--- Costs Summary Payload (Success) ---")
        print(f"Initial Budget: ${data['initial_budget_usd']}")
        print(f"Total Spent: ${data['total_spent_usd']}")
        print(f"Remaining Budget: ${data['remaining_budget_usd']}")
        print(f"Burn Rate: {data['burn_rate_percent']}%")
        print("\nLLM Subscriptions Status:")
        for sub in data['llm_subscriptions']:
            print(f"- {sub['name']} ({sub['provider']}): Status={sub['status']}, Configured={sub['key_configured']}, Cost Spent=${sub['cost_spent_usd']}")
        print("\nBreakdown by Provider:")
        for item in data['breakdown_by_provider']:
            print(f"- {item['provider']}: ${item['cost_usd']} ({item['percentage']}%)")
        print("\nDaily Costs (First 3):")
        for item in data['daily_costs'][:3]:
            print(f"- {item['day']}: ${item['cost_usd']}")
    else:
        print("Error Response:", res.text)
except Exception as e:
    print("Request failed:", e)
