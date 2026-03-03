# Client

```python
class Client
```

Low-level TCP client. You almost never need this directly -- use [`ConnectionListener`](connection-listener.md) instead.

## Constructor

```python
Client(host: str = "127.0.0.1", port: int = 5071)
```

## Methods

| Method | Description |
|---|---|
| `start_background()` | Start the network loop in a daemon thread. |
| `send(data)` | Queue a message. Thread-safe. |
| `close()` | Close the connection. |

## Attributes

| Attribute | Type | Description |
|---|---|---|
| `address` | `tuple[str, int]` | Remote server address. |
