# FunHouse - CloudFX Network Command Listener

CircuitPython-based network command listener for the Adafruit FunHouse ESP32-S2.

## Hardware Requirements

- **Adafruit FunHouse ESP32-S2**
- **CircuitPython 10.0.3** (or any 10.x version)
- WiFi network access
- USB-C cable for power and HID communication

## Overview

The FunHouse acts as a network-connected USB HID keyboard that:
1. Connects to your WiFi network
2. Polls an AdafruitIO feed for commands every 15 seconds
3. Translates received commands into HID keyboard sequences
4. Sends those sequences to the connected host computer
5. Displays the current command on its built-in screen

This allows you to trigger keyboard shortcuts remotely via AdafruitIO!

## Installation

### 1. Install CircuitPython 10.0.3

**IMPORTANT**: ESP32-S2 boards require a bootloader update for CircuitPython 10.x!

1. Update TinyUF2 bootloader to version 0.33.0 or later
   - Download from [TinyUF2 Releases](https://github.com/adafruit/tinyuf2/releases)
   - Follow Adafruit's bootloader update guide
2. Download CircuitPython 10.0.3 for FunHouse from [circuitpython.org](https://circuitpython.org/board/adafruit_funhouse/)
3. Put FunHouse into bootloader mode (double-tap reset button)
4. Drag the `.uf2` file to the `FTHBOOT` drive
5. FunHouse will reboot and appear as `CIRCUITPY`

### 2. Install Required Libraries

1. Download the [CircuitPython 10.x Library Bundle](https://circuitpython.org/libraries)
2. Extract the bundle
3. Copy these files/folders from `lib/` in the bundle to `CIRCUITPY/lib/` on your FunHouse:
   - `adafruit_requests.mpy`
   - `adafruit_hid/` (folder)
   - `adafruit_display_text/` (folder)
   - `adafruit_bitmap_font/` (folder)
   - `adafruit_debouncer.mpy`

### 3. Install the Code

1. Copy these files to the root of your FunHouse's `CIRCUITPY` drive:
   - `code.py` - Main program
   - `macros.py` - Macro definitions
   - Copy `settings.toml.example` to `settings.toml` and edit with your credentials

### 4. (Optional) Install Font

For better display text, install the LemonMilk font:
1. Create a `/fonts` folder on `CIRCUITPY`
2. Copy `LemonMilk-10.pcf` to `/fonts/`
3. If you don't have this font, the code will fall back to the built-in font

### 5. Configure Credentials

Create `settings.toml` on your FunHouse from the example file:

```toml
# settings.toml
CIRCUITPY_WIFI_SSID = "YourWiFiSSID"
CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
AIO_USERNAME = "your_aio_username"
AIO_KEY = "your_aio_key"
```

Get your AdafruitIO credentials from [io.adafruit.com](https://io.adafruit.com/) (click "My Key").

### 6. Create AdafruitIO Feed

1. Go to [io.adafruit.com](https://io.adafruit.com/)
2. Click "Feeds" → "New Feed"
3. Create a feed named **`macros`** (must be exactly this name)
4. This is where you'll send commands

## Configuration

### WiFi Setup

**DHCP (Automatic IP):**
```toml
# settings.toml
CIRCUITPY_WIFI_SSID = "YourNetwork"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
AIO_USERNAME = "username"
AIO_KEY = "key"
```

**Static IP:**
```toml
# settings.toml
CIRCUITPY_WIFI_SSID = "YourNetwork"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
STATIC_IP = "192.168.1.100"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"
AIO_USERNAME = "username"
AIO_KEY = "key"
```

### Macro Definitions

Edit `macros.py` to define your commands:

```python
from adafruit_hid.keycode import Keycode

class Macros:
    macros = [
        {
            "label": "my_command",  # Command name (sent to AdafruitIO)
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.T]
        },
        {
            "label": "another_command",
            "keycodes": [Keycode.GUI, Keycode.D]
        },
        # Add more macros...
    ]
```

The `label` must **exactly match** the value you send to the AdafruitIO feed.

## Usage

### Sending Commands

There are several ways to send commands to your FunHouse:

#### 1. AdafruitIO Dashboard

1. Create a Button or Text Block widget
2. Connect it to your `macros` feed
3. Set the button to send the command label (e.g., "play_pause")

#### 2. HTTP API (cURL)

```bash
curl -X POST \
  -H "X-AIO-Key: YOUR_AIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"play_pause"}' \
  "https://io.adafruit.com/api/v2/YOUR_USERNAME/feeds/macros/data"
```

#### 3. Python Script

```python
import requests

AIO_USERNAME = "your_username"
AIO_KEY = "your_key"
FEED = "macros"

def send_command(command):
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED}/data"
    headers = {"X-AIO-Key": AIO_KEY}
    data = {"value": command}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

send_command("play_pause")
```

#### 4. IFTTT Integration

Create IFTTT applets that send commands to your AdafruitIO feed, allowing voice control, time-based triggers, etc.

### Example Workflow

1. FunHouse connects to WiFi and AdafruitIO
2. You send "play_pause" to the `macros` feed via HTTP API
3. FunHouse polls the feed, sees the command
4. FunHouse looks up "play_pause" in `macros.py`
5. FunHouse sends `CTRL+KEYPAD_PERIOD` to the host computer
6. Your media player responds to the keyboard shortcut
7. FunHouse displays "play_pause" on screen for 5 seconds

## Troubleshooting

### Connection Issues

**WiFi not connecting:**
- Check SSID and password in `settings.toml`
- Verify 2.4GHz WiFi (ESP32-S2 doesn't support 5GHz)
- Check serial console for error messages

**AdafruitIO connection failing:**
- Verify `AIO_USERNAME` and `AIO_KEY` are correct in `settings.toml`
- Check that `macros` feed exists
- Test feed access via web browser

### Commands Not Working

**Commands not executed:**
- Check that command label exactly matches macro definition
- Verify HID keyboard initialized (check serial console)
- Ensure host computer recognizes FunHouse as USB keyboard

**Display not updating:**
- Font file may be missing (code will fall back to default)
- Check serial console for display errors

### Serial Console Debugging

Connect to the FunHouse serial console to see detailed logs:

```
CircuitPython 10.0.3
MacroPad initialized successfully
Loaded 15 macro(s) from macros.py
USB HID keyboard initialized
Display initialized
CloudFX FunHouse starting...
Initializing WiFi connection...
Connected! IP: 192.168.1.100
Listening for commands...
```

### Common Errors

**`ImportError: no module named 'adafruit_requests'`**
- Install `adafruit_requests.mpy` from CircuitPython Bundle

**Settings not loading:**
- Create `settings.toml` from `settings.toml.example`
- Verify all required fields are filled in
- Check for syntax errors (no quotes around values in TOML)

**`ERROR: macros.py not found!`**
- Copy `macros.py` to the FunHouse root directory

## File Organization

```
CIRCUITPY/
├── code.py              # Main program
├── settings.toml        # WiFi and AdafruitIO credentials (DO NOT COMMIT)
├── macros.py            # Macro definitions
├── lib/                 # Libraries folder
│   ├── adafruit_requests.mpy
│   ├── adafruit_hid/
│   ├── adafruit_display_text/
│   └── adafruit_bitmap_font/
└── fonts/               # Optional fonts folder
    └── LemonMilk-10.pcf
```

## Configuration Constants

You can adjust these in `code.py`:

```python
QUEUE_SIZE = 50              # Max queued commands
CLEAR_DELAY = 5              # Seconds before clearing display
LISTENING_INTERVAL = 15      # Seconds between feed polls
RETRY_LIMIT = 3              # Connection retry attempts
RETRY_DELAY = 2              # Seconds between retries
```

## CircuitPython 10.0.3 Migration Notes

This code has been updated from CircuitPython 9.x with the following changes:

- **ESP32-S2 bootloader requirement**: Must use TinyUF2 0.33.0+ for CP 10.x
- Updated exception handling to use `traceback.print_exception()`
- Added version checking on startup
- Enhanced error messages and logging throughout
- Proper WiFi radio API usage for CP 10.x
- Better memory management with explicit `gc.collect()`
- Improved response closing to prevent memory leaks

## Architecture Notes

The FunHouse operates independently from the MacroPad:
- **FunHouse**: Network-connected HID device listening to AdafruitIO
- **MacroPad**: Physical button HID device with local sound playback
- Both send USB HID commands to the same (or different) host computers
- They don't communicate directly with each other

This architecture allows flexible deployment:
- Use FunHouse alone for remote control
- Use MacroPad alone for local sound effects
- Use both together for a complete production system

## Credits

- CloudFX modifications: William C. Chesher
- License: MIT

## Security Notes

- **Never commit `settings.toml`** to version control
- AdafruitIO keys should be kept secret
- Consider using feed-specific keys (not account keys) when possible
- WiFi passwords are stored in plain text - secure physical access to the device
- `settings.toml` is automatically excluded from git via `.gitignore`
