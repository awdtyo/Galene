"""Stdlib logging setup. Request ID + timestamp on every request (see main.py)."""

import logging
import sys

_configured = False


def setup_logging(level: str = "INFO") -> logging.Logger:
    global _configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s",
            defaults={"request_id": "-"},
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _configured = True
    return logging.getLogger("orca")
