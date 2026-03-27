"""
game_launcher.py – Handles game process launching, timing, and termination.
"""

import subprocess
import threading
import time
import os
import sys
import ctypes
from ctypes import wintypes

# Windows Constants
SW_MINIMIZE = 6
SW_RESTORE = 9


class GameLauncher:
    def __init__(self, config_manager, on_game_ended_callback):
        """
        :param config_manager: ConfigManager instance
        :param on_game_ended_callback: Called when the game session ends
        """
        self.config = config_manager
        self.on_game_ended = on_game_ended_callback

        self._process: subprocess.Popen | None = None
        self._timer_thread: threading.Thread | None = None
        self._watchdog_thread: threading.Thread | None = None
        self.running = False
        self.time_remaining = 0
        self._game_window_handle = None

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def launch(self) -> bool:
        """Launch or focus the configured game. Returns True if successful."""
        game_path = self.config.get("game", "path", "")
        duration_minutes = int(self.config.get("game", "duration", 10))
        duration = duration_minutes * 60  # Convert minutes to seconds
        mode = self.config.get("game", "mode", "kill") # "kill" or "minimize"

        if self.running:
            print("[Launcher] Session already active.")
            return False

        if not game_path or not os.path.exists(game_path):
            print(f"[Launcher] Game path invalid: {game_path!r}")
            return False

        exe_name = os.path.basename(game_path)

        if mode == "minimize":
            # Try to find existing window first
            self._game_window_handle = self._find_window_by_exe(exe_name)
            if self._game_window_handle:
                print(f"[Launcher] Found existing window for {exe_name}, restoring...")
                self._focus_window(self._game_window_handle)
                self.running = True
                self.time_remaining = duration
                self._start_timer(duration)
                self._start_background_watchdog()
                return True
            else:
                print(f"[Launcher] Game not running, launching new instance for minimize mode...")

        # Managed / Kill mode OR Minimize mode (if not running)
        try:
            self._process = subprocess.Popen(
                [game_path],
                cwd=os.path.dirname(game_path),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            self.running = True
            self.time_remaining = duration
            print(f"[Launcher] Game started: PID={self._process.pid}")
            self._start_timer(duration)
            
            if mode == "kill":
                self._start_watchdog()
            else:
                # For minimize mode, we need to find the window after a short delay
                threading.Timer(2.0, self._find_and_track_window, args=[exe_name]).start()
                
            return True
        except Exception as e:
            print(f"[Launcher] Launch failed: {e}")
            return False

    def terminate(self):
        """Terminate or minimize the game."""
        mode = self.config.get("game", "mode", "kill")
        
        if mode == "kill":
            if self._process:
                force_kill = self.config.get("game", "force_kill", True)
                try:
                    if force_kill and sys.platform == "win32":
                        os.system(f"taskkill /F /T /PID {self._process.pid}")
                    else:
                        self._process.terminate()
                    print(f"[Launcher] Game terminated (PID={self._process.pid}).")
                except Exception as e:
                    print(f"[Launcher] Error terminating: {e}")
                finally:
                    self._process = None
            else:
                # Fallback: try to kill by exe name if process object is lost
                game_path = self.config.get("game", "path", "")
                if game_path:
                    exe_name = os.path.basename(game_path)
                    print(f"[Launcher] Process object lost, attempting taskkill by name: {exe_name}")
                    os.system(f"taskkill /F /IM {exe_name} /T")
        else:
            # "minimize" mode
            handle = self._game_window_handle or self._find_window_by_exe(os.path.basename(self.config.get("game", "path", "")))
            if handle:
                self._minimize_window(handle)
                print("[Launcher] Game minimized.")
            else:
                print("[Launcher] Could not find window to minimize.")
            self._game_window_handle = None

        self.running = False

    def _find_and_track_window(self, exe_name):
        """Delayed search for window in minimize mode."""
        self._game_window_handle = self._find_window_by_exe(exe_name)
        if self._game_window_handle:
            print(f"[Launcher] Window handle found: {self._game_window_handle}")
            self._start_background_watchdog()
        else:
            print(f"[Launcher] Warning: Could not find window handle for {exe_name} after launch.")

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    def _start_timer(self, duration: int):
        def _countdown():
            for remaining in range(duration, 0, -1):
                self.time_remaining = remaining
                if not self.running:
                    return
                time.sleep(1)
            # Timer expired → end session
            self._end_session(reason="timer")

        self._timer_thread = threading.Thread(target=_countdown, daemon=True, name="GameTimer")
        self._timer_thread.start()

    def _start_watchdog(self):
        def _watch():
            while self.running and self._process:
                ret = self._process.poll()
                if ret is not None:
                    print(f"[Launcher] Game exited early (code={ret}).")
                    self._end_session(reason="exited")
                    return
                time.sleep(1)

        self._watchdog_thread = threading.Thread(target=_watch, daemon=True, name="GameWatchdog")
        self._watchdog_thread.start()

    def _end_session(self, reason: str = "unknown"):
        if not self.running:
            return

        # If timer expired, we DON'T kill immediately to allow "Continue?" screen
        # logic in main.py to show the game while asking for a coin.
        if reason != "timer":
            self.terminate()
        else:
            self.running = False # Stop the timer/watchdogs internally

        print(f"[Launcher] Session ended ({reason}).")
        if self.on_game_ended:
            self.on_game_ended()

    # ──────────────────────────────────────────────
    # Windows Helpers (ctypes)
    # ──────────────────────────────────────────────

    def _find_window_by_exe(self, exe_name: str):
        """Find the main window handle for a process name."""
        if sys.platform != "win32": return None
        
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # We'll use a simple approach: iterate visible windows and check process name
        # Note: This is a simplified version. For production we might need psutil.
        # But we can try to find window by title if exe_name is specific enough.
        # Let's try to match window title to exe_name first (without extension)
        title_to_find = os.path.splitext(exe_name)[0].lower()
        
        found_hwnds = []
        def enum_handler(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if title_to_find in buff.value.lower():
                    found_hwnds.append(hwnd)
            return True

        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(enum_proc(enum_handler), 0)
        
        return found_hwnds[0] if found_hwnds else None

    def _focus_window(self, hwnd):
        if sys.platform != "win32": return
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)

    def _minimize_window(self, hwnd):
        if sys.platform != "win32": return
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, SW_MINIMIZE)

    def _start_background_watchdog(self):
        def _watch():
            user32 = ctypes.windll.user32
            while self.running and self._game_window_handle:
                if not user32.IsWindow(self._game_window_handle):
                    print("[Launcher] Background window lost.")
                    self._end_session(reason="window_lost")
                    return
                time.sleep(1)
        threading.Thread(target=_watch, daemon=True).start()
