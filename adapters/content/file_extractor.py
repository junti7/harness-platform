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


def extract_openapi(signal_id, title, list_id):
    import os
    from core.llm_orchestrator import LLMOrchestrator
    
    api_key = os.getenv("DATA_GO_KR_API_KEY", "")
    logger.info(f"OpenAPI 동적 파서 가동: {title} (list_id: {list_id})")
    
    # 1. API 메타데이터 카탈로그 조회
    catalog_url = f"https://www.data.go.kr/catalog/{list_id}/openapi.json"
    try:
        cat_resp = httpx.get(catalog_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        cat_data = cat_resp.text
    except Exception as e:
        cat_data = str(e)

    # 2. 로컬 LLM (Ollama)을 통해 엔드포인트 및 파라미터 추론 (Dynamic Parsing)
    system_prompt = "주어진 공공데이터 OpenAPI 메타데이터를 분석하여, 데이터를 가져올 수 있는 가장 유력한 REST GET Endpoint URL(단일 문자열)만 응답하세요. 모를 경우 'UNKNOWN'을 반환하세요. 공공데이터포털은 보통 https://api.odcloud.kr/api/{list_id}/v1/uddi:... 형태를 가집니다."
    user_prompt = f"Title: {title}\nList ID: {list_id}\nCatalog Info:\n{cat_data[:1500]}"
    
    endpoint = "UNKNOWN"
    try:
        ollama_payload = {
            "model": "gemma4:latest",
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.0}
        }
        ollama_resp = httpx.post("http://localhost:11434/api/generate", json=ollama_payload, timeout=30)
        if ollama_resp.status_code == 200:
            endpoint = ollama_resp.json().get("response", "").strip()
        else:
            logger.warning(f"Ollama 에러: {ollama_resp.status_code} - {ollama_resp.text}")
    except Exception as e:
        logger.warning(f"로컬 LLM 동적 파싱 실패: {e}")

    if endpoint == "UNKNOWN" or not endpoint.startswith("http"):
        # 표준 odcloud 방식 Fallback 시도
        endpoint = f"https://api.odcloud.kr/api/{list_id}/v1/data?page=1&perPage=100"
        
    logger.info(f" -> 추론된 Endpoint: {endpoint}")
    
    # 3. 실제 API 호출 타격
    headers = {"Authorization": f"Infuser {api_key}"}
    try:
        api_resp = httpx.get(endpoint, headers=headers, timeout=20)
    except Exception as e:
        raise Exception(f"API 네트워크 에러: {e}")

    # 4. 상태 코드에 따른 지연/성공 처리
    if api_resp.status_code in [401, 403]:
        raise Exception("SERVICE_KEY_IS_NOT_REGISTERED_ERROR (동기화 대기 중)")
    elif api_resp.status_code == 200:
        raw_content = api_resp.content.decode('utf-8', errors='replace')[:10000]
        execute_query("""
            INSERT INTO raw_statistics_data (signal_id, source, file_name, raw_content)
            VALUES (%s, %s, %s, %s)
        """, (signal_id, '공공데이터포털_OpenAPI', f"openapi_{list_id}.json", raw_content))
        logger.info(f" -> OpenAPI 데이터 적재 성공! (list_id: {list_id})")
    else:
        logger.warning(f" -> API 응답 에러: {api_resp.status_code} - {api_resp.text[:200]}")

