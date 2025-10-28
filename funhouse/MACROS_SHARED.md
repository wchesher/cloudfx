# Shared HID Macro Definitions

**CRITICAL**: FunHouse **requires** `macros.py` for operation.

## Master Copy Location

The master copy is located at:
```
/shared/macros.py
```

## Deployment

When deploying to your FunHouse device, **always** copy the master file:

```bash
# From repository root
cp shared/macros.py /path/to/FUNHOUSE_CIRCUITPY/macros.py
```

## Why Shared?

Both FunHouse and MacroPad send HID keystrokes to the same AutoHotKey script or application. For consistent behavior, **the keycodes must match**.

However, the two devices use **different file formats**:

- **FunHouse**: Uses `shared/macros.py` with `Macros` class
- **MacroPad**: Uses `/macros/*.py` app files with different structure

See `../macropad/MACROS_SHARED.md` for details on keeping them synchronized.

## DO NOT Edit On Device

**NEVER** edit macros.py directly on the FunHouse device. Always:

1. Edit `shared/macros.py` in the repository
2. Copy to FunHouse: `cp shared/macros.py /path/to/FUNHOUSE_CIRCUITPY/macros.py`
3. Update MacroPad apps if needed (different file format)
4. Test on both devices

## File Format

FunHouse's `macros.py` uses this structure:

```python
from adafruit_hid.keycode import Keycode

class Macros:
    macros = [
        {
            "label": "command_name",  # Sent via AdafruitIO
            "keycodes": [Keycode.CONTROL, Keycode.X]
        },
        # ...
    ]
```

The `label` matches AdafruitIO feed values. The `keycodes` define what HID keys to send.

## Synchronization with MacroPad

When adding a command that both devices should support:

1. **Add to FunHouse** (`shared/macros.py`):
   ```python
   {"label": "my_command", "keycodes": [Keycode.CONTROL, Keycode.X]}
   ```

2. **Add to MacroPad** (e.g., `/macros/app_name.py`):
   ```python
   (0xFF0000, "My Cmd", [Keycode.CONTROL, Keycode.X])
   ```

The keycodes must be identical for consistent behavior!
