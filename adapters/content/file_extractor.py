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

def run_extraction():
    init_tables()
    # fileData가 URL에 포함된 데이터만 10개 조회
    rows = execute_query("""
        SELECT f.id, f.title, r.raw_data
        FROM filtered_signals f
        JOIN raw_signals r ON f.raw_signal_id = r.id
        WHERE f.source LIKE '%공공데이터포털%'
          AND r.raw_data::jsonb->>'url' LIKE '%fileData.do%'
          AND f.id NOT IN (SELECT signal_id FROM raw_statistics_data)
        LIMIT 10
    """, fetch=True)
    
    if not rows:
        logger.info("추출할 파일 데이터가 없습니다.")
        return 0
        
    extracted = 0
    for row in rows:
        signal_id = row['id']
        raw_data = row['raw_data']
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        
        url = raw_data.get('url', '')
        logger.info(f"Scraping file for: {row['title']} ({url})")
        download_url = extract_download_links(url)
        
        if download_url:
            logger.info(f" -> Found download URL: {download_url}")
            try:
                dl_resp = httpx.get(download_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
                if dl_resp.status_code == 200:
                    content_disp = dl_resp.headers.get('content-disposition', '')
                    file_name = 'unknown.csv'
                    if 'filename=' in content_disp:
                        file_name = content_disp.split('filename=')[-1].strip('\"\'')
                        
                    raw_content = dl_resp.content.decode('utf-8', errors='replace')[:10000] # 앞부분 10000자만 저장 (데모용)
                    
                    execute_query("""
                        INSERT INTO raw_statistics_data (signal_id, source, file_name, raw_content)
                        VALUES (%s, %s, %s, %s)
                    """, (signal_id, '공공데이터포털', file_name, raw_content))
                    extracted += 1
                    logger.info(f" -> Successfully saved: {file_name}")
            except Exception as e:
                logger.warning(f" -> Failed to download: {e}")
        else:
            logger.warning(" -> Could not find download link.")
            
    return extracted

if __name__ == '__main__':
    run_extraction()
