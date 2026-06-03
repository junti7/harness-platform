import sys, os, json, requests
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from core.database import execute_query
from core.logger import HarnessLogger

logger = HarnessLogger(tier=3)

# Slack Webhook URL이 환경변수에 세팅되어 있다고 가정합니다 (또는 터미널 로그로 출력)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

def notify_open_api_needs():
    logger.info("Checking for OpenAPI datasets that require authorization...")
    
    # 1. openapi.do 가 URL에 있고, 우리가 관심있는 카테고리이며, 아직 알림을 보내지 않은(또는 승인되지 않은) 목록 조회
    rows = execute_query("""
        SELECT f.id, f.title, f.category, r.raw_data
        FROM filtered_signals f
        JOIN raw_signals r ON f.raw_signal_id = r.id
        WHERE f.source LIKE '%공공데이터포털%'
          AND r.raw_data::jsonb->>'url' LIKE '%openapi.do%'
          AND f.category IN ('RealEstate', 'AI', 'Robotics', 'Education')
        LIMIT 5
    """, fetch=True)
    
    if not rows:
        logger.info("새로 활용신청이 필요한 API 데이터가 없습니다.")
        return
        
    messages = ["🚨 *[활용신청 필요]* 다음 공공데이터 OpenAPI들은 수동 승인이 필요합니다:"]
    for row in rows:
        title = row['title']
        category = row['category']
        raw_data = row['raw_data']
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        url = raw_data.get('url', '')
        
        # Slack 링크 포맷: <url|text>
        messages.append(f"• [{category}] <{url}|{title}> -> 접속 후 '활용신청' 버튼 클릭!")
        
    final_message = "\n".join(messages)
    
    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, json={"text": final_message})
        logger.info("슬랙으로 알림 발송 완료.")
    else:
        logger.warning("Slack Webhook URL이 없어 터미널에만 출력합니다:")
        print("="*60)
        print(final_message)
        print("="*60)

if __name__ == '__main__':
    notify_open_api_needs()
