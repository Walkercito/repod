# Building a client

## Step 1: Subclass ConnectionListener

```python
import time
from repod import ConnectionListener


class ChatClient(ConnectionListener):

    def Network_connected(self, data: dict) -> None:
        """Called when the connection to the server is established."""
        print("Connected to server!")

    def Network_disconnected(self, data: dict) -> None:
        """Called when the connection is lost."""
        print("Disconnected.")

    def Network_message(self, data: dict) -> None:
        """Called when the server sends {"action": "message", ...}."""
        print(f"Server says: {data['text']}")
```

The `Network_connected` and `Network_disconnected` handlers are built-in events that repod sends automatically. You don't have to define them, but you'll almost always want to.

## Step 2: Connect and pump

```python
client = ChatClient()
client.connect("localhost", 5071)

while True:
    client.pump()
    time.sleep(0.01)
```

`connect()` starts a background thread that manages the TCP connection. `pump()` drains the message queue and dispatches each message to the matching `Network_{action}` method. Call it once per frame.

To send a message to the server:

```python
client.send({"action": "message", "text": "Hello server!"})
```

## Full client file

```python
import time
from repod import ConnectionListener


class ChatClient(ConnectionListener):

    def Network_connected(self, data: dict) -> None:
        print("Connected!")
        self.send({"action": "message", "text": "Hello server!"})

    def Network_disconnected(self, data: dict) -> None:
        print("Disconnected.")

    def Network_message(self, data: dict) -> None:
        print(f"Server says: {data['text']}")


client = ChatClient()
client.connect("localhost", 5071)

while True:
    client.pump()
    time.sleep(0.01)
```
