# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
# SPDX-License-Identifier: MIT
#
# MACRO FX for MacroPad - CircuitPython 10.0.3 Edition
# --------------------------------------------
# A robust, student-friendly MacroPad script with screensaver, LED dimming, unified OFF handling,
# and error resilience. If anything goes wrong, the board attempts to recover rather than freeze.
#
# Functionality:
#  - Load "apps" (macro sets) from /macros.json (shared with FunHouse)
#  - Show 12 labels/LEDs per page, navigate pages via the encoder
#  - Execute HID, consumer control, mouse, tone, or file-playback actions on keypress
#  - Unified "OFF" on encoder click: send CTRL+ALT+SHIFT+ESC to stop playback
#  - Screensaver after inactivity: dim LEDs + blank screen, wakes on any input
#  - Graceful error handling everywhere—no unhandled crashes
#  - Comments throughout explain each step for beginners
#
# Prerequisites:
#  - CircuitPython 10.0.3 (or 10.x) on an Adafruit MacroPad
#  - Required libraries from CircuitPython 10.x Bundle:
#    * adafruit_macropad
#    * adafruit_hid
#    * adafruit_display_text
#    * adafruit_display_shapes
#    * neopixel (bundled with MacroPad)
#  - A /macros.json file (copy from shared/macros.json in repository)
#    This JSON defines apps (pages) with buttons containing:
#      - name: App page name
#      - buttons: List of button definitions with label, command, color, keycodes
#
# CircuitPython 10.0.3 Compatibility Notes:
#  - This code has been updated for CP 10.0.3 compatibility
#  - Uses only stable displayio APIs (no deprecated bindings)
#  - Compatible with CircuitPython Bundle 10.x libraries
#  - Error handling uses traceback module (sys.print_exception removed in CP 10)
#
# The /macros.json file can contain multiple "apps" (pages). Each app can have up to 12
# button definitions. Each button specifies keycodes that will be sent when pressed.

import os                                       # For file operations
import sys                                      # For version checking
import time                                     # For sleep() and tracking monotonic time
import displayio                                # To manage the on-board display layers
import terminalio                               # Builtin font for drawing text
import traceback                                # For exception printing (CP 10.x compatible)
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from adafruit_hid.keycode import Keycode        # HID keycodes for keyboard use
import microcontroller                          # For potential watchdog timer use
import supervisor                               # For soft-reboot on fatal errors

# Import JSON loader for macros
try:
    from macros_loader import MacroLoader
except ImportError:
    print("ERROR: macros_loader.py not found!")
    print("Copy shared/macros_loader.py to device")
    raise

# -------------------------------------------------------------------------------
# VERSION CHECK: Ensure we're running on CircuitPython 10.x or later
# -------------------------------------------------------------------------------
try:
    cp_version = sys.implementation.version
    if cp_version[0] < 10:
        print(f"WARNING: This code is designed for CircuitPython 10.x")
        print(f"You are running {cp_version[0]}.{cp_version[1]}.{cp_version[2]}")
        print("Some features may not work correctly. Please upgrade to CP 10.0.3+")
except Exception as e:
    print("Could not determine CircuitPython version:", e)

# The following imports are used only if needed at runtime; we wrap them in try/except
# to avoid a crash if any single piece is missing or fails.
try:
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.consumer_control import ConsumerControl
    from adafruit_hid.consumer_control_code import ConsumerControlCode
    from adafruit_hid.mouse import Mouse
except ImportError as e:
    # If HID modules fail to import, we still want the script to run (just disable HID).
    print("Warning: HID import failed:", e)
    Keyboard = None
    ConsumerControl = None
    ConsumerControlCode = None
    Mouse = None

# -------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# -------------------------------------------------------------------------------
SCREENSAVER_TIMEOUT = 20             # Seconds of inactivity before blanking screen
DIM_BRIGHTNESS      = 0.05           # LED brightness (5%) when screensaver is active
ENCODER_OFF_LABEL   = "OFF"          # Text to display when encoder click (key 12) is pressed

