"""Tests for the repod.constants module."""

from __future__ import annotations

from repod.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    HEADER_FORMAT,
    HEADER_SIZE,
    READ_BUFFER_SIZE,
)


class TestDefaults:
    """Verify default configuration values are sensible."""

    def test_default_host_is_localhost(self) -> None:
        assert DEFAULT_HOST == "127.0.0.1"

    def test_default_port_is_positive(self) -> None:
        assert DEFAULT_PORT > 0

    def test_default_port_value(self) -> None:
        assert DEFAULT_PORT == 5071

    def test_header_size_is_four_bytes(self) -> None:
        assert HEADER_SIZE == 4

    def test_header_format_is_big_endian_unsigned_int(self) -> None:
        assert HEADER_FORMAT == ">I"

    def test_read_buffer_size_is_positive(self) -> None:
        assert READ_BUFFER_SIZE > 0

    def test_read_buffer_size_is_power_of_two(self) -> None:
        assert READ_BUFFER_SIZE & (READ_BUFFER_SIZE - 1) == 0
