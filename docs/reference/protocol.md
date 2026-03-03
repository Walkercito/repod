# Protocol

Low-level serialization functions. You won't need these unless you're building custom transport.

```python
from repod import encode, decode, read_message
```

## `encode(data: dict) -> bytes`

Serialize a dict to a length-prefixed msgpack frame.

```python
frame = encode({"action": "ping", "count": 1})
# frame = 4-byte header + msgpack payload
```

## `decode(data: bytes) -> dict`

Deserialize raw msgpack bytes (without the length header).

```python
import msgpack
raw = msgpack.packb({"action": "ping"})
result = decode(raw)  # {"action": "ping"}
```

## `read_message(stream: bytes) -> tuple[dict | None, int]`

Extract one complete message from a byte buffer. Returns `(message, bytes_consumed)` or `(None, 0)` if the buffer doesn't contain a complete message yet.

```python
frame = encode({"action": "test"})
msg, consumed = read_message(frame)
# msg = {"action": "test"}, consumed = len(frame)

partial = frame[:3]
msg, consumed = read_message(partial)
# msg = None, consumed = 0
```
