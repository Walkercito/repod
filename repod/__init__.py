"""repod -- Modern async networking library for multiplayer games.

A type-safe networking library built on asyncio and msgpack,
designed as a modern replacement for PodSixNet.

Server quick-start::

    from repod import Server, Channel


    class MyChannel(Channel):

        def Network_hello(self, data: dict) -> None:
            self.send({"action": "response", "text": "Hi!"})


    class MyServer(Server):
        channel_class = MyChannel


    MyServer(host="0.0.0.0", port=5071).launch()

Client quick-start::

    import time
    from repod import ConnectionListener


    class MyClient(ConnectionListener):

        def Network_connected(self, data: dict) -> None:
            self.send({"action": "hello", "message": "Hello server!"})

        def Network_response(self, data: dict) -> None:
            print(data["text"])


    client = MyClient()
    client.connect("localhost", 5071)

    while True:
        client.pump()
        time.sleep(0.01)
"""

import logging

from repod.channel import Channel
from repod.client import Client, ConnectionListener
from repod.constants import DEFAULT_HOST, DEFAULT_PORT
from repod.logconfig import configure_logging
from repod.protocol import decode, encode, read_message
from repod.server import Server

# Library best practice: NullHandler so no output unless the
# application explicitly calls configure_logging().
logging.getLogger("repod").addHandler(logging.NullHandler())

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "Channel",
    "Client",
    "ConnectionListener",
    "Server",
    "configure_logging",
    "decode",
    "encode",
    "read_message",
]
