# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX FunHouse - AdafruitIO Command Listener
# CircuitPython 10.0.3 Edition - Optimized & JSON-based
# --------------------------------------------
#
# This code runs on an Adafruit FunHouse and listens to an AdafruitIO feed
# for macro commands. When a command is received, it sends the corresponding
# HID keyboard sequence to the host computer.
#
# FEATURES:
#  - JSON-based macro configuration (single source of truth)
#  - adafruit_io library integration (cleaner code)
#  - DotStar LED status indicators (5 RGB LEDs on side)
#  - Better error recovery
#  - Poll timer visualization
#  - OPTIMIZED for speed and accuracy:
#    * Configurable polling interval (default 2s, adjustable via settings.toml)
#    * Fast main loop (50ms = 20 iterations/second for quick response)
#    * Immediate command processing (no delays between commands)
#    * Reduced CPU overhead (periodic LED updates, periodic GC)
#    * Minimal HID logging for faster execution
#
# Prerequisites:
#  - CircuitPython 10.0.3 (or 10.x) on an Adafruit FunHouse
#  - Required libraries from CircuitPython 10.x Bundle (see LIBRARIES.md)
#  - settings.toml with WiFi and AdafruitIO credentials
#  - macros.json and macros_loader.py with macro definitions

import gc
import os
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

# Import optional libraries with error handling
try:
    import adafruit_requests
    from adafruit_io.adafruit_io import IO_HTTP
except ImportError as e:
    print("ERROR: adafruit_requests or adafruit_io library not found")
    print("Install from CircuitPython 10.x Bundle")
    traceback.print_exception(type(e), e, e.__traceback__)
    raise

try:
    import adafruit_dotstar
    DOTSTAR_AVAILABLE = True
except ImportError:
    print("WARNING: adafruit_dotstar not found, status LEDs disabled")
    DOTSTAR_AVAILABLE = False

try:
    from adafruit_bitmap_font import bitmap_font
except ImportError:
    print("WARNING: adafruit_bitmap_font not found, using default font")
    bitmap_font = None

try:
    from macros_loader import MacroLoader
except ImportError:
    print("ERROR: macros_loader.py not found!")
    print("Copy shared/macros_loader.py to device")
    raise

# -------------------------------------------------------------------------------
# VERSION CHECK
# -------------------------------------------------------------------------------
try:
    cp_version = sys.implementation.version
    print(f"CircuitPython {cp_version[0]}.{cp_version[1]}.{cp_version[2]}")
    if cp_version[0] < 10:
        print(f"WARNING: This code is designed for CircuitPython 10.x")
        print("Please upgrade to CP 10.0.3+")
except Exception as e:
    print("Could not determine CircuitPython version")
    traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# LOAD SETTINGS
# -------------------------------------------------------------------------------
try:
    WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
    WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    AIO_USERNAME = os.getenv("AIO_USERNAME")
    AIO_KEY = os.getenv("AIO_KEY")

    # Optional static IP settings
    STATIC_IP = os.getenv("STATIC_IP")
    NETMASK = os.getenv("NETMASK")
    GATEWAY = os.getenv("GATEWAY")
    DNS = os.getenv("DNS")

    # Optional polling interval override
    poll_override = os.getenv("POLL_INTERVAL")
    if poll_override:
        try:
            POLL_INTERVAL = float(poll_override)
            print(f"Using custom POLL_INTERVAL: {POLL_INTERVAL} seconds")
        except ValueError:
            print(f"WARNING: Invalid POLL_INTERVAL '{poll_override}', using default")

    # Validate required settings
    if not all([WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY]):
        print("ERROR: Missing required settings in settings.toml")
        print("Required: CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD, AIO_USERNAME, AIO_KEY")
        raise ValueError("Incomplete configuration")

    print("Settings loaded successfully from settings.toml")
except Exception as e:
    print("ERROR: Could not load settings from settings.toml")
    traceback.print_exception(type(e), e, e.__traceback__)
    raise

