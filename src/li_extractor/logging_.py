# src/li_extractor/logging_.py
"""Structured JSON logging with event codes and trace correlation."""

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""
    
    def __init__(self, trace_id: str):
        super().__init__()
        self.trace_id = trace_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "trace_id": self.trace_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        
        # Add event code if present
        if hasattr(record, 'event_code'):
            log_entry["event_code"] = record.event_code
        
        # Add metrics if present
        if hasattr(record, 'metrics'):
            log_entry["metrics"] = record.metrics
        
        # Add context if present
        if hasattr(record, 'context'):
            log_entry["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogger:
    """Structured logger with event codes and metrics."""
    
    def __init__(self, name: str, log_file: Path, level: str = "INFO"):
        self.trace_id = str(uuid.uuid4())
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler for JSON logs
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(JSONFormatter(self.trace_id))
        self.logger.addHandler(file_handler)
        
        # Console handler for human-readable logs
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.logger.addHandler(console_handler)
        
        self.logger.propagate = False
    
    def _log_with_extras(
        self,
        level: str,
        message: str,
        event_code: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log with structured extras."""
        extra = {}
        if event_code:
            extra['event_code'] = event_code
        if metrics:
            extra['metrics'] = metrics
        if context:
            extra['context'] = context
        
        getattr(self.logger, level.lower())(message, extra=extra, **kwargs)
    
    def info(
        self,
        message: str,
        event_code: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log info message."""
        self._log_with_extras("INFO", message, event_code, metrics, context)
    
    def warning(
        self,
        message: str,
        event_code: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log warning message."""
        self._log_with_extras("WARNING", message, event_code, metrics, context)
    
    def error(
        self,
        message: str,
        event_code: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """Log error message."""
        self._log_with_extras("ERROR", message, event_code, metrics, context, exc_info=exc_info)
    
    def debug(
        self,
        message: str,
        event_code: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log debug message."""
        self._log_with_extras("DEBUG", message, event_code, metrics, context)


# Event codes constants
class EventCodes:
    """LinkedIn extractor event codes."""
    
    # Session management (LI001-LI004)
    SESSION_REUSED = "LI001"
    LOGIN_REQUIRED = "LI002"
    STORAGE_SAVED = "LI003"
    STORAGE_INVALID = "LI004"
    
    # Navigation & Loading (LI101-LI106)
    POSTS_TAB_OPENED = "LI101"
    LOAD_TIMEOUT = "LI102"
    MIN_POSTS_MET = "LI103"
    SCROLLED_BATCH = "LI104"
    DOM_IDLE = "LI105"
    NAVIGATION_ERROR = "LI106"
    
    # Extraction (LI201-LI205)
    POST_FOUND = "LI201"
    SCHEMA_VALIDATION_ERROR = "LI202"
    PARSE_WARNING = "LI203"
    FIELD_MISSING = "LI204"
    COUNTS_PARSED = "LI205"
    
    # Output (LI301-LI303)
    WRITE_STARTED = "LI301"
    WRITE_OK = "LI302"
    WRITE_FAILED = "LI303"
    
    # Errors (LI900+)
    UNCAUGHT_EXCEPTION = "LI900"