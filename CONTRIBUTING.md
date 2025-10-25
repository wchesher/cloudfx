# Contributing to CloudFX

Thank you for your interest in contributing to CloudFX! This project is designed for education, and we welcome contributions from students, educators, and makers.

## Code of Conduct

This project follows a Code of Conduct. By participating, you agree to uphold these standards. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### For Students

**Learning Contributions**
- Report bugs you encounter
- Suggest improvements to documentation
- Share what confused you (helps us improve clarity)
- Ask questions via GitHub Issues

**Code Contributions**
- Fix typos and documentation errors
- Add new prompt modes
- Improve error messages
- Add comments to clarify code

### For Educators

**Teaching Contributions**
- Share lesson plans
- Suggest curriculum improvements
- Report educational use cases
- Contribute example projects

**Documentation Contributions**
- Improve setup instructions
- Add troubleshooting guides
- Create video tutorials
- Write blog posts about using CloudFX

### For Developers

**Technical Contributions**
- Bug fixes
- Performance improvements
- New features
- Hardware compatibility
- Testing and CI/CD

## Development Principles

CloudFX follows these core principles:

### 1. **No Hardcoded Values**
All configuration must be in `settings.toml` or `secrets.toml`:

```python
# ❌ BAD
camera_resolution = 1
threshold = 30

# ✅ GOOD
camera_resolution = settings.camera_resolution
threshold = settings.dark_threshold
```

### 2. **Security First**
- Never commit secrets
- Always use `secrets.toml` for credentials
- Validate and sanitize inputs
- Handle errors gracefully

### 3. **Educational Clarity**
- Write self-documenting code
- Add educational comments
- Explain the "why" not just the "what"
- Use descriptive variable names

### 4. **Maintainability**
- Keep functions small and focused
- One responsibility per function
- Clear separation of concerns
- Comprehensive error handling

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/cloudfx.git
cd cloudfx
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

### 3. Set Up Environment

```bash
# Copy example secrets
cp secrets.toml.example secrets.toml

# Edit with your credentials
# (Don't worry, secrets.toml is in .gitignore)
```

### 4. Make Changes

Follow the coding standards below.

### 5. Test Your Changes

- Test on actual hardware if possible
- Verify settings load correctly
- Check error handling
- Ensure no hardcoded values

### 6. Commit

Write clear commit messages:

```bash
git commit -m "Add plant identification prompt

- Adds PLANT prompt mode for species identification
- Updates settings.toml with new prompt
- Updates README with prompt documentation"
```

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Python Style

Follow [PEP 8](https://pep8.org/) with these specifics:

```python
# Indentation: 4 spaces (no tabs)
def my_function():
    return True

# Line length: 88 characters (Black formatter standard)

# Function names: lowercase with underscores
def calculate_threshold():
    pass

# Class names: PascalCase
class SettingsLoader:
    pass

# Constants: UPPERCASE with underscores
MAX_RETRIES = 3
```

### Documentation

**Module Docstrings:**
```python
"""
Module description.

Educational focus:
- Key concept 1
- Key concept 2

Author: Your Name
License: MIT
"""
```

**Function Docstrings:**
```python
def capture_image(camera, flash=False):
    """
    Capture image from camera.

    This demonstrates:
    - Hardware interaction
    - Error handling
    - Optional parameters

    Args:
        camera: Camera object
        flash: Enable flash (default: False)

    Returns:
        bytes: JPEG image data

    Raises:
        CameraError: If capture fails
    """
```

### Settings Changes

When adding new settings:

1. **Add to settings.toml** with documentation:
```toml
[new_section]
# Clear explanation of what this does
# Include default value reasoning
new_setting = "default_value"
```

2. **Update settings_loader.py** if needed:
```python
@property
def new_setting(self):
    """Get new setting with clear docstring."""
    return self.get("new_section.new_setting", "default")
```

3. **Update README.md** with usage example

4. **Never read directly** from settings file in main code:
```python
# ❌ BAD
with open("settings.toml") as f:
    settings = toml.load(f)

# ✅ GOOD
settings = load_settings()
value = settings.new_setting
```

## Adding New Prompts

To add a new prompt mode:

### 1. Add to settings.toml

```toml
[prompts.MY_NEW_PROMPT]
label = "DISPLAY NAME"
prompt = """Your instruction to Claude here.
Be specific about what you want.
Multi-line is fine."""

# Add to order
[prompts]
order = "DESCRIBE,...,MY_NEW_PROMPT"
```

### 2. Test It

- Verify it loads: `python lib/settings_loader.py`
- Test with actual image
- Check response quality
- Iterate on prompt wording

### 3. Document It

Add to README.md prompt table with:
- Mode name
- Purpose
- Educational focus

## Pull Request Process

1. **Update Documentation**
   - README if adding features
   - Code comments
   - Docstrings

2. **Ensure Quality**
   - No hardcoded values
   - Error handling in place
   - Educational comments added
   - Secrets not committed

3. **Describe Changes**
   - What does this PR do?
   - Why is it needed?
   - How was it tested?
   - Any breaking changes?

4. **Link Issues**
   - Reference related issues: "Fixes #123"

5. **Be Patient**
   - Maintainers may request changes
   - This is normal and helps improve quality

## Questions?

- **General Questions**: Open a [GitHub Discussion](https://github.com/yourusername/cloudfx/discussions)
- **Bug Reports**: Open a [GitHub Issue](https://github.com/yourusername/cloudfx/issues)
- **Security Issues**: Email [security contact] (do NOT open public issue)

## Recognition

Contributors will be:
- Listed in project credits
- Mentioned in release notes
- Appreciated in the community

Thank you for helping make CloudFX better for everyone! 🎉
