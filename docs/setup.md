# CloudFX Complete Setup Guide

This guide walks you through setting up both devices from scratch.

## Prerequisites

- Computer with USB ports (macOS, Windows, or Linux)
- WiFi network (2.4GHz) for FunHouse
- AdafruitIO account (free tier works)
- Text editor for editing Python files
- Web browser

## Part 1: MacroPad Setup

### Step 1: Install CircuitPython 10.0.3

1. **Download firmware**
   - Go to [circuitpython.org/board/adafruit_macropad_rp2040](https://circuitpython.org/board/adafruit_macropad_rp2040/)
   - Download the latest 10.x version (10.0.3 or newer)

2. **Enter bootloader mode**
   - Hold down the **BOOTSEL** button on the back
   - While holding, plug in the USB cable
   - Release BOOTSEL
   - A drive called `RPI-RP2` should appear

3. **Flash CircuitPython**
   - Drag the `.uf2` file to the `RPI-RP2` drive
   - Drive will disappear and remount as `CIRCUITPY`
   - You now have CircuitPython installed!

### Step 2: Install Libraries

1. **Download the library bundle**
   - Go to [circuitpython.org/libraries](https://circuitpython.org/libraries)
   - Download "Bundle for Version 10.x"
   - Extract the ZIP file

2. **Copy libraries to MacroPad**
   - On the `CIRCUITPY` drive, create a `lib` folder if it doesn't exist
   - From the extracted bundle, copy these items from `lib/` to `CIRCUITPY/lib/`:
     ```
     adafruit_macropad/          (folder)
     adafruit_hid/               (folder)
     adafruit_display_text/      (folder)
     adafruit_display_shapes/    (folder)
     adafruit_debouncer.mpy      (file)
     adafruit_simple_text_display.mpy (file)
     neopixel.mpy                (file)
     ```

### Step 3: Install Code

1. **Copy main code**
   - Copy `macropad/code.py` from this repo to `CIRCUITPY/code.py`

2. **Create macro folder**
   - On the `CIRCUITPY` drive, create a folder called `macros`

3. **Add example macro app**
   - Copy `macros/example_soundfx.py` from this repo
   - Save it as `CIRCUITPY/macros/myapp.py`
   - Edit it to customize your macros

### Step 4: (Optional) Add Sound Files

1. **Create sounds folder**
   - On the `CIRCUITPY` drive, create a folder called `sounds`

2. **Prepare audio files**
   - Use WAV format (recommended)
   - 16-bit PCM, mono or stereo
   - Sample rate: 22050Hz or 44100Hz
   - Keep files under 1MB each for best performance

3. **Copy sound files**
   - Copy your `.wav` files to `CIRCUITPY/sounds/`
   - Note the exact filenames (case-sensitive!)

4. **Update macros to use sounds**
   ```python
   (0xFF0000, "Sound", [{"play": "/sounds/effect.wav"}])
   ```

### Step 5: Test MacroPad

1. **Check serial console**
   - Use Mu Editor, PuTTY, or screen to connect
   - macOS/Linux: `screen /dev/tty.usbmodem* 115200`
   - Windows: Use PuTTY or Mu Editor

2. **Expected output**
   ```
   CircuitPython 10.0.3
   MacroPad initialized successfully
   Loaded macro app: My App
   Successfully loaded 1 macro app(s)
   Active app: My App
   MacroFX ready. Starting main loop...
   ```

3. **Test features**
   - Press keys - LEDs should flash white, macros execute
   - Turn encoder - switch between macro apps
   - Click encoder - sends emergency stop command
   - Leave idle for 20 seconds - screensaver activates

### Troubleshooting MacroPad

**"NO MACROS" on screen**
- Check `/macros` folder exists
- Verify at least one `.py` file with valid `app` dict
- Check serial console for loading errors

**Keys don't do anything**
- Check USB connection
- Verify HID libraries installed correctly
- Look for errors in serial console

**No sound playback**
- Verify audio files are valid WAV format
- Check file paths are correct (case-sensitive)
- Ensure files aren't too large

## Part 2: FunHouse Setup

### Step 1: Update Bootloader (CRITICAL!)

**ESP32-S2 boards require TinyUF2 0.33.0+ for CircuitPython 10.x**

1. **Check current bootloader version**
   - Put FunHouse in bootloader mode (double-tap reset)
   - Look at `INFO_UF2.TXT` on the `FTHBOOT` drive
   - Check version number

2. **Update if needed**
   - Download TinyUF2 0.33.0+ from [github.com/adafruit/tinyuf2/releases](https://github.com/adafruit/tinyuf2/releases)
   - Find `tinyuf2-adafruit_funhouse-*.uf2`
   - Drag to `FTHBOOT` drive
   - Wait for reboot

### Step 2: Install CircuitPython 10.0.3

1. **Download firmware**
   - Go to [circuitpython.org/board/adafruit_funhouse](https://circuitpython.org/board/adafruit_funhouse/)
   - Download latest 10.x version (10.0.3 or newer)

2. **Enter bootloader mode**
   - Double-tap the **RESET** button
   - Drive called `FTHBOOT` should appear

3. **Flash CircuitPython**
   - Drag the `.uf2` file to `FTHBOOT`
   - Drive will remount as `CIRCUITPY`

### Step 3: Install Libraries

1. **Copy libraries to FunHouse**
   - From the CircuitPython 10.x bundle, copy to `CIRCUITPY/lib/`:
     ```
     adafruit_requests.mpy       (file)
     adafruit_hid/               (folder)
     adafruit_display_text/      (folder)
     adafruit_bitmap_font/       (folder)
     adafruit_debouncer.mpy      (file)
     ```

### Step 4: Configure Credentials

1. **Create AdafruitIO account**
   - Go to [io.adafruit.com](https://io.adafruit.com/)
   - Sign up for free account
   - Click "My Key" in top right
   - Note your username and key

2. **Create AdafruitIO feed**
   - Click "Feeds" → "New Feed"
   - Name: **`macros`** (exactly this!)
   - Description: Command feed for CloudFX
   - Click "Create"

3. **Create settings.toml**
   - Copy `funhouse/settings.toml.example` from this repo
   - Save as `CIRCUITPY/settings.toml` on your FunHouse
   - Edit with your credentials:
     ```toml
     CIRCUITPY_WIFI_SSID = "YourWiFiName"
     CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
     AIO_USERNAME = "your_aio_username"
     AIO_KEY = "your_aio_key"
     ```
   - **IMPORTANT**: Use 2.4GHz WiFi only (ESP32-S2 doesn't support 5GHz)

### Step 5: Install Code

1. **Copy files to FunHouse**
   - Copy `funhouse/code.py` → `CIRCUITPY/code.py`
   - Copy `funhouse/macros.py` → `CIRCUITPY/macros.py`
   - Copy `funhouse/settings.toml` → `CIRCUITPY/settings.toml` (your edited version)

2. **(Optional) Install font**
   - Create `CIRCUITPY/fonts/` folder
   - Copy a `.pcf` font file to this folder
   - Edit `code.py` to set correct `FONT_FILE` path
   - Or skip this - code will use default font

### Step 6: Test FunHouse

1. **Check serial console**
   - Connect to serial (same as MacroPad)
   - Expected output:
     ```
     CircuitPython 10.0.3
     Loaded 15 macro(s) from macros.py
     USB HID keyboard initialized
     Display initialized
     CloudFX FunHouse starting...
     Connecting to WiFi...
     Connected! IP: 192.168.1.xxx
     Listening for commands...
     ```

2. **Test command reception**
   - Keep serial console open
   - In another window, send test command (see below)
   - Watch for console output and display update

### Step 7: Send Test Command

**Option A: cURL (command line)**
```bash
curl -X POST \
  -H "X-AIO-Key: YOUR_AIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"play_pause"}' \
  "https://io.adafruit.com/api/v2/YOUR_USERNAME/feeds/macros/data"
```

**Option B: AdafruitIO Dashboard**
1. Go to [io.adafruit.com](https://io.adafruit.com/)
2. Click "Dashboards" → "New Dashboard"
3. Add a "Button" widget
4. Connect to `macros` feed
5. Set button value to `play_pause`
6. Click the button!

**Option C: Python script**
```python
import requests

AIO_USERNAME = "your_username"
AIO_KEY = "your_key"

def send_command(cmd):
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/macros/data"
    headers = {"X-AIO-Key": AIO_KEY}
    data = {"value": cmd}
    return requests.post(url, headers=headers, json=data)

send_command("play_pause")
```

### Troubleshooting FunHouse

**WiFi not connecting**
- Check SSID and password in `settings.toml`
- Verify using 2.4GHz network (not 5GHz)
- Check router allows ESP32 devices
- Look for firewall issues

**AdafruitIO errors**
- Verify username and key are correct
- Check that `macros` feed exists
- Try accessing feed via web browser
- Check rate limits (free tier: 30/min)

**Commands not executing**
- Verify command label matches macro definition exactly
- Check `macros.py` loaded correctly (see console)
- Ensure HID initialized (see console)

**Display not working**
- Font file missing - code will use default font
- Check display errors in console
- Display issues don't affect HID functionality

## Part 3: Integration & Testing

### Test Both Devices

1. **Connect both to computer**
   - Plug in MacroPad via USB
   - Plug in FunHouse via USB
   - Both should appear as HID keyboards

2. **Open a text editor**
   - MacroPad keys should type characters/shortcuts
   - FunHouse commands should type characters/shortcuts

3. **Test MacroPad**
   - Press physical keys
   - Watch for HID output
   - Test sound playback if configured
   - Try encoder rotation and click

4. **Test FunHouse**
   - Send commands via AdafruitIO
   - Wait up to 15 seconds for polling
   - Watch serial console for activity
   - Check display shows command

### Customize Your Setup

#### MacroPad Macros

Edit `/macros/yourapp.py`:
```python
from adafruit_hid.keycode import Keycode

app = {
    "name": "Production",
    "macros": [
        # Sound effects
        (0xFF0000, "FX 1", [{"play": "/sounds/applause.wav"}]),
        (0x00FF00, "FX 2", [{"play": "/sounds/laugh.wav"}]),

        # Keyboard shortcuts
        (0x0000FF, "Scene1", [Keycode.CONTROL, Keycode.ALT, Keycode.ONE]),
        (0xFFFF00, "Scene2", [Keycode.CONTROL, Keycode.ALT, Keycode.TWO]),

        # Media controls
        (0xFF00FF, "Play", [[ConsumerControlCode.PLAY_PAUSE]]),
        (0x00FFFF, "Mute", [[ConsumerControlCode.MUTE]]),

        # Text macros
        (0xFF8800, "Email", ["support@example.com"]),
        (0x8800FF, "Phone", ["+1-555-1234"]),

        # Complex sequences
        (0xFFFFFF, "Multi", [
            {"play": "/sounds/intro.wav"},
            0.5,  # Wait 0.5 seconds
            Keycode.CONTROL, Keycode.ALT, Keycode.T,
            -Keycode.T, -Keycode.ALT, -Keycode.CONTROL,
        ]),

        # Keys 10-12 can be blank
    ]
}
```

#### FunHouse Macros

Edit `macros.py`:
```python
from adafruit_hid.keycode import Keycode

class Macros:
    macros = [
        {
            "label": "scene_1",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.ONE]
        },
        {
            "label": "scene_2",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.TWO]
        },
        {
            "label": "emergency_stop",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_MINUS]
        },
        # Add more...
    ]
```

### Common Use Cases

#### Live Theater Production

**MacroPad**: Sound effects board
- Key 1-8: Sound effects
- Key 9: Emergency stop all audio
- Key 10: Curtain cue
- Encoder: Page through different scenes

**FunHouse**: Remote control from booth
- Send scene change commands
- Trigger specific effects
- Controlled via IFTTT or custom dashboard

#### Streaming Setup

**MacroPad**: Quick access board
- Keys: Scene switches, sound effects, chat macros
- Encoder: Volume control

**FunHouse**: Chat bot integration
- Trigger effects from chat commands
- Webhook from StreamElements/Nightbot
- AdafruitIO as middleware

#### Content Creation

**MacroPad**: Editor shortcuts
- Keys: Timeline markers, export presets
- Sound effects for animatics

**FunHouse**: Render farm control
- Start/stop renders remotely
- Notification system via AdafruitIO

## Part 4: Advanced Configuration

### Static IP (FunHouse)

Edit `settings.toml`:
```toml
CIRCUITPY_WIFI_SSID = "YourNetwork"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
STATIC_IP = "192.168.1.100"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "8.8.8.8"
AIO_USERNAME = "username"
AIO_KEY = "key"
```

### Multiple MacroPad Pages

Create multiple files in `/macros/`:
- `soundfx.py` - Sound effects
- `editing.py` - Video editing shortcuts
- `streaming.py` - Stream controls

Navigate with encoder!

### IFTTT Integration (FunHouse)

1. Create IFTTT applet
2. Trigger: Your choice (voice, time, etc.)
3. Action: **Webhooks**
4. Configure webhook:
   - URL: `https://io.adafruit.com/api/v2/YOUR_USERNAME/feeds/macros/data`
   - Method: POST
   - Content Type: `application/json`
   - Body: `{"value":"command_name"}`
   - Headers: `X-AIO-Key: YOUR_KEY`

Now you can trigger commands via voice, schedule, etc.!

### Debugging Tips

**Enable verbose logging** (add to top of code.py):
```python
DEBUG = True

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")
```

**Monitor USB HID** (Linux):
```bash
sudo evtest  # Select your device
```

**Monitor network** (see AdafruitIO requests):
- Use browser dev tools on io.adafruit.com
- Check feed data via API
- Monitor throttle limits

## Part 5: Maintenance

### Updating CircuitPython

1. Download new `.uf2` file
2. Enter bootloader mode
3. Flash new version
4. Reinstall libraries if needed

### Backing Up Configuration

**MacroPad:**
```
Copy from device:
- /macros/*.py
- /sounds/*.wav (if small enough)
```

**FunHouse:**
```
Copy from device:
- macros.py
- settings.toml (keep secure!)
```

### Resetting to Defaults

**Full reset:**
1. Connect device via USB
2. Delete all files from `CIRCUITPY`
3. Reflash CircuitPython
4. Reinstall from scratch

**Soft reset:**
- MacroPad: Delete `/macros/*.py`, restart
- FunHouse: Delete `macros.py`, restart

## Conclusion

You now have a complete CloudFX system set up! Both devices should be:
- Running CircuitPython 10.0.3
- Loaded with all required libraries
- Configured with your macros/commands
- Ready for production use

For questions and issues, check:
- Device-specific READMEs
- Serial console output
- [CircuitPython docs](https://docs.circuitpython.org/)
- [Adafruit forums](https://forums.adafruit.com/)

Happy controlling!
