# FunHouse CloudFX - Required Libraries
# CircuitPython 10.0.3 Bundle

## REQUIRED (Core Functionality)

### Network & AdafruitIO
adafruit_requests.mpy                  # HTTP client
adafruit_connection_manager.mpy        # Connection pooling (dependency of requests)
adafruit_io/                           # AdafruitIO client library (folder)
  ├── adafruit_io.mpy                  # Main IO client
  └── adafruit_io_errors.mpy           # Error definitions

### USB HID
adafruit_hid/                          # USB HID keyboard/mouse (folder)
  ├── __init__.mpy
  ├── keyboard.mpy                     # HID keyboard
  ├── keycode.mpy                      # Key definitions
  ├── mouse.mpy                        # HID mouse (not used yet)
  ├── consumer_control.mpy             # Media keys (not used yet)
  └── consumer_control_code.mpy        # Media key codes

### Display
adafruit_display_text/                 # Text rendering (folder)
  └── (all files)

## OPTIONAL (Enhanced Features)

### Custom Fonts
adafruit_bitmap_font/                  # Custom fonts (folder)
  └── (all files)
# Note: Falls back to built-in terminalio.FONT if not present

### Status LEDs (for poll timer/status display)
adafruit_dotstar.mpy                   # DotStar RGB LEDs (5 LEDs on side of FunHouse)

### Utilities
adafruit_ticks.mpy                     # Timing utilities (may be dependency)

## NOT NEEDED (Can Delete)
adafruit_adt7410.mpy                   # Temperature sensor
adafruit_ahtx0.mpy                     # Humidity sensor
adafruit_binascii.mpy                  # Binary conversion
adafruit_fakerequests.mpy              # Mock/test library
adafruit_macropad.mpy                  # Wrong device!
adafruit_pixelbuf.mpy                  # Pixel buffer
adafruit_simple_text_display.mpy       # Simpler display lib
neopixel.mpy                           # NeoPixel LEDs (FunHouse uses DotStar)
simpleio.mpy                           # Simple I/O

adafruit_display_shapes/               # Shape drawing (not used)
adafruit_dps310/                       # Pressure sensor
adafruit_esp32spi/                     # ESP32 as peripheral
adafruit_funhouse/                     # High-level FunHouse wrapper (we use low-level)
adafruit_led_animation/                # LED animations
adafruit_midi/                         # MIDI support
adafruit_minimqtt/                     # MQTT (we use HTTP)
adafruit_portalbase/                   # Portal library
adafruit_register/                     # I2C register helper
adafruit_debouncer.mpy                 # Debouncer (not used by our code)

## Minimal Working Setup

For basic functionality (no DotStar, no custom fonts):
```
CIRCUITPY/lib/
├── adafruit_requests.mpy
├── adafruit_connection_manager.mpy
├── adafruit_io/
├── adafruit_hid/
└── adafruit_display_text/
```

For full features (with DotStar status LEDs):
```
CIRCUITPY/lib/
├── adafruit_requests.mpy
├── adafruit_connection_manager.mpy
├── adafruit_io/
├── adafruit_hid/
├── adafruit_display_text/
├── adafruit_dotstar.mpy              ← For status LEDs
├── adafruit_bitmap_font/             ← For custom fonts (optional)
└── adafruit_ticks.mpy                ← Timing utility (may be needed)
```

## Storage Impact

Minimal setup: ~100KB
Full setup: ~200KB
Everything from your list: ~2MB+

**Recommendation:** Use full setup for best features and debugging.
