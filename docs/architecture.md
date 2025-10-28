# CloudFX System Architecture

This document describes the technical architecture of the CloudFX system.

## System Overview

CloudFX consists of two independent CircuitPython devices that both act as USB HID keyboards:

1. **MacroPad RP2040**: Standalone physical interface for sound effects and macros
2. **FunHouse ESP32-S2**: Network-connected remote command receiver

## Design Philosophy

### Independence
Both devices operate independently and don't communicate directly with each other. This provides:
- **Reliability**: One device failing doesn't affect the other
- **Flexibility**: Use either device alone or both together
- **Simplicity**: No complex inter-device communication protocol needed

### USB HID Protocol
Both devices use standard USB HID (Human Interface Device) protocol:
- **Universal compatibility**: Works with any OS (Windows, macOS, Linux)
- **No drivers needed**: OS recognizes devices as standard keyboards
- **Low latency**: Direct USB communication
- **Secure**: No network exposure for MacroPad

## MacroPad Architecture

### Hardware Components
- **RP2040 microcontroller**: Dual-core ARM Cortex-M0+ @ 133MHz
- **12 mechanical keys**: Cherry MX compatible switches
- **12 RGB NeoPixel LEDs**: One per key
- **Rotary encoder**: Page navigation and emergency stop
- **128x64 OLED display**: Shows current app and key labels
- **Built-in speaker**: I2S DAC for audio playback
- **USB-C**: Power and HID communication

### Software Architecture

```
┌─────────────────────────────────────────────┐
│           code.py (Main Program)            │
└──────────┬──────────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐    ┌───▼───────┐
│  App  │    │ Hardware  │
│Loader │    │ Manager   │
└───┬───┘    └───┬───────┘
    │            │
    │      ┌─────┴─────────────────┐
    │      │                       │
┌───▼──────▼───┐    ┌──────────────▼────────┐
│ Macro Engine │    │  Screensaver Manager  │
└───┬──────────┘    └───────────────────────┘
    │
    ├────────────┬───────────┬──────────┐
    │            │           │          │
┌───▼───┐  ┌────▼────┐  ┌───▼───┐  ┌──▼───┐
│ HID   │  │ Audio   │  │ LED   │  │ Display│
│Output │  │Playback │  │Control│  │ Update │
└───────┘  └─────────┘  └───────┘  └────────┘
```

### Key Components

#### App Loader
- Scans `/macros/*.py` for app definitions
- Validates app structure
- Creates `App` objects
- Handles loading errors gracefully

#### Hardware Manager
- Initializes MacroPad hardware
- Manages encoder, keys, pixels, display
- Handles input debouncing
- Tracks activity for screensaver

#### Macro Engine
- Interprets macro action sequences
- Executes HID keycodes
- Handles delays and text input
- Manages consumer control and mouse actions
- Coordinates audio playback
- Tone generation

#### Screensaver Manager
- Tracks input activity
- Dims LEDs after timeout
- Blanks display
- Restores on input

### Data Flow: Key Press

```
1. Physical key pressed
2. Hardware manager detects event
3. App retrieves macro definition
4. Macro engine processes action sequence:
   a. LED flashes white
   b. For each action:
      - Keycode → HID keyboard
      - Float → Delay
      - String → Text input
      - Dict → Audio/tone/mouse
      - List → Consumer control
5. Display shows feedback
6. Key released
7. HID keys released
8. LED returns to color
```

### Memory Management
- **RAM**: ~256KB (RP2040)
- **Flash**: 8MB (for audio files)
- **Strategy**:
  - Load apps on startup
  - Keep only current app active
  - Manual display refresh
  - Explicit `pixels.show()`
  - Lazy audio file loading

## FunHouse Architecture

### Hardware Components
- **ESP32-S2 microcontroller**: Single-core Xtensa @ 240MHz
- **2.4" TFT display**: 320x240 color display
- **WiFi**: 802.11 b/g/n 2.4GHz
- **Sensors**: Temperature, pressure, humidity (optional use)
- **USB-C**: Power and HID communication

### Software Architecture

```
┌─────────────────────────────────────────────┐
│           code.py (Main Program)            │
└──────────┬──────────────────────────────────┘
           │
    ┌──────┴──────────┐
    │                 │
┌───▼──────┐    ┌─────▼────────┐
│  WiFi    │    │   Display    │
│ Manager  │    │   Manager    │
└───┬──────┘    └──────────────┘
    │
┌───▼───────────┐
│  AdafruitIO   │
│   Poller      │
└───┬───────────┘
    │
┌───▼──────────┐
│ Command      │
│ Queue        │
└───┬──────────┘
    │
┌───▼──────────┐
│ Macro        │
│ Processor    │
└───┬──────────┘
    │
┌───▼──────────┐
│ HID Output   │
└──────────────┘
```

### Key Components

#### WiFi Manager
- Connects to WiFi (static or DHCP)
- Handles reconnection
- Manages network errors
- Creates requests session

#### AdafruitIO Poller
- Polls feed every 15 seconds
- Fetches new data items
- Deletes processed items
- Handles rate limits
- HTTP connection management

#### Command Queue
- `collections.deque` based
- FIFO processing
- Configurable size (default 50)
- Handles overflow gracefully

#### Macro Processor
- Loads macro definitions from `macros.py`
- Matches command labels to keycodes
- Executes key sequences via HID

#### Display Manager
- Shows current command
- Auto-clear after timeout
- Brightness control
- Error handling

