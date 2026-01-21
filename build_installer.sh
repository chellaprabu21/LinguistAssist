#!/bin/bash
# Build script to create a macOS installer package (.pkg) for LinguistAssist

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER_DIR="$SCRIPT_DIR/installer"
BUILD_DIR="$SCRIPT_DIR/build"
PKG_DIR="$BUILD_DIR/pkg"
ROOT_DIR="$BUILD_DIR/root"
INSTALL_DIR="/Applications/LinguistAssist"

echo "Building LinguistAssist macOS installer..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$PKG_DIR"
mkdir -p "$ROOT_DIR$INSTALL_DIR"

# Copy installer scripts
echo "Preparing installer scripts..."
mkdir -p "$INSTALLER_DIR"
chmod +x "$INSTALLER_DIR/preinstall" 2>/dev/null || true
chmod +x "$INSTALLER_DIR/postinstall" 2>/dev/null || true

# Copy application files to root directory
echo "Copying application files..."

# Copy Python files
find "$SCRIPT_DIR" -maxdepth 1 -name "*.py" -exec cp {} "$ROOT_DIR$INSTALL_DIR/" \;

# Copy shell scripts
find "$SCRIPT_DIR" -maxdepth 1 -name "*.sh" -exec cp {} "$ROOT_DIR$INSTALL_DIR/" \;

# Copy plist files
find "$SCRIPT_DIR" -maxdepth 1 -name "*.plist" -exec cp {} "$ROOT_DIR$INSTALL_DIR/" \;

# Copy text files (requirements, etc.)
find "$SCRIPT_DIR" -maxdepth 1 -name "*.txt" -exec cp {} "$ROOT_DIR$INSTALL_DIR/" \;

# Copy markdown files
find "$SCRIPT_DIR" -maxdepth 1 -name "*.md" -exec cp {} "$ROOT_DIR$INSTALL_DIR/" \;

# Copy directories if they exist
[ -d "$SCRIPT_DIR/api" ] && cp -R "$SCRIPT_DIR/api" "$ROOT_DIR$INSTALL_DIR/"
[ -d "$SCRIPT_DIR/public" ] && cp -R "$SCRIPT_DIR/public" "$ROOT_DIR$INSTALL_DIR/"
[ -d "$SCRIPT_DIR/static" ] && cp -R "$SCRIPT_DIR/static" "$ROOT_DIR$INSTALL_DIR/"

