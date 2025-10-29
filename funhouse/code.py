# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX FunHouse - UBER OPTIMIZED
# CircuitPython 10.0.3
# ===================================
#
# Blazing fast AdafruitIO → HID command processor
# Stripped to bare essentials for maximum speed and reliability
#
# Features:
#  - Lightning-fast command processing (< 100ms response time)
#  - Minimal overhead (blank display, minimal LEDs, no error bloat)
#  - Blank screen shows command name when executing
#  - JSON-based macros (single source of truth)
#  - Configurable polling (default 2s, set POLL_INTERVAL in settings.toml)
#  - Simple LED status (connecting/connected/error/message received)
#
# Prerequisites:
#  - CircuitPython 10.0.3+ on Adafruit FunHouse
#  - Libraries: adafruit_requests, adafruit_io, adafruit_hid
#  - settings.toml with credentials
#  - /macros.json and /macros_loader.py on device

import gc
import os
import time
import board
import displayio
import terminalio
import wifi
import socketpool
import ssl
import ipaddress
import usb_hid
from collections import deque
from adafruit_display_text import label
from adafruit_hid.keyboard import Keyboard
from adafruit_requests import Session
from adafruit_io.adafruit_io import IO_HTTP
from macros_loader import MacroLoader

# -------------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------------
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))  # Polling interval (seconds)
DISPLAY_TIMEOUT = 1.0                                    # Seconds to show command name on display
LOOP_DELAY = 0.05                                        # Main loop delay (50ms)
GC_INTERVAL = 10                                         # Garbage collection interval
QUEUE_SIZE = 50                                          # Command queue size
FEED_NAME = "macros"                                     # AdafruitIO feed name

print(f"CloudFX FunHouse - UBER OPTIMIZED")
print(f"Poll interval: {POLL_INTERVAL}s")

# -------------------------------------------------------------------------------
# LOAD CREDENTIALS
# -------------------------------------------------------------------------------
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

# Optional static IP
STATIC_IP = os.getenv("STATIC_IP")
GATEWAY = os.getenv("GATEWAY")
NETMASK = os.getenv("NETMASK")
DNS = os.getenv("DNS")

if not all([WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY]):
    raise ValueError("Missing credentials in settings.toml")

# -------------------------------------------------------------------------------
# INITIALIZE HARDWARE
# -------------------------------------------------------------------------------
# Load macros
loader = MacroLoader("/macros.json")
macro_commands = loader.get_commands_for_funhouse()
print(f"Loaded {len(macro_commands)} commands")

# Initialize HID keyboard
kbd = Keyboard(usb_hid.devices)
print("HID keyboard ready")

# Initialize display (blank screen with command text)
display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

# Blank black background
text_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, scale=3)
text_area.x, text_area.y = 10, 60
splash.append(text_area)
display.auto_refresh = False
display.refresh()
print("Display ready (blank)")

# Initialize LEDs (simple status only)
try:
    import adafruit_dotstar
    leds = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 5, brightness=0.2, auto_write=True)
    LED_AVAILABLE = True
    print("LEDs ready")
except:
    LED_AVAILABLE = False
    leds = None

# LED colors
BLUE = (0, 0, 255)       # Connecting
GREEN = (0, 255, 0)      # Connected
RED = (255, 0, 0)        # Error
MAGENTA = (255, 0, 255)  # Message received
OFF = (0, 0, 0)

def set_led(color):
    """Set all LEDs to one color."""
    if leds:
        leds.fill(color)

def flash_led(color, duration=0.6):
    """Flash LEDs briefly then return to OFF."""
    if leds:
        leds.fill(color)
        time.sleep(duration)
        leds.fill(OFF)

# -------------------------------------------------------------------------------
# NETWORK SETUP
# -------------------------------------------------------------------------------
print("Connecting to WiFi...")
set_led(BLUE)

