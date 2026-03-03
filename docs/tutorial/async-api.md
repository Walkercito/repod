# Async API

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

!!! tip
    Most games won't need this. `launch()` is the recommended way to start a server.
