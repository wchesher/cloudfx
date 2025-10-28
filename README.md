# CloudFX

**A dual-device production control system using Adafruit CircuitPython hardware for live sound effects and remote command execution.**

![CircuitPython](https://img.shields.io/badge/CircuitPython-10.0.3-blueviolet.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## What Is This?

CloudFX turns two Adafruit devices into a powerful sound effects and macro controller system:

- **MacroPad RP2040**: Physical 12-button soundboard with rotary encoder (local control)
- **FunHouse ESP32-S2**: Network-connected remote trigger via AdafruitIO (remote control)

Both devices act as **USB HID keyboards**, sending keystrokes to your computer to trigger sounds via AutoHotKey (or any automation software).

## Quick Start

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

**FunHouse users**: Update TinyUF2 bootloader to 0.33.0+ first! See [FunHouse README](funhouse/README.md).

### 3. Get the Code

**Download latest release:**
```bash
git clone https://github.com/wchesher/cloudfx.git
cd cloudfx
```

### 4. Deploy Files

#### MacroPad
Copy these 3 files to the root of your MacroPad's `CIRCUITPY` drive:
```bash
cp macropad/code.py /Volumes/CIRCUITPY/code.py
cp shared/macros.json /Volumes/CIRCUITPY/macros.json
cp shared/macros_loader.py /Volumes/CIRCUITPY/macros_loader.py
```

Then install libraries (see [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for complete list).

#### FunHouse (Optional)
Copy these files to FunHouse's `CIRCUITPY` drive:
```bash
cp funhouse/code_refactored.py /Volumes/CIRCUITPY/code.py
cp shared/macros.json /Volumes/CIRCUITPY/macros.json
cp shared/macros_loader.py /Volumes/CIRCUITPY/macros_loader.py
cp funhouse/settings.toml.example /Volumes/CIRCUITPY/settings.toml
# Edit settings.toml with your WiFi and AdafruitIO credentials
```

Then install libraries (see [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)).

### 5. Add Sound Files

Copy your WAV files to a folder (e.g., `C:\fx\` on Windows) and update your AutoHotKey script to play them.

**Example sound files are in `fx/` folder!** Copy them to your sound directory.

### 6. Setup AutoHotKey (Windows)

Create an AHK v2 script to play sounds when keystrokes are received:

```ahk
#Requires AutoHotkey v2.0
#SingleInstance Force

SoundDir := "C:\fx\"

; SHIFT+ESCAPE: Stop playback (encoder button)
+Escape:: {
    SoundPlay(SoundDir . "off.wav")
}

; CTRL+ALT+SHIFT+F13: Play dj.wav (example)
^!+F13:: {
    SoundPlay(SoundDir . "dj.wav")
}

; Add more hotkeys for each sound...
```

See your deployed `macros.json` for all the key combinations!

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
├── DEPLOYMENT_CHECKLIST.md      # Complete deployment guide
├── LICENSE                      # MIT License
│
├── macropad/                    # MacroPad RP2040 code
│   ├── code.py                  # Main program
│   ├── README.md                # MacroPad setup guide
│   └── LIBRARIES.md             # Required libraries list
│
├── funhouse/                    # FunHouse ESP32-S2 code
│   ├── code_refactored.py       # Main program (use this!)
│   ├── settings.toml.example    # WiFi/AdafruitIO config template
│   ├── README.md                # FunHouse setup guide
│   └── LIBRARIES.md             # Required libraries list
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
✅ Screensaver after 20s inactivity
✅ Completely standalone (no WiFi needed)

### FunHouse Features
✅ Remote control via AdafruitIO
✅ 145+ commands available
✅ Fast 3-second polling
✅ DotStar LED status indicators
✅ WiFi reconnection handling
✅ OLED display shows last command
✅ Static or DHCP IP configuration
✅ Command queuing system

---

## Deployment Checklist

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for:
- ✅ Complete file lists for each device
- ✅ Required CircuitPython libraries
- ✅ Copy/paste deployment commands
- ✅ Verification steps
- ✅ Troubleshooting guide

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

### FunHouse

**Won't connect to WiFi**
- Check credentials in `settings.toml`
- FunHouse only supports 2.4GHz WiFi (not 5GHz)
- Check serial console for error details

**Commands don't trigger sounds**
- Command name must match exactly (case-sensitive!)
- Check command exists in `macros.json`
- Serial console will say "WARNING: Command 'xxx' not found"
- Verify AutoHotKey is running and has matching hotkey

**Too slow / polling takes forever**
- `POLL_INTERVAL = 3` in code (3 seconds)
- Edit `code_refactored.py` line 119 to change

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
✅ ESP32-S2 bootloader requirements documented
✅ JSON-based configuration (no Python import issues)

### HID Timing

Both devices hold keys for **50ms** before releasing - critical for AutoHotKey detection:
```python
kbd.press(keycodes)
time.sleep(0.05)  # 50ms hold
kbd.release_all()
```

### Memory Usage

- MacroPad: ~200KB for libraries + code
- FunHouse: ~200KB for libraries + code
- JSON file: ~40KB (145 commands)

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

**Issues?** Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) troubleshooting section first!

**Still stuck?** Open an issue: https://github.com/wchesher/cloudfx/issues

---

**🎵 Happy sound boarding! 🎵**
