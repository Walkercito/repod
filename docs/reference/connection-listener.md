# ConnectionListener

```python
class ConnectionListener
```

High-level client-side class. Subclass it, define `Network_{action}` methods, and call `pump()` every frame.

## Methods

| Method | Signature | Description |
|---|---|---|
| `connect` | `(host: str, port: int)` | Connect to a server. Starts a background thread. |
| `pump` | `()` | Process all pending messages. Call once per frame. |
| `send` | `(data: dict) -> int` | Send a message to the server. Returns bytes queued, `0` if not connected. |
| `network_received` | `(data: dict)` | Fallback for unmatched actions. Override to handle. |

## Properties

| Property | Type | Description |
|---|---|---|
| `connection` | `Client \| None` | The underlying `Client` instance. |

## Built-in events

These are dispatched automatically by repod. Define them as `Network_{action}` methods:

| Handler | When |
|---|---|
| `Network_connected(data)` | Connection to server established. |
| `Network_disconnected(data)` | Connection lost. |
| `Network_error(data)` | Connection error. `data["error"]` has the message. |

## Message handlers

Same as Channel -- define `Network_{action}` methods:

```python
def Network_chat(self, data: dict) -> None:
    print(data["text"])
```
