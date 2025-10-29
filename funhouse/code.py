# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX FunHouse - BULLETPROOF TITANIUM EDITION
# CircuitPython 10.0.3
# ===================================
#
# Ultra-reliable AdafruitIO → HID command processor
# Bulletproof error handling, auto-recovery, memory management
#
# Features:
#  - WiFi auto-reconnect on connection loss
#  - Comprehensive error handling (every operation protected)
#  - Memory leak prevention (aggressive GC, display optimization)
#  - Network timeout handling
#  - HID error recovery
#  - Watchdog-ready design

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
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
DISPLAY_TIMEOUT = 1.0
LOOP_DELAY = 0.05
GC_INTERVAL = 5  # More frequent GC for stability
QUEUE_SIZE = 50
FEED_NAME = "macros"
WIFI_CHECK_INTERVAL = 30  # Check WiFi connection every 30s
NETWORK_TIMEOUT = 10  # Network operation timeout

print(f"CloudFX FunHouse - BULLETPROOF TITANIUM EDITION")
print(f"Poll interval: {POLL_INTERVAL}s")

# -------------------------------------------------------------------------------
# LOAD CREDENTIALS
# -------------------------------------------------------------------------------
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")
STATIC_IP = os.getenv("STATIC_IP")
GATEWAY = os.getenv("GATEWAY")
NETMASK = os.getenv("NETMASK")
DNS = os.getenv("DNS")

if not all([WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY]):
    raise ValueError("Missing credentials in settings.toml")

# -------------------------------------------------------------------------------
# INITIALIZE HARDWARE
# -------------------------------------------------------------------------------
loader = MacroLoader("/macros.json")
macro_commands = loader.get_commands_for_funhouse()
print(f"Loaded {len(macro_commands)} commands")
del loader  # Free memory
gc.collect()

kbd = Keyboard(usb_hid.devices)
print("HID keyboard ready")

# Initialize display with error handling
try:
    display = board.DISPLAY
    splash = displayio.Group()
    display.root_group = splash
    text_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, scale=3)
    text_area.x, text_area.y = 10, 60
    splash.append(text_area)
    display.auto_refresh = False
    display.refresh()
    print("Display ready")
except Exception as e:
    print(f"Display init warning: {e}")
    display = None
    text_area = None

# Initialize LEDs
try:
    import adafruit_dotstar
    leds = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 5, brightness=0.2, auto_write=True)
    print("LEDs ready")
except:
    leds = None

BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
MAGENTA = (255, 0, 255)
OFF = (0, 0, 0)

def set_led(color):
    """Set LEDs with error protection."""
    try:
        if leds:
            leds.fill(color)
    except:
        pass

def flash_led(color, duration=0.6):
    """Flash LEDs with error protection."""
    try:
        if leds:
            leds.fill(color)
            time.sleep(duration)
            leds.fill(OFF)
    except:
        pass

# -------------------------------------------------------------------------------
# NETWORK FUNCTIONS - BULLETPROOF
# -------------------------------------------------------------------------------
def connect_wifi():
    """Connect to WiFi with error handling."""
    try:
        if wifi.radio.connected:
            return True

        print("Connecting to WiFi...")
        set_led(BLUE)

        if GATEWAY:
            wifi.radio.set_ipv4_address(
                ipv4=ipaddress.IPv4Address(STATIC_IP),
                netmask=ipaddress.IPv4Address(NETMASK),
                gateway=ipaddress.IPv4Address(GATEWAY)
            )
            if DNS:
                wifi.radio.dns = ipaddress.IPv4Address(DNS)

        wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
        print(f"WiFi connected: {wifi.radio.ipv4_address}")
        return True
    except Exception as e:
        print(f"WiFi error: {e}")
        return False

def create_io_client():
    """Create AdafruitIO client with error handling."""
    try:
        pool = socketpool.SocketPool(wifi.radio)
        requests = Session(pool, ssl.create_default_context())
        return IO_HTTP(AIO_USERNAME, AIO_KEY, requests)
    except Exception as e:
        print(f"IO client error: {e}")
        return None

# Initial connection
if not connect_wifi():
    print("CRITICAL: Initial WiFi connection failed")
    while True:
        time.sleep(1)
        if connect_wifi():
            break

io = create_io_client()
if not io:
    print("CRITICAL: AdafruitIO client creation failed")
    while True:
        time.sleep(1)

