# Putting it together

Let's trace what happens when the client sends a message:

1. Client calls `self.send({"action": "message", "text": "Hello!"})`.
2. repod serializes the dict with msgpack, adds a 4-byte length header, and sends it over TCP.
3. On the server, the channel's read loop receives the bytes, parses the frame, and puts the dict in a queue.
4. The server's process loop takes the dict from the queue and calls `channel._dispatch(data)`.
5. `_dispatch` looks at `data["action"]` (which is `"message"`), finds `Network_message` on the channel, and calls it.
6. Your `Network_message` method runs with the full dict as argument.

The same flow works in reverse: a channel calls `self.send(...)`, and the client's `pump()` dispatches it to the matching `Network_{action}` on the `ConnectionListener`.

## Fallback handler

If a message arrives with an action that has no matching `Network_{action}` method, repod calls `network_received()` instead. Override it to catch unhandled messages:

```python
class GameChannel(Channel):

    def Network_move(self, data: dict) -> None:
        ...

    def network_received(self, data: dict) -> None:
        print(f"Unhandled action: {data.get('action')}")
```

This works on both `Channel` and `ConnectionListener`.

## Adding state to channels

Channels are regular Python objects. Add any attributes you need in `__init__`:

```python
class PlayerChannel(Channel):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.username = "anonymous"
        self.score = 0
        self.position = (0, 0)

    def Network_join(self, data: dict) -> None:
        self.username = data["username"]

    def Network_move(self, data: dict) -> None:
        self.position = (data["x"], data["y"])
```
