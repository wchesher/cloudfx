# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
# SPDX-License-Identifier: MIT
#
# CloudFX MacroPad - Optimized & Clean
# CircuitPython 10.0.3
# ====================================================
#
# Fast, clean macro pad controller with JSON-based configuration.
# Optimized for maximum responsiveness with LCD burn-in protection.
#
# Features:
#  - JSON-based macro loading (single source of truth with FunHouse)
#  - 12 macro buttons + encoder click (13th button from JSON)
#  - Page rotation via encoder
#  - Screensaver: dims LEDs to 5% and blanks display (prevents LCD burn-in)
#  - HID keyboard shortcuts only (fast, no complex action types)
#  - Clean, maintainable code
#
# Prerequisites:
#  - CircuitPython 10.0.3+ on Adafruit MacroPad
#  - Libraries: adafruit_macropad, adafruit_hid, adafruit_display_text
#  - /macros.json and /macros_loader.py on device (from shared/)

import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from macros_loader import MacroLoader

# -------------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------------
REGULAR_BRIGHTNESS = 0.3    # Regular LED brightness (default 30%)
SCREENSAVER_TIMEOUT = 30    # Seconds before dimming LEDs (0 = disable)
DIM_BRIGHTNESS = 0.05       # LED brightness when screensaver active

# -------------------------------------------------------------------------------
# INITIALIZE HARDWARE
# -------------------------------------------------------------------------------
macropad = MacroPad()
macropad.display.auto_refresh = False
macropad.pixels.auto_write = False

display = macropad.display
pixels = macropad.pixels

# Set regular brightness
pixels.brightness = REGULAR_BRIGHTNESS
orig_brightness = REGULAR_BRIGHTNESS

# -------------------------------------------------------------------------------
# BUILD UI (12 KEY LABELS + HEADER)
# -------------------------------------------------------------------------------
group = displayio.Group()
labels = []

# Create 12 labels in 3x4 grid
for i in range(12):
    col, row = i % 3, i // 3
    x = (display.width - 1) * col / 2
    y = display.height - 1 - (3 - row) * 12
    lbl = label.Label(
        terminalio.FONT,
        text="",
        color=0xFFFFFF,
        anchored_position=(x, y),
        anchor_point=(col / 2, 1.0)
    )
    labels.append(lbl)
    group.append(lbl)

