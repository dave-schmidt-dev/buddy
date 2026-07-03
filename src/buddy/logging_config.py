"""Logging setup for buddy.

Call ``setup_logging(debug)`` once at startup.  Subsequent calls are
idempotent — duplicate handlers are not added.
"""

from __future__ import annotations

import logging
import logging.handlers

from buddy.config import LOG_PATH

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_LOGGER_NAME = "buddy"


def setup_logging(debug: bool) -> None:
    """Configure a rotating file handler on the ``buddy`` logger.

    Args:
        debug: When *True* set the logger to DEBUG; otherwise WARNING.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    level = logging.DEBUG if debug else logging.WARNING
    logger.setLevel(level)

    # Idempotency: if a RotatingFileHandler for our log path is already attached,
    # keep its level in sync with this call and return (don't add a duplicate).
    # Syncing matters so a later setup_logging(debug=True) actually enables DEBUG
    # output instead of leaving the handler filtering at the earlier level.
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            if getattr(handler, "baseFilename", None) == LOG_PATH:
                handler.setLevel(level)
                return

    handler = logging.handlers.RotatingFileHandler(
        LOG_PATH,
        maxBytes=1_048_576,
        backupCount=2,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    logger.addHandler(handler)
    # Do not propagate to the root logger to avoid spamming unrelated handlers.
    logger.propagate = False
