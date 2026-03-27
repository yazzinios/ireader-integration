"""
config_manager.py – Handles loading and saving the kiosk configuration.
"""

import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "kiosk_config.json")

DEFAULT_CONFIG = {
    "admin": {
        "password": "1234"
    },
    "game": {
        "path": "",
        "duration": 60,
        "allow_multiple_credits": False,
        "mode": "kill",
        "force_kill": True
    },
    "input": {
        "serial_enabled": True,
        "com_port": "COM1",
        "baudrate": 9600,
        "signal_byte": "C",
        "serial_debounce": 0.7,
        "ps2_enabled": False,
        "ps2_key": "space",
        "ps2_debounce": 0.7
    },
    "display": {
        "background_image": "",
        "video_intro": "",
        "attract_video": "",
        "neon_enabled": True,
        "font_size": 48,
        "text_color": "#39ff14"
    },
    "audio": {
        "coin_sound": "",
        "start_sound": "",
        "background_music": "",
        "volume": 0.8
    },
    "ads": {
        "ads_folder": "ads/",
        "duration_per_ad": 5,
        "mode": "sequential"
    },
    "system": {
        "watchdog": True,
        "auto_restart": True,
        "fullscreen_lock": True
    }
}


class ConfigManager:
    def __init__(self):
        self._config = {}
        self.load()

    def load(self):
        """Load config from file, filling in any missing keys from defaults."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._config = self._merge(DEFAULT_CONFIG, loaded)
            except (json.JSONDecodeError, IOError):
                self._config = json.loads(json.dumps(DEFAULT_CONFIG))
        else:
            self._config = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()

    def save(self):
        """Save current config to file."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except IOError as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, section: str, key: str, fallback=None):
        return self._config.get(section, {}).get(key, fallback)

    def set(self, section: str, key: str, value):
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value

    def get_section(self, section: str) -> dict:
        return dict(self._config.get(section, {}))

    def update_section(self, section: str, data: dict):
        if section not in self._config:
            self._config[section] = {}
        self._config[section].update(data)

    @staticmethod
    def _merge(defaults: dict, overrides: dict) -> dict:
        result = json.loads(json.dumps(defaults))
        for k, v in overrides.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = ConfigManager._merge(result[k], v)
            else:
                result[k] = v
        return result
