import logging
import json
import sys
from datetime import datetime
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "line_number": record.lineno
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging() -> None:
    # Setup root logger
    root_logger = logging.getLogger()
    
    # Use standard stdout stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # Clear any default handlers and attach JSON handler
    root_logger.handlers = [handler]
    
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    root_logger.setLevel(log_level)
    
    # Adjust external libraries propagation and configure their logging
    intercept_loggers = ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy.engine"]
    for logger_name in intercept_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.propagate = False
        # Prevent spamming DB queries logs on INFO in development unless explicitly required
        if logger_name == "sqlalchemy.engine":
            logger.setLevel(logging.WARNING)
        else:
            logger.setLevel(log_level)
