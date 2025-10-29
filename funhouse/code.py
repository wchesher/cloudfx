# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: © 2024 William C. Chesher <wchesher@gmail.com>
#
# CloudFX FunHouse
# CircuitPython 10.0.3
# ===================================
#
# AdafruitIO → HID command processor
# Comprehensive error handling, auto-recovery, memory management
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

print(f"CloudFX FunHouse v1.0")
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
    print("Initializing display...")
    display = board.DISPLAY
    splash = displayio.Group()
    display.root_group = splash
    text_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, scale=3)
    text_area.x, text_area.y = 10, 60
    splash.append(text_area)
    display.auto_refresh = False
    display.refresh()
    print("Display initialized, turning off backlight...")
    try:
        display.brightness = 0  # Turn off backlight completely at startup
        print("✓ Display ready (backlight off)")
    except Exception as e:
        print(f"⚠ Backlight control failed: {e}")
        print("  Display will stay on (not critical)")
except Exception as e:
    print(f"✗ Display init error: {e}")
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
# NETWORK FUNCTIONS
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
# COMMAND PROCESSING
# -------------------------------------------------------------------------------
def safe_display_update(text):
    """Update display with full error protection."""
    try:
        if text_area and display:
            text_area.text = str(text)
            display.refresh()

            # Control backlight separately with error handling
            try:
                target_brightness = 1.0 if text else 0.0
                display.brightness = target_brightness
                if text:
                    print(f"  Display: '{text}' (backlight ON)")
                else:
                    print(f"  Display: cleared (backlight OFF)")
            except Exception as e:
                print(f"  ⚠ Backlight control error: {e}")
                # Continue anyway - display text still updated

            return True
    except Exception as e:
        print(f"✗ Display update error: {e}")
        import traceback
        traceback.print_exception(e, e, e.__traceback__)
    return False

def execute_command(command):
    """Execute HID macro with comprehensive error handling."""
    global last_display_time

    try:
        print(f"→ Executing: {command}")

        if command not in macro_commands:
            print(f"  ✗ Command not found in macro list")
            return

        # Display command and turn on magenta LEDs (synced)
        try:
            if safe_display_update(command):
                last_display_time = time.monotonic()
                print(f"  Display timer started ({DISPLAY_TIMEOUT}s)")
        except Exception as e:
            print(f"  ⚠ Display update failed: {e}")

        # Turn on magenta LEDs
        try:
            set_led(MAGENTA)
            print(f"  LEDs: MAGENTA")
        except Exception as e:
            print(f"  ⚠ LED control failed: {e}")

        keycodes = macro_commands[command]

        # Send HID with error handling
        try:
            for key in keycodes:
                kbd.press(key)
            time.sleep(0.05)
            kbd.release_all()
            print(f"  ✓ HID sent successfully")
        except Exception as e:
            print(f"  ✗ HID error: {e}")
            import traceback
            traceback.print_exception(e, e, e.__traceback__)
            # Try to recover HID state
            try:
                kbd.release_all()
            except:
                pass

    except Exception as e:
        print(f"✗ Command execution error: {e}")
        import traceback
        traceback.print_exception(e, e, e.__traceback__)

# -------------------------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------------------------
print("")
print("=" * 50)
print("MAIN LOOP STARTED")
print("=" * 50)
print(f"Free memory: {gc.mem_free()} bytes")
print(f"Poll interval: {POLL_INTERVAL}s")
print(f"Display timeout: {DISPLAY_TIMEOUT}s")
print(f"WiFi check interval: {WIFI_CHECK_INTERVAL}s")
print(f"Commands loaded: {len(macro_commands)}")
print("=" * 50)
print("")

command_queue = deque((), QUEUE_SIZE)
last_poll = 0
last_gc = 0
last_wifi_check = 0
last_display_time = None
is_polling = False
poll_count = 0
consecutive_errors = 0

print("Loop started. Monitoring for commands...")

