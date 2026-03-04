"""Async TCP client for connecting to a repod server.

Provides :class:`Client` (low-level) and :class:`ConnectionListener`
(high-level mixin) for client-side networking.

The client runs an asyncio event loop in a background daemon thread so
that the main game/application loop can remain fully synchronous.

Example::

    import time
    from repod import ConnectionListener


    class GameClient(ConnectionListener):

        def Network_connected(self, data: dict) -> None:
            print("Connected!")
            self.send({"action": "hello", "name": "Alice"})

        def Network_chat(self, data: dict) -> None:
            print(f"{data['name']}: {data['text']}")


    client = GameClient()
    client.connect("localhost", 5071)

    while True:
        client.pump()
        time.sleep(0.01)
"""

from __future__ import annotations

import asyncio
import contextlib
import queue
import socket
import threading
from typing import Any

from repod.constants import DEFAULT_HOST, DEFAULT_PORT, READ_BUFFER_SIZE
from repod.logconfig import get_logger
from repod.protocol import encode, read_message

log = get_logger(__name__)


class Client:
    """Low-level TCP client with a background asyncio event loop.

    Runs asynchronous read/write loops in a daemon thread and exposes
    thread-safe :meth:`send` / :meth:`close` methods for use from the
    main thread.

    Attributes:
        address: ``(host, port)`` tuple for the remote server.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Initialize the client.

        Args:
            host: Server hostname or IP address.
            port: Server port number.
        """
        self.address: tuple[str, int] = (host, port)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._send_queue: queue.Queue[bytes] = queue.Queue()
        self._receive_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._closed = True
        self._buffer = b""
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start_background(self) -> None:
        """Start the network event loop in a daemon thread."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def send(self, data: dict[str, Any]) -> int:
        """Queue a message for sending to the server.

        Thread-safe -- call from your main game loop.

        Args:
            data: Message dictionary.  Should contain an ``action`` key.

        Returns:
            Number of bytes queued, or ``0`` if disconnected.
        """
        if self._closed:
            return 0
        outgoing = encode(data)
        self._send_queue.put(outgoing)
        return len(outgoing)

    def close(self) -> None:
        """Close the connection.

        Safe to call from any thread.  Subsequent calls are no-ops.
        """
        if self._closed:
            return
        self._closed = True
        self._receive_queue.put({"action": "disconnected"})
        if self._writer:
            self._writer.close()

    def _run_loop(self) -> None:
        """Run the asyncio event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._network_task())
        except Exception as exc:
            log.error("network_thread_error", error=str(exc))
        finally:
            self._loop.close()

    async def _network_task(self) -> None:
        """Connect and spawn concurrent read/write loops."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                *self.address,
            )
            sock: socket.socket | None = self._writer.get_extra_info("socket")
            if sock is not None:
                with contextlib.suppress(OSError):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            self._closed = False
            log.info("connected", host=self.address[0], port=self.address[1])
            self._receive_queue.put({"action": "connected"})
            self._receive_queue.put({"action": "socketConnect"})
        except Exception as e:
            log.error(
                "connection_failed",
                host=self.address[0],
                port=self.address[1],
                error=str(e),
            )
            self._receive_queue.put({"action": "error", "error": str(e)})
            return

        await asyncio.gather(self._read_loop(), self._write_loop())

    async def _read_loop(self) -> None:
        """Read data from the socket and enqueue parsed messages."""
        try:
            while not self._closed and self._reader:
                data = await self._reader.read(READ_BUFFER_SIZE)
                if not data:
                    break
                self._buffer += data

                while True:
                    message, consumed = read_message(self._buffer)
                    if message is None:
                        break
                    self._buffer = self._buffer[consumed:]
                    if isinstance(message, dict) and "action" in message:
                        self._receive_queue.put(message)
        except Exception:
            pass
        finally:
            self.close()

    async def _write_loop(self) -> None:
        """Drain the send queue to the socket."""
        try:
            while not self._closed and self._writer:
                if not self._send_queue.empty():
                    while not self._send_queue.empty():
                        try:
                            data = self._send_queue.get_nowait()
                            self._writer.write(data)
                        except queue.Empty:
                            break
                    await self._writer.drain()
                await asyncio.sleep(0.005)
        except Exception:
            self.close()


class ConnectionListener:
    """High-level mixin for handling server messages synchronously.

    Subclass this and define ``Network_{action}`` methods to handle
    incoming messages.  Call :meth:`pump` once per frame in your game
    loop to process queued network events.

    Example::

        class MyClient(ConnectionListener):

            def Network_connected(self, data: dict) -> None:
                print("Connected to server!")

            def Network_chat(self, data: dict) -> None:
                print(f"Chat: {data['text']}")

        client = MyClient()
        client.connect("localhost", 5071)

        while True:
            client.pump()
            time.sleep(0.01)
    """

    _connection: Client | None = None

    def connect(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Connect to a remote server.

        Creates a :class:`Client` and starts its background network
        thread.

        Args:
            host: Server hostname or IP address.
            port: Server port number.
        """
        log.info("connecting", host=host, port=port)
        self._connection = Client(host, port)
        self._connection.start_background()

    @property
    def connection(self) -> Client | None:
        """The underlying :class:`Client` instance, or ``None``."""
        return self._connection

    def pump(self) -> None:
        """Process all pending network messages.

        Call this once per frame in your game loop.  Each queued message
        is dispatched to the matching ``Network_{action}`` method, or to
        :meth:`network_received` as a fallback.
        """
        if self._connection is None:
            return

        while not self._connection._receive_queue.empty():
            try:
                data = self._connection._receive_queue.get_nowait()
            except queue.Empty:
                break

            action = data.get("action", "")
            method_name = f"Network_{action}"
            handler = getattr(self, method_name, None)
            if handler is not None:
                log.debug("message_dispatched", action=action)
                handler(data)
            else:
                log.debug("message_unhandled", action=action)
                self.network_received(data)

    def send(self, data: dict[str, Any]) -> int:
        """Send a message to the server.

        Args:
            data: Message dictionary.  Should contain an ``action`` key.

        Returns:
            Number of bytes queued, or ``0`` if not connected.
        """
        if self._connection is None:
            return 0
        return self._connection.send(data)

    def network_received(self, data: dict[str, Any]) -> None:
        """Fallback handler for unrecognized message actions.

        Override to handle messages that don't match any
        ``Network_{action}`` method.

        Args:
            data: The received message dictionary.
        """
