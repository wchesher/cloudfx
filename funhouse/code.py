# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX FunHouse - AdafruitIO Command Listener
# CircuitPython 10.0.3 Edition
# --------------------------------------------
#
# This code runs on an Adafruit FunHouse and listens to an AdafruitIO feed
# for macro commands. When a command is received, it sends the corresponding
# HID keyboard sequence to the host computer.
#
# Prerequisites:
#  - CircuitPython 10.0.3 (or 10.x) on an Adafruit FunHouse
#  - Required libraries from CircuitPython 10.x Bundle (see requirements.txt)
#  - secrets.py with WiFi and AdafruitIO credentials
#  - macros.py with macro definitions
#  - LemonMilk font file in /fonts/ directory
#
# Architecture:
#  - FunHouse connects to WiFi and polls AdafruitIO feed every 15 seconds
#  - When commands appear in feed, they are queued and processed
#  - Each command triggers a USB HID keyboard sequence
#  - Display shows current command being executed
#  - Display auto-clears after 5 seconds
#
# CircuitPython 10.0.3 Compatibility:
#  - Updated for CP 10.x with version checking
#  - Uses traceback module for exception handling
#  - Compatible with CP 10.x Bundle libraries
#  - Enhanced error logging and recovery

import gc
import sys
import time
import board
import displayio
import ipaddress
import ssl
import wifi
import socketpool
import usb_hid
import traceback
from collections import deque
from adafruit_display_text import label
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Import custom modules with error handling
try:
    import adafruit_requests
except ImportError as e:
    print("ERROR: adafruit_requests library not found")
    print("Install from CircuitPython 10.x Bundle")
    traceback.print_exception(type(e), e, e.__traceback__)
    raise

try:
    from adafruit_bitmap_font import bitmap_font
except ImportError as e:
    print("WARNING: adafruit_bitmap_font not found, display will be limited")
    traceback.print_exception(type(e), e, e.__traceback__)
    bitmap_font = None

try:
    from secrets import secrets
except ImportError:
    print("ERROR: secrets.py not found!")
    print("Create secrets.py with WiFi and AdafruitIO credentials")
    raise

try:
    from macros import Macros
except ImportError:
    print("ERROR: macros.py not found!")
    print("Create macros.py with macro definitions")
    raise

# -------------------------------------------------------------------------------
# VERSION CHECK: Ensure we're running on CircuitPython 10.x or later
# -------------------------------------------------------------------------------
try:
    cp_version = sys.implementation.version
    print(f"CircuitPython {cp_version[0]}.{cp_version[1]}.{cp_version[2]}")
    if cp_version[0] < 10:
        print(f"WARNING: This code is designed for CircuitPython 10.x")
        print(f"You are running {cp_version[0]}.{cp_version[1]}.{cp_version[2]}")
        print("Some features may not work correctly. Please upgrade to CP 10.0.3+")
except Exception as e:
    print("Could not determine CircuitPython version")
    traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# -------------------------------------------------------------------------------
MACROS_FEED_URL = f"http://io.adafruit.com/api/v2/{secrets.get('aio_username', 'default_user')}/feeds/macros/data"
QUEUE_SIZE = 50                 # Maximum number of commands to queue
TEXT_COLOR = 0xFFFFFF           # White text on display
FONT_FILE = "fonts/LemonMilk-10.pcf"  # Display font (optional)
CLEAR_DELAY = 5                 # Seconds before clearing display
LISTENING_INTERVAL = 15         # Seconds between feed polls
RETRY_LIMIT = 3                 # Number of connection retry attempts
RETRY_DELAY = 2                 # Seconds between retries

# -------------------------------------------------------------------------------
# INITIALIZE MACROS
# -------------------------------------------------------------------------------
try:
    macros = Macros.macros
    print(f"Loaded {len(macros)} macro(s) from macros.py")
except Exception as e:
    print("ERROR: Could not load macros from macros.py")
    traceback.print_exception(type(e), e, e.__traceback__)
    macros = []

# -------------------------------------------------------------------------------
# INITIALIZE STATE
# -------------------------------------------------------------------------------
macros_queue = deque((), QUEUE_SIZE)  # Command queue
system_on = True                       # System enabled flag
last_display_time = None               # Time when display was last updated
last_listening_time = 0                # Time when last polled feed

# -------------------------------------------------------------------------------
# HID KEYBOARD SETUP
# -------------------------------------------------------------------------------
try:
    kbd = Keyboard(usb_hid.devices)
    print("USB HID keyboard initialized")