# -------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# -------------------------------------------------------------------------------
FEED_NAME = "macros"             # AdafruitIO feed name
QUEUE_SIZE = 50                  # Maximum number of commands to queue
TEXT_COLOR = 0xFFFFFF            # White text on display
FONT_FILE = "fonts/LemonMilk-10.pcf"  # Display font (optional)
CLEAR_DELAY = 5                  # Seconds before clearing display
POLL_INTERVAL = 2                # Seconds between feed polls (default: 2, adjust via settings.toml)
LOOP_DELAY = 0.05                # Main loop delay in seconds (faster = more responsive)
LED_UPDATE_INTERVAL = 0.2        # Seconds between LED animation updates
GC_INTERVAL = 5                  # Seconds between garbage collections
RETRY_LIMIT = 3                  # Number of connection retry attempts
RETRY_DELAY = 2                  # Seconds between retries

# DotStar LED Colors (if available)
LED_OFF = (0, 0, 0)
LED_CONNECTING = (0, 0, 255)     # Blue
LED_CONNECTED = (0, 255, 0)      # Green
LED_POLLING = (255, 255, 0)      # Yellow
LED_COMMAND = (255, 0, 255)      # Magenta
LED_ERROR = (255, 0, 0)          # Red

# -------------------------------------------------------------------------------
# INITIALIZE MACROS FROM JSON
# -------------------------------------------------------------------------------
try:
    loader = MacroLoader("/macros.json")
    macro_commands = loader.get_commands_for_funhouse()
    print(f"Loaded {len(macro_commands)} command(s) from macros.json")
except Exception as e:
    print("ERROR: Could not load macros from macros.json")
    traceback.print_exception(type(e), e, e.__traceback__)
    macro_commands = {}

# -------------------------------------------------------------------------------
# INITIALIZE STATE
# -------------------------------------------------------------------------------
macros_queue = deque((), QUEUE_SIZE)
system_on = True
last_display_time = None
last_poll_time = 0
last_led_update = 0
last_gc_time = 0

# -------------------------------------------------------------------------------
# INITIALIZE DOTSTAR LEDs (5 RGB LEDs on side of FunHouse)
# -------------------------------------------------------------------------------
dots = None
if DOTSTAR_AVAILABLE:
    try:
        # FunHouse has 5 DotStar LEDs
        dots = adafruit_dotstar.DotStar(
            board.DOTSTAR_CLOCK,
            board.DOTSTAR_DATA,
            5,  # Number of LEDs
            brightness=0.2,
            auto_write=False
        )
        # Turn all off initially
        dots.fill(LED_OFF)
        dots.show()
        print("DotStar LEDs initialized (5 LEDs)")
    except Exception as e:
        print("DotStar initialization error:")
        traceback.print_exception(type(e), e, e.__traceback__)
        dots = None

# -------------------------------------------------------------------------------
# HID KEYBOARD SETUP
# -------------------------------------------------------------------------------
try:
    kbd = Keyboard(usb_hid.devices)
    print("USB HID keyboard initialized")
except Exception as e:
    print("ERROR: HID keyboard initialization failed")
    print("Make sure adafruit_hid library is from CircuitPython 10.x Bundle")
    traceback.print_exception(type(e), e, e.__traceback__)
    kbd = None

# -------------------------------------------------------------------------------
# DISPLAY SETUP
# -------------------------------------------------------------------------------
try:
    display = board.DISPLAY
    splash = displayio.Group()
    display.root_group = splash

    # Try to load custom font, fall back to terminalio
    font = None
    if bitmap_font:
        try:
            font = bitmap_font.load_font(FONT_FILE)
            print(f"Loaded font: {FONT_FILE}")
        except Exception as e:
            print(f"Could not load font {FONT_FILE}, using default")

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
# LED HELPER FUNCTIONS
# -------------------------------------------------------------------------------
def set_leds(color, pattern=None):
    """Set DotStar LEDs to a color or pattern."""
    if not dots:
        return
    try:
        if pattern is None:
            # Solid color on all LEDs
            dots.fill(color)
        elif pattern == "pulse":
            # Pulse effect (animate later in main loop)
            dots.fill(color)
        elif pattern == "progress":
            # Progress bar effect (show poll progress)
            # Will be animated in main loop
            dots.fill(color)
        dots.show()
    except Exception as e:
        print("LED error:")
        traceback.print_exception(type(e), e, e.__traceback__)


