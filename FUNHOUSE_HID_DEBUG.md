# FunHouse HID Debugging Guide

## The Problem

Your FunHouse receives commands from AdafruitIO and displays them on screen, but AutoHotKey isn't detecting the keypresses.

**Root Cause:** The FunHouse was pressing and releasing keys **too fast** (no delay). AutoHotKey needs time to detect the keypress.

## The Fix

Updated `send_key_sequence()` to add a 50ms hold time:

```python
# Press all keys
for key in sequence:
    kbd.press(key)

# Hold for 50ms so OS/AHK can detect
time.sleep(0.05)

# Release all keys
kbd.release_all()
```

## How to Apply the Fix

### Step 1: Update code.py

Copy the updated `funhouse/code.py` to your FunHouse:
```
funhouse/code.py  →  CIRCUITPY/code.py
```

This version includes:
- ✅ 50ms delay between press and release
- ✅ Debug output showing each keypress
- ✅ Better error handling

### Step 2: (Optional) Use Test Macros

For initial testing, use simple macros:

```
funhouse/macros_test.py  →  CIRCUITPY/macros.py
```

This has simple test commands:
- `test_a` - Just types 'a'
- `test_ctrl_a` - Ctrl+A (select all)
- `play_pause` - Your actual command
- `stop` - Emergency stop

### Step 3: Restart FunHouse

1. Safely eject CIRCUITPY
2. Unplug and replug USB
3. Connect to serial console

### Step 4: Test with Simple Command

1. **Open Notepad** (or any text editor)
2. **Send command** to AdafruitIO: `test_a`
3. **Expected result**: Letter 'a' appears in Notepad

**Serial console should show:**
```
Processing command: test_a
Executing macro 'test_a' with 1 keycode(s)
Pressing keys: [4]
  Pressed: 4
Released all keys
```

### Step 5: Test with Ctrl+A

1. **Type some text** in Notepad
2. **Send command**: `test_ctrl_a`
3. **Expected result**: All text is selected

### Step 6: Test Your AutoHotKey Command

1. **Send command**: `play_pause` (or whatever command you're using)
2. **Expected result**: AutoHotKey hotkey triggers

**If it still doesn't work:**
- Check which keycodes your AHK script expects
- Compare with what MacroPad sends (see below)

## Verify FunHouse is Recognized as HID

### Windows

**Device Manager:**
1. Open Device Manager
2. Look under "Keyboards"
3. You should see something like:
   - "USB Input Device" or
   - "HID Keyboard Device" or
   - "Adafruit FunHouse"

**If not listed:**
- Unplug and replug FunHouse
- Check USB cable supports data (not power-only)
- Try different USB port

### Serial Console Output

On startup, you should see:
```
CircuitPython 10.0.3
Loaded X macro(s) from macros.py
USB HID keyboard initialized  ← Must see this!
Display initialized
```

**If you see "ERROR: HID init error":**
- USB HID might be disabled
- Try reflashing CircuitPython
- Check USB cable

## Compare MacroPad vs FunHouse

Since your MacroPad **works** with AutoHotKey, let's make sure FunHouse sends the same keycodes.

### Check Your MacroPad Macro

In your MacroPad's `/macros/yourapp.py`, what keycode sequence triggers AHK?

Example:
```python
(0xFF0000, "Play", [Keycode.CONTROL, Keycode.KEYPAD_PERIOD])
```

### Match in FunHouse

In `funhouse/macros.py`, use the **exact same keycodes**:
```python
{
    "label": "play_pause",
    "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_PERIOD]
}
```

### Common Keycode Differences

| Name | MacroPad | FunHouse | Issue |
|------|----------|----------|-------|
| Keypad numbers | `Keycode.KEYPAD_ONE` | `Keycode.KEYPAD_ONE` | Same ✅ |
| Regular numbers | `Keycode.ONE` | `Keycode.ONE` | Same ✅ |
| Control | `Keycode.CONTROL` or `LEFT_CONTROL` | Same | Usually OK ✅ |
| Alt | `Keycode.ALT` or `LEFT_ALT` | Same | Usually OK ✅ |

**They should be identical!** Both use the same `adafruit_hid` library.

## Advanced Debugging

### 1. Check Serial Console While Sending

Watch serial output when you send a command:

```
Processing command: play_pause
Executing macro 'play_pause' with 2 keycode(s)
Pressing keys: [224, 85]
  Pressed: 224
  Pressed: 85
Released all keys
Display: play_pause
```

**Key numbers:**
- 224 = Left Control
- 85 = Keypad Period

### 2. Test with Windows On-Screen Keyboard

1. Open Windows On-Screen Keyboard
2. Send FunHouse command
3. **Expected**: On-screen keyboard lights up the keys being pressed

**If keys don't light up:** FunHouse HID isn't being recognized properly.

### 3. Use KeyPress Tester Tool

Download a keypress tester (like "Keyboard Test Utility"):
1. Open the tool
2. Send FunHouse command
3. Tool should show which keys were pressed

### 4. Increase Hold Time

If 50ms isn't enough, try 100ms:

Edit `funhouse/code.py`:
```python
time.sleep(0.1)  # Change from 0.05 to 0.1
```

### 5. Check AutoHotKey Script

Make sure your AHK script is:
- **Running** (check system tray)
- **Listening for the right keys**
- **Not paused**

Test by pressing the keys manually on your keyboard:
- Does `Ctrl + Numpad .` trigger your AHK script?
- If not, check your AHK script's hotkey definition

## Still Not Working?

### Option 1: Copy MacroPad Exact Behavior

Tell me:
1. **What MacroPad macro works?** (send me the line from your macros file)
2. **What AHK hotkey is it triggering?**

I can make FunHouse send the **exact same sequence** with **exact same timing**.

### Option 2: Use Different Keycodes

If the issue persists, we can try:
- Different keycode combinations
- Consumer Control codes (media keys)
- Different HID report timing

## Expected Results After Fix

✅ **Serial console shows:**
```
Processing command: play_pause
Pressing keys: [224, 85]
  Pressed: 224
  Pressed: 85
Released all keys
```

✅ **Display shows:** Your command name for 5 seconds

✅ **AutoHotKey triggers:** Your hotkey fires

✅ **MacroPad and FunHouse:** Both work identically

---

**Questions to help debug:**

1. What command are you sending? (e.g., "play_pause")
2. What does your AutoHotKey script expect? (e.g., `^Numpad.::`)
3. What happens if you press those keys manually on your keyboard?
4. Does the simple `test_a` command type 'a' in Notepad?

Let me know the answers and I can help further!
