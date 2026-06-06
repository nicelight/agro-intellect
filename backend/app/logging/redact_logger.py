from __future__ import annotations

from backend.app.privacy import redact_text


class RedactLogger:
    def __init__(self, name: str = "agro") -> None:
        self._name = name

    def info(self, message: str) -> None:
        safe = redact_text(message, high_risk=True)
        print(f"[{self._name}] INFO: {safe.value}")

    def error(self, message: str) -> None:
        safe = redact_text(message, high_risk=True)
        print(f"[{self._name}] ERROR: {safe.value}")


_loggers: dict[str, RedactLogger] = {}


def get_logger(name: str = "agro") -> RedactLogger:
    if name not in _loggers:
        _loggers[name] = RedactLogger(name)
    return _loggers[name]