except Exception as e:
    print("ERROR: HID keyboard initialization failed")
    traceback.print_exception(type(e), e, e.__traceback__)
    kbd = None

# -------------------------------------------------------------------------------
# DISPLAY SETUP
# -------------------------------------------------------------------------------
try:
    display = board.DISPLAY
    splash = displayio.Group()
    display.root_group = splash

    # Try to load custom font, fall back to terminalio if not available
    font = None
    if bitmap_font:
        try:
            font = bitmap_font.load_font(FONT_FILE)
            print(f"Loaded font: {FONT_FILE}")
        except Exception as e:
            print(f"Could not load font {FONT_FILE}, using default")
            traceback.print_exception(type(e), e, e.__traceback__)

    if font is None:
        import terminalio
        font = terminalio.FONT
        print("Using default terminalio font")

    text_area = label.Label(font, text="", color=TEXT_COLOR, scale=3)
    text_area.x, text_area.y = 10, 30
    splash.append(text_area)
    print("Display initialized")
except Exception as e:
    print("ERROR: Display initialization failed")
    traceback.print_exception(type(e), e, e.__traceback__)
    text_area = None

# -------------------------------------------------------------------------------
# DISPLAY HELPER FUNCTIONS
# -------------------------------------------------------------------------------
def safe_display_text(text):
    """Update display with safe error handling."""
    global last_display_time
    if text_area:
        try:
            set_brightness(0.5)
            text_area.text = str(text)
            display.refresh()
            last_display_time = time.monotonic()
            print(f"Display: {text}")
        except Exception as e:
            print("Display update error:")
            traceback.print_exception(type(e), e, e.__traceback__)


def update_display():
    """Clear display text after timeout."""
    global last_display_time
    if last_display_time and (time.monotonic() - last_display_time > CLEAR_DELAY):
        if text_area:
            try:
                text_area.text = ""
                set_brightness(0.0)
                display.refresh()
                last_display_time = None
            except Exception as e:
                print("Display clear error:")
                traceback.print_exception(type(e), e, e.__traceback__)


def set_brightness(level):
    """Clamp brightness to valid range and set."""
    try:
        level = max(0.0, min(1.0, level))
        board.DISPLAY.brightness = level
    except Exception as e:
        print("Brightness set error:")
        traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# NETWORK FUNCTIONS
# -------------------------------------------------------------------------------
def initialize_requests():
    """Connect to Wi-Fi and return requests session object."""
    print("Initializing WiFi connection...")

    for attempt in range(RETRY_LIMIT):
        try:
            # Check if static IP is configured
            if secrets.get("gateway"):
                print("Using static IP configuration")
                wifi.radio.set_ipv4_address(
                    ipv4=ipaddress.IPv4Address(secrets["static_ip"]),
                    netmask=ipaddress.IPv4Address(secrets["netmask"]),
                    gateway=ipaddress.IPv4Address(secrets["gateway"]),
                )
                if "dns" in secrets:
                    wifi.radio.dns = ipaddress.IPv4Address(secrets["dns"])
                print(f"Static IP: {secrets['static_ip']}")
            else:
                print("Using DHCP")

            # Connect to WiFi
            print(f"Connecting to SSID: {secrets['ssid']}")
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            print(f"Connected! IP: {wifi.radio.ipv4_address}")

            # Create and return requests session
            pool = socketpool.SocketPool(wifi.radio)
            ssl_context = ssl.create_default_context()
            session = adafruit_requests.Session(pool, ssl_context)
            print("Requests session created")
            return session

        except Exception as e:
            print(f"Wi-Fi connection error (attempt {attempt + 1}/{RETRY_LIMIT}):")
            traceback.print_exception(type(e), e, e.__traceback__)
            if attempt < RETRY_LIMIT - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError("Wi-Fi connection failed after all retries")


