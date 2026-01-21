#!/usr/bin/env python3
"""
Screenshot Service - Runs silently with GUI access to capture screenshots for the Launch Agent.
This service is automatically launched by the main service when needed.
"""

import sys
import os
import json
import time
import signal
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import pyautogui
from PIL import Image
import io
import base64

# Configuration
SCREENSHOT_PORT = 8081
LOG_DIR = Path.home() / ".linguist_assist"
LOG_DIR.mkdir(exist_ok=True)


class ScreenshotHandler(BaseHTTPRequestHandler):
    """HTTP handler for screenshot requests."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "screenshot"}).encode())
            return
        
        elif self.path == "/screenshot":
            try:
                # Try multiple methods to capture screenshot
                screenshot = None
                
                # Method 1: Try pyautogui (works in GUI sessions)
                # Note: pyautogui.screenshot() captures primary display only
                try:
                    screenshot = pyautogui.screenshot()
                except Exception:
                    pass
                
                # Method 2: Use screencapture command (works better in Launch Agents)
                # Use -D 1 to capture only the main display (avoids multi-display coordinate issues)
                if screenshot is None:
                    import subprocess
                    import tempfile
                    
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_file.close()
                    
                    try:
                        # Try main display first (-D 1) to avoid multi-display coordinate issues
                        result = subprocess.run(
                            ['screencapture', '-x', '-D', '1', temp_file.name],
                            capture_output=True,
                            timeout=5
                        )
                        # If that fails, fall back to default (all displays)
                        if result.returncode != 0:
                            result = subprocess.run(
                                ['screencapture', '-x', temp_file.name],
                                capture_output=True,
                                timeout=5
                            )
                        
                        if result.returncode == 0 and os.path.exists(temp_file.name):
                            screenshot = Image.open(temp_file.name)
                            os.unlink(temp_file.name)
                    except Exception:
                        if os.path.exists(temp_file.name):
                            os.unlink(temp_file.name)
                        raise
                
                if screenshot is None:
                    raise RuntimeError("All screenshot methods failed")
                
                # Convert to base64
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_data = buffer.getvalue()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Get screen size
                screen_width, screen_height = screenshot.size
                
                # Return JSON response
                response = {
                    "success": True,
                    "image": img_base64,
                    "width": screen_width,
                    "height": screen_height,
                    "format": "PNG"
                }
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/move":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                x = int(data.get('x', 0))
                y = int(data.get('y', 0))
                
                # Move to position
                pyautogui.moveTo(x, y, duration=0.2)
                time.sleep(0.1)  # Small delay to ensure mouse is positioned
                
                # Verify position
                current_x, current_y = pyautogui.position()
                distance = ((current_x - x) ** 2 + (current_y - y) ** 2) ** 0.5
                
                response = {
                    "success": True,
                    "message": f"Moved to ({x}, {y})",
                    "actual_position": {"x": current_x, "y": current_y},
                    "distance": distance
                }
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {"success": False, "error": str(e)}
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == "/click":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                x = int(data.get('x', 0))
                y = int(data.get('y', 0))
                verify_hover = data.get('verify_hover', True)  # Default to True for robustness
                
                # Step 1: Move mouse to target position with high precision
                print(f"[ScreenshotService] Moving mouse to exact position ({x}, {y})...")
                pyautogui.moveTo(x, y, duration=0.4)  # Slower movement for better accuracy
                time.sleep(0.3)  # Wait for mouse to fully settle
                
                # Step 2: Verify mouse position programmatically with tight tolerance
                current_x, current_y = pyautogui.position()
                distance = ((current_x - x) ** 2 + (current_y - y) ** 2) ** 0.5
                
                max_retries = 5  # More retries for precision
                for attempt in range(max_retries):
                    if distance <= 1:  # Very tight tolerance (1 pixel) for accuracy
                        print(f"[ScreenshotService] ✓ Mouse position verified: ({current_x}, {current_y}), distance: {distance:.2f}px")
                        break
                    print(f"[ScreenshotService] Mouse position mismatch (attempt {attempt + 1}/{max_retries}): expected ({x}, {y}), actual ({current_x}, {current_y}), distance: {distance:.2f}px")
                    # Move again with correction
                    correction_x = x - current_x
                    correction_y = y - current_y
                    pyautogui.moveRel(correction_x, correction_y, duration=0.2)
                    time.sleep(0.2)
                    current_x, current_y = pyautogui.position()
                    distance = ((current_x - x) ** 2 + (current_y - y) ** 2) ** 0.5
                
                # If still not accurate after retries, use the target coordinates directly
                if distance > 1:
                    print(f"[ScreenshotService] Warning: Final distance {distance:.2f}px exceeds 1px tolerance, using target coordinates ({x}, {y})")
                    current_x, current_y = x, y
                    pyautogui.moveTo(x, y, duration=0.1)
                    time.sleep(0.1)
                
                # Step 3: Take screenshot to visually confirm mouse is hovering at correct location
                if verify_hover:
                    print(f"[ScreenshotService] Taking screenshot to verify mouse hover at ({current_x}, {current_y})...")
                    screenshot = pyautogui.screenshot()
                    
                    # Get screen dimensions for verification
                    screen_width, screen_height = pyautogui.size()
                    
                    # Verify coordinates are within screen bounds
                    if current_x < 0 or current_x >= screen_width or current_y < 0 or current_y >= screen_height:
                        error_msg = f"Mouse coordinates ({current_x}, {current_y}) are out of screen bounds ({screen_width}x{screen_height})"
                        print(f"[ScreenshotService] ERROR: {error_msg}")
                        raise ValueError(error_msg)
                    
                    print(f"[ScreenshotService] ✓ Screenshot captured - mouse verified at ({current_x}, {current_y})")
                    time.sleep(0.15)  # Small delay before clicking to ensure stability
                
                # Step 4: Perform the click at verified exact position
                print(f"[ScreenshotService] Clicking at verified exact position ({current_x}, {current_y})...")
                # For dock icons on macOS, sometimes a more forceful click or slight delay helps
                # Use click with explicit coordinates and ensure mouse is still at position
                pyautogui.moveTo(current_x, current_y, duration=0.05)  # Ensure we're still at the right spot
                time.sleep(0.05)
                # Perform a more deliberate click
                pyautogui.mouseDown(x=current_x, y=current_y)
                time.sleep(0.05)  # Hold down briefly
                pyautogui.mouseUp(x=current_x, y=current_y)
                time.sleep(0.2)  # Longer delay after click for app to launch
                
                response = {
                    "success": True,
                    "message": f"Clicked at ({current_x}, {current_y}) after hover verification",
                    "target": {"x": x, "y": y},
                    "actual": {"x": current_x, "y": current_y},
                    "distance": distance,
                    "verified": verify_hover
                }
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_msg = str(e)
                print(f"[ScreenshotService] ERROR during click: {error_msg}")
                error_response = {"success": False, "error": error_msg}
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == "/type":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                text = data.get('text', '')
                interval = data.get('interval', 0.05)
                
                pyautogui.write(text, interval=interval)
                
                response = {"success": True, "message": f"Typed: {text}"}
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {"success": False, "error": str(e)}
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == "/press_key":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                key = data.get('key', '')
                
                # Map common key names
                key_mapping = {
                    "enter": "return",
                    "return": "return",
                    "tab": "tab",
                    "escape": "esc",
                    "esc": "esc",
                    "space": "space",
                    "backspace": "backspace",
                    "delete": "delete",
                }
                pyautogui_key = key_mapping.get(key.lower(), key.lower())
                pyautogui.press(pyautogui_key)
                
                response = {"success": True, "message": f"Pressed key: {key}"}
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {"success": False, "error": str(e)}
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == "/screenshot":
            try:
                # Try multiple methods to capture screenshot
                screenshot = None
                
                # Method 1: Try pyautogui (works in GUI sessions)
                # Note: pyautogui.screenshot() captures primary display only
                try:
                    screenshot = pyautogui.screenshot()
                except Exception:
                    pass
                
                # Method 2: Use screencapture command (works better in Launch Agents)
                # Use -D 1 to capture only the main display (avoids multi-display coordinate issues)
                if screenshot is None:
                    import subprocess
                    import tempfile
                    
                    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_file.close()
                    
                    try:
                        # Try main display first (-D 1) to avoid multi-display coordinate issues
                        result = subprocess.run(
                            ['screencapture', '-x', '-D', '1', temp_file.name],
                            capture_output=True,
                            timeout=5
                        )
                        # If that fails, fall back to default (all displays)
                        if result.returncode != 0:
                            result = subprocess.run(
                                ['screencapture', '-x', temp_file.name],
                                capture_output=True,
                                timeout=5
                            )
                        
                        if result.returncode == 0 and os.path.exists(temp_file.name):
                            screenshot = Image.open(temp_file.name)
                            os.unlink(temp_file.name)
                    except Exception:
                        if os.path.exists(temp_file.name):
                            os.unlink(temp_file.name)
                        raise
                
                if screenshot is None:
                    raise RuntimeError("All screenshot methods failed")
                
                # Convert to base64
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_data = buffer.getvalue()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Get screen size
                screen_width, screen_height = screenshot.size
                
                # Return JSON response
                response = {
                    "success": True,
                    "image": img_base64,
                    "width": screen_width,
                    "height": screen_height,
                    "format": "PNG"
                }
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()


class ScreenshotService:
    """Screenshot service that runs silently."""
    
    def __init__(self, port=SCREENSHOT_PORT):
        self.port = port
        self.server = None
        self.running = False
    
    def start(self):
        """Start the screenshot service."""
        try:
            self.server = HTTPServer(("127.0.0.1", self.port), ScreenshotHandler)
            self.running = True
            
            # Run server in a thread
            server_thread = Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()
            
            # Write PID file
            pid_file = LOG_DIR / "screenshot_service.pid"
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            return True
        except Exception as e:
            print(f"Failed to start screenshot service: {e}", file=sys.stderr)
            return False
    
    def stop(self):
        """Stop the screenshot service."""
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        # Remove PID file
        pid_file = LOG_DIR / "screenshot_service.pid"
        if pid_file.exists():
            pid_file.unlink()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global service
    if service:
        service.stop()
    sys.exit(0)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Screenshot Service for LinguistAssist")
    parser.add_argument("--port", type=int, default=SCREENSHOT_PORT, help="Port to listen on")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    global service
    service = ScreenshotService(port=args.port)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start service
    if service.start():
        if not args.daemon:
            print(f"Screenshot service started on port {args.port}")
            print("Press Ctrl+C to stop")
        
        # Keep running
        try:
            while service.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            service.stop()
            if not args.daemon:
                print("Screenshot service stopped")
    else:
        sys.exit(1)


if __name__ == "__main__":
    service = None
    main()