def led_flash(color, duration=0.1):
    """Flash LEDs briefly."""
    if not dots:
        return
    try:
        dots.fill(color)
        dots.show()
        time.sleep(duration)
        dots.fill(LED_OFF)
        dots.show()
    except Exception:
        pass

# -------------------------------------------------------------------------------
# DISPLAY HELPER FUNCTIONS
# -------------------------------------------------------------------------------
def safe_display_text(text):
    """Update display with safe error handling."""
    global last_display_time
    if text_area:
        try:
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
                display.refresh()
                last_display_time = None
            except Exception as e:
                print("Display clear error:")
                traceback.print_exception(type(e), e, e.__traceback__)

# -------------------------------------------------------------------------------
# NETWORK FUNCTIONS
# -------------------------------------------------------------------------------
def initialize_network():
    """Connect to WiFi and create AdafruitIO client."""
    print("Initializing network connection...")
    set_leds(LED_CONNECTING)

    for attempt in range(RETRY_LIMIT):
        try:
            # Configure static IP if specified
            if GATEWAY:
                print("Using static IP configuration")
                wifi.radio.set_ipv4_address(
                    ipv4=ipaddress.IPv4Address(STATIC_IP),
                    netmask=ipaddress.IPv4Address(NETMASK),
                    gateway=ipaddress.IPv4Address(GATEWAY),
                )
                if DNS:
                    wifi.radio.dns = ipaddress.IPv4Address(DNS)
                print(f"Static IP: {STATIC_IP}")
            else:
                print("Using DHCP")

            # Connect to WiFi
            print(f"Connecting to SSID: {WIFI_SSID}")
            wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
            print(f"Connected! IP: {wifi.radio.ipv4_address}")

            # Create requests session
            pool = socketpool.SocketPool(wifi.radio)
            ssl_context = ssl.create_default_context()
            requests_session = adafruit_requests.Session(pool, ssl_context)

            # Create AdafruitIO client
            io_client = IO_HTTP(AIO_USERNAME, AIO_KEY, requests_session)
            print("AdafruitIO client created")

            set_leds(LED_CONNECTED)
            led_flash(LED_CONNECTED, 0.5)

            return io_client

        except Exception as e:
            print(f"Network connection error (attempt {attempt + 1}/{RETRY_LIMIT}):")
            traceback.print_exception(type(e), e, e.__traceback__)
            set_leds(LED_ERROR)
            if attempt < RETRY_LIMIT - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError("Network connection failed after all retries")

# -------------------------------------------------------------------------------
# ADAFRUIT IO FUNCTIONS
# -------------------------------------------------------------------------------
def clear_feed(io_client):
    """Clear all existing items from the feed."""
    print(f"Clearing existing items from '{FEED_NAME}' feed...")
    try:
        # Get all data from feed
        data_items = io_client.receive_all_data(FEED_NAME)
        print(f"Found {len(data_items)} item(s) to clear")

        # Delete each item
        for item in data_items:
            try:
                io_client.delete_data(FEED_NAME, item["id"])
                print(f"Cleared item: {item['id']}")
            except Exception as e:
                print(f"Error clearing item {item.get('id', 'unknown')}:")
                traceback.print_exception(type(e), e, e.__traceback__)

        print("Feed cleared")
    except Exception as e:
        print("Feed clear error:")
        traceback.print_exception(type(e), e, e.__traceback__)


def fetch_commands(io_client):
    """Fetch new commands from AdafruitIO feed and queue them."""
    try:
        set_leds(LED_POLLING)

        # Get all data from feed
        data_items = io_client.receive_all_data(FEED_NAME)

        if data_items:
            print(f"Received {len(data_items)} new command(s)")

            # Process in order (oldest first)
            for item in reversed(data_items):
                value = item.get("value", "")
                if value:
                    macros_queue.append(value)
                    print(f"Queued: {value}")

                # Delete item after queuing
                try:
                    io_client.delete_data(FEED_NAME, item["id"])
                except Exception as e:
                    print(f"Error deleting item {item.get('id', 'unknown')}:")
                    traceback.print_exception(type(e), e, e.__traceback__)

        set_leds(LED_CONNECTED)

    except Exception as e:
        print("Fetch commands error:")
        traceback.print_exception(type(e), e, e.__traceback__)
        set_leds(LED_ERROR)
        time.sleep(1)
        set_leds(LED_CONNECTED)

