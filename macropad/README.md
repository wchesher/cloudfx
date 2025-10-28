# MacroPad - CloudFX Sound Controller

CircuitPython-based sound effect controller for the Adafruit MacroPad RP2040.

## Hardware Requirements

- **Adafruit MacroPad RP2040**
- **CircuitPython 10.0.3** (or any 10.x version)
- USB-C cable for power and HID communication

## Installation

### 1. Install CircuitPython 10.0.3

1. Download CircuitPython 10.0.3 for MacroPad from [circuitpython.org](https://circuitpython.org/board/adafruit_macropad_rp2040/)
2. Put MacroPad into bootloader mode (hold BOOTSEL while plugging in)
3. Drag the `.uf2` file to the `RPI-RP2` drive
4. MacroPad will reboot and appear as `CIRCUITPY`

### 2. Install Required Libraries

1. Download the [CircuitPython 10.x Library Bundle](https://circuitpython.org/libraries)
2. Extract the bundle
3. Copy these folders from `lib/` in the bundle to `CIRCUITPY/lib/` on your MacroPad:
   - `adafruit_macropad/`
   - `adafruit_hid/`
   - `adafruit_display_text/`
   - `adafruit_display_shapes/`
   - `adafruit_debouncer.mpy`
   - `adafruit_simple_text_display.mpy`
   - `neopixel.mpy`

### 3. Install the Code

1. Copy `code.py` to the root of your MacroPad's `CIRCUITPY` drive
2. Create a `/macros` folder on the `CIRCUITPY` drive
3. Add your macro app files to `/macros/` (see below)
4. Optionally, create a `/sounds` folder for audio files

### 4. Create Macro Apps

Create `.py` files in the `/macros` folder. Each file should define an `app` dictionary:

```python
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control_code import ConsumerControlCode

app = {
    "name": "My App",
    "macros": [
        # (LED Color, Label, Actions)
        (0xFF0000, "Sound1", [{"play": "/sounds/effect1.wav"}]),
        (0x00FF00, "Sound2", [{"play": "/sounds/effect2.wav"}]),
        (0x0000FF, "Type", ["Hello World", Keycode.ENTER]),
        (0xFF00FF, "Media", [[ConsumerControlCode.PLAY_PAUSE]]),
        # ... up to 12 macros per app
    ]
}
```

## Features

### Multi-App Support
- Load multiple macro sets from `/macros/*.py`
- Navigate between apps using the rotary encoder
- Each app can have up to 12 macros (one per key)

### Action Types

Macros support various action types:

1. **Keycode Press/Release**: `Keycode.A`, `-Keycode.A` (release)
2. **Delays**: `0.5` (float = seconds)
3. **Text Input**: `"Hello World"`
4. **Consumer Control**: `[ConsumerControlCode.VOLUME_UP]`
5. **Mouse Actions**: `{"buttons": Mouse.LEFT_BUTTON, "x": 10, "y": 20}`
6. **Tone Generation**: `{"tone": 440}` (Hz), `{"tone": 0}` (stop)
7. **File Playback**: `{"play": "/sounds/effect.wav"}`

### Screensaver
- After 20 seconds of inactivity, LEDs dim and screen blanks
- Any input (key press, encoder turn) wakes the device

### Emergency Stop
- Click the rotary encoder to send `CTRL+KEYPAD_MINUS`
- Use this to stop playback in your host application

## Example Macro App

```python
# /macros/soundfx.py
from adafruit_hid.keycode import Keycode

app = {
    "name": "Sound FX",
    "macros": [
        (0xFF0000, "Applause", [{"play": "/sounds/applause.wav"}]),
        (0x00FF00, "Laugh", [{"play": "/sounds/laugh.wav"}]),
        (0x0000FF, "Crickets", [{"play": "/sounds/crickets.wav"}]),
        (0xFFFF00, "Drumroll", [{"play": "/sounds/drumroll.wav"}]),
        (0xFF00FF, "Airhorn", [{"play": "/sounds/airhorn.wav"}]),
        (0x00FFFF, "Tada", [{"play": "/sounds/tada.wav"}]),
        # Keys 7-12 can be blank or additional effects
    ]
}
```

## File Organization

```
CIRCUITPY/
├── code.py              # Main program
├── lib/                 # Libraries folder
│   ├── adafruit_macropad/
│   ├── adafruit_hid/
│   └── ...
├── macros/              # Macro app definitions
│   ├── soundfx.py
│   ├── shortcuts.py
│   └── ...
└── sounds/              # Audio files (WAV recommended)
    ├── applause.wav
    ├── laugh.wav
    └── ...
```

## Troubleshooting

### "NO MACROS" on Display
- Ensure `/macros/` folder exists
- Verify `.py` files contain valid `app` dictionary
- Check serial console for error messages

### Keys Not Working
- Check CircuitPython version (must be 10.x)
- Verify all required libraries are installed
- Check serial console for import errors

### Sound Files Not Playing
- Use WAV format (8-16 bit, mono/stereo, ≤48kHz)
- Keep files small (RP2040 has limited RAM)
- Verify file paths are correct (case-sensitive)

### Version Check
Connect to serial console to see startup messages:
```
MacroPad initialized successfully
Loaded macro app: Sound FX
Loaded macro app: Shortcuts
Successfully loaded 2 macro app(s)
Active app: Sound FX
MacroFX ready. Starting main loop...
```

## CircuitPython 10.0.3 Migration Notes

This code has been updated from CircuitPython 9.x with the following changes:

- Added version checking on startup
- Updated exception handling to use `traceback.print_exception()`
- Verified compatibility with CP 10.x displayio APIs
- Enhanced error messages and logging
- Tested with CircuitPython Bundle 10.x libraries

## Credits

- Original code: Phillip Burgess (Adafruit Industries)
- CloudFX modifications: William C. Chesher
- License: MIT
