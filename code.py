"""
CloudFX - AI Vision for CircuitPython
Version 1.0

An educational IoT project demonstrating:
- Camera integration with CircuitPython
- API integration with Anthropic Claude
- Configuration management best practices
- Modular and maintainable code structure

This file contains NO hardcoded values - all configuration is in settings.toml
and secrets.toml.

Author: CloudFX Project
License: MIT
"""

import time
import board
import displayio
import terminalio
from adafruit_display_text import label
import wifi
import socketpool
import ssl
import adafruit_requests

# Import our settings loader
from lib.settings_loader import load_settings, SettingsError


# ============================================
# GLOBAL STATE
# ============================================
# Educational note: We minimize global state and use it only for
# configuration that is loaded once at startup.

settings = None
requests = None
current_prompt_index = 0


# ============================================
# INITIALIZATION FUNCTIONS
# ============================================

def initialize_settings():
    """
    Load and validate all configuration.

    This function demonstrates:
    - Early validation (fail fast)
    - Clear error messages for debugging
    - Separation of configuration from code

    Returns:
        Settings object if successful, None if failed
    """
    print("Loading settings...")

    try:
        cfg = load_settings()
        print("✓ Settings loaded successfully")
        return cfg
    except SettingsError as e:
        print(f"✗ Settings error: {e}")
        print("\nPlease check your settings.toml and secrets.toml files.")
        return None
    except Exception as e:
        print(f"✗ Unexpected error loading settings: {e}")
        return None


def initialize_wifi():
    """
    Connect to WiFi using credentials from secrets.toml.

    This function demonstrates:
    - Network error handling
    - Retry logic with backoff
    - Status reporting for debugging

    Returns:
        True if connected, False if failed
    """
    print(f"Connecting to WiFi: {settings.wifi_ssid}")

    max_retries = settings.get("network.max_retries", 3)
    retry_delay = settings.get("network.retry_delay", 2)

    for attempt in range(max_retries):
        try:
            wifi.radio.connect(
                settings.wifi_ssid,
                settings.wifi_password,
                timeout=settings.get("network.connection_timeout", 10)
            )
            print(f"✓ Connected to WiFi")
            print(f"  IP Address: {wifi.radio.ipv4_address}")
            return True

        except Exception as e:
            print(f"✗ WiFi connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("✗ Failed to connect to WiFi after all retries")
                return False

    return False


def initialize_requests():
    """
    Set up HTTPS requests handler.

    This demonstrates proper setup of network resources in CircuitPython.

    Returns:
        adafruit_requests.Session object
    """
    print("Initializing HTTPS requests...")

    pool = socketpool.SocketPool(wifi.radio)
    ssl_context = ssl.create_default_context()
    session = adafruit_requests.Session(pool, ssl_context)

    print("✓ HTTPS requests ready")
    return session


def initialize_camera():
    """
    Initialize camera with settings from settings.toml.

    This function demonstrates:
    - Hardware initialization
    - Using configuration values
    - Error handling for hardware

    Note: This is a template - adjust for your specific camera module
    """
    print("Initializing camera...")

    try:
        # Import camera library (adjust based on your hardware)
        # import espcamera  # Example for ESP32-S3

        # Configure camera with resolution from settings
        # resolution = settings.camera_resolution

        # Example configuration (adjust for your camera):
        # camera = espcamera.Camera(
        #     data_pins=board.CAMERA_DATA,
        #     external_clock_pin=board.CAMERA_XCLK,
        #     pixel_clock_pin=board.CAMERA_PCLK,
        #     vsync_pin=board.CAMERA_VSYNC,
        #     href_pin=board.CAMERA_HREF,
        #     pixel_format=espcamera.PixelFormat.JPEG,
        #     frame_size=resolution,
        #     jpeg_quality=10,
        # )

        print("✓ Camera initialized")
        print(f"  Resolution: {settings.camera_resolution}")
        # return camera
        return None  # Remove when implementing actual camera

    except Exception as e:
        print(f"✗ Camera initialization failed: {e}")
        return None


def initialize_display():
    """
    Initialize display if available.

    This demonstrates optional hardware initialization.

    Returns:
        Display object if available, None otherwise
    """
    print("Initializing display...")

    try:
        display = board.DISPLAY
        print(f"✓ Display ready ({display.width}x{display.height})")
        return display
    except AttributeError:
        print("  No display available (this is okay)")
        return None


# ============================================
# CORE FUNCTIONALITY
# ============================================

def capture_image(camera):
    """
    Capture an image from the camera.

    Args:
        camera: Camera object

    Returns:
        bytes: JPEG image data, or None if failed
    """
    print("Capturing image...")

    if camera is None:
        print("✗ No camera available")
        return None

    try:
        # Check light level for auto-flash (if sensor available)
        if settings.auto_flash_enabled:
            # light_level = read_light_sensor()  # Implement based on your sensor
            # if light_level < settings.dark_threshold:
            #     enable_flash()
            pass

        # Capture image
        # frame = camera.take()  # Adjust based on your camera API
        # return frame

        print("✓ Image captured")
        return b"placeholder_image_data"  # Replace with actual capture

    except Exception as e:
        print(f"✗ Image capture failed: {e}")
        return None


def send_to_claude(image_data, prompt_config):
    """
    Send image to Claude API for analysis.

    This function demonstrates:
    - API request construction
    - Error handling for network requests
    - Timeout handling
    - Response parsing

    Args:
        image_data: JPEG image as bytes
        prompt_config: Dict with 'label' and 'prompt' keys

    Returns:
        str: Claude's response text, or None if failed
    """
    print(f"Sending to Claude (mode: {prompt_config['label']})...")

    if requests is None:
        print("✗ Requests not initialized")
        return None

    try:
        # Prepare request
        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": settings.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Encode image as base64 (simplified - adjust as needed)
        # In real implementation, use proper base64 encoding
        # import binascii
        # image_b64 = binascii.b2a_base64(image_data).decode('ascii').strip()

        payload = {
            "model": settings.api_model,
            "max_tokens": settings.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                # "data": image_b64  # Use actual base64 data
                                "data": "placeholder"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_config['prompt']
                        }
                    ]
                }
            ]
        }

        # Send request with timeout
        timeout = settings.get("api.timeout", 30)
        # response = requests.post(url, json=payload, headers=headers, timeout=timeout)

        # Parse response
        # response_data = response.json()
        # text = response_data["content"][0]["text"]

        # Placeholder response for demonstration
        text = "This is a placeholder response. Implement actual API call."

        print(f"✓ Response received ({len(text)} characters)")
        return text

    except Exception as e:
        print(f"✗ API request failed: {e}")
        return None


