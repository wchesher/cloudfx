# CloudFX Deployment Guide - JSON Macros

## Single Source of Truth

Both MacroPad and FunHouse now use **shared/macros.json** as the single source of truth for macro definitions.

## Files to Deploy

### To MacroPad
Copy these files from repository to CIRCUITPY drive:
```bash
# Required files
cp macropad/code.py /path/to/MACROPAD_CIRCUITPY/code.py
cp shared/macros.json /path/to/MACROPAD_CIRCUITPY/macros.json
cp shared/macros_loader.py /path/to/MACROPAD_CIRCUITPY/macros_loader.py

# Libraries (from CircuitPython 10.x Bundle)
# See macropad/LIBRARIES.md for complete list
```

### To FunHouse
Copy these files from repository to CIRCUITPY drive:
```bash
# Required files
cp funhouse/code_refactored.py /path/to/FUNHOUSE_CIRCUITPY/code.py
cp shared/macros.json /path/to/FUNHOUSE_CIRCUITPY/macros.json
cp shared/macros_loader.py /path/to/FUNHOUSE_CIRCUITPY/macros_loader.py

# Create settings.toml from template
cp funhouse/settings.toml.example /path/to/FUNHOUSE_CIRCUITPY/settings.toml
# Edit settings.toml with your WiFi and AdafruitIO credentials

# Libraries (from CircuitPython 10.x Bundle)
# See funhouse/LIBRARIES.md for complete list
```

## JSON Structure

The `macros.json` file contains:
- **apps**: Array of MacroPad pages (e.g., "Media Controls", "Recording")
- **buttons**: Each app has buttons with:
  - `label`: Display text (5 chars max for MacroPad)
  - `command`: Unique identifier for FunHouse
  - `color`: Hex RGB (e.g., "0xFF0000" for red)
  - `keycodes`: Array of keycode names (e.g., ["CONTROL", "A"])

Example:
```json
{
  "apps": [
    {
      "name": "Media Controls",
      "buttons": [
        {
          "label": "Play",
          "command": "play_pause",
          "color": "0xFF0000",
          "keycodes": ["CONTROL", "KEYPAD_PERIOD"]
        }
      ]
    }
  ]
}
```

## How It Works

### MacroPad
1. Loads `macros.json`
2. Creates "pages" from each app
3. Displays 12 buttons per page
4. Rotate encoder to switch between pages
5. Press button to send keycodes

### FunHouse
1. Loads `macros.json`
2. Extracts all commands (ignores app structure)
3. Listens to AdafruitIO feed
4. When command received, looks up keycodes by command name
5. Sends keycodes via HID

## Adding New Macros

1. **Edit** `shared/macros.json`
2. **Deploy** to both devices:
   ```bash
   cp shared/macros.json /path/to/MACROPAD_CIRCUITPY/macros.json
   cp shared/macros.json /path/to/FUNHOUSE_CIRCUITPY/macros.json
   ```
3. **Restart** both devices (they read JSON at startup)

## Advantages

✅ **Single source**: Edit one JSON file, deploy to both
✅ **No manual sync**: Keycodes automatically match
✅ **Easy editing**: JSON is human-readable
✅ **Version control**: Track changes in git
✅ **MacroPad pages**: Supports multiple apps/pages
✅ **FunHouse commands**: Extracts all commands automatically

## Troubleshooting

**"ERROR: Could not load macros from macros.json"**
- Verify `macros.json` exists on device
- Check JSON syntax (use validator like jsonlint.com)
- View serial console for detailed error

**"ERROR: macros_loader.py not found!"**
- Copy `shared/macros_loader.py` to device root
- Both devices need this file

**"WARNING: Unknown keycode 'XXX'"**
- Check keycode name matches adafruit_hid.keycode
- Common keycodes: CONTROL, ALT, SHIFT, GUI, A-Z, F1-F12, etc.
- See [Keycode reference](https://docs.circuitpython.org/projects/hid/en/latest/api.html#adafruit-hid-keycode-keycode)

## Rollback

If JSON approach has issues, rollback to the working version:

```bash
git checkout v1.0-working
```

This restores the previous version where:
- FunHouse used `macros.py`
- MacroPad used `/macros/*.py` app files
