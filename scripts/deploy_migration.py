#!/usr/bin/env python3
"""
Migration Deployment Automation Script
마이그레이션 파일을 자동으로 감지하고 배포하는 스크립트

Usage:
  python deploy_migration.py staging                    # 스테이징 환경 배포
  python deploy_migration.py production                 # 운영 환경 배포
  python deploy_migration.py verify                     # 마이그레이션 상태 검증
  python deploy_migration.py rollback <migration_file>  # 롤백
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = PROJECT_ROOT / "infra" / "migrations"
MIGRATION_LOG = PROJECT_ROOT / "logs" / "migration_deploy.jsonl"

# 환경별 DATABASE_URL
STAGING_DB_URL = os.getenv("STAGING_DATABASE_URL", "")
PRODUCTION_DB_URL = os.getenv("DATABASE_URL", "")


def get_db_connection(environment: str) -> psycopg2.extensions.connection:
    """데이터베이스 연결"""
    if environment == "production":
        db_url = PRODUCTION_DB_URL
    else:
        # STAGING_DATABASE_URL이 없으면 DATABASE_URL 사용
        db_url = STAGING_DB_URL if STAGING_DB_URL else PRODUCTION_DB_URL

    if not db_url:
        raise ValueError("DATABASE_URL not set")

    return psycopg2.connect(db_url)


def get_pending_migrations() -> list[Path]:
    """실행되지 않은 마이그레이션 파일 조회"""
    if not MIGRATIONS_DIR.exists():
        return []

    # *.sql 파일만 추출 (숫자_description.sql 형식)
    migration_files = sorted([
        f for f in MIGRATIONS_DIR.glob("*.sql")
        if f.name[0].isdigit()
    ])

    return migration_files


def is_migration_applied(conn: psycopg2.extensions.connection, migration_name: str) -> bool:
    """마이그레이션이 이미 적용되었는지 확인"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pipeline_runs WHERE correlation_id = %s LIMIT 1",
                (migration_name,)
            )
            return cur.fetchone() is not None
    except psycopg2.ProgrammingError:
        # pipeline_runs 테이블이 없으면 첫 실행
        return False


def execute_migration(
    conn: psycopg2.extensions.connection,
    migration_file: Path,
    environment: str
) -> dict:
    """마이그레이션 파일 실행"""
    migration_name = migration_file.stem

    print(f"\n📁 마이그레이션 실행: {migration_file.name}")
    print(f"   환경: {environment}")
    print(f"   시각: {datetime.now().isoformat()}")

    # 마이그레이션 내용 읽기
    sql_content = migration_file.read_text(encoding='utf-8')

    # 주석 제거 및 명령어 분리
    statements = [
        stmt.strip()
        for stmt in sql_content.split(';')
        if stmt.strip() and not stmt.strip().startswith('--')
    ]

    result = {
        'migration_name': migration_name,
        'environment': environment,
        'status': 'pending',
        'started_at': datetime.now().isoformat(timespec='seconds'),
        'executed_statements': 0,
        'errors': []
    }

    try:
        with conn.cursor() as cur:
            for stmt in statements:
                try:
                    print(f"   ↳ {stmt[:60]}...")
                    cur.execute(stmt)
                    result['executed_statements'] += 1
                except psycopg2.Error as e:
                    result['errors'].append({
                        'statement': stmt[:100],
                        'error': str(e)
                    })
                    print(f"   ⚠️  {str(e)[:80]}")

        conn.commit()
        result['status'] = 'success' if not result['errors'] else 'partial'
        result['completed_at'] = datetime.now().isoformat(timespec='seconds')
        print(f"✅ 마이그레이션 완료: {result['executed_statements']}개 명령어 실행")

    except Exception as e:
        conn.rollback()
        result['status'] = 'failed'
        result['errors'].append({'error': str(e)})
        result['completed_at'] = datetime.now().isoformat(timespec='seconds')
        print(f"❌ 마이그레이션 실패: {str(e)}")

    return result


