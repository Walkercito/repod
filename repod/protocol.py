"""Message serialization protocol.

Handles encoding and decoding of network messages using msgpack
serialization with length-prefix framing.

Message format::

    ┌──────────────┬────────────────────────┐
    │ 4 bytes      │ N bytes                │
    │ length (BE)  │ msgpack payload        │
    └──────────────┴────────────────────────┘

This framing method is efficient (O(1) boundary detection), safe
(no delimiter collision risk), and standard (used by Kafka, Redis,
Protocol Buffers, etc.).

Example::

    >>> from repod.protocol import encode, decode
    >>> data = {"action": "chat", "message": "Hello!"}
    >>> encoded = encode(data)
    >>> decoded = decode(encoded[4:])  # skip the 4-byte header
    >>> decoded
    {'action': 'chat', 'message': 'Hello!'}
"""

from __future__ import annotations

import struct
from typing import cast

import msgpack

from repod.constants import HEADER_FORMAT, HEADER_SIZE


def encode(data: dict) -> bytes:
    """Encode a dictionary as a length-prefixed message frame.

    The message is serialized with msgpack and prefixed with a 4-byte
    big-endian length header.

    Args:
        data: Dictionary containing the message data.  Can include any
            msgpack-serializable types (dict, list, str, int, float,
            bool, None).

    Returns:
        The encoded message with its 4-byte length prefix.

    Raises:
        TypeError: If *data* contains non-serializable types.

    Example::

        >>> encoded = encode({"action": "ping", "count": 5})
        >>> len(encoded) > 4  # includes the 4-byte header
        True
    """
    packed = cast(bytes, msgpack.packb(data, use_bin_type=True))
    length = struct.pack(HEADER_FORMAT, len(packed))
    return length + packed


def decode(data: bytes) -> dict:
    """Decode msgpack-serialized bytes into a dictionary.

    Note:
        This expects raw msgpack data, **not** a full length-prefixed
        frame.  Use :func:`read_message` for stream-based decoding.

    Args:
        data: Raw msgpack-serialized bytes.

    Returns:
        The decoded message dictionary.

    Raises:
        msgpack.UnpackException: If *data* is not valid msgpack.

    Example::

        >>> import msgpack
        >>> raw = msgpack.packb({"action": "hello"})
        >>> decode(raw)
        {'action': 'hello'}
    """
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


def read_message(stream: bytes) -> tuple[dict | None, int]:
    """Read a complete message from a byte stream.

    Implements length-prefix framing to extract complete messages from
    a potentially partial byte buffer.

    Args:
        stream: Byte buffer that may contain partial or complete
            messages.

    Returns:
        A ``(message, bytes_consumed)`` tuple.  If the stream does not
        yet contain a full message, returns ``(None, 0)``.

    Example::

        >>> frame = encode({"action": "test"})
        >>> msg, consumed = read_message(frame)
        >>> msg
        {'action': 'test'}
        >>> consumed == len(frame)
        True
    """
    if len(stream) < HEADER_SIZE:
        return None, 0

    length: int = struct.unpack(HEADER_FORMAT, stream[:HEADER_SIZE])[0]
    total_size = HEADER_SIZE + length

    if len(stream) < total_size:
        return None, 0

    payload = stream[HEADER_SIZE:total_size]
    return msgpack.unpackb(payload, raw=False, strict_map_key=False), total_size
