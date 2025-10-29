# CloudFX v1.0

**A dual-device production control system using Adafruit CircuitPython hardware for live sound effects and remote command execution.**

![CircuitPython](https://img.shields.io/badge/CircuitPython-10.0.3-blueviolet.svg)
![Version](https://img.shields.io/badge/version-1.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## What Is This?

CloudFX turns two Adafruit devices into a powerful sound effects and macro controller system:

- **MacroPad RP2040**: Physical 12-button soundboard with rotary encoder (local control)
- **FunHouse ESP32-S2**: Network-connected remote trigger via AdafruitIO (remote control)

Both devices act as **USB HID keyboards**, sending keystrokes to your computer to trigger sounds via AutoHotKey (or any automation software).

---

## Quick Start

**Setup Overview:**
1. Install CircuitPython on devices
2. Install AutoHotkey v2 on Windows
3. Create `C:\fx\` directory and copy sound files
4. Create and compile AutoHotkey script (`cloud.ahk` → `cloud.exe`)
5. Add `cloud.exe` to Windows startup
6. Deploy CloudFX code to devices
7. Start using your soundboard!

### 1. Hardware You Need
- [Adafruit MacroPad RP2040](https://www.adafruit.com/product/5128)
- [Adafruit FunHouse ESP32-S2](https://www.adafruit.com/product/4985) (optional - for remote control)
- USB-C cables
- Computer running Windows/Mac/Linux
- WiFi network (for FunHouse only)

### 2. Install CircuitPython 10.0.3

Download and install CircuitPython 10.0.3 on your devices:
- [MacroPad downloads](https://circuitpython.org/board/adafruit_macropad_rp2040/)
- [FunHouse downloads](https://circuitpython.org/board/adafruit_funhouse/)

**FunHouse users**: Update TinyUF2 bootloader to 0.33.0+ first! See [CircuitPython documentation](https://learn.adafruit.com/adafruit-funhouse/circuitpython).

### 3. Get the Code

**Download latest release:**
```bash
git clone https://github.com/wchesher/cloudfx.git
cd cloudfx
```

### 4. Windows Setup (Required)

**Overview**: CloudFX devices send HID keystrokes to your computer. You need AutoHotkey v2 running on Windows to receive these keystrokes and play the corresponding sound files.

#### Install AutoHotkey v2

Download and install AutoHotkey v2 from:
**https://www.autohotkey.com/download/ahk-v2.exe**

Make sure to install **v2.0+** (not v1.x).

#### Create Sound Directory

Create the directory for your sound files:
```cmd
mkdir C:\fx
```

#### Copy Sound Files

**Copy ALL 145+ WAV files from the repository's `fx/` folder to `C:\fx\`:**

From the cloudfx directory, run:
```cmd
xcopy fx\*.wav C:\fx\ /Y
```

This copies all sound files at once. You should see 145+ files being copied.

**Or manually:** Open the `fx/` folder and drag/drop all WAV files to `C:\fx\`.

#### Create AutoHotkey Script

Create a file called `cloud.ahk` in a convenient location (e.g., `C:\Users\YourName\Documents\cloud.ahk`) with this content:

```ahk
#Requires AutoHotkey v2.0
#SingleInstance Force

SoundDir := "C:\fx\"

; SHIFT+ESCAPE: Stop playback (encoder button)
+Escape:: {
    SoundPlay(SoundDir . "off.wav")
}

; CTRL+ALT+SHIFT+F13: Play dj.wav
^!+F13:: {
    SoundPlay(SoundDir . "dj.wav")
}

; CTRL+ALT+SHIFT+F14: Play crickets.wav
^!+F14:: {
    SoundPlay(SoundDir . "crickets.wav")
}

; Add more hotkeys for each sound...
; See macros.json for all key combinations
```

**See `shared/macros.json` for the complete list of key combinations to map!**

#### Compile to Executable (Optional but Recommended)

1. Right-click `cloud.ahk`
2. Select **"Compile Script"**
3. This creates `cloud.exe` in the same folder

#### Add to Startup

Add `cloud.exe` (or `cloud.ahk`) to Windows startup so it runs automatically:

**Method 1: Startup Folder**
1. Press `Win+R` and type: `shell:startup`
2. Copy `cloud.exe` into the Startup folder
3. Or create a shortcut to `cloud.exe` in the Startup folder

**Method 2: Task Scheduler**
1. Open Task Scheduler
2. Create Basic Task → Name it "CloudFX"
3. Trigger: "When I log on"
4. Action: "Start a program" → Browse to `cloud.exe`
5. Finish

### 5. Deploy Files to Devices

#### MacroPad
Copy these 3 files to the root of your MacroPad's `CIRCUITPY` drive:
```bash
cp macropad/code.py /Volumes/CIRCUITPY/code.py
cp shared/macros.json /Volumes/CIRCUITPY/macros.json
cp shared/macros_loader.py /Volumes/CIRCUITPY/macros_loader.py
```

**Required Libraries** (install to `/lib/` on device):
- `adafruit_macropad.mpy`
- `adafruit_hid/` (folder)
- `adafruit_display_text/` (folder)
- `adafruit_display_shapes/` (folder)

Download from [CircuitPython 10.x Library Bundle](https://circuitpython.org/libraries).

#### FunHouse (Optional)
Copy these files to FunHouse's `CIRCUITPY` drive:
```bash
cp funhouse/code.py /Volumes/CIRCUITPY/code.py
cp shared/macros.json /Volumes/CIRCUITPY/macros.json
cp shared/macros_loader.py /Volumes/CIRCUITPY/macros_loader.py
cp funhouse/settings.toml.example /Volumes/CIRCUITPY/settings.toml
# Edit settings.toml with your WiFi and AdafruitIO credentials
```

**Required Libraries** (install to `/lib/` on device):
- `adafruit_hid/` (folder)
- `adafruit_requests.mpy`
- `adafruit_io/` (folder)
- `adafruit_display_text/` (folder)
- `adafruit_dotstar.mpy`

Download from [CircuitPython 10.x Library Bundle](https://circuitpython.org/libraries).

### 6. Configure FunHouse (Optional)

Edit `settings.toml` on your FunHouse:

```toml
# WiFi Configuration
CIRCUITPY_WIFI_SSID = "YourWiFiName"
CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"

# AdafruitIO Credentials (get from io.adafruit.com)
AIO_USERNAME = "your_username"
AIO_KEY = "your_aio_key"

# Static IP (optional - comment out for DHCP)
STATIC_IP = "192.168.1.100"
GATEWAY = "192.168.1.1"
NETMASK = "255.255.255.0"
DNS = "8.8.8.8"

# Polling Configuration
POLL_INTERVAL = "2"  # seconds between AdafruitIO checks
```

---

## How It Works

### MacroPad Pages

The MacroPad loads **12 "pages"** (apps) from `macros.json`. Rotate the encoder to switch between pages:

1. **EFFECTS** - Sound effects (dj, crickets, dundun, etc.)
2. **UPBEAT** - Positive sounds (rimshot, tada, applause, etc.)
3. **DOWNBEAT** - Negative sounds (fail, wahwah, nope, etc.)
4. **RANDOM 1** - Random effects (Jetsons, psycho, train, etc.)
5. **RANDOM 2** - More random (Shrek, wilhelm scream, etc.)
6. **RICK 1** - Rick & Morty clips #1
7. **RICK 2** - Rick & Morty clips #2
8. **SONGS** - Music clips (circus, imperial march, etc.)
9. **SPONGEBOB** - Spongebob sounds
10. **STAR WARS 1** - Star Wars clips #1
11. **STAR WARS 2** - Star Wars clips #2
12. **JEOPARDY** - Jeopardy music/effects

Each page has up to 12 buttons mapped to your 12 physical keys.

**Encoder Button**: Click the encoder to send **SHIFT+ESCAPE** (stops playback).

**Encoder Rotation**: Turn left/right to navigate between pages.

### FunHouse Remote Control

Send commands to your FunHouse via AdafruitIO:

1. Create an AdafruitIO account at [io.adafruit.com](https://io.adafruit.com/)
2. Create a feed named **"macros"**
3. Send command names (like "dj", "rimshot", "intro") to the feed
4. FunHouse receives the command and triggers the keystroke
5. Your AutoHotKey script plays the sound

**Command List**: See `macros.json` - the `"command"` field is what you send to AdafruitIO.

---

## Project Structure

```
cloudfx/
├── README.md                    # This file
├── LICENSE                      # MIT License
│
├── macropad/                    # MacroPad RP2040 code
│   └── code.py                  # Main program
│
├── funhouse/                    # FunHouse ESP32-S2 code
│   ├── code.py                  # Main program
│   └── settings.toml.example    # WiFi/AdafruitIO config template
│
├── shared/                      # Shared between both devices
│   ├── macros.json              # 🎯 SINGLE SOURCE OF TRUTH - all macros defined here
│   └── macros_loader.py         # JSON parser for both devices
│
└── fx/                          # Example WAV sound files
    ├── dj.wav
    ├── rimshot.wav
    └── ... (145+ sound files)
```

## Single Source of Truth: `macros.json`

**Everything** is defined in `shared/macros.json`:
- MacroPad button labels, colors, and keycodes
- MacroPad page names and order
- FunHouse command names and keycodes
- Encoder button behavior

### JSON Structure

```json
{
  "apps": [
    {
      "name": "EFFECTS",
      "buttons": [
        {
          "label": "dj",
          "command": "dj",
          "color": "0x17A398",
          "keycodes": ["LEFT_CONTROL", "LEFT_ALT", "LEFT_SHIFT", "F13"]
        }
      ]
    }
  ]
}
```

- **label**: Button text on MacroPad (5-7 chars max)
- **command**: Command name for FunHouse (sent to AdafruitIO)
- **color**: LED color in hex (MacroPad only)
- **keycodes**: HID keys to send (both devices)

### Adding New Sounds

1. Edit `shared/macros.json`
2. Add a new button entry with unique command name and keycodes
3. Copy updated `macros.json` to both devices
4. Add sound file to your sound directory (e.g., `C:\fx\newsound.wav`)
5. Add hotkey to AutoHotKey script
6. Restart devices

---

## Features

### MacroPad Features
✅ 12 programmable keys per page
✅ 12 pages (144 total sounds!)
✅ RGB LED indicators per key
✅ Rotary encoder for page switching
✅ Click encoder to stop playback (SHIFT+ESCAPE)
✅ OLED display shows current page name
✅ Screensaver after 30s inactivity (prevents LCD burn-in)
✅ Configurable LED brightness (30% default)
✅ Completely standalone (no WiFi needed)
✅ Symmetric encoder navigation (fixed in v1.0)

### FunHouse Features
✅ Remote control via AdafruitIO
✅ 145+ commands available
✅ Fast 2-second polling (configurable)
✅ DotStar LED status indicators
✅ WiFi auto-reconnect (30s health checks)
✅ Display backlight control (turns off when idle)
✅ Synced display and LED timing
✅ Static or DHCP IP configuration
✅ Command queuing system (50 command buffer)
✅ Comprehensive error logging
✅ Memory monitoring and garbage collection
✅ HID error recovery
✅ Network resilience with auto-recovery

---

## LED Indicators

### MacroPad
- **Per-button RGB LEDs**: Show page colors and button status
- **Dimmed to 5%**: During screensaver mode (after 30s idle)
- **Full brightness (30%)**: When active

### FunHouse DotStars (5 LEDs)
- **Blue**: Connecting to WiFi
- **Green**: Connected (shown during first 2 polls)
- **Off**: Normal operation (after startup)
- **Magenta**: Command received and executing (1 second flash, synced with display)
- **Red**: Error occurred

---

## Architecture

```
┌─────────────────┐                    ┌──────────────────┐
│    MacroPad     │                    │    FunHouse      │
│   (RP2040)      │                    │   (ESP32-S2)     │
│                 │                    │                  │
│  ┌───────────┐  │                    │  ┌────────────┐  │
│  │ Physical  │  │                    │  │ AdafruitIO │  │
│  │  Buttons  │  │                    │  │  Listener  │  │
│  │ (12 keys) │  │                    │  │  (WiFi)    │  │
│  └─────┬─────┘  │                    │  └──────┬─────┘  │
│        │        │                    │         │        │
│  ┌─────▼─────┐  │                    │  ┌──────▼─────┐  │
│  │   JSON    │  │                    │  │    JSON    │  │
│  │  Loader   │  │                    │  │   Loader   │  │
│  └─────┬─────┘  │                    │  └──────┬─────┘  │
│        │        │                    │         │        │
│  ┌─────▼─────┐  │                    │  ┌──────▼─────┐  │
│  │HID Output │  │                    │  │ HID Output │  │
│  └─────┬─────┘  │                    │  └──────┬─────┘  │
└────────┼────────┘                    └─────────┼────────┘
         │                                       │
         │         USB                           │  USB
         └───────────────────┬───────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │   Host Computer    │
                   │  (AutoHotKey/AHK)  │
                   │   Plays WAV Files  │
                   └────────────────────┘
```

Both devices:
1. Read `macros.json` at startup
2. Convert keycode strings to HID codes
3. Send HID keystrokes via USB
4. Computer receives keystrokes
5. AutoHotKey plays corresponding sound

They operate **independently** - no direct communication between them.

---

## Technical Details

### CircuitPython 10.0.3 Compatibility

✅ Updated exception handling (`traceback.print_exception`)
✅ Modern `settings.toml` config (FunHouse)
✅ Compatible with CP 10.x Library Bundle
✅ JSON-based configuration (no Python import issues)
✅ Aggressive memory management

### HID Timing

Both devices hold keys for **50ms** before releasing - critical for AutoHotKey detection:
```python
kbd.press(keycodes)
time.sleep(0.05)  # 50ms hold
kbd.release_all()
```

### Memory Management

**FunHouse** (ESP32-S2):
- Aggressive garbage collection every 5 seconds
- Memory monitoring with warnings below 10KB free
- Loader deleted immediately after use
- Typical free memory: 30-50KB

**MacroPad** (RP2040):
- Simple memory management
- No aggressive GC needed (more RAM available)
- Typical free memory: 100-150KB

### Error Handling

**FunHouse** includes comprehensive error handling:
- Full tracebacks printed to serial console
- WiFi auto-reconnect with exponential backoff
- HID error recovery (release all keys on failure)
- Display/LED operation failures don't crash the program
- KeyboardInterrupt handler logs diagnostic info
- Separate error handling for backlight control

**MacroPad** includes basic error handling:
- Safe screensaver wake logic
- Encoder position sync on startup
- Display refresh protection

### Configuration

**MacroPad** (`macropad/code.py`):
```python
REGULAR_BRIGHTNESS = 0.3    # Regular LED brightness (30%)
SCREENSAVER_TIMEOUT = 30    # Seconds before screensaver (0 = disable)
DIM_BRIGHTNESS = 0.05       # LED brightness when dimmed
```

**FunHouse** (`funhouse/settings.toml`):
```toml
POLL_INTERVAL = "2"         # Seconds between AdafruitIO polls
```

**FunHouse** (`funhouse/code.py`):
```python
DISPLAY_TIMEOUT = 1.0       # Seconds to show command name
GC_INTERVAL = 5             # Seconds between garbage collection
QUEUE_SIZE = 50             # Max commands in queue
WIFI_CHECK_INTERVAL = 30    # Seconds between WiFi health checks
```

---

## Troubleshooting

### MacroPad

**"NO MACROS" on display**
- Missing `macros.json` or `macros_loader.py`
- Check serial console for errors

**Keys don't work**
- Verify CircuitPython 10.0.3 installed
- Check all required libraries in `/lib/` folder
- Connect to serial console to see errors

**Encoder button doesn't stop playback**
- Check AutoHotKey script has `+Escape::` hotkey
- Verify `off.wav` exists in sound directory

**Encoder navigation is weird**
- Fixed in v1.0 - encoder position now syncs on startup
- Update to latest code

**Screensaver not waking**
- Fixed in v1.0 - screen_active flag set before display activation
- Update to latest code

### FunHouse

**Won't connect to WiFi**
- Check credentials in `settings.toml`
- FunHouse only supports 2.4GHz WiFi (not 5GHz)
- Check serial console for detailed error messages
- WiFi will auto-reconnect every 30 seconds if disconnected

**Commands don't trigger sounds**
- Command name must match exactly (case-sensitive!)
- Check command exists in `macros.json`
- Serial console will say "✗ Command not found in macro list"
- Verify AutoHotKey is running and has matching hotkey

**Display stays on all the time**
- v1.0 includes backlight control
- Backlight turns off after 1 second when idle
- Update to latest code

**Device crashes or freezes**
- v1.0 includes comprehensive error handling
- Check serial console for error messages and tracebacks
- Look for memory warnings (below 10KB free)
- WiFi disconnections are now handled automatically

**Verbose logging**
- v1.0 includes detailed logging for all operations
- Connect to serial console to see:
  - Poll activity and received commands
  - Command execution steps (display, LEDs, HID)
  - WiFi health checks
  - Memory status and garbage collection
  - Full error tracebacks

---

## Version History

### v1.0 (2025-01-29)
- Initial stable release
- Fixed encoder navigation asymmetry
- Added FunHouse display backlight control
- Synced FunHouse DotStar LEDs with display timing
- Comprehensive error handling and logging
- WiFi auto-reconnect with health checks
- Memory monitoring and aggressive garbage collection
- Improved screensaver wake logic
- Command queuing system
- Network resilience with auto-recovery

---

## Use Cases

🎭 **Live Production**: Sound effects board for theater, podcasts, live streams
🎬 **Content Creation**: Quick sound effects while recording/editing
🎮 **Streaming**: Instant reactions and sound bites
📡 **Remote Control**: Trigger sounds from phone/tablet via AdafruitIO
🎵 **DJing**: Quick sound drops and effects
🎓 **Education**: Learn CircuitPython, USB HID, IoT integration

---

## Credits

- **Original MacroPad code**: Phillip Burgess (Adafruit Industries)
- **CloudFX modifications**: William C. Chesher
- **CircuitPython**: Adafruit Industries and contributors
- **Sound effects**: Various sources (see individual files for attribution)

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Links

- **Repository**: https://github.com/wchesher/cloudfx
- **CircuitPython**: https://circuitpython.org/
- **Adafruit MacroPad**: https://www.adafruit.com/product/5128
- **Adafruit FunHouse**: https://www.adafruit.com/product/4985
- **AdafruitIO**: https://io.adafruit.com/
- **AutoHotkey v2**: https://www.autohotkey.com/

---

## Support

**Issues?** Check the troubleshooting section above first!

**Still stuck?** Open an issue: https://github.com/wchesher/cloudfx/issues

---

**🎵 Happy sound boarding! 🎵**
