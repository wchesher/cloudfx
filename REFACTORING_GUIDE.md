# FunHouse Code Refactoring - adafruit_io & DotStar LEDs

## What Changed

The FunHouse code has been refactored to use modern libraries and add visual status feedback.

### Major Improvements

1. **Uses `adafruit_io` library** instead of raw HTTP requests
2. **DotStar LED support** (5 RGB LEDs show status)
3. **Cleaner code** - easier to read and maintain
4. **Better error recovery**
5. **Visual poll timer** on LEDs

## File Comparison

| Feature | Old (code.py) | New (code_refactored.py) |
|---------|---------------|--------------------------|
| HTTP | Raw `requests.get()` | `IO_HTTP` client |
| Feed access | Manual URL construction | `io.receive_all_data()` |
| Delete | Manual DELETE requests | `io.delete_data()` |
| Status LEDs | None | DotStar 5 LEDs |
| Code lines | ~430 | ~490 (with LED features) |

## New Features in Refactored Version

### 1. DotStar LED Status Indicators

The 5 RGB LEDs on the side of the FunHouse now show:

- **Blue** - Connecting to WiFi
- **Green** - Connected and idle
- **Yellow** - Polling AdafruitIO
- **Magenta** - Processing command (flash)
- **Red** - Error

**Poll Timer Visualization:**
- LEDs light up progressively showing time until next poll
- All 5 LEDs on = almost time to poll again

### 2. Cleaner AdafruitIO Integration

**Before (raw HTTP):**
```python
headers = {"X-AIO-Key": AIO_KEY}
resp = requests.get(MACROS_FEED_URL, headers=headers)
items = resp.json()
for item in items:
    delete_resp = requests.delete(f"{MACROS_FEED_URL}/{item['id']}", headers=headers)
```

**After (adafruit_io library):**
```python
io = IO_HTTP(AIO_USERNAME, AIO_KEY, requests_session)
items = io.receive_all_data("macros")
for item in items:
    io.delete_data("macros", item["id"])
```

Much cleaner and easier to understand!

### 3. Better Error Messages

Errors now include more context and point to specific library issues.

## Migration Steps

### Option 1: Replace Existing File

If you want to switch completely:

1. **Backup your current code.py:**
   ```
   cp CIRCUITPY/code.py CIRCUITPY/code.py.backup
   ```

2. **Install required libraries:**
   ```
   Make sure you have:
   - adafruit_io/ (folder)
   - adafruit_dotstar.mpy
   - (keep all existing libraries)
   ```

3. **Copy refactored code:**
   ```
   cp funhouse/code_refactored.py CIRCUITPY/code.py
   ```

4. **Restart FunHouse**

### Option 2: Test Side-by-Side

Keep both files and rename to test:

1. **Save current as code_old.py:**
   ```
   CIRCUITPY/code.py → CIRCUITPY/code_old.py
   ```

2. **Test refactored version:**
   ```
   CIRCUITPY/code_refactored.py → CIRCUITPY/code.py
   ```

3. **Switch back if needed:**
   ```
   CIRCUITPY/code_old.py → CIRCUITPY/code.py
   ```

## Required Libraries

### New Required:
```
adafruit_io/                  ← NEW! AdafruitIO client
  ├── adafruit_io.mpy
  └── adafruit_io_errors.mpy
```

### New Optional:
```
adafruit_dotstar.mpy          ← NEW! For status LEDs
```

### Keep Existing:
```
adafruit_requests.mpy
adafruit_connection_manager.mpy
adafruit_hid/
adafruit_display_text/
adafruit_bitmap_font/ (optional)
adafruit_ticks.mpy (may be dependency)
```

### Can Delete:
Everything else not listed above!

## Testing the Refactored Version

### 1. Check Serial Console

