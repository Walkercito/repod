# Installation

## With pip

```bash
pip install repodnet
```

## With uv

```bash
uv add repodnet
```

!!! note
    The PyPI package name is `repodnet`, but the import is `repod`:

    ```python
    from repod import Server, Channel, ConnectionListener
    ```

## Requirements

- **Python 3.12+**
- Only dependency: [msgpack](https://msgpack.org/)
