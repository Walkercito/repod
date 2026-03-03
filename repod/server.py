"""Async TCP server for multiplayer games.

The :class:`Server` manages multiple client connections, creating a
:class:`~repod.channel.Channel` instance for each one.  It can run in
the main thread or in a background daemon thread for host/client P2P
setups.

Example::

    class GameChannel(Channel):

        def Network_chat(self, data: dict) -> None:
            self.server.send_to_all(
                {"action": "chat", "text": data["text"]}
            )


    class GameServer(Server):
        channel_class = GameChannel


    GameServer(host="0.0.0.0", port=5071).launch()
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from repod.channel import Channel


class Server[C: Channel]:
    """Async TCP server that manages client channels.

    Attributes:
        host: Hostname or IP address the server is bound to.
        port: Port number the server is listening on.
        channels: List of currently connected client channels.
        channel_class: The :class:`Channel` subclass instantiated for
            each new connection.  Must be set in your subclass.
    """

    channel_class: type[C]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5071,
    ) -> None:
        """Initialize the server.

        Args:
            host: Hostname or IP to bind to.  Use ``"0.0.0.0"`` for all
                interfaces.
            port: Port number to listen on.
        """
        self.host = host
        self.port = port
        self.channels: list[C] = []
        self._tcp_server: asyncio.Server | None = None

    @property
    def address(self) -> tuple[str, int]:
        """Server bind address as a ``(host, port)`` tuple."""
        return (self.host, self.port)

    async def start(self) -> None:
        """Start accepting connections.

        Binds to ``host:port`` and begins listening for incoming TCP
        connections.
        """
        self._tcp_server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        addr = self._tcp_server.sockets[0].getsockname()
        print(f"Server started on {addr[0]}:{addr[1]}")

    async def run(self) -> None:
        """Run the server forever.

        Blocks until the server is stopped or the task is cancelled.
        """
        await asyncio.Future()

    def launch(self) -> None:
        """Start the server and block forever.

        Convenience wrapper that hides asyncio boilerplate.  Equivalent
        to calling :meth:`start` then :meth:`run` inside
        ``asyncio.run()``.  Handles ``KeyboardInterrupt`` gracefully.

        Example::

            GameServer(host="0.0.0.0", port=5071).launch()
        """

        async def _main() -> None:
            await self.start()
            try:
                await self.run()
            except asyncio.CancelledError:
                pass
            finally:
                await self.stop()

        try:
            asyncio.run(_main())
        except KeyboardInterrupt:
            print("\nServer stopped.")

    async def stop(self) -> None:
        """Stop the server and disconnect all clients."""
        for channel in self.channels[:]:
            await channel._handle_close()
        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()

    def start_background(self) -> threading.Thread:
        """Start the server in a daemon background thread.

        Useful for *Host Game* scenarios where the main thread needs to
        remain free for the game loop or UI.

        Returns:
            The :class:`threading.Thread` running the server.
        """
        thread = threading.Thread(target=self._run_in_thread, daemon=True)
        thread.start()
        return thread

    def on_connect(self, channel: C, addr: tuple[str, int]) -> None:
        """Called when a new client connects.

        Override to run per-client setup (e.g. add to a player list).

        Args:
            channel: The newly created channel for this client.
            addr: ``(host, port)`` of the remote client.
        """

    def on_disconnect(self, channel: C) -> None:
        """Called when a client disconnects.

        Override to run per-client cleanup.

        Args:
            channel: The channel that disconnected.
        """

    def send_to_all(self, data: dict[str, Any]) -> None:
        """Broadcast a message to every connected client.

        Args:
            data: Message dictionary to send to all channels.
        """
        for channel in self.channels:
            channel.send(data)

    def _run_in_thread(self) -> None:
        """Create a new event loop and run the server inside it."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start())
        try:
            loop.run_until_complete(self.run())
        except Exception as e:
            print(f"Background server error: {e}")
        finally:
            loop.run_until_complete(self.stop())
            loop.close()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a newly connected client."""
        channel = self.channel_class(reader, writer, server=self)
        self.channels.append(channel)

        channel.send({"action": "connected"})
        channel.on_connect()
        self.on_connect(channel, writer.get_extra_info("peername"))

        try:
            await asyncio.gather(
                channel._read_loop(),
                channel._write_loop(),
                self._process_loop(channel),
            )
        except Exception as e:
            channel.on_error(e)
        finally:
            await self._remove_channel(channel)

    async def _process_loop(self, channel: C) -> None:
        """Drain the channel's receive queue and dispatch messages."""
        try:
            while not channel._closed:
                data = await channel._receive_queue.get()
                if data.get("action") == "disconnected":
                    break
                channel._dispatch(data)
        except Exception:
            pass

    async def _remove_channel(self, channel: C) -> None:
        """Remove a channel and notify via :meth:`on_disconnect`."""
        if channel in self.channels:
            self.channels.remove(channel)
        self.on_disconnect(channel)
