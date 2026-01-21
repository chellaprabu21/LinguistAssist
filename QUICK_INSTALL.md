# Quick Install Guide for macOS

## Option 1: Using the Installer Package (Recommended)

### Build the Installer
```bash
./build_installer.sh
```

### Install
Double-click `build/LinguistAssist-Installer.pkg` and follow the wizard.

## Option 2: Manual Installation

### Quick Install Script
```bash
./install_service.sh
```

### Manual Steps
1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Set up API key:
   ```bash
   echo "GEMINI_API_KEY=your_key_here" > .env
   ```

3. Install Launch Agent:
   ```bash
   ./install_service.sh
   ```

## Post-Installation

1. **Configure API Key:**
   - Edit `.env` file (or `/Applications/LinguistAssist/.env` if using installer)
   - Add your Gemini API key from https://makersuite.google.com/app/apikey

2. **Grant Permissions:**
   - System Settings > Privacy & Security > Screen Recording
   - Enable for Terminal/Python

3. **Start Service:**
   ```bash
   launchctl start com.jumpcloud.linguistassist
   ```

4. **Test:**
   ```bash
   python3 submit_task.py "Test task"
   ```

For detailed information, see [INSTALLER_GUIDE.md](INSTALLER_GUIDE.md) or [README.md](README.md).
