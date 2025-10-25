"""
CloudFX Settings Loader
Version 1.0

This module provides utilities for loading and validating configuration
from settings.toml and secrets.toml files.

Educational Focus:
- Configuration management best practices
- Error handling and validation
- Separation of concerns (settings vs secrets)
- Type safety and data validation

Author: CloudFX Project
License: MIT
"""

import os
import toml


class SettingsError(Exception):
    """Raised when there is an error loading or validating settings."""
    pass


class Settings:
    """
    Manages application settings and secrets.

    This class demonstrates:
    - Lazy loading of configuration files
    - Validation of required settings
    - Separation of settings and secrets
    - Defensive programming with clear error messages
    """

    def __init__(self, settings_path="settings.toml", secrets_path="secrets.toml"):
        """
        Initialize settings loader.

        Args:
            settings_path: Path to settings.toml file
            secrets_path: Path to secrets.toml file
        """
        self.settings_path = settings_path
        self.secrets_path = secrets_path
        self._settings = None
        self._secrets = None

    def load(self):
        """
        Load both settings and secrets files.

        Raises:
            SettingsError: If required files are missing or invalid
        """
        self._load_settings()
        self._load_secrets()
        self._validate()

    def _load_settings(self):
        """Load and parse settings.toml file."""
        if not os.path.exists(self.settings_path):
            raise SettingsError(
                f"Settings file not found: {self.settings_path}\n"
                "Please ensure settings.toml exists in the root directory."
            )

        try:
            with open(self.settings_path, 'r') as f:
                self._settings = toml.load(f)
        except Exception as e:
            raise SettingsError(
                f"Error parsing settings.toml: {str(e)}\n"
                "Please check the file for syntax errors."
            )

    def _load_secrets(self):
        """Load and parse secrets.toml file."""
        if not os.path.exists(self.secrets_path):
            raise SettingsError(
                f"Secrets file not found: {self.secrets_path}\n"
                "Please copy secrets.toml.example to secrets.toml and fill in your credentials."
            )

        try:
            with open(self.secrets_path, 'r') as f:
                self._secrets = toml.load(f)
        except Exception as e:
            raise SettingsError(
                f"Error parsing secrets.toml: {str(e)}\n"
                "Please check the file for syntax errors."
            )

    def _validate(self):
        """
        Validate that all required settings are present.

        This is an example of defensive programming - we validate early
        to provide clear error messages before the application tries to use
        missing configuration.
        """
        # Validate required secrets
        required_secrets = [
            "CIRCUITPY_WIFI_SSID",
            "CIRCUITPY_WIFI_PASSWORD",
            "ANTHROPIC_API_KEY"
        ]

        for key in required_secrets:
            if key not in self._secrets or not self._secrets[key]:
                raise SettingsError(
                    f"Missing required secret: {key}\n"
                    f"Please add this to {self.secrets_path}"
                )

        # Validate required settings sections
        required_sections = ["camera", "flash", "prompts", "api"]

        for section in required_sections:
            if section not in self._settings:
                raise SettingsError(
                    f"Missing required settings section: [{section}]\n"
                    f"Please check {self.settings_path}"
                )

        # Validate camera resolution is in valid range
        resolution = self._settings.get("camera", {}).get("resolution")
        if resolution is None or not (0 <= resolution <= 6):
            raise SettingsError(
                "Camera resolution must be between 0 and 6\n"
                f"Current value: {resolution}"
            )

    def get(self, key_path, default=None):
        """
        Get a setting value using dot notation.

        Args:
            key_path: Path to setting (e.g., "camera.resolution")
            default: Default value if key not found

        Returns:
            The setting value or default

        Examples:
            >>> settings.get("camera.resolution")
            1
            >>> settings.get("flash.dark_threshold")
            30
        """
        if self._settings is None:
            raise SettingsError("Settings not loaded. Call load() first.")

        keys = key_path.split('.')
        value = self._settings

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_secret(self, key, default=None):
        """
        Get a secret value.

        Args:
            key: Secret key name
            default: Default value if key not found

        Returns:
            The secret value or default
        """
        if self._secrets is None:
            raise SettingsError("Secrets not loaded. Call load() first.")

        return self._secrets.get(key, default)

    def get_prompt(self, prompt_name):
        """
        Get a specific prompt configuration.

        Args:
            prompt_name: Name of the prompt (e.g., "DESCRIBE")

        Returns:
            Dictionary with 'label' and 'prompt' keys

        Raises:
            SettingsError: If prompt not found
        """
        prompts = self._settings.get("prompts", {})
        prompt_config = prompts.get(prompt_name)

        if not prompt_config:
            raise SettingsError(
                f"Prompt '{prompt_name}' not found in settings.\n"
                "Available prompts: " + ", ".join(
                    k for k in prompts.keys() if k != "order"
                )
            )

        return prompt_config

    def get_prompt_order(self):
        """
        Get the ordered list of prompt names.

        Returns:
            List of prompt names in display order
        """
        order_str = self.get("prompts.order", "")
        return [p.strip() for p in order_str.split(',') if p.strip()]

    @property
    def camera_resolution(self):
        """Get camera resolution setting."""
        return self.get("camera.resolution", 1)

    @property
    def auto_flash_enabled(self):
        """Get auto flash enabled setting."""
        return self.get("flash.auto_flash_enabled", True)

    @property
    def dark_threshold(self):
        """Get dark threshold for flash."""
        return self.get("flash.dark_threshold", 30)

    @property
    def api_model(self):
        """Get Claude API model name."""
        return self.get("api.model", "claude-3-haiku-20240307")

    @property
    def max_tokens(self):
        """Get maximum tokens for API response."""
        return self.get("api.max_tokens", 1024)

    @property
    def wifi_ssid(self):
        """Get WiFi SSID from secrets."""
        return self.get_secret("CIRCUITPY_WIFI_SSID")

    @property
    def wifi_password(self):
        """Get WiFi password from secrets."""
        return self.get_secret("CIRCUITPY_WIFI_PASSWORD")

    @property
    def api_key(self):
        """Get Anthropic API key from secrets."""
        return self.get_secret("ANTHROPIC_API_KEY")


def load_settings():
    """
    Convenience function to load and return settings.

    Returns:
        Settings: Loaded and validated settings object

    Example:
        >>> settings = load_settings()
        >>> print(settings.camera_resolution)
        1
    """
    settings = Settings()
    settings.load()
    return settings


# Example usage when run as main (for testing)
if __name__ == "__main__":
    try:
        settings = load_settings()
        print("✓ Settings loaded successfully!")
        print(f"  Camera resolution: {settings.camera_resolution}")
        print(f"  Auto flash: {settings.auto_flash_enabled}")
        print(f"  Dark threshold: {settings.dark_threshold}")
        print(f"  API model: {settings.api_model}")
        print(f"  Prompts configured: {len(settings.get_prompt_order())}")
    except SettingsError as e:
        print(f"✗ Settings error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
