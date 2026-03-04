"""Optional structured logging for repod.

By default repod is silent -- it attaches a :class:`~logging.NullHandler`
to the ``"repod"`` logger so no output appears unless the application
explicitly opts in.

Call :func:`configure_logging` once at startup to enable colored,
wide-event log output inspired by structlog::

    from repod import configure_logging

    configure_logging()          # INFO and above
    configure_logging("DEBUG")   # everything

Output format::

    HH:MM:SS [+] server_started                     |  host=0.0.0.0  port=5071
    HH:MM:SS [+] client_connected                   |  addr=127.0.0.1:52340
    HH:MM:SS [*] message_dispatched                  |  action=chat  channel=1

The module also exposes :func:`get_logger`, which returns a thin
:class:`StructuredLogger` wrapper that accepts ``key=value`` kwargs
on every call -- these are rendered as structured context after the
``|`` separator.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

# -- ANSI codes ---------------------------------------------------------------

_R = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_W = "\033[97m"

_LEVEL_STYLES: dict[str, tuple[str, str]] = {
    "DEBUG": ("\033[90m", "[*]"),
    "INFO": ("\033[92m", "[+]"),
    "WARNING": ("\033[93m", "[!]"),
    "ERROR": ("\033[91m", "[-]"),
    "CRITICAL": ("\033[91;1m", "[x]"),
}

_VAL_COLORS: dict[str, str] = {
    "error": "\033[91m",
    "host": "\033[96m",
    "port": "\033[96m",
    "addr": "\033[96m",
    "action": "\033[94m",
    "channel": "\033[94m",
    "bytes": "\033[93m",
    "clients": "\033[93m",
}


# -- Formatter ----------------------------------------------------------------

_EVENT_COL_WIDTH = 38


class RepodFormatter(logging.Formatter):
    """Colored wide-event formatter for repod log records.

    Produces one line per record with the structure::

        HH:MM:SS [+] <event padded>  |  key=value  key=value

    Structured key-value pairs are read from
    ``record._structured`` (a :class:`dict`) when present.
    """

    converter = time.localtime

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%H:%M:%S", self.converter(record.created))
        level = record.levelname
        color, icon = _LEVEL_STYLES.get(level, ("\033[37m", "[?]"))
        event = record.getMessage().ljust(_EVENT_COL_WIDTH)

        line = f"{_DIM}{ts}{_R} {_BOLD}{color}{icon}{_R} {_W}{event}{_R}"

        structured: dict[str, Any] = getattr(record, "_structured", {})
        if structured:
            kvs = "  ".join(
                f"{_DIM}{k}{_R}={_val_color(k, v)}{v}{_R}" for k, v in structured.items()
            )
            line += f"  {_DIM}|{_R}  {kvs}"

        return line


def _val_color(key: str, value: Any) -> str:
    """Pick an ANSI color for a key-value pair."""
    if key == "status":
        try:
            code = int(value)
            if code < 300:
                return "\033[92m"
            if code < 500:
                return "\033[93m"
            return "\033[91m"
        except (TypeError, ValueError):
            pass
    return _VAL_COLORS.get(key, _W)


# -- Structured logger wrapper ------------------------------------------------


class StructuredLogger:
    """Thin wrapper around :class:`~logging.Logger` supporting ``**kwargs``.

    Accepts ``key=value`` keyword arguments on every call and stores
    them in the log record's ``_structured`` dict for the formatter.

    Example::

        log = get_logger(__name__)
        log.info("server_started", host="0.0.0.0", port=5071)
    """

    __slots__ = ("_logger",)

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log at DEBUG level with structured context."""
        self._log(logging.DEBUG, event, kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log at INFO level with structured context."""
        self._log(logging.INFO, event, kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log at WARNING level with structured context."""
        self._log(logging.WARNING, event, kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log at ERROR level with structured context."""
        self._log(logging.ERROR, event, kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        """Log at CRITICAL level with structured context."""
        self._log(logging.CRITICAL, event, kwargs)

    def _log(self, level: int, event: str, structured: dict[str, Any]) -> None:
        if not self._logger.isEnabledFor(level):
            return
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(repod)",
            0,
            event,
            (),
            None,
        )
        record._structured = structured  # type: ignore[attr-defined]
        self._logger.handle(record)


# -- Public API ---------------------------------------------------------------


def get_logger(name: str) -> StructuredLogger:
    """Return a :class:`StructuredLogger` bound to *name*.

    Typically called at module level::

        from repod.logging import get_logger

        log = get_logger(__name__)
    """
    return StructuredLogger(name)


def configure_logging(
    level: int | str = logging.INFO,
    stream: Any = None,
) -> None:
    """Enable colored structured logging for the ``"repod"`` logger.

    Call once at application startup **before** creating any server or
    client.  If never called, repod remains silent (NullHandler).

    Args:
        level: Minimum log level.  Accepts an :class:`int`
            (``logging.DEBUG``, etc.) or a string (``"DEBUG"``).
        stream: Output stream.  Defaults to :data:`sys.stderr`.

    Example::

        from repod import configure_logging

        configure_logging()            # INFO level to stderr
        configure_logging("DEBUG")     # verbose
    """
    if stream is None:
        stream = sys.stderr

    root = logging.getLogger("repod")

    # Remove existing handlers (including NullHandler) to avoid
    # duplicate output on repeated calls.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(RepodFormatter())
    root.addHandler(handler)

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(level)
