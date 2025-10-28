# FunHouse: "no module named adafruit_hid.find_device" Fix

## The Problem

You're seeing this error:
```
ImportError: no module named adafruit_hid.find_device
```

## Root Cause

You have an **old or incompatible version** of the `adafruit_hid` library on your FunHouse.

- **Old versions** (CircuitPython 7.x/8.x) used `find_device` module
- **New versions** (CircuitPython 9.x/10.x) removed `find_device`
- Your FunHouse has CircuitPython 10.x but old library files!

## Quick Fix

### Option 1: Update adafruit_hid Library (Recommended)

1. **Download CircuitPython 10.x Bundle**
   - Go to: https://circuitpython.org/libraries
   - Download "Bundle for Version 10.x"
   - Extract the ZIP file

2. **Delete Old Library**
   ```
   On CIRCUITPY drive:
   Delete: lib/adafruit_hid/  (entire folder)
   ```

3. **Copy New Library**
   ```
   From Bundle: lib/adafruit_hid/
   To CIRCUITPY: lib/adafruit_hid/
   ```

4. **Restart FunHouse**
   - Safely eject
   - Unplug and replug

### Option 2: Clean Install All Libraries

If you're not sure what library versions you have:

1. **Backup your files**
   ```
   Copy from CIRCUITPY:
   - code.py
   - macros.py
   - settings.toml
   ```

2. **Delete entire lib folder**
   ```
   Delete: CIRCUITPY/lib/  (entire folder)
   ```

3. **Reinstall from Bundle 10.x**
   ```
   From CircuitPython 10.x Bundle, copy to CIRCUITPY/lib/:
   - adafruit_requests.mpy
   - adafruit_hid/  (folder)
   - adafruit_display_text/  (folder)
   - adafruit_bitmap_font/  (folder)
   - adafruit_debouncer.mpy
   ```

4. **Restore your files**
   ```
   Copy back:
   - code.py
   - macros.py
   - settings.toml
   ```

5. **Restart FunHouse**

## Verify the Fix

After updating, you should see in serial console:
```
CircuitPython 10.0.3
Loaded X macro(s) from macros.py
USB HID keyboard initialized  ← Success!
```

**No more import errors!**

## How to Check Your Library Version

On your CIRCUITPY drive:
```
CIRCUITPY/lib/adafruit_hid/
```

**If you see files like:**
- `find_device.mpy` or `find_device.py` ← OLD version (CircuitPython 7.x/8.x)

**Should only have:**
- `keyboard.mpy`
- `keycode.mpy`
- `mouse.mpy`
- `consumer_control.mpy`
- `consumer_control_code.mpy`
- `__init__.mpy`

## Why This Happened

Your FunHouse likely had:
1. CircuitPython updated to 10.x ✅
2. But old library files still in `lib/` ❌

**Always update libraries when updating CircuitPython!**

## Prevention

When upgrading CircuitPython in the future:
1. ✅ Flash new CircuitPython version
2. ✅ Delete old `lib/` folder
3. ✅ Install matching library bundle
4. ✅ Restore your code files

## Still Getting Error?

### Check Library Structure

Your `CIRCUITPY/lib/adafruit_hid/` should look like:
```
adafruit_hid/
├── __init__.mpy
├── keyboard.mpy
├── keycode.mpy
├── mouse.mpy
├── consumer_control.mpy
└── consumer_control_code.mpy
```

**Should NOT have:**
- ❌ find_device.mpy
- ❌ find_device.py

### Verify Bundle Version

Double-check you downloaded **Bundle for Version 10.x**, NOT:
- ❌ Bundle for Version 9.x
- ❌ Bundle for Version 8.x
- ❌ Bundle for Version 7.x

The bundle version must match your CircuitPython version!

### Nuclear Option: Reflash Everything

If all else fails:
1. Flash CircuitPython 10.0.3 (redownload fresh)
2. Format the drive (or delete all files)
3. Fresh install of Bundle 10.x libraries
4. Copy code files fresh from this repo

---

**After the fix, you should be good to go!** The HID keyboard will initialize properly and you can test the timing fix we made earlier. 🎯
