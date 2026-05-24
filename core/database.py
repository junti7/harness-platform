import os
from dotenv import load_dotenv

load_dotenv()

# .venv 가상환경 및 로컬 격리 개발을 위해 SQLite fallback 지원
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///Users/juntae.park/projects/harness-platform/core/harness.db")

def get_connection():
    """
    DATABASE_URL 기반으로 PostgreSQL 또는 SQLite 커넥션을 생성하여 반환.
    무한 대기(Hang) 방지를 위해 강제 5초 타임아웃 옵션을 주입합니다.
    """
    if _DATABASE_URL.startswith("postgresql://") or _DATABASE_URL.startswith("postgres://"):
        import psycopg2
        # connect_timeout=5 를 DSN 파라미터로 주입하여 무한 TCP 지연 예방
        return psycopg2.connect(_DATABASE_URL, connect_timeout=5), "postgresql"
    else:
        # SQLite 연결
        db_path = _DATABASE_URL.replace("sqlite://", "")
        # 절대 경로가 아니라면 로컬 harness.db로 설정
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "harness.db"))
        
        # 상위 폴더 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        import sqlite3
        # 락 경합 시 무한 대기 방지를 위해 timeout=5.0 적용
        conn = sqlite3.connect(db_path, timeout=5.0)
        # dict 변환을 위해 row_factory 설정
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def execute_query(query: str, params=None, fetch=False):
    """
    PostgreSQL과 SQLite를 둘 다 투명하게 지원하는 공통 쿼리 실행기.
    SQLite의 경우 %s 플레이스홀더를 ?로 동적 치환하여 호환성을 확보합니다.
    """
    conn, db_type = get_connection()
    try:
        if db_type == "sqlite":
            # SQLite 호환을 위해 %s를 ?로 변환
            converted_query = query.replace("%s", "?")
            cur = conn.cursor()
            cur.execute(converted_query, params or ())
            
            if fetch:
                # Row 객체를 dict 리스트로 변환하여 psycopg2 RealDictCursor 호환성 확보
                rows = cur.fetchall()
                result = [dict(row) for row in rows]
            else:
                result = None
            
            conn.commit()
            return result
        else:
            # PostgreSQL 처리
            import psycopg2
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchall() if fetch else None
                conn.commit()
                return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
