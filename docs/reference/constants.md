# Constants

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
