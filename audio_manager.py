"""
audio_manager.py – Handles all audio: background music, coin and start sounds.
Uses pygame.mixer for reliable cross-platform audio.
"""

import os
import threading
import pygame


class AudioManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self._music_playing = False
        self._lock = threading.Lock()

        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self._initialized = True
            print("[Audio] pygame.mixer initialized.")
        except Exception as e:
            print(f"[Audio] Failed to initialize mixer: {e}")
            self._initialized = False

    # ──────────────────────────────────────────────
    # Volume
    # ──────────────────────────────────────────────

    def _get_volume(self) -> float:
        return float(self.config.get("audio", "volume", 0.8))

    def set_volume(self, value: float):
        """Set master volume 0.0–1.0 and update config."""
        value = max(0.0, min(1.0, value))
        self.config.set("audio", "volume", value)
        with self._lock:
            if self._initialized:
                pygame.mixer.music.set_volume(value)

    # ──────────────────────────────────────────────
    # Background Music
    # ──────────────────────────────────────────────

    def play_music(self):
        """Start looping background music."""
        if not self._initialized:
            return
        path = self.config.get("audio", "background_music", "")
        if not path or not os.path.exists(path):
            return
        with self._lock:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._get_volume())
                pygame.mixer.music.play(loops=-1)
                self._music_playing = True
                print(f"[Audio] Music playing: {path}")
            except Exception as e:
                print(f"[Audio] Music error: {e}")

    def stop_music(self):
        """Stop background music."""
        if not self._initialized:
            return
        with self._lock:
            try:
                pygame.mixer.music.stop()
                self._music_playing = False
            except Exception as e:
                print(f"[Audio] Stop music error: {e}")

    def pause_music(self):
        if not self._initialized:
            return
        with self._lock:
            pygame.mixer.music.pause()

    def unpause_music(self):
        if not self._initialized:
            return
        with self._lock:
            pygame.mixer.music.unpause()

    # ──────────────────────────────────────────────
    # Sound Effects
    # ──────────────────────────────────────────────

    def play_coin_sound(self):
        self._play_sfx(self.config.get("audio", "coin_sound", ""))

    def play_start_sound(self):
        self._play_sfx(self.config.get("audio", "start_sound", ""))

    def _play_sfx(self, path: str):
        if not self._initialized or not path or not os.path.exists(path):
            return
        def _do():
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self._get_volume())
                sound.play()
            except Exception as e:
                print(f"[Audio] SFX error: {e}")
        threading.Thread(target=_do, daemon=True).start()

    # ──────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────

    def shutdown(self):
        if self._initialized:
            pygame.mixer.quit()
            print("[Audio] Mixer shut down.")