while True:
    try:
        now = time.monotonic()

        # WiFi health check (every 30s)
        if now - last_wifi_check >= WIFI_CHECK_INTERVAL:
            last_wifi_check = now
            print(f"[WiFi Check] Status: {'Connected' if wifi.radio.connected else 'Disconnected'}")
            if not wifi.radio.connected:
                print("  ✗ WiFi disconnected! Reconnecting...")
                set_led(BLUE)
                if connect_wifi():
                    print("  ✓ WiFi reconnected, recreating IO client...")
                    io = create_io_client()
                    set_led(GREEN if poll_count >= 2 else GREEN)
                    if poll_count >= 2:
                        set_led(OFF)
                    consecutive_errors = 0
                else:
                    print("  ✗ Reconnection failed")
                    consecutive_errors += 1
                    set_led(RED)
            else:
                print(f"  ✓ WiFi healthy ({wifi.radio.ipv4_address})")

        # Poll AdafruitIO
        if now - last_poll >= POLL_INTERVAL and not is_polling and wifi.radio.connected:
            is_polling = True
            last_poll = now
            poll_count += 1
            print(f"[Poll #{poll_count}] Checking AdafruitIO feed...")

            try:
                data_items = io.receive_all_data(FEED_NAME)

                if data_items:
                    print(f"  ← Received {len(data_items)} command(s)")
                    for item in reversed(data_items):
                        value = item.get("value", "")
                        if value and len(command_queue) < QUEUE_SIZE:
                            command_queue.append(value)
                            print(f"    Queued: {value}")

                    for item in data_items:
                        try:
                            io.delete_data(FEED_NAME, item["id"])
                        except Exception as e:
                            print(f"    ⚠ Delete failed: {e}")

                    consecutive_errors = 0
                else:
                    print(f"  No new commands")

                if poll_count == 2:
                    set_led(OFF)
                    print("✓ Startup complete, LEDs off")

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
                print(f"[Queue] Processing command (queue size: {len(command_queue)})")
                execute_command(command)
            except Exception as e:
                print(f"✗ Command processing error: {e}")
                import traceback
                traceback.print_exception(e, e, e.__traceback__)

        # Clear display and LEDs after timeout (synced)
        if last_display_time and (now - last_display_time >= DISPLAY_TIMEOUT):
            try:
                print(f"[Timeout] Clearing display and LEDs after {DISPLAY_TIMEOUT}s")
                safe_display_update("")  # Turns off backlight
                try:
                    set_led(OFF)  # Turn off magenta LEDs (synced with display)
                    print(f"  LEDs: OFF")
                except Exception as e:
                    print(f"  ⚠ LED off failed: {e}")
                last_display_time = None
            except Exception as e:
                print(f"✗ Timeout handler error: {e}")
                import traceback
                traceback.print_exception(e, e, e.__traceback__)

        # Aggressive garbage collection
        if now - last_gc >= GC_INTERVAL:
            last_gc = now
            before = gc.mem_free()
            gc.collect()
            after = gc.mem_free()
            freed = after - before

            # Log memory status
            if freed > 1000 or after < 20000:
                print(f"[GC] Memory: {after} bytes free (freed {freed} bytes)")

            # Memory warning
            if after < 10000:
                print(f"⚠⚠⚠ WARNING: LOW MEMORY: {after} bytes ⚠⚠⚠")
                set_led(RED)
                time.sleep(0.5)
                set_led(OFF if poll_count >= 2 else GREEN)

        time.sleep(LOOP_DELAY)

    except KeyboardInterrupt as e:
        # Handle forced stops
        print(f"⚠ KeyboardInterrupt caught in main loop")
        print(f"  This usually means supervisor killed the program")
        print(f"  Memory at interrupt: {gc.mem_free()} bytes")
        print(f"  Poll count: {poll_count}, Queue size: {len(command_queue)}")
        raise  # Re-raise to stop program

    except Exception as e:
        # Catch-all for any unhandled errors
        print(f"✗✗✗ CRITICAL LOOP ERROR ✗✗✗")
        print(f"Error: {e}")
        import traceback
        traceback.print_exception(e, e, e.__traceback__)
        print(f"Memory: {gc.mem_free()} bytes")
        print(f"Poll count: {poll_count}, Queue size: {len(command_queue)}")
        set_led(RED)
        time.sleep(2)
        # Try to continue
        try:
            gc.collect()
            print("Attempting to continue...")
        except:
            pass
