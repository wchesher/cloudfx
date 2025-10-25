# CloudFX - AI Vision for CircuitPython

**Version 1.0**

CloudFX is an educational CircuitPython project that demonstrates how to integrate camera hardware with AI vision capabilities using Anthropic's Claude API. Designed for teaching computer science concepts including IoT development, API integration, configuration management, and real-world AI applications.

## 🎯 Educational Objectives

This project teaches:
- **Configuration Management**: Separating secrets, settings, and code
- **API Integration**: Working with modern AI APIs
- **Hardware Interfacing**: Camera and sensor control in CircuitPython
- **Software Architecture**: Modular design and separation of concerns
- **Best Practices**: Security, documentation, and maintainable code

## 📋 Requirements

### Hardware
- CircuitPython-compatible board with WiFi (ESP32-S3 recommended)
- Camera module (compatible with your board)
- Optional: Light sensor for auto-flash
- Optional: Display (240x240 recommended)

### Software
- CircuitPython 9.0 or higher
- Required libraries (see Installation section)
- Anthropic API key (free tier available)

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/cloudfx.git
cd cloudfx
```

### 2. Set Up Secrets

```bash
cp secrets.toml.example secrets.toml
```

Edit `secrets.toml` with your credentials:
```toml
CIRCUITPY_WIFI_SSID = "your-network"
CIRCUITPY_WIFI_PASSWORD = "your-password"
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```

**⚠️ IMPORTANT**: Never commit `secrets.toml` - it's already in `.gitignore`

### 3. Customize Settings

Edit `settings.toml` to configure:
- Camera resolution
- Flash sensitivity
- Prompt modes
- Display options
- Network settings

### 4. Deploy to Device

Copy these files to your CircuitPython device:
- `code.py` (main program)
- `settings.toml`
- `secrets.toml`
- `lib/` folder (CircuitPython libraries)

## 🎨 Prompt Modes

CloudFX includes 12 creative AI prompt modes:

| Mode | Purpose | Educational Focus |
|------|---------|-------------------|
| **DESCRIBE** | Accessibility-focused image descriptions | Social media accessibility, alt text |
| **ART ANALYSIS** | Formal art critique | Art education, critical thinking |
| **HAIKU** | Creative poetry generation | Creative AI, constraint-based generation |
| **TRANSLATE** | OCR and translation | Computer vision + NLP |
| **ALIEN** | Perspective-shifting descriptions | Creative thinking, context awareness |
| **WEIRD** | Anomaly detection | Object recognition, context understanding |
| **MOVIE** | Title and tagline generation | Creative AI, marketing concepts |
| **PLANT** | Species identification | Classification, domain knowledge |
| **CAR** | Imaginative product design | Creative reasoning, product development |
| **DRAMA** | Soap opera storytelling | Creative writing, character development |
| **STUDY** | Educational tutoring | Teaching methodology, interactive learning |
| **KINDNESS** | Social-emotional observation | AI ethics, human connection |

## 📂 Project Structure

```
cloudfx/
├── code.py                    # Main application (NO hardcoded values)
├── settings.toml              # All configuration settings
├── secrets.toml               # Credentials (NOT in git)
├── secrets.toml.example       # Template for secrets
├── lib/                       # CircuitPython libraries
│   ├── settings_loader.py     # Settings management utility
│   └── ...                    # Other required libraries
├── README.md                  # This file
├── LICENSE                    # MIT License
├── CONTRIBUTING.md            # Contribution guidelines
└── .gitignore                 # Git ignore rules

```

## 🏗️ Architecture Principles

### 1. **Separation of Concerns**
- **Code** (`code.py`): Business logic only
- **Settings** (`settings.toml`): Non-sensitive configuration
- **Secrets** (`secrets.toml`): Credentials and sensitive data

### 2. **No Hardcoded Values**
All configuration is externalized:
```python
# ❌ BAD - Hardcoded
camera_resolution = 1
flash_threshold = 30

# ✅ GOOD - From settings
camera_resolution = settings["camera"]["resolution"]
flash_threshold = settings["flash"]["dark_threshold"]
```

### 3. **Security First**
- Secrets never committed to git
- Example files for safe sharing
- Clear documentation on security

### 4. **Maintainability**
- Clear comments and documentation
- Modular code structure
- Descriptive variable names
- Type hints where applicable

## 🔧 Configuration Guide

### Camera Settings

```toml
[camera]
resolution = 1  # 0-6, see settings.toml for details
```

**Choosing Resolution:**
- `0` (240x240): Best for displays, fastest
- `1` (320x240): Balanced quality/speed
- `2+`: Higher quality, slower processing, larger files

### Flash Settings

```toml
[flash]
auto_flash_enabled = true
dark_threshold = 30  # 0-255, lower = darker needed
```

**Tuning Threshold:**
- Test in your environment
- Start at 30, adjust based on results
- Lower values = flash only in darker conditions

### Custom Prompts

Add your own prompt to `settings.toml`:

```toml
[prompts.MY_CUSTOM]
label = "CUSTOM NAME"
prompt = """Your custom instruction here..."""
```

Then add to the order:
```toml
[prompts]
order = "DESCRIBE,MY_CUSTOM,..."
```

## 🛠️ Development

### Adding New Features

1. **Identify Configuration**: What should be user-configurable?
2. **Update settings.toml**: Add new settings with documentation
3. **Update Code**: Read settings, never hardcode
4. **Document**: Update README and code comments
5. **Test**: Verify with different configurations

### Code Style Guidelines

- Use descriptive variable names
- Comment complex logic
- No magic numbers - use settings
- Handle errors gracefully
- Log important events

## 📚 Teaching Notes

### Lesson Plan Ideas

1. **Lesson 1: IoT Basics**
   - Hardware setup
   - WiFi connectivity
   - Sensor reading

2. **Lesson 2: API Integration**
   - REST API concepts
   - Authentication
   - Request/response handling

3. **Lesson 3: Configuration Management**
   - Why separate settings from code
   - Security best practices
   - TOML format

4. **Lesson 4: Image Processing**
   - Camera operation
   - Image encoding
   - Data transmission

5. **Lesson 5: Prompt Engineering**
   - How to write effective prompts
   - Testing and iteration
   - Domain-specific applications

### Discussion Topics

- **Ethics**: When should AI vision be used? Privacy concerns?
- **Accessibility**: How does AI help people with disabilities?
- **Creativity**: Can AI be creative? What makes a good creative prompt?
- **Reliability**: How do we handle errors and unexpected results?

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### For Students
- Report bugs you find
- Suggest new prompt modes
- Improve documentation
- Share your projects

### For Educators
- Share lesson plans
- Suggest improvements
- Report issues
- Contribute examples

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

Copyright (c) 2025 William Chesher

## 🙏 Acknowledgments

- Built with [CircuitPython](https://circuitpython.org/)
- Powered by [Anthropic Claude](https://www.anthropic.com/)
- Inspired by the maker and education communities

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cloudfx/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cloudfx/discussions)
- **Documentation**: This README and inline code comments

## 🔗 Resources

- [CircuitPython Documentation](https://docs.circuitpython.org/)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [TOML Specification](https://toml.io/)

---

**Made with ❤️ for education and learning**
