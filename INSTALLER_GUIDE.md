# LinguistAssist macOS Installer Guide

This guide explains how to create and use a macOS installer package (.pkg) for LinguistAssist.

## Prerequisites

To build the installer, you need:
- macOS (10.14 or later)
- Xcode Command Line Tools installed
  ```bash
  xcode-select --install
  ```

## Building the Installer

1. **Make the build script executable:**
   ```bash
   chmod +x build_installer.sh
   ```

2. **Run the build script:**
   ```bash
   ./build_installer.sh
   ```

3. **The installer will be created at:**
   ```
   build/LinguistAssist-Installer.pkg
   ```

## What the Installer Does

The installer package:

1. **Installs files** to `/Applications/LinguistAssist/`
2. **Installs Python dependencies** using pip
3. **Configures Launch Agent** plist files with correct paths
4. **Creates necessary directories** (`~/.linguist_assist/`, etc.)
5. **Creates a `.env` template** file for API key configuration
6. **Sets proper permissions** on all files

## Installing from the Package

### Option 1: Double-click Installation
1. Double-click `LinguistAssist-Installer.pkg`
2. Follow the installer wizard
3. Complete the post-installation steps (see below)

### Option 2: Command Line Installation
```bash
sudo installer -pkg build/LinguistAssist-Installer.pkg -target /
```

## Post-Installation Steps

After installation, you need to:

### 1. Configure API Key
Edit `/Applications/LinguistAssist/.env` and add your Gemini API key:
```bash
nano /Applications/LinguistAssist/.env
```

Get your API key from: https://makersuite.google.com/app/apikey

### 2. Grant Screen Recording Permissions
1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security** > **Screen Recording**
3. Enable permissions for:
   - **Terminal** (if running from command line)
   - **Python** (if running Python directly)

### 3. Start the Service
```bash
launchctl start com.jumpcloud.linguistassist
```

### 4. Verify Installation
```bash
# Check service status
launchctl list | grep linguistassist

# View logs
tail -f ~/.linguist_assist/service.log

# Submit a test task
python3 /Applications/LinguistAssist/submit_task.py "Test task"
```

## Creating a Signed Installer (Optional)

To create a signed installer that won't show security warnings:

1. **Get a Developer ID Installer certificate** from Apple Developer Program

2. **Sign the installer:**
   ```bash
   productbuild --sign "Developer ID Installer: Your Name" \
     --distribution installer/distribution.xml \
     --package-path build/pkg \
     --resources build/pkg \
     LinguistAssist-Installer-Signed.pkg
   ```

3. **Notarize the installer** (for distribution outside App Store):
   ```bash
   xcrun notarytool submit LinguistAssist-Installer-Signed.pkg \
     --apple-id your@email.com \
     --team-id YOUR_TEAM_ID \
     --password YOUR_APP_SPECIFIC_PASSWORD \
     --wait
   ```

## Creating a DMG (Optional)

To create a disk image (.dmg) containing the installer:

```bash
# Create DMG
hdiutil create -volname "LinguistAssist Installer" \
  -srcfolder build/LinguistAssist-Installer.pkg \
  -ov -format UDZO \
  LinguistAssist-Installer.dmg
```

## Uninstallation

To uninstall LinguistAssist:

1. **Stop the service:**
   ```bash
   launchctl stop com.jumpcloud.linguistassist
   launchctl unload ~/Library/LaunchAgents/com.jumpcloud.linguistassist.plist
   ```

2. **Remove files:**
   ```bash
   rm -rf /Applications/LinguistAssist
   rm ~/Library/LaunchAgents/com.jumpcloud.linguistassist.plist
   ```

3. **Remove data (optional):**
   ```bash
   rm -rf ~/.linguist_assist
   ```

## Troubleshooting

### Installer fails to build
- Ensure Xcode Command Line Tools are installed: `xcode-select --install`
- Check that all required files exist in the project directory

### Service won't start
- Check logs: `tail -f ~/.linguist_assist/service.log`
- Verify Python path in plist file
- Ensure API key is configured in `.env` file

### Permission errors
- Ensure Screen Recording permissions are granted
- Check that files have correct permissions: `ls -la /Applications/LinguistAssist`

### Python dependencies fail to install
- Try installing manually: `pip3 install -r /Applications/LinguistAssist/requirements.txt`
- Check Python version: `python3 --version` (requires 3.7+)

## File Structure

After installation:
```
/Applications/LinguistAssist/
├── *.py              # Python scripts
├── *.sh              # Shell scripts
├── *.plist           # Launch Agent configurations
├── requirements.txt  # Python dependencies
├── .env              # API key configuration (created by installer)
└── README.md         # Documentation

~/Library/LaunchAgents/
└── com.jumpcloud.linguistassist.plist  # Launch Agent

~/.linguist_assist/
├── service.log       # Service logs
├── queue/            # Task queue
├── processing/       # Tasks being processed
└── completed/        # Completed tasks
```

## Advanced: Custom Installation Path

To install to a different location, modify `build_installer.sh`:
- Change `INSTALL_DIR` variable
- Update `component.plist` bundle path
- Update postinstall script paths

## Support

For issues or questions:
- Check the main README.md
- Review logs in `~/.linguist_assist/`
- Check service status: `launchctl list | grep linguistassist`
