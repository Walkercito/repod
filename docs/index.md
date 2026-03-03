# repod

**Networking library for multiplayer games in Python.**

---

repod is designed to make it easy to write multiplayer games in Python. It uses `asyncio` and `msgpack` to asynchronously serialize network events and arbitrary data structures, and delivers them to your high-level classes through simple callback methods.

It is a modernized fork of [PodSixNet](https://github.com/chr15m/PodSixNet). Same ideas -- channels, action-based message dispatch, synchronous pump loops -- but rebuilt from scratch for Python 3.12+ with async I/O, binary msgpack serialization, and full type annotations.

---

**Source Code**: [https://github.com/Walkercito/repod](https://github.com/Walkercito/repod)

---

## Quick start

=== "Server"

    ```python
    from repod import Channel, Server

    class ClientChannel(Channel):
        def Network_message(self, data: dict) -> None:
            print(data)

    class MyServer(Server):
        channel_class = ClientChannel

    MyServer(host="0.0.0.0", port=5071).launch()
    ```

=== "Client"

    ```python
    import time
    from repod import ConnectionListener

    class MyClient(ConnectionListener):
        def Network_connected(self, data: dict) -> None:
            print("connected!")

        def Network_message(self, data: dict) -> None:
            print(data)

    client = MyClient()
    client.connect("localhost", 5071)

    while True:
        client.pump()
        time.sleep(0.01)
    ```

## Features

- **Simple API** -- send dicts, receive dicts. `Network_{action}` method dispatch.
- **asyncio** under the hood, but you never touch it. `launch()` and `pump()` handle everything.
- **msgpack** with length-prefix framing -- fast, compact, binary-safe.
- **Full type annotations** with optional PEP 695 generics.
- **Works with any game framework** -- pygame, raylib, arcade, pyglet. Just call `pump()` in your loop.
- **Python 3.12+** only. No compatibility shims.

## Why not PodSixNet?

PodSixNet was great for its time, but:

- It's built on `asyncore`, which was **removed in Python 3.12**
- It uses `rencode` / custom delimiter-based framing, which is fragile with binary data
- It has no type annotations, no modern tooling support
- It is no longer maintained

repod keeps the same simple API philosophy but replaces the internals with modern Python.
