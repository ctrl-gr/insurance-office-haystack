from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from backend.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", record.name),
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "audit_fields", {})
        payload.update({key: value for key, value in fields.items() if value is not None})
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _log_directory() -> Path:
    directory = get_settings().mcp_log_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@lru_cache(maxsize=None)
def get_audit_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(f"insurance.mcp.audit.{service}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    settings = get_settings()
    handler = RotatingFileHandler(
        _log_directory() / f"mcp-{service}.log",
        maxBytes=settings.mcp_log_max_bytes,
        backupCount=settings.mcp_log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def audit(logger: logging.Logger, service: str, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    logger.log(level, event, extra={"service": service, "event": event, "audit_fields": fields})
