# Channel

```python
class Channel[S: Server]
```

Represents one connected client on the server side. Subclass it and define `Network_{action}` methods.

## Constructor

```python
Channel(reader, writer, server=None)
```

!!! note
    You don't call this directly. The server creates channels automatically.

## Properties

| Property | Type | Description |
|---|---|---|
| `addr` | `tuple[str, int]` | Remote `(host, port)`. |
| `is_connected` | `bool` | Whether the connection is active. |
| `server` | `S` | The parent Server instance. Raises `RuntimeError` if not connected to a server. |

## Methods

| Method | Signature | Description |
|---|---|---|
| `send` | `(data: dict) -> int` | Queue a message to send. Returns bytes queued, `0` if disconnected. |

## Callbacks

Override these in your subclass:

| Callback | Signature | When |
|---|---|---|
| `on_connect` | `()` | Connection established. |
| `on_close` | `()` | Connection closed. |
| `on_error` | `(error: Exception)` | A connection error occurred. |
| `network_received` | `(data: dict)` | No `Network_{action}` handler found for a message. |

## Message handlers

Define methods named `Network_{action}` to handle specific message types:

```python
def Network_move(self, data: dict) -> None:
    ...

def Network_chat(self, data: dict) -> None:
    ...
```

The `action` value in the dict determines which method is called. Unmatched actions go to `network_received()`.