### Data Flow: Remote Command

```
1. User sends command to AdafruitIO feed
2. FunHouse polls feed (every 15s)
3. HTTP GET retrieves feed items
4. Items added to command queue
5. HTTP DELETE removes items from feed
6. Queue processor:
   a. Pop command from queue
   b. Display command on screen
   c. Look up macro definition
   d. Send HID keycode sequence
   e. Wait for auto-clear timeout
7. Display clears
8. Loop continues
```

### Network Protocol

#### AdafruitIO HTTP API

**Fetch Feed Data:**
```
GET https://io.adafruit.com/api/v2/{username}/feeds/macros/data
Headers:
  X-AIO-Key: {aio_key}

Response:
[
  {
    "id": "12345",
    "value": "play_pause",
    "created_at": "2025-10-28T12:34:56Z"
  },
  ...
]
```

**Delete Feed Item:**
```
DELETE https://io.adafruit.com/api/v2/{username}/feeds/macros/data/{id}
Headers:
  X-AIO-Key: {aio_key}
```

### Memory Management
- **RAM**: ~320KB (ESP32-S2)
- **Flash**: 4MB
- **Strategy**:
  - Close HTTP responses immediately
  - Limited queue size
  - Periodic `gc.collect()`
  - Lazy macro loading
  - Display buffer reuse

## USB HID Protocol

Both devices implement USB HID keyboard class:

### HID Descriptors
- **Keyboard**: Standard 101-key
- **Consumer Control**: Media keys (optional)
- **Mouse**: 3-button + wheel (MacroPad only)

### Key Press Sequence
```python
1. kbd.press(Keycode.CONTROL)     # Press modifier
2. kbd.press(Keycode.C)            # Press key
3. time.sleep(0.01)                # Brief hold
4. kbd.release(Keycode.C)          # Release key
5. kbd.release(Keycode.CONTROL)    # Release modifier
```

Or use `kbd.release_all()` to release everything.

### HID Reports
- **Input Report**: Key states sent to host
- **Output Report**: LED states (Caps Lock, etc.) from host
- **Report Rate**: Up to 1000Hz (1ms polling)

## Security Considerations

### MacroPad
- **Physical access**: Anyone with physical access can press buttons
- **Mitigation**: Keep device secure, use encoder emergency stop
- **USB**: Trusted device, no network exposure

### FunHouse
- **Network exposure**: WiFi credentials stored on device
- **AdafruitIO keys**: Stored in plaintext in `secrets.py`
- **Mitigations**:
  - Don't commit `secrets.py` to git
  - Use feed-specific keys (not account keys)
  - Secure physical access to device
  - Monitor AdafruitIO feed for unauthorized access
  - Use strong WiFi passwords

### Host Computer
- Both devices send arbitrary keystrokes
- **Risks**: Malicious macro definitions could harm system
- **Mitigations**:
  - Review all macro definitions
  - Don't run untrusted code
  - Limit HID permissions if OS supports it

## Error Handling Strategy

Both devices use **graceful degradation**:

### Principles
1. **Never crash**: Catch all exceptions
2. **Log errors**: Print to serial console
3. **Continue operation**: Isolate failures
4. **User feedback**: Display errors when possible

### Implementation
```python
try:
    risky_operation()
except Exception as e:
    print("Error description:")
    traceback.print_exception(type(e), e, e.__traceback__)
    # Continue with fallback behavior
```

### Recovery Mechanisms
- **WiFi failure**: Retry with exponential backoff
- **Feed error**: Continue polling, skip failed items
- **HID error**: Release all keys, continue
- **Display error**: Continue without display updates
- **Audio error**: Continue without audio

## Performance Characteristics

### MacroPad
- **Key latency**: <10ms (press to HID report)
- **Audio latency**: ~100ms (press to sound start)
- **Screen update**: ~50ms per refresh
- **Memory usage**: ~50KB Python heap
- **Battery**: N/A (USB powered only)

### FunHouse
- **Poll interval**: 15 seconds (configurable)
- **Command latency**: 0-15s (depends on poll timing)
- **WiFi latency**: 100-500ms per HTTP request
- **HID latency**: <10ms (command to HID report)
- **Memory usage**: ~80KB Python heap
- **Battery**: N/A (USB powered only)

## Scalability

### Adding More Devices
- **Multiple MacroPads**: Unique macro sets per device
- **Multiple FunHouses**: Different AdafruitIO feeds
- **Shared host**: All devices send to same computer

### Limitations
- **USB bandwidth**: Negligible (<1%)
- **AdafruitIO rate limits**:
  - Free: 30 requests/min, 60 requests/hour
  - Plus: 60 requests/min, 120 requests/hour
- **Command queue**: 50 commands (configurable)

## Future Enhancements

### Possible Additions
- **MQTT support**: Alternative to AdafruitIO HTTP
- **Bluetooth HID**: Wireless operation
- **Multi-host**: KVM switch support
- **Macro recording**: Record and playback sequences
- **Web dashboard**: Configure without editing files
- **OTA updates**: Update code over network

### Not Planned
- **Direct device communication**: Complexity vs. benefit
- **Video streaming**: Hardware limitations
- **Battery operation**: Power requirements too high

## Conclusion

CloudFX demonstrates a clean architecture for production control systems:
- Simple, independent components
- Standard protocols (USB HID, HTTP)
- Graceful error handling
- Flexible deployment options

The system is designed for reliability and ease of use in live production environments.