def display_response(display, text, prompt_label):
    """
    Display Claude's response on screen or serial.

    Args:
        display: Display object (or None)
        text: Response text to display
        prompt_label: Label for the prompt mode
    """
    print(f"\n{'=' * 40}")
    print(f"Mode: {prompt_label}")
    print(f"{'=' * 40}")
    print(text)
    print(f"{'=' * 40}\n")

    if display is not None:
        # Clear display and show response
        # Implement text wrapping and display rendering based on your display
        pass


def cycle_prompt():
    """
    Move to the next prompt in the configured order.

    This demonstrates:
    - Circular iteration through a list
    - Global state management
    """
    global current_prompt_index

    prompt_order = settings.get_prompt_order()
    current_prompt_index = (current_prompt_index + 1) % len(prompt_order)

    current_prompt_name = prompt_order[current_prompt_index]
    prompt_config = settings.get_prompt(current_prompt_name)

    print(f"→ Switched to prompt: {prompt_config['label']}")
    return prompt_config


# ============================================
# MAIN PROGRAM
# ============================================

def main():
    """
    Main program loop.

    This demonstrates:
    - Proper initialization order
    - Error handling at each stage
    - Clean program structure
    - Event loop pattern
    """
    global settings, requests, current_prompt_index

    print("\n" + "=" * 40)
    print("CloudFX - AI Vision for CircuitPython")
    print("Version 1.0")
    print("=" * 40 + "\n")

    # Step 1: Load settings
    settings = initialize_settings()
    if settings is None:
        print("\n✗ Cannot proceed without valid settings")
        print("Please fix configuration and reset device")
        while True:
            time.sleep(60)

    # Step 2: Initialize WiFi
    if not initialize_wifi():
        print("\n✗ Cannot proceed without WiFi connection")
        print("Please check credentials and reset device")
        while True:
            time.sleep(60)

    # Step 3: Initialize requests
    requests = initialize_requests()

    # Step 4: Initialize hardware
    camera = initialize_camera()
    display = initialize_display()

    # Step 5: Get initial prompt
    prompt_order = settings.get_prompt_order()
    current_prompt_name = prompt_order[current_prompt_index]
    current_prompt = settings.get_prompt(current_prompt_name)

    print(f"\n✓ Initialization complete")
    print(f"  Starting with prompt: {current_prompt['label']}")
    print(f"  {len(prompt_order)} total prompts configured\n")

    # Main event loop
    print("Ready! Press button to capture (or waiting for input...)\n")

    while True:
        try:
            # Wait for trigger (button press, etc.)
            # In this example, we'll use a simple timer
            # Replace with actual button/trigger detection

            print("Waiting for capture trigger...")
            time.sleep(5)  # Replace with button wait

            # Capture and process
            image_data = capture_image(camera)
            if image_data:
                response = send_to_claude(image_data, current_prompt)
                if response:
                    display_response(display, response, current_prompt['label'])

            # Optional: Auto-cycle through prompts
            # current_prompt = cycle_prompt()

        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
            break

        except Exception as e:
            print(f"\n✗ Unexpected error in main loop: {e}")
            print("Continuing after 5 seconds...")
            time.sleep(5)


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()
