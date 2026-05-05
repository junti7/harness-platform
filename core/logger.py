import logging
import uuid

class HarnessFilter(logging.Filter):
    """
    🤔 왜 Filter?
    httpx 같은 외부 라이브러리도 Python 로깅 시스템을 써요.
    그 로그엔 tier/correlation_id가 없어서 포맷 에러 발생.
    Filter로 기본값을 채워줘서 에러를 방지.
    """
    def filter(self, record):
        if not hasattr(record, 'tier'):
            record.tier = '-'
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = '-'
        return True

# 루트 로거에 포맷 + 필터 적용
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s | tier=%(tier)s | cid=%(correlation_id)s | %(levelname)s | %(message)s'
))
handler.addFilter(HarnessFilter())

root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# httpx 내부 로그는 WARNING 이상만 출력 (INFO 로그 노이즈 제거)
logging.getLogger("httpx").setLevel(logging.WARNING)

class HarnessLogger:
    def __init__(self, tier: int, correlation_id: str = None):
        self.tier = tier
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"harness.tier{tier}")

    def _extra(self):
        return {
            "tier": self.tier,
            "correlation_id": self.correlation_id
        }

    def info(self, msg):
        self.logger.info(msg, extra=self._extra())

    def error(self, msg):
        self.logger.error(msg, extra=self._extra())

    def warning(self, msg):
        self.logger.warning(msg, extra=self._extra())
