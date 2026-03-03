"""Network configuration constants.

Default values used throughout the repod networking library.

Example::

    from repod.constants import DEFAULT_HOST, DEFAULT_PORT
"""

from typing import Final

DEFAULT_HOST: Final[str] = "127.0.0.1"
"""Default hostname for connections (localhost)."""

DEFAULT_PORT: Final[int] = 5071
"""Default port for connections."""

HEADER_SIZE: Final[int] = 4
"""Size in bytes of the message length header."""

HEADER_FORMAT: Final[str] = ">I"
"""Struct format for the header (big-endian unsigned int)."""

READ_BUFFER_SIZE: Final[int] = 4096
"""Buffer size in bytes for reading from sockets."""