After restart, you should see:
```
CircuitPython 10.0.3
Loaded X macro(s) from macros.py
DotStar LEDs initialized (5 LEDs)  ← NEW!
USB HID keyboard initialized
Display initialized
Settings loaded successfully from settings.toml
CloudFX FunHouse starting...
Connecting to SSID: YourNetwork
Connected! IP: 192.168.1.xxx
AdafruitIO client created         ← NEW! Cleaner
Clearing existing items from 'macros' feed...
Polling for commands...
```

### 2. Check DotStar LEDs

**LEDs should:**
- Turn **blue** when connecting
- Turn **green** when connected
- Show **progress bar** (filling up as poll timer counts down)
- Flash **magenta** when processing command
- Turn **red** on errors

**If LEDs don't work:**
- Check `adafruit_dotstar.mpy` is installed
- Serial console will show: "WARNING: adafruit_dotstar not found"
- Code still works, just no LED indicators

### 3. Test Commands

Send a command to your AdafruitIO feed - should work exactly the same as before!

## Configuration Options

### Disable LED Features

If you don't want LEDs (to save battery or they're distracting):

In `code.py`, change line with `DOTSTAR_AVAILABLE`:
```python
DOTSTAR_AVAILABLE = False  # Force disable even if library exists
```

### Adjust LED Brightness

Find this line:
```python
dots = adafruit_dotstar.DotStar(
    board.DOTSTAR_CLOCK,
    board.DOTSTAR_DATA,
    5,
    brightness=0.2,  # ← Change this (0.0 to 1.0)
    auto_write=False
)
```

Lower values = dimmer LEDs, use less power.

### Change LED Colors

Edit the color constants at the top:
```python
LED_CONNECTING = (0, 0, 255)     # Blue - change RGB values
LED_CONNECTED = (0, 255, 0)      # Green
LED_POLLING = (255, 255, 0)      # Yellow
LED_COMMAND = (255, 0, 255)      # Magenta
LED_ERROR = (255, 0, 0)          # Red
```

Values are (Red, Green, Blue) from 0-255.

## Advantages of Refactored Version

### 1. Cleaner Code
- Fewer lines for same functionality
- Easier to understand
- Better organized

### 2. Visual Feedback
- See connection status at a glance
- Know when polls are happening
- Catch errors visually

### 3. Better Library Support
- Uses official `adafruit_io` library
- Future updates easier
- Bug fixes from Adafruit automatically included

### 4. Easier Debugging
- LED colors show what's happening
- Better error messages
- More context in logs

## Troubleshooting

### "no module named adafruit_io"

You need to install the `adafruit_io` library folder:
```
From Bundle: lib/adafruit_io/
To CIRCUITPY: lib/adafruit_io/
```

### "no module named adafruit_dotstar"

Optional library for LEDs. Install or code will run without LED features:
```
From Bundle: lib/adafruit_dotstar.mpy
To CIRCUITPY: lib/adafruit_dotstar.mpy
```

### LEDs Not Working

Check serial console for:
```
WARNING: adafruit_dotstar not found, status LEDs disabled
```

Install `adafruit_dotstar.mpy` to enable.

### Old Code Works, New Code Doesn't

Make sure you have:
1. ✅ `adafruit_io/` folder installed
2. ✅ All previous libraries still installed
3. ✅ Same `settings.toml` file
4. ✅ Same `macros.py` file

## Reverting to Old Code

If you need to go back:

1. **Delete new code:**
   ```
   Delete CIRCUITPY/code.py
   ```

2. **Restore backup:**
   ```
   Rename CIRCUITPY/code.py.backup to code.py
   ```

3. **Restart FunHouse**

Old code doesn't need `adafruit_io/` folder, so you can delete it if you want.

## Recommendation

**Use the refactored version!** It's better in every way:
- Cleaner code
- Visual feedback
- Easier to maintain
- Better error handling
- Future-proof

The only reason not to: if you don't want to install `adafruit_io` library folder.

---

**Questions?** Check the serial console output for specific errors!