# -------------------------------------------------------------------------------
# INITIALIZE HARDWARE & GLOBAL STATE
# -------------------------------------------------------------------------------

# Instantiate the MacroPad object
try:
    macropad = MacroPad()
    print(f"MacroPad initialized successfully")
except Exception as e:
    # If MacroPad fails to initialize, nothing else can proceed. Halt indefinitely.
    print("ERROR: Could not initialize MacroPad hardware:")
    traceback.print_exception(type(e), e, e.__traceback__)
    while True:
        time.sleep(1)

# For convenience, alias display and pixels (LEDs)
display = macropad.display
pixels  = macropad.pixels

# Disable automatic updates; we will refresh manually when needed
macropad.display.auto_refresh = False
macropad.pixels.auto_write   = False

# Store original LED brightness to restore after screensaver
orig_brightness = pixels.brightness

# Track whether the screen is currently "active" (not blanked by screensaver)
screen_active = True
# Record time of last input (key press or encoder movement)
last_activity = time.monotonic()

# -------------------------------------------------------------------------------
# BUILD UI LAYOUT FOR 12 KEYS + HEADER
# -------------------------------------------------------------------------------

# We will display 12 labels (one for each physical key) plus a header bar at the top.

# Group that holds all active-page labels + header
group = displayio.Group()
# List of Label objects, one per key (0–11)
labels = []

# Create 12 labels arranged in a 3×4 grid:
#   - positions: x = 0,1,2 → columns; y = 0,1,2,3 → rows
for idx in range(12):
    col = idx % 3
    row = idx // 3
    # Text anchor: centered horizontally in each third of screen
    x_pos = (display.width - 1) * col / 2
    # y_pos: leave 13 pixels at top for header, then stack rows downward
    y_pos = display.height - 1 - (3 - row) * 12
    lbl = label.Label(
        terminalio.FONT,
        text="",
        color=0xFFFFFF,
        anchored_position=(x_pos, y_pos),
        anchor_point=(col / 2, 1.0),
    )
    labels.append(lbl)
    group.append(lbl)

