# CloudFX Deployment Checklist

## MacroPad CIRCUITPY Drive

### Required Files (Root Directory)
- [ ] `code.py` (from `macropad/code.py`)
- [ ] `macros.json` (from `shared/macros.json`)
- [ ] `macros_loader.py` (from `shared/macros_loader.py`)

### Required Folders
- [ ] `/lib/` - CircuitPython libraries (see below)
- [ ] `/sounds/` - Your WAV files (optional, for audio playback)

### Required Libraries in `/lib/`
From CircuitPython 10.x Bundle:
- [ ] `adafruit_macropad.mpy`
- [ ] `adafruit_debouncer.mpy`
- [ ] `adafruit_pixelbuf.mpy`
- [ ] `adafruit_simple_text_display.mpy`
- [ ] `adafruit_ticks.mpy`
- [ ] `neopixel.mpy`
- [ ] `adafruit_midi/` (folder - hidden dependency!)
- [ ] `adafruit_hid/` (folder)
- [ ] `adafruit_display_text/` (folder)
- [ ] `adafruit_display_shapes/` (folder)

### Optional Files
- [ ] `/sounds/*.wav` - Sound effects (dj.wav, rimshot.wav, etc.)

### Files to DELETE (if present)
- [ ] `ref.py` - Not needed
- [ ] `macros.py` - Old system, not used anymore
- [ ] `/macros/*.py` - Old macro files, replaced by macros.json
- [ ] `adafruit_led_animation/` - Not required

---

## FunHouse CIRCUITPY Drive

### Required Files (Root Directory)
- [ ] `code.py` (from `funhouse/code_refactored.py` - rename it!)
- [ ] `macros.json` (from `shared/macros.json`)
- [ ] `macros_loader.py` (from `shared/macros_loader.py`)
- [ ] `settings.toml` (from `funhouse/settings.toml.example` - edit with your credentials!)

### Required Folders
- [ ] `/lib/` - CircuitPython libraries (see below)
- [ ] `/fonts/` - Display fonts (optional)

### Required Libraries in `/lib/`
From CircuitPython 10.x Bundle:
- [ ] `adafruit_requests.mpy`
- [ ] `adafruit_connection_manager.mpy`
- [ ] `adafruit_io/` (folder)
- [ ] `adafruit_hid/` (folder)
- [ ] `adafruit_display_text/` (folder)
- [ ] `adafruit_dotstar.mpy` (for status LEDs)
- [ ] `adafruit_bitmap_font/` (folder - optional, for custom fonts)

### Optional Files
- [ ] `/fonts/LemonMilk-10.pcf` - Display font

### Files to DELETE (if present)
- [ ] `macros.py` - Old system, replaced by macros.json
- [ ] `secrets.py` - Old system, replaced by settings.toml
- [ ] `code.py` (old version) - Replace with code_refactored.py

---

## settings.toml Configuration (FunHouse only)

Edit `settings.toml` with your credentials:

```toml
CIRCUITPY_WIFI_SSID = "YourWiFiSSID"
CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
AIO_USERNAME = "your_aio_username"
AIO_KEY = "your_aio_key"
```

Optional static IP (if needed):
```toml
STATIC_IP = "192.168.1.100"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"
```

---

## Quick Deployment Commands

### Copy to MacroPad
```bash
# Adjust path to your MacroPad drive
MACROPAD="/Volumes/CIRCUITPY"

cp shared/macros.json $MACROPAD/macros.json
cp shared/macros_loader.py $MACROPAD/macros_loader.py
cp macropad/code.py $MACROPAD/code.py
```

### Copy to FunHouse
```bash
# Adjust path to your FunHouse drive
FUNHOUSE="/Volumes/CIRCUITPY"

cp shared/macros.json $FUNHOUSE/macros.json
cp shared/macros_loader.py $FUNHOUSE/macros_loader.py
cp funhouse/code_refactored.py $FUNHOUSE/code.py
# Edit settings.toml with your credentials before copying
cp funhouse/settings.toml $FUNHOUSE/settings.toml
```

---

## Verification

### MacroPad - Serial Console Should Show:
```
CircuitPython 10.x.x
MacroPad initialized successfully
Loaded 12 macro app(s) from macros.json
Successfully loaded 12 macro app(s)
Active app: EFFECTS
```

### FunHouse - Serial Console Should Show:
```
CircuitPython 10.x.x
Loaded XX command(s) from macros.json
USB HID keyboard initialized
Connected! IP: 192.168.x.x
Listening for commands...
```

---

## Testing

### MacroPad
1. Rotate encoder → should cycle through 12 pages (EFFECTS → UPBEAT → ... → JEOPARDY)
2. Press any button → should send HID keycode
3. **Click encoder → should send SHIFT+ESCAPE** (stops playback in AHK)

### FunHouse
1. Check serial console → should connect to WiFi and AdafruitIO
2. Send command to AdafruitIO feed → should trigger HID keycode
3. Send "off" command → should send SHIFT+ESCAPE (stops playback)
4. DotStar LEDs should show status (blue→green→yellow during polling)

---

## Troubleshooting

### MacroPad Shows "NO MACROS"
- Missing `macros.json` or `macros_loader.py`
- Check serial console for import errors

### MacroPad Keys Don't Work
- Wrong CircuitPython version (need 10.x)
- Missing libraries in `/lib/`
- Check serial console for errors

### FunHouse Won't Connect to WiFi
- Check credentials in `settings.toml`
- Use 2.4GHz WiFi only (ESP32-S2 doesn't support 5GHz)
- Check serial console for error messages

### FunHouse Commands Don't Work
- Check AdafruitIO feed name is exactly "macros"
- Command name must match JSON exactly (case-sensitive)
- Check serial console: "WARNING: Command 'xxx' not found"

### Encoder Button Doesn't Stop Playback
- Check AutoHotkey script has `+Escape::` handler
- Check `off.wav` file exists in `C:\fx\`
- Test: Press SHIFT+ESCAPE manually on keyboard

---

## Latest Version Info

**Git Branch**: `claude/session-011CUZdd6iKKTfeX3z2T2GND`
**Latest Commit**: `ef42867` (Encoder button: SHIFT+ESCAPE)

**Download Latest**:
https://github.com/wchesher/cloudfx/tree/claude/session-011CUZdd6iKKTfeX3z2T2GND