# Remove build artifacts and unnecessary files
echo "Cleaning up unnecessary files..."
rm -rf "$ROOT_DIR$INSTALL_DIR"/build 2>/dev/null || true
rm -rf "$ROOT_DIR$INSTALL_DIR"/installer 2>/dev/null || true
rm -rf "$ROOT_DIR$INSTALL_DIR"/__pycache__ 2>/dev/null || true
rm -rf "$ROOT_DIR$INSTALL_DIR"/*.pyc 2>/dev/null || true
rm -rf "$ROOT_DIR$INSTALL_DIR"/.git 2>/dev/null || true
rm -rf "$ROOT_DIR$INSTALL_DIR"/.gitignore 2>/dev/null || true

# Make scripts executable
chmod +x "$ROOT_DIR$INSTALL_DIR"/*.sh 2>/dev/null || true
chmod +x "$ROOT_DIR$INSTALL_DIR"/*.py 2>/dev/null || true

# Set proper permissions
chmod 755 "$ROOT_DIR$INSTALL_DIR"

# Build the component package
echo "Building component package..."
pkgbuild \
    --root "$ROOT_DIR" \
    --scripts "$INSTALLER_DIR" \
    --identifier "com.jumpcloud.linguistassist" \
    --version "1.0.0" \
    --install-location "/" \
    "$PKG_DIR/LinguistAssist.pkg" || {
    echo "ERROR: pkgbuild failed. Make sure you have Xcode Command Line Tools installed."
    echo "Install with: xcode-select --install"
    exit 1
}

# Create distribution.xml
echo "Creating distribution file..."
cat > "$PKG_DIR/distribution.xml" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>LinguistAssist</title>
    <organization>com.jumpcloud</organization>
    <domains enable_localSystem="true" enable_anywhere="true" enable_currentUserHome="false"/>
    <options customize="never" require-scripts="false" rootVolumeOnly="false" hostArchitectures="x86_64,arm64"/>
    <welcome file="welcome.html" mime-type="text/html"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    <pkg-ref id="com.jumpcloud.linguistassist"/>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="default">
            <line choice="com.jumpcloud.linguistassist"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="com.jumpcloud.linguistassist" visible="false">
        <pkg-ref id="com.jumpcloud.linguistassist"/>
    </choice>
    <pkg-ref id="com.jumpcloud.linguistassist" version="1.0.0" onConclusion="none">LinguistAssist.pkg</pkg-ref>
</installer-gui-script>
EOF

# Create welcome and conclusion HTML files
echo "Creating welcome and conclusion files..."
cat > "$PKG_DIR/welcome.html" <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; }
        h1 { color: #333; }
        p { line-height: 1.6; }
    </style>
</head>
<body>
    <h1>Welcome to LinguistAssist</h1>
    <p>LinguistAssist is a GUI automation agent that uses Google's Gemini API to intelligently detect and interact with UI elements based on natural language descriptions.</p>
    <h2>Requirements</h2>
    <ul>
        <li>macOS 10.14 or later</li>
        <li>Python 3.7 or later</li>
        <li>Google Gemini API key</li>
        <li>Screen Recording permissions</li>
    </ul>
    <h2>What will be installed</h2>
    <ul>
        <li>LinguistAssist application files</li>
        <li>Python dependencies</li>
        <li>macOS Launch Agent service</li>
    </ul>
</body>
</html>
EOF

cat > "$PKG_DIR/conclusion.html" <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; }
        h1 { color: #333; }
        p { line-height: 1.6; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Installation Complete!</h1>
    <p>LinguistAssist has been successfully installed.</p>
    <h2>Next Steps</h2>
    <ol>
        <li><strong>Configure your API key:</strong><br>
            Edit <code>/Applications/LinguistAssist/.env</code> and add your Gemini API key.<br>
            Get your key from: <a href="https://makersuite.google.com/app/apikey">Google AI Studio</a>
        </li>
        <li><strong>Grant Screen Recording permissions:</strong><br>
            Go to System Settings > Privacy & Security > Screen Recording<br>
            Enable permissions for Terminal (or Python)
        </li>
        <li><strong>Start the service:</strong><br>
            <code>launchctl start com.jumpcloud.linguistassist</code>
        </li>
        <li><strong>Submit a task:</strong><br>
            <code>python3 /Applications/LinguistAssist/submit_task.py 'Your goal here'</code>
        </li>
    </ol>
    <p>For more information, see the README.md file in the installation directory.</p>
</body>
</html>
EOF

# Build the final installer package
echo "Building final installer package..."
productbuild \
    --distribution "$PKG_DIR/distribution.xml" \
    --package-path "$PKG_DIR" \
    --resources "$PKG_DIR" \
    "$BUILD_DIR/LinguistAssist-Installer.pkg" || {
    echo "ERROR: productbuild failed. Make sure you have Xcode Command Line Tools installed."
    echo "Install with: xcode-select --install"
    exit 1
}

echo ""
echo "✓ Installer package created successfully!"
echo ""
echo "Installer location: $BUILD_DIR/LinguistAssist-Installer.pkg"
echo ""
echo "To install:"
echo "  open $BUILD_DIR/LinguistAssist-Installer.pkg"
echo ""
echo "To create a signed installer (requires Developer ID):"
echo "  productbuild --sign 'Developer ID Installer: Your Name' \\"
echo "    --distribution $PKG_DIR/distribution.xml \\"
echo "    --package-path $PKG_DIR \\"
echo "    --resources $PKG_DIR \\"
echo "    LinguistAssist-Installer-Signed.pkg"
