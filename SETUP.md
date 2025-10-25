# CloudFX Setup Guide

Detailed setup instructions for getting CloudFX running on your CircuitPython device.

## Hardware Requirements

### Recommended Hardware

**ESP32-S3 Based Boards** (Recommended for Students)
- Adafruit ESP32-S3 Feather with Camera
- Adafruit QT Py ESP32-S3 with Camera
- Waveshare ESP32-S3 Camera Board

**Other Compatible Boards**
- Any CircuitPython board with:
  - WiFi capability
  - Camera interface
  - Minimum 2MB RAM
  - CircuitPython 9.0+ support

### Optional Components

- **Display**: 240x240 TFT display (for visual feedback)
- **Light Sensor**: For auto-flash functionality
- **Buttons**: For mode switching and capture triggering
- **LED/Flash**: For low-light photography

## Software Requirements

### CircuitPython

**Version**: 9.0 or higher

Download from: https://circuitpython.org/downloads

**Installation**:
1. Download the `.uf2` file for your board
2. Put board in bootloader mode (double-tap reset)
3. Drag `.uf2` file to `BOOT` drive
4. Board will restart as `CIRCUITPY` drive

### Required CircuitPython Libraries

Copy these to the `lib/` folder on your device:

**Core Libraries** (from [CircuitPython Bundle](https://circuitpython.org/libraries)):
- `adafruit_requests.mpy`
- `adafruit_display_text/` (folder)
- `adafruit_bitmap_font/` (folder)

**Camera Libraries** (board-specific):
- For ESP32-S3: `espcamera.mpy`
- Check your board's documentation

**Additional Libraries**:
- TOML parser (may be built-in to CircuitPython 9+)

**Finding Libraries**:
1. Download the [CircuitPython Library Bundle](https://circuitpython.org/libraries)
2. Extract the bundle
3. Copy required `.mpy` files to your `lib/` folder

### API Credentials

**Anthropic Claude API**:
1. Visit https://console.anthropic.com/
2. Create an account (free tier available)
3. Generate an API key
4. Save for use in `secrets.toml`

**Important**: The free tier has usage limits. Monitor your usage at the console.

## Installation Steps

### 1. Prepare Your Board

```bash
# Connect your CircuitPython board via USB
# Verify it appears as CIRCUITPY drive
ls /media/CIRCUITPY  # Linux/Mac
# or
dir D:  # Windows (adjust drive letter)
```

### 2. Clone CloudFX Repository

```bash
git clone https://github.com/yourusername/cloudfx.git
cd cloudfx
```

### 3. Configure Secrets

```bash
# Copy the example file
cp secrets.toml.example secrets.toml

# Edit with your credentials
nano secrets.toml  # or use your preferred editor
```

Fill in:
```toml
CIRCUITPY_WIFI_SSID = "YourNetworkName"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
```

**Security Reminder**: Never commit `secrets.toml` to version control!

### 4. Customize Settings (Optional)

Edit `settings.toml` to customize:

```toml
[camera]
resolution = 1  # Adjust based on your needs

[flash]
dark_threshold = 30  # Tune for your environment

[prompts]
order = "DESCRIBE,HAIKU,..."  # Reorder as desired
```

### 5. Copy Files to Device

```bash
# Copy main files
cp code.py /media/CIRCUITPY/
cp settings.toml /media/CIRCUITPY/
cp secrets.toml /media/CIRCUITPY/

# Copy library files
cp -r lib/ /media/CIRCUITPY/lib/

# On Windows:
# copy code.py D:\
# copy settings.toml D:\
# copy secrets.toml D:\
# xcopy /E /I lib D:\lib
```

### 6. Verify Installation

Check your device has these files:
```
CIRCUITPY/
├── code.py
├── settings.toml
├── secrets.toml
└── lib/
    ├── settings_loader.py
    └── [other libraries]
```

### 7. Test Connectivity

Connect to the serial console:

```bash
# Linux/Mac
screen /dev/ttyUSB0 115200

# Windows - use Mu Editor or PuTTY
# Port: COM3 (or appropriate COM port)
# Baud: 115200
```

Press reset on your board and watch for:
```
CloudFX - AI Vision for CircuitPython
Version 1.0
========================================

Loading settings...
✓ Settings loaded successfully
Connecting to WiFi: YourNetworkName
✓ Connected to WiFi
  IP Address: 192.168.1.100
✓ HTTPS requests ready
✓ Camera initialized
  Resolution: 1
✓ Initialization complete
```

## Troubleshooting

### "Settings file not found"

**Problem**: Can't find `settings.toml`

**Solutions**:
- Verify file is in root of CIRCUITPY drive (not in a folder)
- Check filename is exactly `settings.toml` (no `.txt` extension)
- Verify file was copied completely

### "Secrets file not found"

**Problem**: Can't find `secrets.toml`

**Solutions**:
- Did you copy `secrets.toml.example` to `secrets.toml`?
- Is it in the root directory?
- Check the filename

### "WiFi connection failed"

**Problem**: Can't connect to WiFi

**Solutions**:
- Verify SSID and password are correct
- Check WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Ensure WiFi is not hidden
- Try connecting from serial console to see detailed errors
- Check antenna connection (if external)

### "Error parsing settings.toml"

**Problem**: TOML syntax error

**Solutions**:
- Validate TOML syntax at https://www.toml-lint.com/
- Check for common issues:
  - Missing quotes around strings
  - Unclosed brackets
  - Invalid characters
- Compare with `settings.toml.example`

### "API request failed"

**Problem**: Can't reach Claude API

**Solutions**:
- Verify API key is correct
- Check API key has not expired
- Verify internet connectivity (ping test)
- Check Anthropic API status
- Ensure you haven't exceeded rate limits

### "Camera initialization failed"

**Problem**: Camera not working

**Solutions**:
- Verify camera is properly connected
- Check you have correct camera library
- Verify pin configuration in code matches your hardware
- Test camera with simple example first

### "Out of memory"

**Problem**: Device runs out of RAM

**Solutions**:
- Reduce camera resolution
- Clear unnecessary files from CIRCUITPY
- Use `.mpy` compiled libraries (not `.py`)
- Reduce max_tokens in settings

## Testing

### Test Settings Loading

```bash
# On your computer (not device)
cd cloudfx
python lib/settings_loader.py
```

Expected output:
```
✓ Settings loaded successfully!
  Camera resolution: 1
  Auto flash: True
  Dark threshold: 30
  API model: claude-3-haiku-20240307
  Prompts configured: 12
```

### Test Individual Components

Create test files to verify each component:

**Test WiFi Only**:
```python
import wifi
wifi.radio.connect("SSID", "password")
print(wifi.radio.ipv4_address)
```

**Test Camera Only**:
```python
import espcamera
camera = espcamera.Camera(...)
frame = camera.take()
print(f"Captured {len(frame)} bytes")
```

## Performance Tuning

### For Faster Response

```toml
[camera]
resolution = 0  # 240x240 is fastest

[api]
model = "claude-3-haiku-20240307"  # Fastest Claude model
max_tokens = 512  # Reduce for shorter responses
```

### For Better Quality

```toml
[camera]
resolution = 2  # 640x480 VGA

[api]
model = "claude-3-5-sonnet-20241022"  # Better quality
max_tokens = 1024  # Longer responses
```

### For Battery Life

```toml
[flash]
auto_flash_enabled = false  # Disable flash

[camera]
resolution = 0  # Lower resolution uses less power

[network]
# Disconnect when not in use (implement in code)
```

## Next Steps

Once setup is complete:

1. **Read the README**: Understand the prompt modes
2. **Try Different Prompts**: Cycle through the modes
3. **Customize Prompts**: Edit settings.toml to create your own
4. **Join the Community**: Share your projects and learn from others
5. **Contribute Back**: Improve the project for others

## Getting Help

- **Documentation**: Start with README.md
- **Issues**: https://github.com/yourusername/cloudfx/issues
- **Discussions**: https://github.com/yourusername/cloudfx/discussions
- **CircuitPython Help**: https://discord.gg/circuitpython

## Educational Resources

### Learning CircuitPython
- [CircuitPython Essentials](https://learn.adafruit.com/circuitpython-essentials)
- [CircuitPython on Hardware](https://github.com/adafruit/awesome-circuitpython)

### Learning AI/APIs
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

### Learning Configuration Management
- [TOML Specification](https://toml.io/)
- [The Twelve-Factor App](https://12factor.net/) - See factor III (Config)

---

**Happy Making! 🚀**
