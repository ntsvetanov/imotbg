"""Tests for logger_setup module."""

import logging
import pytest
from unittest.mock import patch

import src.logger_setup as logger_module
from src.logger_setup import get_logger


class TestGetLogger:
    """Tests for get_logger function."""

    def setup_method(self):
        """Reset logger state before each test."""
        # Reset the initialization flag
        logger_module._logger_initialized = False
        # Clear any handlers on root logger added by previous tests
        root_logger = logging.getLogger()
        root_logger.handlers = []

    def test_returns_logger_instance(self):
        """get_logger returns a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_returns_logger_with_correct_name(self):
        """get_logger returns logger with the specified name."""
        logger = get_logger("my_module")
        assert logger.name == "my_module"

    def test_different_names_return_different_loggers(self):
        """get_logger returns different loggers for different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"

    def test_same_name_returns_same_logger(self):
        """get_logger returns the same logger for the same name."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2

    def test_initializes_only_once(self):
        """Logger initialization happens only on first call."""
        assert logger_module._logger_initialized is False

        get_logger("first")
        assert logger_module._logger_initialized is True

        # Second call should not re-initialize
        with patch.object(logging, "StreamHandler") as mock_handler:
            get_logger("second")
            mock_handler.assert_not_called()

    def test_sets_log_level_to_info(self):
        """Logger is configured with INFO level."""
        logger = get_logger("test_level")
        assert logger.level == logging.INFO

    def test_root_logger_has_handler(self):
        """Root logger gets a StreamHandler added."""
        get_logger("test_handler")
        root_logger = logging.getLogger()

        # Should have at least one handler
        assert len(root_logger.handlers) >= 1

        # At least one should be StreamHandler
        stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_root_logger_level_set_to_info(self):
        """Root logger level is set to INFO."""
        get_logger("test_root_level")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_handler_has_formatter(self):
        """StreamHandler has a formatter configured."""
        get_logger("test_formatter")
        root_logger = logging.getLogger()

        stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

        handler = stream_handlers[0]
        assert handler.formatter is not None

    def test_formatter_includes_expected_fields(self):
        """Formatter includes timestamp, name, level, and message."""
        get_logger("test_format")
        root_logger = logging.getLogger()

        stream_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]

        # Find the handler we added (with asctime in format)
        our_handler = None
        for handler in stream_handlers:
            if handler.formatter and "%(asctime)s" in handler.formatter._fmt:
                our_handler = handler
                break

        assert our_handler is not None, "Expected to find handler with asctime format"
        format_str = our_handler.formatter._fmt
        assert "%(asctime)s" in format_str
        assert "%(name)s" in format_str
        assert "%(levelname)s" in format_str
        assert "%(message)s" in format_str


class TestLoggerIntegration:
    """Integration tests for logger functionality."""

    def setup_method(self):
        """Reset logger state before each test."""
        logger_module._logger_initialized = False
        root_logger = logging.getLogger()
        root_logger.handlers = []

    def test_logger_can_log_info(self, caplog):
        """Logger can log INFO level messages."""
        with caplog.at_level(logging.INFO):
            logger = get_logger("integration_test")
            logger.info("Test message")

        assert "Test message" in caplog.text

    def test_logger_can_log_warning(self, caplog):
        """Logger can log WARNING level messages."""
        with caplog.at_level(logging.WARNING):
            logger = get_logger("integration_warning")
            logger.warning("Warning message")

        assert "Warning message" in caplog.text

    def test_logger_can_log_error(self, caplog):
        """Logger can log ERROR level messages."""
        with caplog.at_level(logging.ERROR):
            logger = get_logger("integration_error")
            logger.error("Error message")

        assert "Error message" in caplog.text
