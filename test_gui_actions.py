#!/usr/bin/env python3
"""Test GUI actions to verify they work."""

import requests
import time

print("=== Testing GUI Actions ===")
print()

# Test click
print("1. Testing click at (500, 500)...")
print("   Watch your screen - you should see a click!")
time.sleep(2)

try:
    response = requests.post(
        "http://127.0.0.1:8081/click",
        json={"x": 500, "y": 500},
        timeout=2
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result.get('message')}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

time.sleep(1)

# Test typing
print("\n2. Testing typing...")
print("   Make sure a text field is focused!")
time.sleep(2)

try:
    response = requests.post(
        "http://127.0.0.1:8081/type",
        json={"text": "Hello from LinguistAssist!", "interval": 0.1},
        timeout=5
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result.get('message')}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

time.sleep(1)

# Test key press
print("\n3. Testing key press (Enter)...")
time.sleep(1)

try:
    response = requests.post(
        "http://127.0.0.1:8081/press_key",
        json={"key": "enter"},
        timeout=2
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ {result.get('message')}")
    else:
        print(f"   ✗ Error: {response.status_code}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

print("\n=== Test Complete ===")
print("If you saw clicks/typing happen, the GUI service is working!")
print("If not, check screen recording permissions for Python.app")
