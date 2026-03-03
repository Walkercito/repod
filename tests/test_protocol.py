"""Tests for the repod.protocol module."""

from __future__ import annotations

import struct

import msgpack

from repod.constants import HEADER_FORMAT, HEADER_SIZE
from repod.protocol import decode, encode, read_message


class TestEncode:
    """Tests for the encode function."""

    def test_returns_bytes(self) -> None:
        result = encode({"action": "test"})
        assert isinstance(result, bytes)

    def test_starts_with_length_header(self) -> None:
        data = {"action": "ping"}
        result = encode(data)
        length = struct.unpack(HEADER_FORMAT, result[:HEADER_SIZE])[0]
        assert length == len(result) - HEADER_SIZE

    def test_payload_is_valid_msgpack(self) -> None:
        data = {"action": "chat", "message": "Hello!"}
        result = encode(data)
        payload = result[HEADER_SIZE:]
        decoded = msgpack.unpackb(payload, raw=False)
        assert decoded == data

    def test_empty_dict(self) -> None:
        result = encode({})
        assert len(result) > HEADER_SIZE

    def test_nested_data(self) -> None:
        data = {
            "action": "state",
            "players": [{"name": "Alice", "x": 10, "y": 20}],
            "tick": 42,
        }
        result = encode(data)
        payload = result[HEADER_SIZE:]
        assert msgpack.unpackb(payload, raw=False) == data

    def test_various_value_types(self) -> None:
        data = {
            "action": "data",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "str": "hello",
        }
        result = encode(data)
        payload = result[HEADER_SIZE:]
        decoded = msgpack.unpackb(payload, raw=False)
        assert decoded == data


class TestDecode:
    """Tests for the decode function."""

    def test_roundtrip(self) -> None:
        data = {"action": "hello", "name": "world"}
        packed = msgpack.packb(data, use_bin_type=True)
        assert decode(packed) == data

    def test_decode_simple_dict(self) -> None:
        data = {"key": "value"}
        packed = msgpack.packb(data, use_bin_type=True)
        assert decode(packed) == data

    def test_decode_empty_dict(self) -> None:
        packed = msgpack.packb({}, use_bin_type=True)
        assert decode(packed) == {}


class TestReadMessage:
    """Tests for the read_message function."""

    def test_complete_message(self) -> None:
        frame = encode({"action": "test"})
        message, consumed = read_message(frame)
        assert message is not None
        assert message["action"] == "test"
        assert consumed == len(frame)

    def test_incomplete_header(self) -> None:
        message, consumed = read_message(b"\x00\x00")
        assert message is None
        assert consumed == 0

    def test_empty_stream(self) -> None:
        message, consumed = read_message(b"")
        assert message is None
        assert consumed == 0

    def test_incomplete_payload(self) -> None:
        frame = encode({"action": "test"})
        # Send header but only part of the payload.
        partial = frame[: HEADER_SIZE + 1]
        message, consumed = read_message(partial)
        assert message is None
        assert consumed == 0

    def test_multiple_messages_in_stream(self) -> None:
        msg1 = encode({"action": "first"})
        msg2 = encode({"action": "second"})
        stream = msg1 + msg2

        # First read.
        message, consumed = read_message(stream)
        assert message is not None
        assert message["action"] == "first"
        assert consumed == len(msg1)

        # Second read from remaining bytes.
        stream = stream[consumed:]
        message, consumed = read_message(stream)
        assert message is not None
        assert message["action"] == "second"
        assert consumed == len(msg2)

    def test_message_with_trailing_bytes(self) -> None:
        frame = encode({"action": "test"})
        stream = frame + b"\xde\xad\xbe\xef"
        message, consumed = read_message(stream)
        assert message is not None
        assert message["action"] == "test"
        assert consumed == len(frame)


class TestEncodeDecodeRoundtrip:
    """End-to-end roundtrip tests."""

    def test_simple_roundtrip(self) -> None:
        original = {"action": "chat", "text": "Hello world!"}
        frame = encode(original)
        message, consumed = read_message(frame)
        assert message == original
        assert consumed == len(frame)

    def test_large_payload_roundtrip(self) -> None:
        original = {"action": "bulk", "data": list(range(1000))}
        frame = encode(original)
        message, consumed = read_message(frame)
        assert message == original
        assert consumed == len(frame)

    def test_unicode_roundtrip(self) -> None:
        original = {"action": "chat", "text": "Hola mundo!"}
        frame = encode(original)
        message, _consumed = read_message(frame)
        assert message == original

    def test_binary_safe_strings(self) -> None:
        original = {"action": "data", "payload": "abc\x00def"}
        frame = encode(original)
        message, _consumed = read_message(frame)
        assert message == original
