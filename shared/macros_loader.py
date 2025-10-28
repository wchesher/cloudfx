# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX Macro Loader - JSON Parser for Both Devices
# ====================================================
# Shared module for loading macros.json on MacroPad and FunHouse

import json
from adafruit_hid.keycode import Keycode


class MacroLoader:
    """Load and parse macros.json for both MacroPad and FunHouse."""

    def __init__(self, json_path="/macros.json"):
        """
        Initialize the macro loader.

        Args:
            json_path: Path to macros.json file on device
        """
        self.json_path = json_path
        self.data = None
        self._load_json()

    def _load_json(self):
        """Load JSON from file."""
        try:
            with open(self.json_path, "r") as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load {self.json_path}: {e}")
            self.data = {"apps": []}

    def _keycode_from_string(self, keycode_str):
        """
        Convert keycode string to Keycode constant.

        Args:
            keycode_str: String like "CONTROL", "A", "F5"

        Returns:
            Keycode constant or None if not found
        """
        try:
            return getattr(Keycode, keycode_str)
        except AttributeError:
            print(f"WARNING: Unknown keycode '{keycode_str}'")
            return None

    def _convert_keycodes(self, keycode_strings):
        """
        Convert list of keycode strings to list of Keycode constants.

        Args:
            keycode_strings: List of strings like ["CONTROL", "A"]

        Returns:
            List of Keycode constants
        """
        keycodes = []
        for key_str in keycode_strings:
            keycode = self._keycode_from_string(key_str)
            if keycode is not None:
                keycodes.append(keycode)
        return keycodes

    def get_apps_for_macropad(self):
        """
        Get apps formatted for MacroPad.

        Returns:
            List of dicts with:
            {
                "name": "App Name",
                "macros": [
                    (color_int, label_str, [Keycode.X, Keycode.Y, ...]),
                    ...
                ]
            }
        """
        apps = []

        for app_data in self.data.get("apps", []):
            app_name = app_data.get("name", "Unnamed")
            macros = []

            for button in app_data.get("buttons", []):
                # Convert color string to int
                color_str = button.get("color", "0xFFFFFF")
                color_int = int(color_str, 16)

                # Get label
                label = button.get("label", "???")

                # Convert keycodes
                keycode_strings = button.get("keycodes", [])
                keycodes = self._convert_keycodes(keycode_strings)

                # Create macro tuple: (color, label, actions)
                macros.append((color_int, label, keycodes))

            apps.append({
                "name": app_name,
                "macros": macros
            })

        return apps

    def get_commands_for_funhouse(self):
        """
        Get commands formatted for FunHouse.

        Returns:
            Dict mapping command name to keycodes:
            {
                "play_pause": [Keycode.CONTROL, Keycode.KEYPAD_PERIOD],
                "next_track": [Keycode.CONTROL, Keycode.KEYPAD_PLUS],
                ...
            }
        """
        commands = {}

        for app_data in self.data.get("apps", []):
            for button in app_data.get("buttons", []):
                command = button.get("command")
                keycode_strings = button.get("keycodes", [])

                if command:
                    keycodes = self._convert_keycodes(keycode_strings)
                    commands[command] = keycodes

        return commands

    def get_command_keycodes(self, command_name):
        """
        Get keycodes for a specific command (FunHouse usage).

        Args:
            command_name: Command name like "play_pause"

        Returns:
            List of Keycode constants or None if not found
        """
        commands = self.get_commands_for_funhouse()
        return commands.get(command_name)
