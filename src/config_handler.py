"""
Configuration Handler
Manages loading and saving of user configuration.
"""
import os
import json
import base64

# Config file path in user's AppData
CONFIG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'HearingAutomation')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def load_config() -> dict:
    """Load config from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"accounts": {}, "last_username": "", "last_store": "", "last_folder": ""}

def save_config(config: dict):
    """Save config to file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] Error saving config: {e}")

def encode_password(password: str) -> str:
    """Encode password with Base64."""
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')

def decode_password(encoded: str) -> str:
    """Decode Base64 encoded password."""
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
    except:
        return ""
