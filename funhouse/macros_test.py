# Test macros for FunHouse HID debugging
# Replace your macros.py with this temporarily to test

from adafruit_hid.keycode import Keycode

class Macros:
    """Simple test macros to verify HID is working."""

    macros = [
        # Simple single key test
        {
            "label": "test_a",
            "keycodes": [Keycode.A]
        },

        # Simple combo test
        {
            "label": "test_ctrl_a",
            "keycodes": [Keycode.CONTROL, Keycode.A]
        },

        # Your actual command (adjust to match your AHK script)
        {
            "label": "play_pause",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_PERIOD]
        },

        # Emergency stop (matches MacroPad)
        {
            "label": "stop",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_MINUS]
        },
    ]