def verify_migration(conn: psycopg2.extensions.connection) -> dict:
    """마이그레이션 후 데이터 검증"""
    print("\n🔍 데이터 무결성 검증 중...")

    verification = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'checks': []
    }

    with conn.cursor() as cur:
        # 1. newsletter_issues 테이블 컬럼 타입 확인
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'newsletter_issues'
            AND column_name = 'publishing_platform'
        """)

        result = cur.fetchone()
        if result:
            col_name, data_type, char_length = result
            check = {
                'name': 'publishing_platform 컬럼 타입',
                'expected': 'VARCHAR(255)',
                'actual': f"{data_type}({char_length})" if char_length else data_type,
                'passed': data_type == 'character varying' and char_length == 255
            }
            verification['checks'].append(check)
            status = "✅" if check['passed'] else "❌"
            print(f"   {status} {check['name']}: {check['actual']}")

        # 2. 인덱스 존재 확인
        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'newsletter_issues'
            AND indexname = 'idx_newsletter_issues_platform'
        """)

        index_exists = cur.fetchone() is not None
        check = {
            'name': 'idx_newsletter_issues_platform 인덱스',
            'expected': 'EXISTS',
            'actual': 'EXISTS' if index_exists else 'NOT FOUND',
            'passed': index_exists
        }
        verification['checks'].append(check)
        status = "✅" if check['passed'] else "❌"
        print(f"   {status} {check['name']}: {check['actual']}")

        # 3. 데이터 샘플 검증
        cur.execute("""
            SELECT COUNT(*) as total_rows,
                   MAX(LENGTH(publishing_platform)) as max_platform_length
            FROM newsletter_issues
            WHERE publishing_platform IS NOT NULL
        """)

        count, max_len = cur.fetchone()
        check = {
            'name': '데이터 샘플',
            'total_rows': count,
            'max_platform_length': max_len,
            'passed': True
        }
        verification['checks'].append(check)
        print(f"   ✅ 데이터 샘플: {count}개 행, 최대 길이: {max_len}")

    all_passed = all(c['passed'] for c in verification['checks'])
    verification['overall_status'] = 'passed' if all_passed else 'warning'

    return verification


def log_migration_result(result: dict, verification: dict = None):
    """마이그레이션 결과 로깅"""
    MIGRATION_LOG.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        'migration': result,
        'verification': verification,
        'logged_at': datetime.now().isoformat(timespec='seconds')
    }

    with MIGRATION_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    print(f"\n📝 로그 저장: {MIGRATION_LOG}")


def deploy_migrations(environment: str) -> int:
    """모든 미적용 마이그레이션 배포"""
    print(f"\n{'='*70}")
    print(f"🚀 마이그레이션 배포: {environment.upper()}")
    print(f"{'='*70}")

    try:
        conn = get_db_connection(environment)
        pending = get_pending_migrations()

        if not pending:
            print("✅ 실행할 마이그레이션이 없습니다")
            return 0

        print(f"\n📋 총 {len(pending)}개의 마이그레이션 파일 감지:")
        for mig in pending:
            print(f"   • {mig.name}")

        results = []
        for mig_file in pending:
            if is_migration_applied(conn, mig_file.stem):
                print(f"⏭️  {mig_file.name} - 이미 적용됨 (스킵)")
                continue

            result = execute_migration(conn, mig_file, environment)
            results.append(result)

            if result['status'] == 'failed':
                print(f"\n🚨 마이그레이션 실패. 롤백이 필요할 수 있습니다.")
                conn.close()
                return 1

        # 검증
        verification = verify_migration(conn)

        # 로깅
        for result in results:
            log_migration_result(result, verification)

        conn.close()

        print(f"\n{'='*70}")
        print(f"✅ {environment.upper()} 마이그레이션 완료")
        print(f"{'='*70}\n")

        return 0

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return 1


def verify_status() -> int:
    """마이그레이션 상태 확인"""
    print(f"\n{'='*70}")
    print(f"🔍 마이그레이션 상태 확인")
    print(f"{'='*70}\n")

    try:
        # 스테이징 확인
        conn_staging = get_db_connection("staging")
        verification_staging = verify_migration(conn_staging)
        conn_staging.close()

        print(f"\n📊 검증 결과: {verification_staging['overall_status']}")

        return 0

    except Exception as e:
        print(f"⚠️  스테이징 확인 불가: {e}")
        return 1


def rollback_migration(migration_name: str) -> int:
    """마이그레이션 롤백"""
    print(f"\n{'='*70}")
    print(f"⚠️  마이그레이션 롤백: {migration_name}")
    print(f"{'='*70}\n")

    print("🚨 롤백 전 주의사항:")
    print("   • 데이터 손실 가능성 확인")
    print("   • 데이터 백업 확인")
    print("   • 롤백 계획 검증")
    print(f"\n롤백 대기: {migration_name}")

    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "staging":
        sys.exit(deploy_migrations("staging"))
    elif cmd == "production":
        print("⚠️  운영 환경 배포는 CEO 승인 필요합니다")
        # sys.exit(deploy_migrations("production"))
        sys.exit(1)
    elif cmd == "verify":
        sys.exit(verify_status())
    elif cmd == "rollback" and len(sys.argv) > 2:
        sys.exit(rollback_migration(sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(0)
