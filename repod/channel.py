"""Network channel representing a single connection.

A :class:`Channel` represents one side of a TCP connection.  On the
server side, each connected client gets its own ``Channel`` instance.

Subclass ``Channel`` and define ``Network_{action}`` methods to handle
specific message types::

    class GameChannel(Channel):

        def Network_chat(self, data: dict) -> None:
            print(f"Chat: {data['message']}")

        def Network_move(self, data: dict) -> None:
            print(f"Player moved to {data['x']}, {data['y']}")
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from repod.server import Server


class Channel[S: Server]:
    """Represents a single network connection.

    Attributes:
        addr: ``(host, port)`` tuple of the remote endpoint.
        is_connected: Whether the connection is currently active.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        server: S | None = None,
    ) -> None:
        """Initialize a channel with asyncio stream reader/writer.

        Args:
            reader: Async stream reader for incoming data.
            writer: Async stream writer for outgoing data.
            server: Optional reference to the parent
                :class:`~repod.server.Server`.
        """
        self._reader = reader
        self._writer = writer
        self._send_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._receive_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._closed = False
        self._address: tuple[str, int] = writer.get_extra_info("peername")
        self._server: S | None = server
        self._buffer = b""

        # Disable Nagle's algorithm for low-latency real-time communication.
        sock: socket.socket | None = writer.get_extra_info("socket")
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    @property
    def addr(self) -> tuple[str, int]:
        """Remote address as a ``(host, port)`` tuple."""
        return self._address

    @property
    def is_connected(self) -> bool:
        """Whether this channel is still connected."""
        return not self._closed

    @property
    def server(self) -> S:
        """The parent :class:`~repod.server.Server` instance.

        Raises:
            RuntimeError: If the channel is not connected to a server.
        """
        if self._server is None:
            raise RuntimeError("Channel is not connected to a server")
        return self._server

    def send(self, data: dict[str, Any]) -> int:
        """Queue a message to be sent to the remote endpoint.

        The dictionary is serialized with msgpack and framed with a
        4-byte length prefix before being placed in the async send
        queue.

        Args:
            data: Message dictionary.  Should contain an ``action`` key
                to identify the message type on the receiver side.

        Returns:
            Number of bytes queued, or ``0`` if disconnected.
        """
        if self._closed:
            return 0

        from repod.protocol import encode

        outgoing = encode(data)
        self._send_queue.put_nowait(outgoing)
        return len(outgoing)

    def on_connect(self) -> None:
        """Called when the connection is established.

        Override in your subclass to run setup logic when a client
        connects.
        """

    def on_close(self) -> None:
        """Called when the connection is closed.

        Override in your subclass to run cleanup logic when a client
        disconnects.
        """

    def on_error(self, error: Exception) -> None:
        """Called when a connection error occurs.

        Override to implement custom error handling.

        Args:
            error: The exception that was raised.
        """
        print(f"Channel error: {error}")

    def network_received(self, data: dict[str, Any]) -> None:
        """Fallback handler for messages with no specific handler.

        Called when a message's ``action`` does not match any
        ``Network_{action}`` method.  Override to handle unrecognized
        messages.

        Args:
            data: The received message dictionary.
        """

    def _dispatch(self, data: dict[str, Any]) -> None:
        """Route a message to the matching ``Network_{action}`` method.

        Falls back to :meth:`network_received` when no specific handler
        is found.

        Args:
            data: Message dictionary with an ``action`` key.
        """
        action = data.get("action", "")
        method_name = f"Network_{action}"
        handler = getattr(self, method_name, None)
        if handler is not None:
            handler(data)
        else:
            self.network_received(data)

    async def _write_loop(self) -> None:
        """Continuously drain the send queue to the socket."""
        try:
            while not self._closed:
                data = await self._send_queue.get()
                if not data:
                    break
                self._writer.write(data)
                await self._writer.drain()
        except Exception:
            self._closed = True

    async def _read_loop(self) -> None:
        """Continuously read from the socket and parse messages."""
        from repod.constants import READ_BUFFER_SIZE
        from repod.protocol import read_message

        try:
            while not self._closed:
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
                        self._receive_queue.put_nowait(message)
        except Exception:
            pass
        finally:
            await self._handle_close()

    async def _handle_close(self) -> None:
        """Handle connection teardown and cleanup."""
        if self._closed:
            return

        self._closed = True
        self._receive_queue.put_nowait({"action": "disconnected"})
        self.on_close()

        # Unblock a pending ``_write_loop`` waiting on the queue.
        self._send_queue.put_nowait(b"")

        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass
