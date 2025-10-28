# Shared Macros - JSON Single Source of Truth

## Overview

FunHouse now uses **shared/macros.json** as its source for macro definitions. This is the **same file** used by MacroPad.

## Benefits

✅ **Single source**: Edit one JSON file shared with MacroPad
✅ **Auto-sync**: Keycodes automatically match between devices
✅ **Easy editing**: JSON is human-readable
✅ **Version control**: Track changes in git

## File Location

Master copy: **shared/macros.json**

Deploy to device: **CIRCUITPY/macros.json**

```bash
cp shared/macros.json /path/to/FUNHOUSE_CIRCUITPY/macros.json
```

## How FunHouse Uses JSON

1. Reads `macros.json` at startup
2. Loads `macros_loader.py` helper module
3. Extracts all commands (ignores app structure)
4. Creates command→keycodes dictionary
5. When AdafruitIO receives command, looks up keycodes
6. Sends keycodes via HID

## JSON Structure for FunHouse

FunHouse uses the `command` field to identify macros:

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

- **command**: What you send to AdafruitIO feed (e.g., "play_pause")
- **keycodes**: HID keys to send when command received
- **label**, **color**: Used by MacroPad (FunHouse ignores)

## Required Files

FunHouse needs these files to use JSON macros:

1. `code.py` - Main program (use code_refactored.py, modified for JSON)
2. `macros.json` - Macro definitions (from shared/)
3. `macros_loader.py` - JSON parser (from shared/)
4. `settings.toml` - WiFi/AdafruitIO credentials
5. Libraries - See LIBRARIES.md

## Sending Commands

Send commands to AdafruitIO feed using the `command` value:

```bash
curl -X POST \
  -H "X-AIO-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"play_pause"}' \
  "https://io.adafruit.com/api/v2/YOUR_USERNAME/feeds/macros/data"
```

The command name must match exactly (case-sensitive).

## Adding New Commands

1. Edit `shared/macros.json` in repository
2. Add button with unique `command` name
3. Deploy to device: `cp shared/macros.json /path/to/CIRCUITPY/macros.json`
4. Restart FunHouse
5. Send command name to AdafruitIO feed

## Keeping in Sync with MacroPad

Both devices use the same JSON file. The keycodes will automatically match because they come from the same source.

MacroPad uses the app/page structure for organization, FunHouse just extracts commands.

## Rollback

If you need to go back to the old `macros.py` approach:

```bash
git checkout v1.0-working
```
