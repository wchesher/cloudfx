# Helper Applications

This directory is reserved for third-party helper applications used with CloudFX.

## Purpose

Helper apps are external tools that complement the MacroPad and FunHouse devices. Examples include:

- Desktop applications for sending AdafruitIO commands
- Audio file conversion utilities
- Macro configuration editors
- Dashboard applications
- Testing tools

## Adding Helper Apps

If you develop or use helper applications with CloudFX:

1. Create a subdirectory for each app
2. Include a README.md with:
   - Purpose and functionality
   - Installation instructions
   - Usage examples
   - Dependencies
3. Include source code or installation packages

## Example Structure

```
helper-app/
├── aio-sender/           # Command line tool for sending AdafruitIO commands
│   ├── README.md
│   ├── send_command.py
│   └── requirements.txt
├── audio-converter/      # Batch audio file converter for MacroPad
│   ├── README.md
│   └── convert.sh
└── dashboard/            # Web dashboard for monitoring
    ├── README.md
    ├── index.html
    └── app.js
```

## Suggested Helper Apps

### 1. AdafruitIO Command Sender

A simple GUI or CLI tool to send commands to FunHouse without using cURL.

**Features**:
- Store AIO credentials
- Dropdown of available commands
- Send button
- History of sent commands

### 2. Audio File Batch Converter

Convert various audio formats to MacroPad-compatible WAV files.

**Features**:
- Batch processing
- Automatic format conversion (MP3/OGG/FLAC → WAV)
- Sample rate conversion (to 22050Hz or 44100Hz)
- File size optimization
- Output to /sounds directory

### 3. Macro Configuration Editor

GUI for creating and editing macro definitions without editing Python files.

**Features**:
- Visual macro builder
- Keycode picker
- Action sequence editor
- Test/preview functionality
- Export to .py format

### 4. Serial Monitor Dashboard

Real-time monitoring of both devices' serial output in one window.

**Features**:
- Dual serial port monitoring
- Color-coded output
- Log filtering
- Export logs

### 5. System Tester

Automated testing tool to verify both devices are working correctly.

**Features**:
- Device detection
- Library verification
- Network connectivity test (FunHouse)
- Send test commands
- Generate test report

## Integration Ideas

### IFTTT Integration

Create IFTTT applets to trigger FunHouse commands:
- Voice commands (Google Assistant, Alexa)
- Time-based triggers
- Location-based triggers
- Smart home integration

### Home Assistant Integration

Integrate FunHouse with Home Assistant:
- Trigger commands from automations
- Use with other smart devices
- Dashboard controls

### OBS Studio Integration

Control OBS via CloudFX devices:
- Scene switching from MacroPad
- Remote scene control via FunHouse
- Sound effects directly from MacroPad

### Discord/Slack Bots

Create bots that send commands to FunHouse:
- Chat commands trigger actions
- Scheduled announcements
- Event-driven controls

## Community Contributions

If you create a helper app for CloudFX, consider:
- Sharing it with the community
- Creating a pull request
- Adding documentation
- Including examples

## License

Helper applications may have their own licenses. Check each subdirectory for license information.

---

**Note**: This directory is currently empty. Add your own helper applications as needed!
