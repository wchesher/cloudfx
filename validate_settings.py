#!/usr/bin/env python3
"""
CloudFX Settings Validator
Version 1.0

This script validates that:
1. settings.toml is properly formatted and complete
2. secrets.toml exists and has required fields
3. No hardcoded values exist in code.py
4. All prompts are properly configured

Run this before deploying to your device!

Usage:
    python validate_settings.py

Author: CloudFX Project
License: MIT
"""

import sys
import os
import re
from pathlib import Path


# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text):
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_info(text):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")


class Validator:
    """Main validator class."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.root = Path(__file__).parent

    def validate_all(self):
        """Run all validation checks."""
        print_header("CloudFX Settings Validation")

        self.check_file_structure()
        self.check_settings_toml()
        self.check_secrets_example()
        self.check_secrets_toml()
        self.check_code_hardcoded_values()
        self.check_gitignore()

        self.print_summary()

        return len(self.errors) == 0

    def check_file_structure(self):
        """Verify required files exist."""
        print_info("Checking file structure...")

        required_files = [
            "settings.toml",
            "secrets.toml.example",
            "code.py",
            "lib/settings_loader.py",
            ".gitignore",
            "README.md",
            "LICENSE"
        ]

        for file_path in required_files:
            full_path = self.root / file_path
            if full_path.exists():
                print_success(f"Found: {file_path}")
            else:
                self.errors.append(f"Missing required file: {file_path}")
                print_error(f"Missing: {file_path}")

    def check_settings_toml(self):
        """Validate settings.toml structure and content."""
        print_info("\nValidating settings.toml...")

        settings_path = self.root / "settings.toml"
        if not settings_path.exists():
            self.errors.append("settings.toml not found")
            return

        try:
            import toml
            settings = toml.load(settings_path)
            print_success("settings.toml is valid TOML")

            # Check required sections
            required_sections = ["camera", "flash", "prompts", "api"]
            for section in required_sections:
                if section in settings:
                    print_success(f"Section [{section}] exists")
                else:
                    self.errors.append(f"Missing section: [{section}]")
                    print_error(f"Missing section: [{section}]")

            # Validate camera settings
            if "camera" in settings:
                resolution = settings["camera"].get("resolution")
                if resolution is not None:
                    if 0 <= resolution <= 6:
                        print_success(f"Camera resolution: {resolution} (valid)")
                    else:
                        self.errors.append(f"Camera resolution {resolution} out of range (0-6)")
                        print_error(f"Camera resolution out of range: {resolution}")
                else:
                    self.errors.append("Camera resolution not set")
                    print_error("Camera resolution not set")

            # Validate flash settings
            if "flash" in settings:
                threshold = settings["flash"].get("dark_threshold")
                if threshold is not None:
                    if 0 <= threshold <= 255:
                        print_success(f"Dark threshold: {threshold} (valid)")
                    else:
                        self.warnings.append(f"Dark threshold {threshold} may be out of range")
                        print_warning(f"Dark threshold unusual: {threshold}")

            # Validate prompts
            if "prompts" in settings:
                prompt_order = settings["prompts"].get("order", "")
                prompt_names = [p.strip() for p in prompt_order.split(',') if p.strip()]

                if prompt_names:
                    print_success(f"Found {len(prompt_names)} prompts in order")

                    # Check each prompt is defined
                    for name in prompt_names:
                        if name in settings["prompts"]:
                            prompt = settings["prompts"][name]
                            if "label" in prompt and "prompt" in prompt:
                                print_success(f"  Prompt '{name}' properly configured")
                            else:
                                self.errors.append(f"Prompt '{name}' missing label or prompt")
                                print_error(f"  Prompt '{name}' incomplete")
                        else:
                            self.errors.append(f"Prompt '{name}' referenced but not defined")
                            print_error(f"  Prompt '{name}' not found")
                else:
                    self.warnings.append("No prompts configured in order")
                    print_warning("No prompts in order")

        except Exception as e:
            self.errors.append(f"Error parsing settings.toml: {str(e)}")
            print_error(f"Parse error: {str(e)}")

    def check_secrets_example(self):
        """Validate secrets.toml.example exists and has placeholders."""
        print_info("\nValidating secrets.toml.example...")

        example_path = self.root / "secrets.toml.example"
        if not example_path.exists():
            self.errors.append("secrets.toml.example not found")
            print_error("secrets.toml.example not found")
            return

        content = example_path.read_text()

        # Check for required keys
        required_keys = [
            "CIRCUITPY_WIFI_SSID",
            "CIRCUITPY_WIFI_PASSWORD",
            "ANTHROPIC_API_KEY"
        ]

        for key in required_keys:
            if key in content:
                print_success(f"Template includes: {key}")
            else:
                self.errors.append(f"secrets.toml.example missing: {key}")
                print_error(f"Missing template key: {key}")

        # Ensure no actual secrets in example
        if "sk-ant-api03-" in content and "your-actual-api-key" not in content:
            self.warnings.append("secrets.toml.example may contain real API key")
            print_warning("Example file may have real API key!")

    def check_secrets_toml(self):
        """Check if secrets.toml exists (should for deployment, but warn if not)."""
        print_info("\nChecking secrets.toml...")

        secrets_path = self.root / "secrets.toml"
        if secrets_path.exists():
            print_success("secrets.toml exists")

            try:
                import toml
                secrets = toml.load(secrets_path)

                # Check for required keys
                required_keys = [
                    "CIRCUITPY_WIFI_SSID",
                    "CIRCUITPY_WIFI_PASSWORD",
                    "ANTHROPIC_API_KEY"
                ]

                for key in required_keys:
                    if key in secrets:
                        value = secrets[key]
                        if value and value != f"your-{key.lower().replace('_', '-')}":
                            print_success(f"{key} is set")
                        else:
                            self.warnings.append(f"{key} not filled in")
                            print_warning(f"{key} still has placeholder value")
                    else:
                        self.errors.append(f"secrets.toml missing: {key}")
                        print_error(f"Missing: {key}")

            except Exception as e:
                self.errors.append(f"Error parsing secrets.toml: {str(e)}")
                print_error(f"Parse error: {str(e)}")
        else:
            self.warnings.append("secrets.toml not found - copy from secrets.toml.example")
            print_warning("secrets.toml not found (needed for deployment)")

    def check_code_hardcoded_values(self):
        """Scan code.py for potential hardcoded values."""
        print_info("\nScanning code.py for hardcoded values...")

        code_path = self.root / "code.py"
        if not code_path.exists():
            self.warnings.append("code.py not found")
            return

        content = code_path.read_text()

        # Patterns that might indicate hardcoded values
        suspicious_patterns = [
            (r'resolution\s*=\s*\d+(?!\s*#.*settings)', "Hardcoded resolution value"),
            (r'threshold\s*=\s*\d+(?!\s*#.*settings)', "Hardcoded threshold value"),
            (r'ssid\s*=\s*["\'](?!.*settings)', "Hardcoded WiFi SSID"),
            (r'password\s*=\s*["\'](?!.*settings)', "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\']sk-', "Hardcoded API key"),
            (r'model\s*=\s*["\']claude-(?!\s*#.*settings)', "Hardcoded model name"),
        ]

        found_issues = False
        for pattern, description in suspicious_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                self.warnings.append(f"{description} at line {line_num}")
                print_warning(f"{description} at line {line_num}")
                found_issues = True

        if not found_issues:
            print_success("No obvious hardcoded values found")

        # Check that settings are actually being loaded
        if "load_settings()" in content or "Settings()" in content:
            print_success("Settings loader is being used")
        else:
            self.warnings.append("Settings loader may not be used in code.py")
            print_warning("Settings loader not detected in code.py")

    def check_gitignore(self):
        """Verify .gitignore protects secrets."""
        print_info("\nValidating .gitignore...")

        gitignore_path = self.root / ".gitignore"
        if not gitignore_path.exists():
            self.errors.append(".gitignore not found")
            print_error(".gitignore not found")
            return

        content = gitignore_path.read_text()

        # Critical: secrets.toml must be ignored
        if "secrets.toml" in content:
            print_success("secrets.toml is in .gitignore")
        else:
            self.errors.append("secrets.toml NOT in .gitignore - security risk!")
            print_error("CRITICAL: secrets.toml not in .gitignore!")

        # Check for other recommended ignores
        recommended = [
            ("__pycache__", "Python cache"),
            ("*.pyc", "Compiled Python"),
            (".vscode", "VS Code settings"),
        ]

        for pattern, description in recommended:
            if pattern in content:
                print_success(f"{description} is ignored")
            else:
                print_info(f"Consider adding: {pattern} ({description})")

    def print_summary(self):
        """Print validation summary."""
        print_header("Validation Summary")

        if self.errors:
            print(f"\n{Colors.RED}ERRORS ({len(self.errors)}):{Colors.RESET}")
            for error in self.errors:
                print(f"  {Colors.RED}✗{Colors.RESET} {error}")

        if self.warnings:
            print(f"\n{Colors.YELLOW}WARNINGS ({len(self.warnings)}):{Colors.RESET}")
            for warning in self.warnings:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} {warning}")

        print()
        if len(self.errors) == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ VALIDATION PASSED{Colors.RESET}")
            print(f"{Colors.GREEN}Your CloudFX configuration looks good!{Colors.RESET}")
            if self.warnings:
                print(f"{Colors.YELLOW}Review warnings before deployment.{Colors.RESET}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ VALIDATION FAILED{Colors.RESET}")
            print(f"{Colors.RED}Please fix errors before deploying.{Colors.RESET}")


def main():
    """Main entry point."""
    # Check for required dependencies
    try:
        import toml
    except ImportError:
        print_error("TOML library not found. Install with: pip install toml")
        print_info("Or use: pip install -r requirements.txt")
        sys.exit(1)

    validator = Validator()
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
