# Example Macro App - Sound FX
# Place this file in the /macros folder on your MacroPad
# Copy to your MacroPad and rename/modify as needed

from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control_code import ConsumerControlCode

app = {
    "name": "Sound FX",
    "macros": [
        # Format: (LED_COLOR, LABEL_TEXT, [ACTIONS])
        # LED_COLOR: 0xRRGGBB hex color
        # LABEL_TEXT: Up to 5 chars displays best
        # ACTIONS: List of actions (see examples below)

        # Example 1: Play a sound file
        (0xFF0000, "FX 1", [{"play": "/sounds/effect1.wav"}]),

        # Example 2: Play sound with different LED color
        (0x00FF00, "FX 2", [{"play": "/sounds/effect2.wav"}]),

        # Example 3: Type text and press Enter
        (0x0000FF, "Hello", ["Hello World!", Keycode.ENTER]),

        # Example 4: Media control (play/pause)
        (0xFFFF00, "Play", [[ConsumerControlCode.PLAY_PAUSE]]),

        # Example 5: Keyboard shortcut (Ctrl+C)
        (0xFF00FF, "Copy", [Keycode.LEFT_CONTROL, Keycode.C, -Keycode.C, -Keycode.LEFT_CONTROL]),

        # Example 6: Multiple actions in sequence with delays
        (0x00FFFF, "Multi", [
            {"play": "/sounds/intro.wav"},
            0.5,  # Wait 0.5 seconds
            "Automated text",
            Keycode.ENTER
        ]),

        # Example 7: Play tone at 440Hz
        (0xFF8800, "Tone", [{"tone": 440}, 0.5, {"tone": 0}]),

        # Example 8: Volume control
        (0x8800FF, "Vol+", [[ConsumerControlCode.VOLUME_INCREMENT]]),

        # Example 9: Another sound effect
        (0xFF0088, "FX 3", [{"play": "/sounds/effect3.wav"}]),

        # Example 10: Mute toggle
        (0x880000, "Mute", [[ConsumerControlCode.MUTE]]),

        # Example 11: Browser control
        (0x008800, "Home", [[ConsumerControlCode.AC_HOME]]),

        # Example 12: Custom keyboard combo
        (0x888888, "Custom", [
            Keycode.LEFT_CONTROL,
            Keycode.LEFT_ALT,
            Keycode.T,
            -Keycode.T,
            -Keycode.LEFT_ALT,
            -Keycode.LEFT_CONTROL
        ]),
    ]
}
