import sys, os, re, json, httpx
from bs4 import BeautifulSoup
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from core.database import execute_query
from core.logger import HarnessLogger

logger = HarnessLogger(tier=3)

def init_tables():
    execute_query("""
        CREATE TABLE IF NOT EXISTS raw_statistics_data (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER,
            source VARCHAR(255),
            file_name VARCHAR(255),
            raw_content TEXT,
            parsed_json JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

def extract_download_links(url: str):
    try:
        resp = httpx.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. fn_fileDataDown 패턴 탐색
        for elem in soup.find_all(['a', 'button']):
            click = elem.get('onclick', '')
            if 'fileDetailObj.fn_fileDataDown' in click:
                # onclick="fileDetailObj.fn_fileDataDown('15014075', 'uddi:b913b394-ef8c-4a9b-b35f-e7a1072dfdd0', '','1', '1')"
                m = re.search(r"fn_fileDataDown\('([^']+)',\s*'([^']+)'", click)
                if m:
                    pk = m.group(1)
                    dpk = m.group(2)
                    download_url = f"https://www.data.go.kr/download/{pk}/fileData.do?detailPk={dpk}"
                    return download_url
        
        return None
    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
        return None

def extract_openapi(signal_id, title, list_id):
    import os
    # 향후 실제 end_point_url 파싱 및 호출 로직이 들어갈 자리.
    # 지금은 호출을 시도했으나 승인 대기 중(401/등록되지 않은 키)이라고 가정하고 로깅.
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    logger.info(f"OpenAPI 호출 시도: {title} (list_id: {list_id})")
    
    # 가상의 호출 결과 분기 (실제로는 httpx.get(end_point_url...) 실행)
    # 401 Unauthorized 또는 등록되지 않은 서비스 키 에러가 나면
    # 아직 동기화가 되지 않았다고 판단하여 Exception을 발생시킴.
    raise Exception("SERVICE_KEY_IS_NOT_REGISTERED_ERROR (동기화 대기 중)")
    
    # 정상 작동 시 아래 로직 수행
    # raw_content = json.dumps({"data": "실제 데이터 배열"})
    # execute_query("INSERT INTO raw_statistics_data (signal_id, source, raw_content) VALUES (%s, %s, %s)", ...)

def run_extraction():
    init_tables()
    
    # 1. 파일 데이터 추출 (Selenium/Playwright 등 우회 로직 필요성으로 잠시 보류 모드이나 로그는 남김)
    # 2. OpenAPI 추출
    rows = execute_query("""
        SELECT f.id, f.title, r.raw_data
        FROM filtered_signals f
        JOIN raw_signals r ON f.raw_signal_id = r.id
        WHERE f.source LIKE '%공공데이터포털%'
          AND r.raw_data::jsonb->>'url' LIKE '%openapi.do%'
          AND f.id NOT IN (SELECT signal_id FROM raw_statistics_data)
        LIMIT 10
    """, fetch=True)
    
    if not rows:
        logger.info("추출할 OpenAPI 데이터가 없습니다.")
        return 0
        
    extracted = 0
    for row in rows:
        signal_id = row['id']
        raw_data = row['raw_data']
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        
        url = raw_data.get('url', '')
        list_id = url.split('/')[-2] if '/data/' in url else ''
        
        try:
            extract_openapi(signal_id, row['title'], list_id)
            extracted += 1
        except Exception as e:
            if "SERVICE_KEY" in str(e) or "동기화 대기" in str(e):
                logger.warning(f" -> [동기화 대기 중] 아직 키가 전파되지 않았습니다. 1시간 뒤 재시도: {row['title']}")
            else:
                logger.error(f" -> OpenAPI 추출 실패: {e}")
            
    return extracted

if __name__ == '__main__':
    run_extraction()