# Static IP if configured
if GATEWAY:
    wifi.radio.set_ipv4_address(
        ipv4=ipaddress.IPv4Address(STATIC_IP),
        netmask=ipaddress.IPv4Address(NETMASK),
        gateway=ipaddress.IPv4Address(GATEWAY)
    )
    if DNS:
        wifi.radio.dns = ipaddress.IPv4Address(DNS)
    print(f"Static IP: {STATIC_IP}")

# Connect
wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
print(f"Connected: {wifi.radio.ipv4_address}")

# Create AdafruitIO client
pool = socketpool.SocketPool(wifi.radio)
requests = Session(pool, ssl.create_default_context())
io = IO_HTTP(AIO_USERNAME, AIO_KEY, requests)
print("AdafruitIO ready")

set_led(GREEN)

# -------------------------------------------------------------------------------
# COMMAND PROCESSING
# -------------------------------------------------------------------------------
def execute_command(command):
    """Look up and execute HID macro. Ultra-fast."""
    global last_display_time

    if command in macro_commands:
        # Display command name on screen (new commands overwrite immediately)
        text_area.text = command
        display.refresh()
        last_display_time = time.monotonic()

        keycodes = macro_commands[command]

        # Press all keys
        for key in keycodes:
            kbd.press(key)

        # Hold 50ms
        time.sleep(0.05)

        # Release
        kbd.release_all()

        print(f"✓ {command}")

        # Display will be cleared by main loop after 1 second
    else:
        print(f"✗ {command} (not found)")

# -------------------------------------------------------------------------------
# MAIN LOOP - ULTRA FAST WITH SAFEGUARDS
# -------------------------------------------------------------------------------
print(f"Polling every {POLL_INTERVAL}s")
print("Ready!")

command_queue = deque((), QUEUE_SIZE)
last_poll = 0
last_gc = 0
last_display_time = None  # Track when command was displayed
is_polling = False  # Safeguard: prevent concurrent polling
poll_count = 0      # Count polls to turn off LEDs after 2

while True:
    now = time.monotonic()

    # Poll AdafruitIO at intervals (SAFEGUARD: skip if already polling)
    if now - last_poll >= POLL_INTERVAL and not is_polling:
        is_polling = True  # Lock polling
        last_poll = now
        poll_count += 1

        try:
            # Fetch commands from feed
            data_items = io.receive_all_data(FEED_NAME)

            if data_items:
                # Flash magenta when messages received from queue (0.6 seconds)
                flash_led(MAGENTA, 0.6)

                # Queue commands (oldest first)
                for item in reversed(data_items):
                    value = item.get("value", "")
                    if value and len(command_queue) < QUEUE_SIZE:
                        # SAFEGUARD: Don't overflow queue
                        command_queue.append(value)

                # Delete from feed
                for item in data_items:
                    try:
                        io.delete_data(FEED_NAME, item["id"])
                    except:
                        pass  # Don't block on delete failures

                print(f"← {len(data_items)} command(s)")

            # Turn off green LEDs after first 2 polls
            if poll_count == 2:
                set_led(OFF)
                print("LEDs off (startup complete)")

        except Exception as e:
            print(f"Poll error: {e}")
            set_led(RED)
            time.sleep(0.5)  # Brief pause on error
            # Don't restore green after error if already turned off
            if poll_count < 2:
                set_led(GREEN)

        finally:
            is_polling = False  # Always unlock polling

    # Process queued commands immediately (one per loop iteration)
    # SAFEGUARD: Process only one command per loop to keep loop fast
    if command_queue:
        command = command_queue.popleft()
        execute_command(command)

    # Clear display after timeout if no new commands
    if last_display_time and (now - last_display_time >= DISPLAY_TIMEOUT):
        text_area.text = ""
        display.refresh()
        last_display_time = None

    # Periodic garbage collection
    if now - last_gc >= GC_INTERVAL:
        last_gc = now
        gc.collect()

    # Fast loop (50ms = 20 iterations/second)
    time.sleep(LOOP_DELAY)
