# CloudFX

A dual-device production control system using Adafruit CircuitPython hardware for live sound effects and remote command execution.

![CircuitPython](https://img.shields.io/badge/CircuitPython-10.0.3-blueviolet.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Overview

CloudFX is a complete production control system consisting of two independent CircuitPython devices:

- **MacroPad**: Physical button interface for triggering sound effects and keyboard macros
- **FunHouse**: Network-connected device that listens to AdafruitIO for remote commands

Both devices act as USB HID keyboards, allowing them to send keyboard shortcuts to any connected computer without special drivers or software.

## Project Structure

```
cloudfx/
├── macropad/              # MacroPad RP2040 code
│   ├── code.py           # Main program
│   ├── lib/              # CircuitPython libraries
│   ├── sounds/           # WAV/MP3 audio files
│   ├── requirements.txt  # Library dependencies
│   └── README.md         # Setup instructions
│
├── funhouse/             # FunHouse ESP32-S2 code
│   ├── code.py           # Main program
│   ├── macros.py         # Macro definitions
│   ├── secrets.py.example # Credentials template
│   ├── lib/              # CircuitPython libraries
│   ├── fonts/            # Display fonts (optional)
│   ├── requirements.txt  # Library dependencies
│   └── README.md         # Setup instructions
│
├── macros/               # Example macro apps for MacroPad
│   └── example_soundfx.py
│
├── helper-app/           # Third-party helper applications
│   └── README.md         # Documentation for helper apps
│
├── shared/               # Shared code/configs (if any)
│
├── docs/                 # Additional documentation
│   ├── architecture.md   # System architecture
│   ├── setup.md          # Complete setup guide
│   └── migration.md      # CP 10.0.3 migration notes
│
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Hardware Requirements

### MacroPad
- Adafruit MacroPad RP2040
- CircuitPython 10.0.3+
- USB-C cable

### FunHouse
- Adafruit FunHouse ESP32-S2
- CircuitPython 10.0.3+
- WiFi network access
- USB-C cable
- **IMPORTANT**: Requires TinyUF2 bootloader 0.33.0+ for CP 10.x

## Quick Start

### 1. Install CircuitPython 10.0.3

Download and install CircuitPython 10.0.3 on both devices:
- [MacroPad downloads](https://circuitpython.org/board/adafruit_macropad_rp2040/)
- [FunHouse downloads](https://circuitpython.org/board/adafruit_funhouse/)

**ESP32-S2 users**: Update TinyUF2 bootloader first! See [FunHouse README](funhouse/README.md).

### 2. Install Libraries

Download the [CircuitPython 10.x Library Bundle](https://circuitpython.org/libraries) and install required libraries on each device.

See device-specific README files for detailed library lists:
- [MacroPad requirements](macropad/requirements.txt)
- [FunHouse requirements](funhouse/requirements.txt)

### 3. Deploy Code

#### MacroPad
1. Copy `macropad/code.py` to `CIRCUITPY` drive
2. Copy library folders to `CIRCUITPY/lib/`
3. Create `/macros` folder and add macro definition files
4. Add sound files to `/sounds` folder (optional)

#### FunHouse
1. Copy `funhouse/code.py` to `CIRCUITPY` drive
2. Copy `funhouse/macros.py` to `CIRCUITPY` drive
3. Copy `funhouse/secrets.py.example` to `CIRCUITPY/secrets.py` and edit
4. Copy library folders to `CIRCUITPY/lib/`
5. Create `/fonts` folder and add fonts (optional)

### 4. Configure

**MacroPad**: Create macro apps in `/macros/*.py` (see [example](macros/example_soundfx.py))

**FunHouse**: Edit `secrets.py` with WiFi and AdafruitIO credentials

## Features

### MacroPad Features
- 12 programmable keys with RGB LEDs
- Multiple "pages" of macros via rotary encoder
- Sound file playback (WAV/MP3)
- HID keyboard, mouse, and consumer control
- Screensaver after inactivity
- Emergency stop via encoder button
- Completely standalone operation

### FunHouse Features
- Network-connected command listener
- AdafruitIO integration for remote control
- USB HID keyboard output
- Visual feedback on built-in display
- Command queuing system
- Automatic feed cleanup
- WiFi reconnection handling
- Static or DHCP IP configuration

## Use Cases

### Live Production
- **MacroPad**: Sound effects board for live shows
- **FunHouse**: Remote control from production booth via AdafruitIO

### Content Creation
- **MacroPad**: Quick access to audio clips and keyboard shortcuts
- **FunHouse**: Scene switching triggered by automation/IFTTT

### Streaming
- **MacroPad**: Instant sound effects and scene changes
- **FunHouse**: Control from phone/tablet via AdafruitIO dashboard

### Education
- Both devices demonstrate:
  - CircuitPython programming
  - USB HID protocols
  - Network programming (FunHouse)
  - Audio playback (MacroPad)
  - Display programming

## Architecture

```
┌─────────────────┐                    ┌──────────────────┐
│    MacroPad     │                    │    FunHouse      │
│   (RP2040)      │                    │   (ESP32-S2)     │
│                 │                    │                  │
│  ┌───────────┐  │                    │  ┌────────────┐  │
│  │ Physical  │  │                    │  │ AdafruitIO │  │
│  │  Buttons  │  │                    │  │  Listener  │  │
│  └─────┬─────┘  │                    │  └──────┬─────┘  │
│        │        │                    │         │        │
│  ┌─────▼─────┐  │                    │  ┌──────▼─────┐  │
│  │   Audio   │  │                    │  │    WiFi    │  │
│  │ Playback  │  │                    │  └──────┬─────┘  │
│  └───────────┘  │                    │         │        │
│        │        │                    │  ┌──────▼─────┐  │
│  ┌─────▼─────┐  │                    │  │ HID Output │  │
│  │HID Output │  │                    │  └──────┬─────┘  │
│  └─────┬─────┘  │                    │         │        │
└────────┼────────┘                    └─────────┼────────┘
         │                                       │
         │         USB                           │  USB
         └───────────────────┬───────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │   Host Computer    │
                   │  (macOS/Win/Linux) │
                   └────────────────────┘
```

Both devices send USB HID commands independently to the host computer. They don't communicate directly with each other.

## Documentation

- [MacroPad Setup Guide](macropad/README.md)
- [FunHouse Setup Guide](funhouse/README.md)
- [System Architecture](docs/architecture.md)
- [Complete Setup Guide](docs/setup.md)
- [CircuitPython 10.0.3 Migration Guide](docs/migration.md)

## CircuitPython 10.0.3 Compatibility

This project has been fully updated for CircuitPython 10.0.3:

✅ Updated exception handling (`traceback.print_exception`)
✅ Version checking on startup
✅ Compatible with CP 10.x Library Bundle
✅ ESP32-S2 bootloader requirements documented
✅ Enhanced error handling and logging

See [migration.md](docs/migration.md) for detailed changes from CP 9.x.

## Development

### Adding Macro Apps (MacroPad)

Create a new `.py` file in `/macros/`:

```python
from adafruit_hid.keycode import Keycode

app = {
    "name": "My App",
    "macros": [
        (0xFF0000, "Label", [Keycode.CONTROL, Keycode.C]),
        # ... up to 12 macros
    ]
}
```

### Adding Commands (FunHouse)

Edit `macros.py` and add entries:

```python
{
    "label": "my_command",
    "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.T]
}
```

Then send `"my_command"` to your AdafruitIO `macros` feed.

## Troubleshooting

### MacroPad
- **"NO MACROS"**: Check `/macros` folder exists with valid `.py` files
- **No sound**: Verify audio files are in `/sounds` and are valid WAV files
- **Keys not working**: Check USB connection and HID library installation

### FunHouse
- **WiFi not connecting**: Verify credentials, use 2.4GHz network only
- **Commands not executing**: Check AdafruitIO feed name is exactly `macros`
- **Bootloader error**: Update to TinyUF2 0.33.0+ for CP 10.x support

See device-specific READMEs for detailed troubleshooting.

## Contributing

This is a personal project, but feel free to fork and adapt for your needs!

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

- **MacroPad base code**: Phillip Burgess (Adafruit Industries)
- **CloudFX modifications**: William C. Chesher
- **CircuitPython**: Adafruit Industries and contributors

## Acknowledgments

- Adafruit Industries for excellent hardware and CircuitPython
- CircuitPython community for libraries and support
- AdafruitIO for reliable IoT infrastructure

---

**Note**: This project requires CircuitPython 10.0.3 or later. Earlier versions are not supported.