# Header bar and text
header_rect = Rect(0, 0, display.width, 13, fill=0xFFFFFF)
header_text = label.Label(
    terminalio.FONT,
    text="",
    color=0x000000,
    anchored_position=(display.width // 2, 0),
    anchor_point=(0.5, 0.0)
)
group.append(header_rect)
group.append(header_text)
display.root_group = group

# Blank screen for screensaver (prevent LCD burn-in)
blank_group = displayio.Group()
blank_group.append(Rect(0, 0, display.width, display.height, fill=0x000000))
print("Screensaver blank screen ready")

# -------------------------------------------------------------------------------
# APP CLASS (SIMPLIFIED)
# -------------------------------------------------------------------------------
class App:
    """Represents one page of macros."""

    def __init__(self, appdata):
        self.name = appdata.get("name", "")
        self.macros = appdata.get("macros", [])

    def activate(self):
        """Draw app name, labels, and LED colors."""
        header_text.text = self.name
        header_rect.fill = 0xFFFFFF if self.name else 0x000000

        for i in range(12):
            if i < len(self.macros):
                color, text, _ = self.macros[i]
                pixels[i] = color
                labels[i].text = text
            else:
                pixels[i] = 0
                labels[i].text = ""

        # Release all HID keys
        macropad.keyboard.release_all()

        # Only update display if screen is active (prevents flickering)
        if screen_active:
            pixels.show()
            display.refresh()

# -------------------------------------------------------------------------------
# LOAD MACROS FROM JSON
# -------------------------------------------------------------------------------
print("Loading macros from JSON...")
loader = MacroLoader("/macros.json")
apps = [App(data) for data in loader.get_apps_for_macropad()]
print(f"Loaded {len(apps)} apps")

if not apps:
    header_text.text = "NO MACROS"
    display.refresh()
    print("ERROR: No macros found in /macros.json")
    while True:
        time.sleep(1)

# -------------------------------------------------------------------------------
# SCREENSAVER (PREVENTS LCD BURN-IN)
# -------------------------------------------------------------------------------
screen_active = True
last_activity = time.monotonic()

def activate_screensaver():
    """Dim LEDs to 5% and blank display to prevent burn-in."""
    global screen_active
    if not screen_active:
        return  # Already in screensaver

    # Dim LEDs to 5%
    pixels.brightness = DIM_BRIGHTNESS
    pixels.show()

    # Blank display (prevent LCD burn-in)
    display.root_group = blank_group
    display.refresh()

    screen_active = False
    print("Screensaver active")

def wake_from_screensaver():
    """Restore brightness and display on activity."""
    global screen_active, last_activity, current_app

    if screen_active:
        # Already awake, just update activity time
        last_activity = time.monotonic()
        return

    # Set screen active BEFORE restoring (so activate() will refresh)
    screen_active = True
    last_activity = time.monotonic()

    # Restore LED brightness
    pixels.brightness = orig_brightness

    # Restore display
    display.root_group = group

    # Redraw current app (will now properly show/refresh)
    apps[current_app].activate()

    print("Screensaver wake")

def check_screensaver():
    """Check if screensaver should activate."""
    if SCREENSAVER_TIMEOUT == 0:
        return  # Screensaver disabled

    if screen_active and (time.monotonic() - last_activity >= SCREENSAVER_TIMEOUT):
        activate_screensaver()

# -------------------------------------------------------------------------------
# MACRO EXECUTION (OPTIMIZED - HID ONLY)
# -------------------------------------------------------------------------------
def execute_macro(keycodes):
    """Execute HID key sequence. Fast, no overhead."""
    # Press all keys
    for keycode in keycodes:
        macropad.keyboard.press(keycode)

    # Hold briefly (50ms minimum for reliable HID detection)
    time.sleep(0.05)

    # Release all keys
    macropad.keyboard.release_all()

# -------------------------------------------------------------------------------
# MAIN LOOP (OPTIMIZED)
# -------------------------------------------------------------------------------
print("MacroPad ready!")

# Initialize encoder tracking and sync current_app with encoder position
last_encoder_pos = macropad.encoder
current_app = last_encoder_pos % len(apps)
apps[current_app].activate()

last_encoder_btn = False

while True:
    # Check screensaver timeout
    check_screensaver()

    # --- ENCODER ROTATION (Page Select) ---
    encoder_pos = macropad.encoder
    if encoder_pos != last_encoder_pos:
        wake_from_screensaver()
        last_encoder_pos = encoder_pos
        current_app = encoder_pos % len(apps)
        apps[current_app].activate()
        continue

    # --- ENCODER CLICK (13th Button from JSON) ---
    macropad.encoder_switch_debounced.update()
    encoder_btn = macropad.encoder_switch_debounced.pressed

    if encoder_btn != last_encoder_btn:
        wake_from_screensaver()
        last_encoder_btn = encoder_btn

        if encoder_btn:  # Button pressed
            # Execute 13th macro from JSON (encoder click)
            if len(apps[current_app].macros) > 12:
                _, _, keycodes = apps[current_app].macros[12]
                execute_macro(keycodes)
        continue

    # --- KEY PRESS/RELEASE (Macros 0-11) ---
    event = macropad.keys.events.get()
    if not event:
        continue

    wake_from_screensaver()
    key_num = event.key_number

    # Validate key number
    if key_num >= len(apps[current_app].macros):
        continue

    color, text, keycodes = apps[current_app].macros[key_num]

    if event.pressed:
        # Key down: flash white and execute macro (only if awake)
        if screen_active:
            pixels[key_num] = 0xFFFFFF
            pixels.show()
        execute_macro(keycodes)
    else:
        # Key up: restore LED color (only if awake)
        if screen_active:
            pixels[key_num] = color
            pixels.show()