def extract_file_data(signal_id, title, url):
    import os
    from playwright.sync_api import sync_playwright
    import tempfile
    
    logger.info(f"Playwright 파일 다운로드 봇 가동: {title} ({url})")
    
    with sync_playwright() as p:
        # headless=True 로 백그라운드 브라우저 실행. 봇 탐지 우회를 위한 아규먼트 추가
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 추가적인 navigator.webdriver 우회 스크립트 주입
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        
        try:
            page.goto(url, timeout=30000)
            
            # 페이지에 다운로드 버튼이 로드될 때까지 대기
            # 공공데이터포털은 주로 <a> 태그나 <button>에 fn_fileDataDown(...)를 연결함
            # 더 넓은 범위의 다운로드 버튼을 커버하도록 CSS/XPath 다중 타겟팅
            selectors = [
                ".btn-download", 
                "a[href*='fn_fileDataDown']", 
                "a:has-text('다운로드')", 
                "a:has-text('파일')", 
                "button:has-text('다운로드')"
            ]
            selector_str = ", ".join(selectors)
            
            page.wait_for_selector(selector_str, timeout=15000)
            
            # 다운로드 이벤트 대기 상태 진입
            with page.expect_download(timeout=30000) as download_info:
                # 찾은 첫 번째 다운로드 버튼 클릭
                page.locator(selector_str).first.click()
            
            download = download_info.value
            file_name = download.suggested_filename
            logger.info(f" -> 파일 가로채기 성공: {file_name}")
            
            # 임시 파일로 저장 후 읽기
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                download.save_as(tmp.name)
                
                # NUL 바이트 에러(PostgreSQL 한계) 방지 및 바이너리 텍스트 파싱
                file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
                binary_exts = ['hwp', 'zip', 'xls', 'xlsx', 'png', 'jpg', 'jpeg']
                
                raw_content = ""
                if file_ext == 'hwpx':
                    # HWPX는 zip 압축된 XML 파일 묶음이므로 파싱 시도
                    try:
                        import zipfile, xml.etree.ElementTree as ET
                        with zipfile.ZipFile(tmp.name, 'r') as zf:
                            xml_texts = []
                            for name in zf.namelist():
                                if name.startswith('Contents/section') and name.endswith('.xml'):
                                    xml_data = zf.read(name)
                                    root = ET.fromstring(xml_data)
                                    # 모든 텍스트 노드 추출 (네임스페이스 무시하고 단순 텍스트 결합)
                                    texts = "".join(root.itertext())
                                    if texts:
                                        xml_texts.append(texts.strip())
                            if xml_texts:
                                parsed = "\n".join(xml_texts)[:10000]
                                raw_content = f"[HWPX 파싱 결과 요약]\n{parsed}".replace('\x00', '')
                            else:
                                raw_content = "[HWPX 파싱 실패: 텍스트 노드를 찾을 수 없습니다]"
                    except Exception as e:
                        raw_content = f"[HWPX 파싱 실패: {e}]"
                        
                elif file_ext == 'pdf':
                    # PDF는 PyMuPDF(fitz)로 텍스트 추출
                    try:
                        import fitz
                        doc = fitz.open(tmp.name)
                        pdf_texts = []
                        for page in doc:
                            pdf_texts.append(page.get_text())
                        parsed = "\n".join(pdf_texts)[:10000]
                        raw_content = f"[PDF 파싱 결과 요약]\n{parsed}".replace('\x00', '')
                    except Exception as e:
                        raw_content = f"[PDF 파싱 실패: {e}]"
                
                elif file_ext in binary_exts:
                    raw_content = f"[지원하지 않는 바이너리 형식: {file_name}]\n데이터 크기: {os.path.getsize(tmp.name)} bytes\n(HWPX 및 PDF만 본문 파싱을 지원합니다)"
                else:
                    with open(tmp.name, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()[:10000] # 앞부분 10000자만 저장
                        # PostgreSQL NUL 바이트(\x00) 에러 완벽 차단
                        raw_content = content.replace('\x00', '')
            
            os.remove(tmp.name)
            
            execute_query("""
                INSERT INTO raw_statistics_data (signal_id, source, file_name, raw_content)
                VALUES (%s, %s, %s, %s)
            """, (signal_id, '공공데이터포털_FileData', file_name, raw_content))
            
            logger.info(f" -> DB 적재 완료! (signal_id: {signal_id})")
            return True
            
        except Exception as e:
            logger.warning(f" -> 다운로드 우회 실패: {e}")
            return False
        finally:
            browser.close()

def run_extraction():
    init_tables()
    
    # 1. 파일 데이터 추출 (Selenium/Playwright 우회 로직 가동)
    file_rows = execute_query("""
        SELECT f.id, f.title, r.raw_data
        FROM filtered_signals f
        JOIN raw_signals r ON f.raw_signal_id = r.id
        WHERE f.source LIKE '%공공데이터포털%'
          AND r.raw_data::jsonb->>'url' LIKE '%fileData.do%'
          AND f.id NOT IN (SELECT signal_id FROM raw_statistics_data)
        LIMIT 5
    """, fetch=True)
    
    if file_rows:
        logger.info(f"파일 데이터 추출 타겟 {len(file_rows)}건 발견, 봇 가동 시작.")
        for row in file_rows:
            raw_data = row['raw_data']
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            extract_file_data(row['id'], row['title'], raw_data.get('url', ''))
    
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
