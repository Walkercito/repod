"""Integration tests for server-client communication."""

from __future__ import annotations

import asyncio

import pytest

from repod.channel import Channel
from repod.server import Server


class EchoChannel(Channel["EchoServer"]):
    """Channel that echoes messages back to the sender."""

    def Network_echo(self, data: dict) -> None:
        self.send({"action": "echo_reply", "text": data["text"]})

    def Network_broadcast(self, data: dict) -> None:
        self.server.send_to_all({"action": "broadcast_reply", "text": data["text"]})


class EchoServer(Server[EchoChannel]):
    """Simple echo server for testing."""

    channel_class = EchoChannel


@pytest.fixture
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestServerLifecycle:
    """Test server startup and shutdown."""

    def test_server_init(self) -> None:
        server = EchoServer(host="127.0.0.1", port=0)
        assert server.host == "127.0.0.1"
        assert server.channels == []
        assert server._tcp_server is None

    def test_server_address_property(self) -> None:
        server = EchoServer(host="127.0.0.1", port=5555)
        assert server.address == ("127.0.0.1", 5555)

    def test_server_start_and_stop(self, event_loop: asyncio.AbstractEventLoop) -> None:
        server = EchoServer(host="127.0.0.1", port=0)

        async def _run() -> None:
            await server.start()
            assert server._tcp_server is not None
            await server.stop()

        event_loop.run_until_complete(_run())


class TestChannelProperties:
    """Test Channel without a server reference."""

    def test_server_property_raises_without_server(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        async def _run() -> None:
            reader = asyncio.StreamReader()
            # Create a mock writer via a connected socket pair.
            server_started = asyncio.Event()
            writer_ref: list[asyncio.StreamWriter] = []

            async def on_connect(
                _reader: asyncio.StreamReader, writer: asyncio.StreamWriter
            ) -> None:
                writer_ref.append(writer)
                server_started.set()

            srv = await asyncio.start_server(on_connect, "127.0.0.1", 0)
            addr = srv.sockets[0].getsockname()

            _, client_writer = await asyncio.open_connection(addr[0], addr[1])
            await server_started.wait()

            channel = EchoChannel(reader, client_writer)
            with pytest.raises(RuntimeError, match="not connected to a server"):
                _ = channel.server

            client_writer.close()
            await client_writer.wait_closed()
            for w in writer_ref:
                w.close()
            srv.close()
            await srv.wait_closed()

        event_loop.run_until_complete(_run())


class TestClientServerRoundtrip:
    """Test full client-server message exchange."""

    def test_echo_roundtrip(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """Start a server, connect a client, send a message, verify reply."""
        received: list[dict] = []

        async def _run() -> None:
            server = EchoServer(host="127.0.0.1", port=0)
            await server.start()
            assert server._tcp_server is not None
            addr = server._tcp_server.sockets[0].getsockname()

            reader, writer = await asyncio.open_connection(addr[0], addr[1])

            from repod.protocol import encode, read_message

            # Read the initial "connected" message from the server.
            buffer = b""
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                buffer += data
                msg, consumed = read_message(buffer)
                if msg is not None:
                    buffer = buffer[consumed:]
                    received.append(msg)
                    break

            assert received[0]["action"] == "connected"

            # Send an echo request.
            writer.write(encode({"action": "echo", "text": "hello"}))
            await writer.drain()

            # Read the echo reply.
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                buffer += data
                msg, consumed = read_message(buffer)
                if msg is not None:
                    buffer = buffer[consumed:]
                    received.append(msg)
                    break

            assert received[1]["action"] == "echo_reply"
            assert received[1]["text"] == "hello"

            writer.close()
            await writer.wait_closed()
            await server.stop()

        event_loop.run_until_complete(_run())

    def test_multiple_clients(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """Test that multiple clients can connect and communicate."""

        async def _run() -> None:
            server = EchoServer(host="127.0.0.1", port=0)
            await server.start()
            assert server._tcp_server is not None
            addr = server._tcp_server.sockets[0].getsockname()

            from repod.protocol import read_message

            clients = []
            for _ in range(3):
                reader, writer = await asyncio.open_connection(addr[0], addr[1])
                clients.append((reader, writer))

                # Read the initial "connected" message.
                buffer = b""
                while True:
                    data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                    buffer += data
                    msg, _consumed = read_message(buffer)
                    if msg is not None:
                        break

            # Give the server a moment to register all channels.
            await asyncio.sleep(0.05)
            assert len(server.channels) == 3

            for _reader, writer in clients:
                writer.close()
                await writer.wait_closed()

            await server.stop()

        event_loop.run_until_complete(_run())
