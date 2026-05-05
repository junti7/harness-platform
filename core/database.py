import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    DB 연결 반환.
    🤔 왜 함수로? 매번 새 연결을 만들어 
    연결 누수(leak)를 방지하기 위해.
    """
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def execute_query(query: str, params=None, fetch=False):
    """
    쿼리 실행 공통 함수.
    🤔 왜 공통 함수? 
    - 모든 DB 호출이 동일한 에러 처리를 거치게 함
    - PLATFORM.md의 "일관된 관측성" 원칙
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
                return result
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        # 🤔 왜 finally? 에러가 나도 반드시 연결 닫기
        conn.close()
