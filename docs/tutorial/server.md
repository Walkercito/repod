# Building a server

A server needs two classes: a **Channel** subclass (handles messages from one client) and a **Server** subclass (manages all channels).

## Step 1: Define your Channel

```python
from repod import Channel, Server


class ChatChannel(Channel):

    def Network_message(self, data: dict) -> None:
        """Called when a client sends {"action": "message", ...}."""
        print(f"Received: {data['text']}")
```

Every method named `Network_{something}` is a message handler. When a client sends `{"action": "message", "text": "hello"}`, repod calls `Network_message(data)` on that client's channel.

You can define as many handlers as you need:

```python
class GameChannel(Channel):

    def Network_move(self, data: dict) -> None:
        print(f"Player moved to {data['x']}, {data['y']}")

    def Network_attack(self, data: dict) -> None:
        print(f"Player attacked with {data['weapon']}")

    def Network_chat(self, data: dict) -> None:
        print(f"Chat: {data['text']}")
```

## Step 2: Define your Server

```python
class ChatServer(Server):
    channel_class = ChatChannel
```

That's the minimum. `channel_class` tells the server which Channel class to instantiate for each new connection.

## Step 3: Launch it

```python
if __name__ == "__main__":
    ChatServer(host="0.0.0.0", port=5071).launch()
```

`launch()` starts accepting connections and blocks forever. It handles `Ctrl+C` gracefully.

## Full server file

```python
from repod import Channel, Server


class ChatChannel(Channel):

    def Network_message(self, data: dict) -> None:
        print(f"Received: {data['text']}")


class ChatServer(Server):
    channel_class = ChatChannel


if __name__ == "__main__":
    ChatServer(host="0.0.0.0", port=5071).launch()
```
