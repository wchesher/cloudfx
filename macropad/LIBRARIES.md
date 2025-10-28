# MacroPad CloudFX - Required Libraries
# CircuitPython 10.0.3 Bundle

## REQUIRED (Core Functionality)

### MacroPad Library
adafruit_macropad.mpy                  # Main MacroPad hardware library

### USB HID
adafruit_hid/                          # USB HID keyboard/mouse/consumer (folder)
  ├── __init__.mpy
  ├── keyboard.mpy                     # HID keyboard
  ├── keycode.mpy                      # Key definitions
  ├── mouse.mpy                        # HID mouse
  ├── consumer_control.mpy             # Media keys
  └── consumer_control_code.mpy        # Media key codes

### Display
adafruit_display_text/                 # Text rendering (folder)
  └── (all files)
adafruit_display_shapes/               # Shape drawing (Rect for header) (folder)
  └── (all files)

### NeoPixel LEDs
neopixel.mpy                           # For MacroPad's 12 RGB key LEDs

### Dependencies
adafruit_debouncer.mpy                 # Debouncing (used by macropad library)
adafruit_pixelbuf.mpy                  # Pixel buffer (used by neopixel)
adafruit_ticks.mpy                     # Timing utilities (may be dependency)

## OPTIONAL (Enhanced Features)

### Custom Fonts
adafruit_bitmap_font/                  # Custom fonts (folder)
  └── (all files)
# Note: Code uses built-in terminalio.FONT, so this is optional

## NOT NEEDED (Can Delete)

adafruit_led_animation/                # LED animations (not used)
adafruit_midi/                         # MIDI support (not used)
adafruit_simple_text_display.mpy       # Simpler display wrapper (not used)
output.txt                             # User file (not a library!)

## Minimal Working Setup

```
CIRCUITPY/lib/
├── adafruit_macropad.mpy              ← Main library
├── adafruit_debouncer.mpy             ← Dependency
├── adafruit_pixelbuf.mpy              ← Dependency for LEDs
├── adafruit_ticks.mpy                 ← Timing utility
├── neopixel.mpy                       ← LED control
├── adafruit_hid/                      ← HID keyboard/mouse (folder)
├── adafruit_display_text/             ← Display text (folder)
└── adafruit_display_shapes/           ← Display shapes (folder)
```

## With Optional Features

```
CIRCUITPY/lib/
├── adafruit_macropad.mpy
├── adafruit_debouncer.mpy
├── adafruit_pixelbuf.mpy
├── adafruit_ticks.mpy
├── neopixel.mpy
├── adafruit_hid/
├── adafruit_display_text/
├── adafruit_display_shapes/
└── adafruit_bitmap_font/              ← Optional: custom fonts
```

## Notes

1. **adafruit_macropad.mpy** is the main library that controls:
   - The 12 mechanical keys
   - The 12 NeoPixel RGB LEDs
   - The rotary encoder
   - The OLED display
   - The speaker

2. **neopixel.mpy** is REQUIRED even though not directly imported in your code.
   The macropad library uses it internally for the LED control.

3. **adafruit_debouncer.mpy** is REQUIRED as a dependency of macropad.

4. **adafruit_pixelbuf.mpy** is REQUIRED for NeoPixel operations.

5. **adafruit_display_shapes/** is used for drawing the header rectangle.

6. **adafruit_bitmap_font/** is optional - code falls back to terminalio.FONT.

## Storage Impact

Minimal setup: ~150KB
With optional features: ~200KB
Everything from your list: ~300KB

**Recommendation:** Keep everything except led_animation, midi, and simple_text_display.
