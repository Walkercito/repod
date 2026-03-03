# repod documentation

## Table of contents

- [What is repod?](#what-is-repod)
- [Installation](#installation)
- [Tutorial](#tutorial)
  - [How repod works](#how-repod-works)
  - [Building a server](#building-a-server)
  - [Building a client](#building-a-client)
  - [Putting it together](#putting-it-together)
  - [Broadcasting messages](#broadcasting-messages)
  - [Handling connections and disconnections](#handling-connections-and-disconnections)
  - [Using repod with pygame](#using-repod-with-pygame)
  - [Host + play (background server)](#host--play-background-server)
  - [Type-safe generics](#type-safe-generics)
  - [Async API](#async-api)
- [API reference](#api-reference)
  - [Server](#server)
  - [Channel](#channel)
  - [ConnectionListener](#connectionlistener)
  - [Client](#client)
  - [Protocol functions](#protocol-functions)
  - [Constants](#constants)
- [Wire format](#wire-format)
- [Examples](#examples)

---

## What is repod?

repod is a networking library for multiplayer games in Python. It's a modernized replacement for [PodSixNet](https://github.com/chr15m/PodSixNet), built on `asyncio` and `msgpack` instead of the deprecated `asyncore` module.

The design philosophy is simple: **messages are Python dicts**. You send a dict with an `"action"` key, and repod automatically routes it to a method named `Network_{action}` on the other side. That's it.

```
Client sends:  {"action": "move", "x": 10, "y": 20}
                        │
                        ▼
Server calls:  channel.Network_move({"action": "move", "x": 10, "y": 20})
```

repod handles the TCP connection, serialization (msgpack), framing (length-prefix), and threading for you. You just define handler methods and send dicts.

## Installation

```bash
pip install repod
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add repod
```

Requires Python 3.12+.

---

## Tutorial

### How repod works

There are three classes you need to know:

| Class | Side | What it does |
|---|---|---|
| `Server` | Server | Listens for TCP connections. Creates a `Channel` for each client that connects. |
| `Channel` | Server | Represents one connected client. You define `Network_{action}` methods here to handle messages from that client. |
| `ConnectionListener` | Client | Connects to a server. You define `Network_{action}` methods here to handle messages from the server. Call `pump()` every frame to process them. |

The flow looks like this:

```
┌────────────────────┐          ┌────────────────────┐
│      Client        │          │      Server        │
│                    │          │                    │
│ ConnectionListener │◄────────►│  Server            │
│  - pump()          │   TCP    │  - launch()        │
│  - send()          │          │  - on_connect()    │
│  - Network_*()     │          │  - on_disconnect() │
│                    │          │                    │
│                    │          │  Channel (per client)│
│                    │          │  - send()           │
│                    │          │  - Network_*()      │
└────────────────────┘          └────────────────────┘
```

### Building a server

A server needs two classes: a **Channel** subclass (handles messages from one client) and a **Server** subclass (manages all channels).

#### Step 1: Define your Channel

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

#### Step 2: Define your Server

```python
class ChatServer(Server):
    channel_class = ChatChannel
```

That's the minimum. `channel_class` tells the server which Channel class to instantiate for each new connection.

#### Step 3: Launch it

```python
if __name__ == "__main__":
    ChatServer(host="0.0.0.0", port=5071).launch()
```

`launch()` starts accepting connections and blocks forever. It handles `Ctrl+C` gracefully.

**Full server file:**

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

### Building a client

#### Step 1: Subclass ConnectionListener

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

#### Step 2: Connect and pump

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

**Full client file:**

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

### Putting it together

Let's trace what happens when the client sends a message:

1. Client calls `self.send({"action": "message", "text": "Hello!"})`.
2. repod serializes the dict with msgpack, adds a 4-byte length header, and sends it over TCP.
3. On the server, the channel's read loop receives the bytes, parses the frame, and puts the dict in a queue.
4. The server's process loop takes the dict from the queue and calls `channel._dispatch(data)`.
5. `_dispatch` looks at `data["action"]` (which is `"message"`), finds `Network_message` on the channel, and calls it.
6. Your `Network_message` method runs with the full dict as argument.

The same flow works in reverse: a channel calls `self.send(...)`, and the client's `pump()` dispatches it to the matching `Network_{action}` on the `ConnectionListener`.

### Broadcasting messages

From inside a Channel, you can access the server via `self.server` and all connected channels via `self.server.channels`:

```python
class ChatChannel(Channel):

    def Network_message(self, data: dict) -> None:
        # Send to ALL connected clients (including sender)
        self.server.send_to_all({"action": "message", "text": data["text"]})
```

`send_to_all()` is a built-in convenience method. You can also loop manually:

```python
def Network_message(self, data: dict) -> None:
    for channel in self.server.channels:
        if channel is not self:  # skip the sender
            channel.send({"action": "message", "text": data["text"]})
```

### Handling connections and disconnections

On the **server**, override `on_connect` and `on_disconnect`:

```python
class GameServer(Server):
    channel_class = GameChannel

    def __init__(self, host: str = "127.0.0.1", port: int = 5071) -> None:
        super().__init__(host, port)
        self.players: list[GameChannel] = []

    def on_connect(self, channel: GameChannel, addr: tuple[str, int]) -> None:
        """Called when a new client connects."""
        print(f"New player from {addr}")
        self.players.append(channel)

    def on_disconnect(self, channel: GameChannel) -> None:
        """Called when a client disconnects."""
        print(f"Player left")
        if channel in self.players:
            self.players.remove(channel)
```

On the **channel**, override `on_connect` and `on_close`:

```python
class GameChannel(Channel):

    def on_connect(self) -> None:
        """Called when this channel's connection is established."""
        print(f"Client connected: {self.addr}")

    def on_close(self) -> None:
        """Called when this channel's connection is closed."""
        print(f"Client disconnected: {self.addr}")
```

On the **client**, these are just regular `Network_*` handlers:

```python
class GameClient(ConnectionListener):

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_disconnected(self, data: dict) -> None:
        print("Lost connection.")

    def Network_error(self, data: dict) -> None:
        print(f"Connection error: {data.get('error')}")
```

### Fallback handler

If a message arrives with an action that has no matching `Network_{action}` method, repod calls `network_received()` instead. Override it to catch unhandled messages:

```python
class GameChannel(Channel):

    def Network_move(self, data: dict) -> None:
        ...

    def network_received(self, data: dict) -> None:
        print(f"Unhandled action: {data.get('action')}")
```

This works on both `Channel` and `ConnectionListener`.

### Adding state to channels

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

### Using repod with pygame

`ConnectionListener.pump()` is designed to drop into any game loop. Here's a pygame example:

```python
import pygame as pg
from repod import ConnectionListener


class Game(ConnectionListener):

    def __init__(self) -> None:
        pg.init()
        self.screen = pg.display.set_mode((800, 600))
        self.clock = pg.time.Clock()
        self.running = True
        self.connect("localhost", 5071)

    def run(self) -> None:
        while self.running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False

            self.pump()  # <-- process network messages here

            self.screen.fill((0, 0, 0))
            # ... draw game state ...
            pg.display.flip()
            self.clock.tick(60)

        pg.quit()

    def Network_connected(self, data: dict) -> None:
        print("Connected to server!")

    def Network_state(self, data: dict) -> None:
        # Update game state from server
        pass


if __name__ == "__main__":
    Game().run()
```

This works with any framework that has a main loop: pygame, raylib, arcade, pyglet, etc. Just call `pump()` once per frame.

### Host + play (background server)

For "Host Game" scenarios where the player who hosts also plays, run the server in a background thread:

```python
from repod import Server, ConnectionListener


class GameServer(Server):
    channel_class = GameChannel


class GameClient(ConnectionListener):
    ...


# Start server in background (doesn't block)
server = GameServer(host="0.0.0.0", port=5071)
thread = server.start_background()

# Connect as a regular client
client = GameClient()
client.connect("localhost", 5071)

# Normal game loop
while True:
    client.pump()
    time.sleep(0.01)
```

`start_background()` spawns a daemon thread, so it dies automatically when the main program exits.

### Type-safe generics

This is **optional**. If you don't use generics, everything works fine -- `self.server` is typed as a generic `Server`.

But if you want your IDE to autocomplete custom methods on `self.server`, pass your server class as a type parameter:

```python
class GameChannel(Channel["GameServer"]):

    def Network_chat(self, data: dict) -> None:
        # IDE knows self.server is GameServer, not generic Server
        self.server.broadcast(data)  # autocompletes!


class GameServer(Server[GameChannel]):
    channel_class = GameChannel

    def broadcast(self, data: dict) -> None:
        for ch in self.channels:
            ch.send(data)
```

Use it when you want the IDE help. Skip it when you just want to get something working.

### Async API

`launch()` hides asyncio for simple cases. If you need control over the event loop (e.g., combining with other async services, or running multiple servers), use the async methods directly:

```python
import asyncio


async def main() -> None:
    server = GameServer(host="0.0.0.0", port=5071)
    await server.start()
    try:
        await server.run()
    finally:
        await server.stop()


asyncio.run(main())
```

---

## API reference

### Server

```python
class Server[C: Channel]
```

TCP server that manages client channels. Subclass it and set `channel_class`.

#### Class attributes

| Attribute | Type | Description |
|---|---|---|
| `channel_class` | `type[C]` | The Channel subclass to instantiate per connection. **Required.** |

#### Constructor

```python
Server(host: str = "127.0.0.1", port: int = 5071)
```

| Parameter | Default | Description |
|---|---|---|
| `host` | `"127.0.0.1"` | IP to bind to. Use `"0.0.0.0"` for all interfaces. |
| `port` | `5071` | Port to listen on. |

#### Instance attributes

| Attribute | Type | Description |
|---|---|---|
| `host` | `str` | Bound hostname. |
| `port` | `int` | Bound port. |
| `channels` | `list[C]` | Currently connected channels. |

#### Properties

| Property | Type | Description |
|---|---|---|
| `address` | `tuple[str, int]` | `(host, port)` tuple. |

#### Methods

| Method | Description |
|---|---|
| `launch()` | Start the server and block forever. Hides asyncio. Handles `Ctrl+C`. |
| `send_to_all(data)` | Send a dict to every connected channel. |
| `start_background()` | Start in a daemon background thread. Returns the `Thread`. |
| `await start()` | Bind and start accepting connections. |
| `await run()` | Block until stopped. |
| `await stop()` | Disconnect all clients and shut down. |

#### Callbacks (override these)

| Callback | Signature | When |
|---|---|---|
| `on_connect` | `(channel: C, addr: tuple[str, int])` | A new client connected. |
| `on_disconnect` | `(channel: C)` | A client disconnected. |

---

### Channel

```python
class Channel[S: Server]
```

Represents one connected client on the server side. Subclass it and define `Network_{action}` methods.

#### Constructor

```python
Channel(reader, writer, server=None)
```

You don't call this directly. The server creates channels automatically.

#### Properties

| Property | Type | Description |
|---|---|---|
| `addr` | `tuple[str, int]` | Remote `(host, port)`. |
| `is_connected` | `bool` | Whether the connection is active. |
| `server` | `S` | The parent Server instance. Raises `RuntimeError` if not connected to a server. |

#### Methods

| Method | Signature | Description |
|---|---|---|
| `send` | `(data: dict) -> int` | Queue a message to send. Returns bytes queued, `0` if disconnected. |

#### Callbacks (override these)

| Callback | Signature | When |
|---|---|---|
| `on_connect` | `()` | Connection established. |
| `on_close` | `()` | Connection closed. |
| `on_error` | `(error: Exception)` | A connection error occurred. |
| `network_received` | `(data: dict)` | No `Network_{action}` handler found for a message. |

#### Message handlers

Define methods named `Network_{action}` to handle specific message types:

```python
def Network_move(self, data: dict) -> None:
    ...

def Network_chat(self, data: dict) -> None:
    ...
```

The `action` value in the dict determines which method is called. Unmatched actions go to `network_received()`.

---

### ConnectionListener

```python
class ConnectionListener
```

High-level client-side class. Subclass it, define `Network_{action}` methods, and call `pump()` every frame.

#### Methods

| Method | Signature | Description |
|---|---|---|
| `connect` | `(host: str, port: int)` | Connect to a server. Starts a background thread. |
| `pump` | `()` | Process all pending messages. Call once per frame. |
| `send` | `(data: dict) -> int` | Send a message to the server. Returns bytes queued, `0` if not connected. |
| `network_received` | `(data: dict)` | Fallback for unmatched actions. Override to handle. |

#### Properties

| Property | Type | Description |
|---|---|---|
| `connection` | `Client \| None` | The underlying `Client` instance. |

#### Built-in events

These are dispatched automatically by repod. Define them as `Network_{action}` methods:

| Handler | When |
|---|---|
| `Network_connected(data)` | Connection to server established. |
| `Network_disconnected(data)` | Connection lost. |
| `Network_error(data)` | Connection error. `data["error"]` has the message. |

#### Message handlers

Same as Channel -- define `Network_{action}` methods:

```python
def Network_chat(self, data: dict) -> None:
    print(data["text"])
```

---

### Client

```python
class Client
```

Low-level TCP client. You almost never need this directly -- use `ConnectionListener` instead.

#### Constructor

```python
Client(host: str = "127.0.0.1", port: int = 5071)
```

#### Methods

| Method | Description |
|---|---|
| `start_background()` | Start the network loop in a daemon thread. |
| `send(data)` | Queue a message. Thread-safe. |
| `close()` | Close the connection. |

#### Attributes

| Attribute | Type | Description |
|---|---|---|
| `address` | `tuple[str, int]` | Remote server address. |

---

### Protocol functions

Low-level serialization. You won't need these unless you're building custom transport.

```python
from repod import encode, decode, read_message
```

#### `encode(data: dict) -> bytes`

Serialize a dict to a length-prefixed msgpack frame.

```python
frame = encode({"action": "ping", "count": 1})
# frame = 4-byte header + msgpack payload
```

#### `decode(data: bytes) -> dict`

Deserialize raw msgpack bytes (without the length header).

```python
import msgpack
raw = msgpack.packb({"action": "ping"})
result = decode(raw)  # {"action": "ping"}
```

#### `read_message(stream: bytes) -> tuple[dict | None, int]`

Extract one complete message from a byte buffer. Returns `(message, bytes_consumed)` or `(None, 0)` if the buffer doesn't contain a complete message yet.

```python
frame = encode({"action": "test"})
msg, consumed = read_message(frame)
# msg = {"action": "test"}, consumed = len(frame)

partial = frame[:3]
msg, consumed = read_message(partial)
# msg = None, consumed = 0
```

---

### Constants

```python
from repod.constants import DEFAULT_HOST, DEFAULT_PORT
```

| Constant | Value | Description |
|---|---|---|
| `DEFAULT_HOST` | `"127.0.0.1"` | Default connection host. |
| `DEFAULT_PORT` | `5071` | Default connection port. |
| `HEADER_SIZE` | `4` | Bytes in the length-prefix header. |
| `HEADER_FORMAT` | `">I"` | `struct` format string (big-endian unsigned int). |
| `READ_BUFFER_SIZE` | `4096` | Socket read buffer size. |

---

## Wire format

Messages are serialized with [msgpack](https://msgpack.org/) and framed with a 4-byte big-endian length prefix:

```
┌──────────────────┬──────────────────────────┐
│ 4 bytes          │ N bytes                  │
│ length (uint32)  │ msgpack payload          │
└──────────────────┴──────────────────────────┘
```

This means:

- **No delimiter collisions** -- unlike PodSixNet's `\0---\0` separator, binary payloads can't accidentally split a message.
- **O(1) boundary detection** -- the receiver reads 4 bytes, knows exactly how many more to read.
- **Industry standard** -- same approach used by Kafka, Redis, Protocol Buffers, etc.

---

## Examples

The `examples/` directory has working demos:

| Example | Description |
|---|---|
| `chat_server.py` + `chat_client.py` | Multi-user chat room |
| `lag_time_server.py` + `lag_time_client.py` | Ping/pong round-trip latency |
| `whiteboard_server.py` + `whiteboard_client.py` | Shared drawing canvas (pygame-ce) |

```bash
# Terminal 1
python examples/chat_server.py

# Terminal 2
python examples/chat_client.py
```