def clear_existing_feed(requests):
    """Delete all items currently in the AdafruitIO feed."""
    print("Clearing existing feed items...")
    headers = {"X-AIO-Key": secrets["aio_key"]}

    try:
        resp = requests.get(MACROS_FEED_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json()
            print(f"Found {len(items)} item(s) in feed")
            for item in reversed(items):
                try:
                    delete_url = f"{MACROS_FEED_URL}/{item['id']}"
                    delete_resp = requests.delete(delete_url, headers=headers, timeout=10)
                    if delete_resp.status_code == 200:
                        print(f"Cleared item: {item['id']}")
                    else:
                        print(f"Failed to clear {item['id']}: HTTP {delete_resp.status_code}")
                    delete_resp.close()
                except Exception as e:
                    print(f"Error clearing item {item.get('id', 'unknown')}:")
                    traceback.print_exception(type(e), e, e.__traceback__)
            resp.close()
        else:
            print(f"Feed fetch failed: HTTP {resp.status_code}")
            resp.close()
    except Exception as e:
        print("Feed clear error:")
        traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# HID & MACRO FUNCTIONS
# -------------------------------------------------------------------------------
def send_key_sequence(sequence):
    """Send HID key sequence with error handling."""
    if not kbd:
        print("ERROR: Keyboard not available")
        return

    try:
        # Press all keys in sequence
        for key in sequence:
            kbd.press(key)
        # Release all keys
        kbd.release_all()
        print(f"Sent key sequence: {sequence}")
    except Exception as e:
        print("Key sequence error:")
        traceback.print_exception(type(e), e, e.__traceback__)
        # Try to release all keys on error
        try:
            kbd.release_all()
        except:
            pass


def process_command(command):
    """Find macro by label and execute its key sequence."""
    command = str(command).strip()

    for macro in macros:
        if macro.get("label") == command:
            keycodes = macro.get("keycodes", [])
            print(f"Executing macro '{command}' with {len(keycodes)} keycode(s)")
            send_key_sequence(keycodes)
            return

    print(f"WARNING: Command '{command}' not found in macros")


def update_data(requests):
    """Fetch new items from AdafruitIO feed and queue them."""
    headers = {"X-AIO-Key": secrets["aio_key"]}

    try:
        resp = requests.get(MACROS_FEED_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json()
            if items:
                print(f"Received {len(items)} new item(s)")
                # Process in reverse order (oldest first)
                for item in reversed(items):
                    value = item.get("value", "")
                    if value:
                        macros_queue.append(value)
                        print(f"Queued: {value}")

                    # Delete item from feed after queuing
                    try:
                        delete_url = f"{MACROS_FEED_URL}/{item['id']}"
                        delete_resp = requests.delete(delete_url, headers=headers, timeout=10)
                        if delete_resp.status_code != 200:
                            print(f"Delete failed: HTTP {delete_resp.status_code}")
                        delete_resp.close()
                    except Exception as e:
                        print(f"Error deleting item {item.get('id', 'unknown')}:")
                        traceback.print_exception(type(e), e, e.__traceback__)
            resp.close()
        else:
            print(f"Feed fetch error: HTTP {resp.status_code}")
            resp.close()
    except Exception as e:
        print("Data update error:")
        traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------------------------------
print("CloudFX FunHouse starting...")
set_brightness(0.0)

try:
    # Initialize WiFi and requests session
    requests = initialize_requests()

    # Clear any old commands from the feed
    clear_existing_feed(requests)

    print("Entering main loop...")
    print(f"Polling AdafruitIO feed every {LISTENING_INTERVAL} seconds")

    # Main event loop
    while True:
        now = time.monotonic()

        # Log listening status periodically
        if now - last_listening_time >= LISTENING_INTERVAL:
            print("Listening for commands...")
            last_listening_time = now

        # Check for new commands if system is enabled
        if system_on:
            try:
                update_data(requests)
            except Exception as e:
                print("Error updating data:")
                traceback.print_exception(type(e), e, e.__traceback__)

            # Process queued commands
            while macros_queue:
                try:
                    macro_data = macros_queue.popleft()
                    print(f"Processing command: {macro_data}")
                    safe_display_text(macro_data)
                    process_command(macro_data)
                except Exception as e:
                    print("Error processing command:")
                    traceback.print_exception(type(e), e, e.__traceback__)

        # Update display (clear if timeout expired)
        try:
            update_display()
        except Exception as e:
            print("Error updating display:")
            traceback.print_exception(type(e), e, e.__traceback__)

        # Small delay and garbage collection
        time.sleep(0.1)
        gc.collect()

except KeyboardInterrupt:
    print("Program stopped by user")
    set_brightness(0.0)

except Exception as e:
    print("CRITICAL FAILURE:")
    traceback.print_exception(type(e), e, e.__traceback__)
    set_brightness(0.0)
    # Keep running but in a safe state
    while True:
        time.sleep(1)