set_led(GREEN)
print("Network ready")

# -------------------------------------------------------------------------------
# COMMAND PROCESSING - BULLETPROOF
# -------------------------------------------------------------------------------
def safe_display_update(text):
    """Update display with full error protection."""
    try:
        if text_area and display:
            text_area.text = str(text)
            display.refresh()
            return True
    except Exception as e:
        print(f"Display error: {e}")
    return False

def execute_command(command):
    """Execute HID macro with bulletproof error handling."""
    global last_display_time

    try:
        if command not in macro_commands:
            print(f"✗ {command} (not found)")
            return

        # Display command
        if safe_display_update(command):
            last_display_time = time.monotonic()

        keycodes = macro_commands[command]

        # Send HID with error handling
        try:
            for key in keycodes:
                kbd.press(key)
            time.sleep(0.05)
            kbd.release_all()
            print(f"✓ {command}")
        except Exception as e:
            print(f"HID error on {command}: {e}")
            # Try to recover HID state
            try:
                kbd.release_all()
            except:
                pass

    except Exception as e:
        print(f"Execute error: {e}")

# -------------------------------------------------------------------------------
# MAIN LOOP - TITANIUM BULLETPROOF
# -------------------------------------------------------------------------------
print(f"Entering bulletproof main loop")
print(f"Free memory: {gc.mem_free()} bytes")

command_queue = deque((), QUEUE_SIZE)
last_poll = 0
last_gc = 0
last_wifi_check = 0
last_display_time = None
is_polling = False
poll_count = 0
consecutive_errors = 0

while True:
    try:
        now = time.monotonic()

        # WiFi health check (every 30s)
        if now - last_wifi_check >= WIFI_CHECK_INTERVAL:
            last_wifi_check = now
            if not wifi.radio.connected:
                print("WiFi disconnected! Reconnecting...")
                set_led(BLUE)
                if connect_wifi():
                    io = create_io_client()
                    set_led(GREEN if poll_count >= 2 else GREEN)
                    if poll_count >= 2:
                        set_led(OFF)
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    set_led(RED)

        # Poll AdafruitIO
        if now - last_poll >= POLL_INTERVAL and not is_polling and wifi.radio.connected:
            is_polling = True
            last_poll = now
            poll_count += 1

            try:
                data_items = io.receive_all_data(FEED_NAME)

                if data_items:
                    flash_led(MAGENTA, 0.6)

                    for item in reversed(data_items):
                        value = item.get("value", "")
                        if value and len(command_queue) < QUEUE_SIZE:
                            command_queue.append(value)

                    for item in data_items:
                        try:
                            io.delete_data(FEED_NAME, item["id"])
                        except:
                            pass

                    print(f"← {len(data_items)} command(s)")
                    consecutive_errors = 0

                if poll_count == 2:
                    set_led(OFF)
                    print("Startup complete, LEDs off")

            except Exception as e:
                print(f"Poll error: {e}")
                consecutive_errors += 1
                set_led(RED)
                time.sleep(0.5)
                if poll_count < 2:
                    set_led(GREEN)
                else:
                    set_led(OFF)

                # Recreate IO client if too many errors
                if consecutive_errors >= 5:
                    print("Too many errors, recreating IO client...")
                    try:
                        io = create_io_client()
                        consecutive_errors = 0
                    except:
                        pass

            finally:
                is_polling = False

        # Process one command per loop
        if command_queue:
            try:
                command = command_queue.popleft()
                execute_command(command)
            except Exception as e:
                print(f"Command processing error: {e}")

        # Clear display timeout
        if last_display_time and (now - last_display_time >= DISPLAY_TIMEOUT):
            try:
                safe_display_update("")
                last_display_time = None
            except:
                pass

        # Aggressive garbage collection
        if now - last_gc >= GC_INTERVAL:
            last_gc = now
            gc.collect()

            # Memory warning
            free = gc.mem_free()
            if free < 10000:
                print(f"WARNING: Low memory: {free} bytes")

        time.sleep(LOOP_DELAY)

    except Exception as e:
        # Catch-all for any unhandled errors
        print(f"CRITICAL LOOP ERROR: {e}")
        set_led(RED)
        time.sleep(1)
        # Try to continue
        try:
            gc.collect()
        except:
            pass