# -------------------------------------------------------------------------------
# HID & MACRO FUNCTIONS
# -------------------------------------------------------------------------------
def send_key_sequence(sequence):
    """Send HID key sequence with error handling. Optimized for speed."""
    if not kbd:
        print("ERROR: Keyboard not available")
        return

    try:
        # Press all keys in sequence (optimized - minimal logging)
        for key in sequence:
            kbd.press(key)

        # Hold keys briefly so OS/AHK can detect them (50ms is minimum reliable time)
        time.sleep(0.05)

        # Release all keys
        kbd.release_all()
        print(f"Sent HID: {len(sequence)} key(s)")
    except Exception as e:
        print("Key sequence error:")
        traceback.print_exception(type(e), e, e.__traceback__)
        # Try to release all keys on error
        try:
            kbd.release_all()
        except:
            pass


def process_command(command):
    """Find macro by command name and execute its key sequence. Optimized."""
    command = str(command).strip()

    # Look up command in macro_commands dict (fast dict lookup)
    if command in macro_commands:
        keycodes = macro_commands[command]
        print(f"Executing: '{command}' ({len(keycodes)} keys)")

        # Flash LEDs briefly to indicate command received
        led_flash(LED_COMMAND, 0.05)

        # Send HID sequence
        send_key_sequence(keycodes)
    else:
        print(f"WARNING: Command '{command}' not found in macros")

# -------------------------------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------------------------------
print("CloudFX FunHouse starting...")

try:
    # Initialize network and AdafruitIO
    io = initialize_network()

    # Clear any old commands from the feed
    clear_feed(io)

    print("Entering main loop...")
    print(f"Polling AdafruitIO feed '{FEED_NAME}' every {POLL_INTERVAL} seconds")

    # Main event loop - optimized for speed and accuracy
    while True:
        now = time.monotonic()

        # Poll for new commands at regular intervals
        if now - last_poll_time >= POLL_INTERVAL:
            print("Polling for commands...")
            last_poll_time = now

            if system_on:
                try:
                    fetch_commands(io)
                except Exception as e:
                    print("Error polling feed:")
                    traceback.print_exception(type(e), e, e.__traceback__)
                    set_leds(LED_ERROR)

        # Process queued commands immediately (no delay between commands)
        while macros_queue:
            try:
                command = macros_queue.popleft()
                print(f"Processing command: {command}")
                safe_display_text(command)
                process_command(command)
                # No delay here - process next command immediately
            except Exception as e:
                print("Error processing command:")
                traceback.print_exception(type(e), e, e.__traceback__)

        # Update display (clear if timeout expired) - only check periodically
        if last_display_time:
            try:
                update_display()
            except Exception as e:
                print("Error updating display:")
                traceback.print_exception(type(e), e, e.__traceback__)

        # Show poll progress on LEDs - only update at intervals to save CPU
        if dots and system_on and (now - last_led_update >= LED_UPDATE_INTERVAL):
            last_led_update = now
            try:
                # Calculate progress through poll interval
                progress = (now - last_poll_time) / POLL_INTERVAL
                num_leds_on = int(progress * 5)
                for i in range(5):
                    if i < num_leds_on:
                        dots[i] = LED_CONNECTED
                    else:
                        dots[i] = LED_OFF
                dots.show()
            except Exception:
                pass

        # Garbage collection - run periodically, not every loop
        if now - last_gc_time >= GC_INTERVAL:
            last_gc_time = now
            gc.collect()

        # Short delay for responsiveness (50ms = 20 loops/second)
        time.sleep(LOOP_DELAY)

except KeyboardInterrupt:
    print("Program stopped by user")
    set_leds(LED_OFF)

except Exception as e:
    print("CRITICAL FAILURE:")
    traceback.print_exception(type(e), e, e.__traceback__)
    set_leds(LED_ERROR)
    # Keep running but in safe state
    while True:
        time.sleep(1)