# Create header bar (white rectangle) and header text (black) at top
header_rect = Rect(0, 0, display.width, 13, fill=0xFFFFFF)
header_text = label.Label(
    terminalio.FONT,
    text="",
    color=0x000000,
    anchored_position=(display.width // 2, 0),
    anchor_point=(0.5, 0.0),
)
group.append(header_rect)
group.append(header_text)

# Assign this group as the root for display
display.root_group = group

# For the screensaver, we will swap in a "blank" group that covers the whole screen
blank_group = displayio.Group()
blank_group.append(
    Rect(0, 0, display.width, display.height, fill=0x000000)
)

# -------------------------------------------------------------------------------
# SCREENSAVER FUNCTIONS
# -------------------------------------------------------------------------------
def blank_screen():
    """
    Dim LEDs to DIM_BRIGHTNESS and display a solid black screen.
    Called when SCREENSAVER_TIMEOUT elapses without input.
    """
    global screen_active
    try:
        pixels.brightness = DIM_BRIGHTNESS
        pixels.show()
    except Exception as e:
        print("Warning: could not dim pixels:")
        traceback.print_exception(type(e), e, e.__traceback__)
    try:
        display.root_group = blank_group
        display.refresh()
    except Exception as e:
        print("Warning: could not blank display:")
        traceback.print_exception(type(e), e, e.__traceback__)
    screen_active = False


def restore_screen():
    """
    Restore LEDs to original brightness and return to the main UI group.
    Also re-paint the current app's labels by calling its activate() method.
    """
    global screen_active, last_activity
    try:
        pixels.brightness = orig_brightness
        pixels.show()
    except Exception as e:
        print("Warning: could not restore pixel brightness:")
        traceback.print_exception(type(e), e, e.__traceback__)
    try:
        display.root_group = group
        # Re-activate the current app so labels/LEDs redraw
        if apps and 0 <= current_app < len(apps):
            apps[current_app].activate()
    except Exception as e:
        print("Warning: could not restore display:")
        traceback.print_exception(type(e), e, e.__traceback__)
    screen_active = True
    last_activity = time.monotonic()


def wake_if_needed():
    """
    If the screensaver is currently active (blank screen), restore it.
    Called whenever we detect input (encoder or key event).
    """
    if not screen_active:
        restore_screen()

# -------------------------------------------------------------------------------
# "OFF" ACTION (Encoder Click)
# -------------------------------------------------------------------------------
def send_Escape():
    """
    Send a CTRL+KEYPAD_MINUS keystroke via USB HID to signal the host to stop playback.
    We press, wait a short time, then release.
    """
    if not hasattr(macropad, "keyboard") or macropad.keyboard is None:
        return
    try:
        macropad.keyboard.press(Keycode.LEFT_CONTROL, Keycode.KEYPAD_MINUS)
        time.sleep(0.05)
        macropad.keyboard.release(Keycode.LEFT_CONTROL, Keycode.KEYPAD_MINUS)
    except Exception as e:
        print("Warning: could not send Escape combo:")
        traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# APPLICATION CONTAINER CLASS
# -------------------------------------------------------------------------------
class App:
    """
    Represents a single "page" of 12 macros.
    Expects a dictionary `appdata` with keys:
      - "name": string (app title)
      - "macros": list of up to 12 tuples:
          (led_color (int hex), label_text (str), action_sequence (list))
    The action_sequence can contain:
      - int >= 0: HID Keycode press
      - int < 0 : HID Keycode release (-value)
      - float   : delay in seconds
      - str     : literal string to type via keyboard_layout.write()
      - list    : interpret as consumer/mouse codes (see below)
      - dict    : interpret for mouse move / tone / file playback
    """
    def __init__(self, appdata):
        self.name   = appdata.get("name", "")
        self.macros = appdata.get("macros", [])

    def activate(self):
        """
        Draw the app's name in the header, set LED colors and labels for each key,
        then release any held HID states. Called whenever we switch pages.
        """
        # Update header text and rectangle color (invert if no name)
        header_text.text = self.name
        header_rect.fill = 0xFFFFFF if self.name else 0x000000

        # For each of the 12 physical keys:
        for i in range(12):
            try:
                if i < len(self.macros):
                    led_color, label_text, _ = self.macros[i]
                    pixels[i]        = led_color
                    labels[i].text   = label_text
                else:
                    # No macro defined at this index: turn LED off and blank label
                    pixels[i]        = 0
                    labels[i].text   = ""
            except Exception as e:
                # Safeguard against malformed macro entries
                pixels[i]      = 0
                labels[i].text = ""
                print(f"Warning: bad macro data at index {i} in '{self.name}':")
                traceback.print_exception(type(e), e, e.__traceback__)

        # Release all HID states to avoid any stuck keys/buttons/tone
        try:
            if hasattr(macropad, "keyboard") and macropad.keyboard:
                macropad.keyboard.release_all()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        try:
            if hasattr(macropad, "consumer_control") and macropad.consumer_control:
                macropad.consumer_control.release()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        try:
            if hasattr(macropad, "mouse") and macropad.mouse:
                macropad.mouse.release_all()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        try:
            macropad.stop_tone()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

        try:
            pixels.show()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        try:
            display.refresh()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# LOAD MACRO APPS FROM JSON
# -------------------------------------------------------------------------------
apps = []

try:
    loader = MacroLoader("/macros.json")
    app_data_list = loader.get_apps_for_macropad()

    for app_data in app_data_list:
        apps.append(App(app_data))
        print(f"Loaded macro app: {app_data.get('name', 'Unnamed')}")

    print(f"Successfully loaded {len(apps)} macro app(s) from macros.json")

except Exception as e:
    print("ERROR: Could not load macros from macros.json")
    traceback.print_exception(type(e), e, e.__traceback__)

# If no apps loaded, show "NO MACROS" and halt
if not apps:
    header_text.text = "NO MACROS"
    try:
        display.refresh()
    except Exception:
        pass
    print("ERROR: No macro apps found in macros.json")
    print("Copy shared/macros.json to device as /macros.json")
    while True:
        time.sleep(1)

# -------------------------------------------------------------------------------
# INITIAL PAGE STATE
# -------------------------------------------------------------------------------
last_pos     = macropad.encoder  # Current encoder position
last_enc_btn = macropad.encoder_switch_debounced.pressed  # Encoder switch (click) state
current_app  = 0                  # Index of the current App in apps[]
# Activate the first app/page:
try:
    apps[0].activate()
    print(f"Active app: {apps[0].name}")
except Exception as e:
    print("Error activating initial app:")
    traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# MAIN LOOP – HANDLE ENCODER, BUTTONS, SCREENSAVER, MACRO EXECUTION
# -------------------------------------------------------------------------------
print("MacroFX ready. Starting main loop...")

while True:
    now = time.monotonic()

    # 1) SCREENSAVER: If the screen is active and we haven't seen input for SCREENSAVER_TIMEOUT,
    #    then blank the screen (dim LEDs + show black display).
    if screen_active and (now - last_activity) >= SCREENSAVER_TIMEOUT:
        blank_screen()

    # 2) ENCODER ROTATION: If the encoder position changed, treat it as "page select".
    pos = macropad.encoder
    if pos != last_pos:
        last_pos      = pos
        wake_if_needed()
        last_activity = now
        # Wrap around number of apps
        current_app   = pos % len(apps)
        try:
            apps[current_app].activate()
        except Exception as e:
            print(f"Error activating app index {current_app}:")
            traceback.print_exception(type(e), e, e.__traceback__)
        continue  # skip to next iteration (don't process keys this same loop)

    # 3) ENCODER CLICK vs. KEYPAD EVENT:
    macropad.encoder_switch_debounced.update()
    enc_btn = macropad.encoder_switch_debounced.pressed
    if enc_btn != last_enc_btn:
        # Encoder switch state changed (pressed or released)
        last_enc_btn  = enc_btn
        wake_if_needed()
        last_activity = now
        key_idx, pressed = 12, enc_btn  # We assign index 12 for encoder "OFF" action
    else:
        # No change in encoder switch—check for a key press/release event
        event = macropad.keys.events.get()
        if not event or event.key_number >= len(apps[current_app].macros):
            # No event or invalid index—nothing to do this iteration
            continue
        wake_if_needed()
        last_activity = now
        key_idx, pressed = event.key_number, event.pressed

    # 4) ENCODER CLICK HANDLING: Execute 13th button action from JSON (index 12)
    # This allows each app to define custom encoder click behavior in macros.json
    if key_idx == 12:
        if pressed:
            # Fetch the 13th macro (encoder click) from current app
            try:
                if len(apps[current_app].macros) > 12:
                    color, label_text, seq = apps[current_app].macros[12]
                    # Execute the encoder macro sequence
                    for item in seq:
                        if isinstance(item, int) and item >= 0:
                            macropad.keyboard.press(item)
                    time.sleep(0.05)  # Hold for 50ms
                    macropad.keyboard.release_all()
                else:
                    # Fallback if no 13th macro defined
                    send_Escape()
            except Exception as e:
                print(f"Error executing encoder action:")
                traceback.print_exception(type(e), e, e.__traceback__)
                send_Escape()  # Fallback to hardcoded action
        continue

    # 5) MACRO EXECUTION: Look up the macro corresponding to (current_app, key_idx)
    try:
        color, label_text, seq = apps[current_app].macros[key_idx]
    except Exception as e:
        print(f"Error fetching macro data for app {current_app}, key {key_idx}:")
        traceback.print_exception(type(e), e, e.__traceback__)
        continue

    if pressed:
        # a) KEY DOWN: flash LED white, then execute each action in sequence
        try:
            pixels[key_idx] = 0xFFFFFF
            pixels.show()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

        # Execute each element of seq, allowing multiple types
        for act in seq:
            try:
                # 5.1) If act is an integer:
                #      - If >=  0: treat as HID Keycode press
                #      - If <  0: treat as HID Keycode release (-act)
                if isinstance(act, int):
                    if act >= 0:
                        if macropad.keyboard:
                            macropad.keyboard.press(act)
                    else:
                        if macropad.keyboard:
                            macropad.keyboard.release(-act)

                # 5.2) If act is a float: pause for that many seconds
                elif isinstance(act, float):
                    time.sleep(act)

                # 5.3) If act is a string: send literal text via keyboard_layout
                elif isinstance(act, str):
                    if macropad.keyboard:
                        macropad.keyboard_layout.write(act)

                # 5.4) If act is a list: interpret as consumer_control codes
                elif isinstance(act, list):
                    # Example: [ConsumerControlCode.VOLUME_UP, 0.1, ConsumerControlCode.VOLUME_DOWN]
                    for code in act:
                        if isinstance(code, int):
                            if macropad.consumer_control:
                                # Always release any previous consumer button first
                                macropad.consumer_control.release()
                                macropad.consumer_control.press(code)
                        elif isinstance(code, float):
                            time.sleep(code)

                # 5.5) If act is a dict: support mouse / tone / file playback
                elif isinstance(act, dict):
                    # 5.5a) Mouse buttons + movement
                    if "buttons" in act or "x" in act or "y" in act or "wheel" in act:
                        btn = act.get("buttons", None)
                        if btn is not None:
                            if btn >= 0:
                                if macropad.mouse:
                                    macropad.mouse.press(btn)
                            else:
                                if macropad.mouse:
                                    macropad.mouse.release(-btn)
                        # Mouse move/wheel does not require press/release
                        mx = act.get("x", 0)
                        my = act.get("y", 0)
                        mw = act.get("wheel", 0)
                        if macropad.mouse and any([mx, my, mw]):
                            macropad.mouse.move(mx, my, mw)

                    # 5.5b) Tone generation
                    if "tone" in act:
                        t = act["tone"]
                        if t > 0:
                            macropad.stop_tone()
                            macropad.start_tone(t)
                        else:
                            macropad.stop_tone()

                    # 5.5c) File playback (e.g., WAV/MP3)
                    if "play" in act:
                        try:
                            macropad.play_file(act["play"])
                        except Exception as e:
                            print(f"Error playing file '{act['play']}':")
                            traceback.print_exception(type(e), e, e.__traceback__)

                else:
                    # Unknown action type—skip
                    print(f"Warning: unhandled action type: {type(act)}")

            except Exception as e:
                # Catch any exception inside the action loop and continue
                print(f"Error executing action {act}:")
                traceback.print_exception(type(e), e, e.__traceback__)
                # Attempt to clear any stuck HID state
                try:
                    if macropad.keyboard:
                        macropad.keyboard.release_all()
                except Exception:
                    pass
                try:
                    if macropad.consumer_control:
                        macropad.consumer_control.release()
                except Exception:
                    pass
                try:
                    if macropad.mouse:
                        macropad.mouse.release_all()
                except Exception:
                    pass

    else:
        # b) KEY UP: release any HID or mouse states, stop tones if needed, restore LED
        for act in seq:
            try:
                if isinstance(act, int) and act >= 0:
                    # Release that HID key
                    if macropad.keyboard:
                        macropad.keyboard.release(act)
                elif isinstance(act, dict) and "buttons" in act:
                    # Release mouse button
                    btn = act["buttons"]
                    if btn >= 0 and macropad.mouse:
                        macropad.mouse.release(btn)
                elif isinstance(act, dict) and "tone" in act:
                    # Stop tone if it was playing
                    macropad.stop_tone()
            except Exception as e:
                print(f"Error on key-up for action {act}:")
                traceback.print_exception(type(e), e, e.__traceback__)

        # Always release any held consumer control buttons
        try:
            if macropad.consumer_control:
                macropad.consumer_control.release()
        except Exception:
            pass

        # Restore LED color for this key
        try:
            pixels[key_idx] = apps[current_app].macros[key_idx][0]
            pixels.show()
        except Exception:
            pass

    # 6) Continue; next loop handles screensaver, encoder, etc.

# End
