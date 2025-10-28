# Shared Macros - JSON Single Source of Truth

## Overview

MacroPad now uses **shared/macros.json** as its source for macro definitions. This is the **same file** used by FunHouse.

## Benefits

✅ **Single source**: Edit one JSON file, not multiple Python files
✅ **Auto-sync**: Keycodes automatically match between devices
✅ **Pages preserved**: Still supports multiple apps (pages) via encoder
✅ **Easy editing**: JSON is more readable than Python tuples

## File Location

Master copy: **shared/macros.json**

Deploy to device: **CIRCUITPY/macros.json**

```bash
cp shared/macros.json /path/to/MACROPAD_CIRCUITPY/macros.json
```

## How MacroPad Uses JSON

1. Reads `macros.json` at startup
2. Loads `macros_loader.py` helper module
3. Converts JSON to internal app structure
4. Creates one "page" per app
5. Rotate encoder to switch pages

## JSON Structure for MacroPad

Each app becomes a page:

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

- **name**: Page title shown at top of display
- **buttons**: Up to 12 buttons (one per key)
- **label**: Button text (5 chars max for visibility)
- **color**: LED color in hex (0xRRGGBB)
- **keycodes**: Key sequence to send when pressed

## Required Files

MacroPad needs these files to use JSON macros:

1. `code.py` - Main program (modified to load JSON)
2. `macros.json` - Macro definitions (from shared/)
3. `macros_loader.py` - JSON parser (from shared/)
4. Libraries - See LIBRARIES.md

## Adding New Pages/Buttons

1. Edit `shared/macros.json` in repository
2. Add new app or buttons
3. Deploy to device: `cp shared/macros.json /path/to/CIRCUITPY/macros.json`
4. Restart MacroPad

## Keeping in Sync with FunHouse

Both devices use the same JSON file. The keycodes will automatically match because they come from the same source.

FunHouse ignores the app/page structure and just extracts commands by their `command` field.

## Rollback

If you need to go back to the old `/macros/*.py` approach:

```bash
git checkout v1.0-working
```
