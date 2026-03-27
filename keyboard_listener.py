"""
keyboard_listener.py – Background thread for the PS/2 (keyboard) coin acceptor.
"""

import threading
import time
from pynput import keyboard


class KeyboardListener:
    def __init__(self, config_manager, on_coin_callback):
        """
        :param config_manager: ConfigManager instance
        :param on_coin_callback: Callable, called on the main thread when a valid key is pressed
        """
        self.config = config_manager
        self.on_coin = on_coin_callback

        self._thread: threading.Thread | None = None
        self._running = False
        self._last_coin_time = 0.0
        self._listener = None

    def start(self):
        """Start the listener."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_listener, daemon=True, name="KeyboardListener")
        self._thread.start()
        print("[Keyboard] Listener thread started.")

    def stop(self):
        """Stop the listener."""
        self._running = False
        if self._listener:
            self._listener.stop()
        print("[Keyboard] Listener stopped.")

    def _run_listener(self):
        with keyboard.Listener(on_press=self._on_press) as listener:
            self._listener = listener
            while self._running:
                # Check if enabled
                if self.config.get("input", "ps2_enabled") is False:
                    time.sleep(1)
                    continue
                
                # Check if listener is still running, if not restart
                if not listener.running:
                    break
                
                time.sleep(0.1)

    def _on_press(self, key):
        if not self._running or self.config.get("input", "ps2_enabled") is False:
            return

        target_key_str = self.config.get("input", "ps2_key", "space").lower()
        debounce = float(self.config.get("input", "ps2_debounce", 0.7))

        # Check if the pressed key matches
        try:
            # Handle special keys (space, enter, etc.)
            if hasattr(key, 'name'):
                key_name = key.name
            elif hasattr(key, 'char'):
                key_name = key.char
            else:
                key_name = str(key)
            
            if key_name and key_name.lower() == target_key_str:
                now = time.time()
                if now - self._last_coin_time >= debounce:
                    self._last_coin_time = now
                    print(f"[Keyboard] Key '{key_name}' detected as coin input!")
                    self.on_coin()
        except AttributeError:
            pass
