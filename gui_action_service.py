#!/usr/bin/env python3
"""
GUI Action Service - Provides GUI actions (click, type, press_key) via HTTP API.
This service runs with GUI access and executes actions on behalf of the Launch Agent.
"""

import pyautogui
import requests

def click_via_service(x: int, y: int) -> bool:
    """Click at coordinates via screenshot service."""
    try:
        response = requests.post(
            "http://127.0.0.1:8081/click",
            json={"x": x, "y": y},
            timeout=2
        )
        return response.status_code == 200 and response.json().get("success", False)
    except Exception:
        return False

def type_via_service(text: str, interval: float = 0.05) -> bool:
    """Type text via screenshot service."""
    try:
        response = requests.post(
            "http://127.0.0.1:8081/type",
            json={"text": text, "interval": interval},
            timeout=5
        )
        return response.status_code == 200 and response.json().get("success", False)
    except Exception:
        return False

def press_key_via_service(key: str) -> bool:
    """Press a key via screenshot service."""
    try:
        response = requests.post(
            "http://127.0.0.1:8081/press_key",
            json={"key": key},
            timeout=2
        )
        return response.status_code == 200 and response.json().get("success", False)
    except Exception:
        return False
