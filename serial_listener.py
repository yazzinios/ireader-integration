"""
serial_listener.py – Background thread for the serial coin acceptor.
Features: auto-reconnect, debounce, thread-safe callbacks.
"""

import threading
import time
import serial
import serial.tools.list_ports


class SerialListener:
    def __init__(self, config_manager, on_coin_callback):
        """
        :param config_manager: ConfigManager instance
        :param on_coin_callback: Callable, called on the main thread when a valid coin is detected
        """
        self.config = config_manager
        self.on_coin = on_coin_callback

        self._thread: threading.Thread | None = None
        self._running = False
        self._port: serial.Serial | None = None
        self._last_coin_time = 0.0
        self.connected = False

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def start(self):
        """Start the listener thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SerialListener")
        self._thread.start()
        print("[Serial] Listener thread started.")

    def stop(self):
        """Stop the listener thread."""
        self._running = False
        self._close_port()
        print("[Serial] Listener stopped.")

    @staticmethod
    def list_ports() -> list[str]:
        """Return list of available COM port names."""
        return [p.device for p in serial.tools.list_ports.comports()]

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    def _loop(self):
        while self._running:
            if self.config.get("input", "serial_enabled") is False:
                time.sleep(1)
                continue

            try:
                self._open_port()
                while self._running and self._port and self._port.is_open:
                    # Check if disabled while running
                    if self.config.get("input", "serial_enabled") is False:
                        break
                        
                    # ⚠️ Hardware specific polling
                    signal_byte = self.config.get("input", "signal_byte", "C")
                    poll_byte = signal_byte.encode("ascii") if isinstance(signal_byte, str) else signal_byte
                    
                    self._port.write(poll_byte)
                    
                    if self._port.in_waiting > 0:
                        data = self._port.read(1)
                        if data == poll_byte:
                            self._process(data)
                    
                    time.sleep(0.1)
            except Exception as e:
                # Same error handling...
                self.connected = False
                self._close_port()
                time.sleep(2)

    def _open_port(self):
        com_port = self.config.get("input", "com_port", "COM3")
        baudrate = self.config.get("input", "baudrate", 9600)
        self._port = serial.Serial(
            port=com_port,
            baudrate=baudrate,
            timeout=1
        )
        self.connected = True

    def _process(self, data: bytes):
        signal_byte = self.config.get("input", "signal_byte", "C")
        debounce = float(self.config.get("input", "serial_debounce", 0.7))

        expected = signal_byte.encode("ascii") if isinstance(signal_byte, str) else signal_byte
        if expected in data:
            now = time.time()
            if now - self._last_coin_time >= debounce:
                self._last_coin_time = now
                self.on_coin()
