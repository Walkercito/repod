# repod -- multiplayer networking library for Python games

[![Python 3.12+](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FWalkercito%2Frepod%2Fmain%2Fpyproject.toml&logo=python&logoColor=white&label=Python)](https://www.python.org/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![msgpack](https://img.shields.io/badge/serialization-msgpack-orange)](https://msgpack.org/)
[![asyncio](https://img.shields.io/badge/I%2FO-asyncio-purple)](https://docs.python.org/3/library/asyncio.html)

repod is a networking library designed to make it easy to write multiplayer games in Python. It uses `asyncio` and `msgpack` to asynchronously serialize network events and arbitrary data structures, and delivers them to your high-level classes through simple callback methods.

It is a modernized fork of [PodSixNet](https://github.com/chr15m/PodSixNet). Same ideas -- channels, action-based message dispatch, synchronous pump loops -- but rebuilt from scratch for Python 3.12+ with async I/O, binary msgpack serialization, and full type annotations. PodSixNet was built on `asyncore`, which was removed in Python 3.12; repod is the drop-in replacement.

Each class within your game client which wants to receive network events subclasses `ConnectionListener` and implements `Network_*` methods to catch specific events from the server. You don't have to wait for buffers to fill, or check sockets for waiting data or anything like that -- just call `client.pump()` once per game loop and the library handles everything else, passing off events to your listener. Sending data back to the server is just as easy with `client.send(mydata)`. On the server side, events are propagated to `Network_*` callbacks on your `Channel` subclass, and data is sent back to clients with `channel.send(mydata)`.

## Install

```bash
pip install repodnet
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add repodnet
```

## Examples

Chat example:

- `python examples/chat_server.py`
- and a couple of instances of `python examples/chat_client.py`

Whiteboard example (requires pygame-ce):

- `python examples/whiteboard_server.py`
- and a couple of instances of `python examples/whiteboard_client.py`

LagTime example (measures round-trip time from server to client):

- `python examples/lag_time_server.py`
- and a couple of instances of `python examples/lag_time_client.py`

## Quick start -- Server

You need to subclass two classes to make your own server. Each time a client connects, a new `Channel` instance is created, so you subclass `Channel` to make your server-side representation of a client:

```python
from repod import Channel

class ClientChannel(Channel):

    def network_received(self, data: dict) -> None:
        print(data)

    def Network_myaction(self, data: dict) -> None:
        print("myaction:", data)
```

Whenever the client sends data, the `network_received()` fallback is called if no specific handler exists. The method `Network_myaction()` is only called if your data has an `"action"` key with a value of `"myaction"`. In other words, if the data looks like:

```python
{"action": "myaction", "blah": 123, ...}
```

Next, subclass `Server`:

```python
from repod import Server

class MyServer(Server):
    channel_class = ClientChannel

    def on_connect(self, channel, addr):
        print("new connection:", channel)
```

Set `channel_class` to the Channel subclass you created above. The `on_connect()` method is called whenever a new client connects.

To run the server, call `launch()`:

```python
MyServer(host="0.0.0.0", port=5071).launch()
```

That's it. One line. `launch()` handles the event loop internally and catches `Ctrl+C` for clean shutdown.

When you want to send data to a specific client, use the `send` method on the Channel:

```python
channel.send({"action": "hello", "message": "hello client!"})
```

## Quick start -- Client

To connect to your server, subclass `ConnectionListener`:

```python
import time
from repod import ConnectionListener

class MyClient(ConnectionListener):

    def Network_connected(self, data: dict) -> None:
        print("connected to the server")

    def Network_error(self, data: dict) -> None:
        print("error:", data["error"])

    def Network_disconnected(self, data: dict) -> None:
        print("disconnected from the server")

    def Network_myaction(self, data: dict) -> None:
        print("myaction:", data)
```

Network events are received by `Network_*` callback methods. Replace `*` with the value of the `"action"` key you want to catch. The `connected`, `disconnected`, and `error` events are sent automatically by repod.

Connect and pump:

```python
client = MyClient()
client.connect("localhost", 5071)

while True:
    client.pump()
    time.sleep(0.01)
```

Call `pump()` once per game loop and repod handles everything -- reading from the socket, deserializing, and dispatching to your `Network_*` methods. Sending data to the server:

```python
client.send({"action": "myaction", "blah": 123, "things": [3, 4, 3, 4, 7]})
```

This works with any game framework that has a main loop: pygame, raylib, arcade, pyglet, etc. Just drop `pump()` into the loop.

## Documentation

Full tutorial and API reference: **[docs/DOCS.md](docs/DOCS.md)**

## Why not PodSixNet?

PodSixNet was great for its time, but:

- It's built on `asyncore`, which was **removed in Python 3.12**
- It uses `rencode` / custom delimiter-based framing (`\0---\0`), which is fragile with binary data
- It has no type annotations, no modern tooling support
- It is no longer maintained ([chr15m/PodSixNet#46](https://github.com/chr15m/PodSixNet/issues/46))

repod keeps the same simple API philosophy but replaces the internals:

- **asyncio** instead of asyncore
- **msgpack** with length-prefix framing instead of rencode with delimiter framing
- **Full type annotations** with PEP 695 generics (optional)
- **Python 3.12+** only -- no compatibility shims

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest tests/ -v
```

## License

Copyright Walker Gonzales, 2025.

repod is licensed under the terms of the **LGPL v3.0** or later. See the [COPYING](COPYING) file for details.

This is the same license as [PodSixNet](https://github.com/chr15m/PodSixNet), from which repod is forked. In short: you can use repod in any project (commercial or otherwise), but if you modify the repod library code itself, you must make the modified source available.
