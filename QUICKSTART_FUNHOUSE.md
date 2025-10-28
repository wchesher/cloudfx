# FunHouse Quick Start - settings.toml Migration

Follow these steps to update your FunHouse to use settings.toml:

## Step 1: Copy Updated Code

Copy the new `code.py` to your FunHouse:

**From this repo:**
```
funhouse/code.py  →  CIRCUITPY/code.py (replace existing)
```

This file now uses `settings.toml` instead of `secrets.py`.

## Step 2: Create settings.toml

1. **Copy the template:**
   ```
   funhouse/settings.toml.example  →  CIRCUITPY/settings.toml
   ```

2. **Edit CIRCUITPY/settings.toml** with your actual credentials:

```toml
# settings.toml
CIRCUITPY_WIFI_SSID = "YourWiFiNetworkName"
CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
AIO_USERNAME = "your_aio_username"
AIO_KEY = "aio_xxxxxxxxxxxxxxxxxxxx"
```

**IMPORTANT Notes:**
- Use your actual values (remove the example text)
- No quotes needed in TOML (CircuitPython adds them)
- WiFi must be 2.4GHz (ESP32-S2 limitation)
- Get AIO credentials from https://io.adafruit.com/ → "My Key"

## Step 3: (Optional) Static IP

If you want a static IP, add these lines to `settings.toml`:

```toml
STATIC_IP = "192.168.1.100"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"
```

Otherwise, leave them out for DHCP (automatic).

## Step 4: Verify Other Files

Make sure you also have:
- ✅ `macros.py` on CIRCUITPY
- ✅ All libraries in `lib/` folder
- ✅ (Optional) Font file in `fonts/` folder

## Step 5: Restart FunHouse

1. **Safely eject** the CIRCUITPY drive
2. **Unplug** USB cable
3. **Plug back in**
4. Watch serial console for connection messages

## Expected Serial Output

```
CircuitPython 10.0.3
Loaded 15 macro(s) from macros.py
USB HID keyboard initialized
Display initialized
Settings loaded successfully from settings.toml
CloudFX FunHouse starting...
Initializing WiFi connection...
Connecting to SSID: YourNetwork
Connected! IP: 192.168.1.xxx
Listening for commands...
```

## Troubleshooting

**"ERROR: Missing required settings"**
- Check all 4 required fields are in settings.toml
- Verify no typos in variable names

**"WiFi connection failed"**
- Verify SSID and password are correct
- Ensure using 2.4GHz network
- Check WiFi is in range

**Still getting "no module named secrets"**
- Old code.py is still loaded
- Make sure you copied the NEW code.py from funhouse/code.py
- Check file was actually saved to device

## What Changed

| Old (secrets.py) | New (settings.toml) |
|------------------|---------------------|
| Python dictionary format | TOML format |
| `from secrets import secrets` | `os.getenv("VAR_NAME")` |
| `secrets["ssid"]` | `CIRCUITPY_WIFI_SSID` |
| Manual import | Automatic loading |

## Files on Your FunHouse

After setup, you should have:
```
CIRCUITPY/
├── code.py              ← NEW version (uses settings.toml)
├── settings.toml        ← YOUR credentials (not in repo)
├── macros.py
├── lib/
│   ├── adafruit_requests.mpy
│   ├── adafruit_hid/
│   └── ...
└── fonts/ (optional)
```

**Do NOT have:**
- ❌ secrets.py (old, not needed anymore)

---

**Need help?** Check the serial console output for specific error messages.
