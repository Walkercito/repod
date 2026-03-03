# Wire format

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
