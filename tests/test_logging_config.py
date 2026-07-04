"""Tests for buddy.logging_config.setup_logging()."""

from __future__ import annotations

import logging
import logging.handlers
import os

import pytest

from buddy.config import LOG_PATH
from buddy.logging_config import setup_logging


@pytest.fixture(autouse=True)
def clean_buddy_logger():
    """Remove all handlers from 'buddy' logger before and after each test."""
    logger = logging.getLogger("buddy")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    yield
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


def test_log_path_is_namespaced_by_pid():
    """LOG_PATH carries this process's PID so concurrent instances don't share a file."""
    assert LOG_PATH == f"/tmp/buddy-{os.getpid()}.log"


def test_debug_mode_attaches_rotating_handler_at_debug_level():
    """debug=True: logger is set to DEBUG and has exactly one RotatingFileHandler."""
    setup_logging(debug=True)
    logger = logging.getLogger("buddy")
    assert logger.level == logging.DEBUG
    rfh = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rfh) == 1


def test_warning_mode_sets_warning_level():
    """debug=False: logger level is WARNING."""
    setup_logging(debug=False)
    logger = logging.getLogger("buddy")
    assert logger.level == logging.WARNING


def test_idempotent_second_call_does_not_add_duplicate_handler():
    """Calling setup_logging twice must not attach a second RotatingFileHandler."""
    setup_logging(debug=True)
    setup_logging(debug=True)
    logger = logging.getLogger("buddy")
    rfh = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rfh) == 1


def test_reenabling_debug_raises_existing_handler_to_debug():
    """setup_logging(False) then (True) must raise the existing handler to DEBUG,
    not leave it filtering at WARNING — otherwise --debug drops debug records."""
    setup_logging(debug=False)
    setup_logging(debug=True)
    logger = logging.getLogger("buddy")
    rfh = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rfh) == 1
    assert rfh[0].level == logging.DEBUG
    assert logger.level == logging.DEBUG
