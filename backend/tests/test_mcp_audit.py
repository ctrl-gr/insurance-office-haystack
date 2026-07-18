import json
import logging

from backend.mcp_audit import JsonFormatter


def test_audit_formatter_emits_structured_trace_fields_without_payload_values():
    record = logging.LogRecord(
        name="insurance.mcp.audit.proxy",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="route.completed",
        args=(),
        exc_info=None,
    )
    record.service = "proxy"
    record.event = "route.completed"
    record.audit_fields = {
        "request_id": "trace-123",
        "company": "blue",
        "tool": "thebluecompany_get_quote",
        "status": "success",
        "duration_ms": 12.5,
    }

    payload = json.loads(JsonFormatter().format(record))

    assert payload["service"] == "proxy"
    assert payload["event"] == "route.completed"
    assert payload["request_id"] == "trace-123"
    assert payload["company"] == "blue"
    assert payload["duration_ms"] == 12.5
    assert "arguments" not in payload
    assert "result" not in payload
