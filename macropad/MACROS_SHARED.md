# Shared HID Macro Definitions

**NOTE**: This documentation explains the relationship between MacroPad and FunHouse HID codes.

## MacroPad Does NOT Use macros.py

The MacroPad code **does not** import `macros.py`. Instead, it loads "macro apps" from `/macros/*.py` files with a different structure (see [README.md](README.md)).

MacroPad macro apps look like this:
```python
from adafruit_hid.keycode import Keycode

app = {
    "name": "My App",
    "macros": [
        (0xFF0000, "Label", [Keycode.CONTROL, Keycode.KEYPAD_PERIOD]),
        # ...
    ]
}
```

## FunHouse DOES Use macros.py

The FunHouse code **requires** `macros.py` (it imports: `from macros import Macros`).

## Master Copy Location

The master HID macro definitions are located at:
```
/shared/macros.py
```

This file is specifically for **FunHouse deployment**:

```bash
# From repository root
cp shared/macros.py /path/to/FUNHOUSE_CIRCUITPY/macros.py
```

## Why Keep Them in Sync?

Both devices send HID keystrokes to the same AutoHotKey script. For consistent behavior:

- FunHouse commands (in `shared/macros.py`) should use the same keycodes as
- MacroPad buttons (in `/macros/*.py` app files)

**Example**: If both devices have a "play_pause" command, both should send `CTRL+KEYPAD_PERIOD`.

## Synchronization Strategy

When adding a new command:

1. **Define in FunHouse**: Edit `shared/macros.py`
   ```python
   {"label": "my_cmd", "keycodes": [Keycode.CONTROL, Keycode.X]}
   ```

2. **Deploy to FunHouse**: `cp shared/macros.py /path/to/FUNHOUSE_CIRCUITPY/macros.py`

3. **Add to MacroPad**: Edit `/macros/your_app.py`
   ```python
   (0xFF0000, "My Cmd", [Keycode.CONTROL, Keycode.X])
   ```

4. **Deploy to MacroPad**: Copy the app file to device

The keycodes must match, but the file formats are different!
