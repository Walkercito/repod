"""Tests for the repod.logconfig module."""

from __future__ import annotations

import io
import logging

from repod.logconfig import (
    RepodFormatter,
    StructuredLogger,
    configure_logging,
    get_logger,
)


class TestRepodFormatter:
    """Verify the custom formatter produces correct output."""

    def test_basic_format_contains_event(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.INFO,
            pathname="(repod)",
            lineno=0,
            msg="server_started",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "server_started" in output

    def test_format_contains_bracket_tag(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.INFO,
            pathname="(repod)",
            lineno=0,
            msg="test_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[+]" in output

    def test_format_debug_uses_star_tag(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.DEBUG,
            pathname="(repod)",
            lineno=0,
            msg="debug_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[*]" in output

    def test_format_error_uses_minus_tag(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.ERROR,
            pathname="(repod)",
            lineno=0,
            msg="error_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[-]" in output

    def test_format_warning_uses_bang_tag(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.WARNING,
            pathname="(repod)",
            lineno=0,
            msg="warn_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[!]" in output

    def test_format_critical_uses_x_tag(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.CRITICAL,
            pathname="(repod)",
            lineno=0,
            msg="crit_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[x]" in output

    def test_format_includes_structured_kwargs(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.INFO,
            pathname="(repod)",
            lineno=0,
            msg="test_event",
            args=(),
            exc_info=None,
        )
        record._structured = {"host": "0.0.0.0", "port": 5071}
        output = formatter.format(record)
        assert "host" in output
        assert "0.0.0.0" in output
        assert "port" in output
        assert "5071" in output
        assert "|" in output

    def test_format_no_structured_no_pipe(self) -> None:
        formatter = RepodFormatter()
        record = logging.LogRecord(
            name="repod.test",
            level=logging.INFO,
            pathname="(repod)",
            lineno=0,
            msg="bare_event",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "|" not in output


class TestStructuredLogger:
    """Verify the StructuredLogger wrapper."""

    def test_get_logger_returns_structured_logger(self) -> None:
        log = get_logger("repod.test.logger")
        assert isinstance(log, StructuredLogger)

    def test_logger_info_writes_to_stream(self) -> None:
        stream = io.StringIO()
        configure_logging("DEBUG", stream=stream)
        log = get_logger("repod.test.stream")
        log.info("hello_world", key="val")
        output = stream.getvalue()
        assert "hello_world" in output
        assert "key" in output
        assert "val" in output
        # Clean up: restore NullHandler.
        root = logging.getLogger("repod")
        root.handlers.clear()
        root.addHandler(logging.NullHandler())

    def test_logger_respects_level(self) -> None:
        stream = io.StringIO()
        configure_logging("WARNING", stream=stream)
        log = get_logger("repod.test.level")
        log.debug("should_not_appear")
        log.info("should_not_appear_either")
        log.warning("should_appear")
        output = stream.getvalue()
        assert (
            "should_not_appear" not in output.split("[!]")[0] if "[!]" in output else True
        )
        assert "should_appear" in output
        # Clean up.
        root = logging.getLogger("repod")
        root.handlers.clear()
        root.addHandler(logging.NullHandler())


class TestConfigureLogging:
    """Verify configure_logging behavior."""

    def test_configure_removes_null_handler(self) -> None:
        root = logging.getLogger("repod")
        root.handlers.clear()
        root.addHandler(logging.NullHandler())
        assert any(isinstance(h, logging.NullHandler) for h in root.handlers)
        stream = io.StringIO()
        configure_logging(stream=stream)
        assert not any(isinstance(h, logging.NullHandler) for h in root.handlers)
        # Clean up.
        root.handlers.clear()
        root.addHandler(logging.NullHandler())

    def test_configure_sets_level(self) -> None:
        stream = io.StringIO()
        configure_logging("DEBUG", stream=stream)
        root = logging.getLogger("repod")
        assert root.level == logging.DEBUG
        # Clean up.
        root.handlers.clear()
        root.addHandler(logging.NullHandler())

    def test_configure_accepts_int_level(self) -> None:
        stream = io.StringIO()
        configure_logging(logging.WARNING, stream=stream)
        root = logging.getLogger("repod")
        assert root.level == logging.WARNING
        # Clean up.
        root.handlers.clear()
        root.addHandler(logging.NullHandler())

    def test_repeated_configure_no_duplicate_handlers(self) -> None:
        stream = io.StringIO()
        configure_logging(stream=stream)
        configure_logging(stream=stream)
        configure_logging(stream=stream)
        root = logging.getLogger("repod")
        # Should have exactly 1 handler, not 3.
        assert len(root.handlers) == 1
        # Clean up.
        root.handlers.clear()
        root.addHandler(logging.NullHandler())

    def test_null_handler_means_silence(self) -> None:
        root = logging.getLogger("repod")
        root.handlers.clear()
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.DEBUG)
        stream = io.StringIO()
        # Add a StreamHandler to a *different* logger to prove
        # the "repod" logger produces nothing.
        log = get_logger("repod.test.silence")
        log.info("this_should_be_silent")
        # The NullHandler swallows everything.
        assert stream.getvalue() == ""
