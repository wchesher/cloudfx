# Macro definitions for CloudFX FunHouse
# Each macro maps a label (command name) to a sequence of HID keycodes
#
# Format:
# {
#     "label": "command_name",  # Must match commands sent to AdafruitIO feed
#     "keycodes": [Keycode.X, Keycode.Y, ...]  # Key sequence to send
# }

from adafruit_hid.keycode import Keycode

class Macros:
    """Macro definitions for FunHouse command processing."""

    macros = [
        # Media controls
        {
            "label": "play_pause",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_PERIOD]
        },
        {
            "label": "next_track",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_PLUS]
        },
        {
            "label": "prev_track",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_MINUS]
        },

        # Volume controls
        {
            "label": "volume_up",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_EIGHT]
        },
        {
            "label": "volume_down",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_TWO]
        },
        {
            "label": "mute",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_ZERO]
        },

        # Application controls
        {
            "label": "stop_playback",
            "keycodes": [Keycode.CONTROL, Keycode.KEYPAD_MINUS]
        },
        {
            "label": "start_recording",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.R]
        },
        {
            "label": "stop_recording",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.S]
        },

        # Scene/mode switching
        {
            "label": "scene_1",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.ONE]
        },
        {
            "label": "scene_2",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.TWO]
        },
        {
            "label": "scene_3",
            "keycodes": [Keycode.CONTROL, Keycode.ALT, Keycode.THREE]
        },

        # Window/app switching
        {
            "label": "switch_audio",
            "keycodes": [Keycode.CONTROL, Keycode.SHIFT, Keycode.A]
        },
        {
            "label": "minimize_all",
            "keycodes": [Keycode.GUI, Keycode.D]
        },

        # Custom commands (examples)
        {
            "label": "emergency_stop",
            "keycodes": [Keycode.ESCAPE]
        },
        {
            "label": "refresh",
            "keycodes": [Keycode.F5]
        },

        # Add your custom macros here
        # {
        #     "label": "your_command",
        #     "keycodes": [Keycode.YOUR, Keycode.KEYS]
        # },
    ]
