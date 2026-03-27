"""
admin_panel.py – Password-protected admin settings panel.
Opens as a Toplevel window over the main kiosk screen.
"""

import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox


class AdminPanel(ctk.CTkToplevel):
    def __init__(self, master, config_manager, audio_manager, serial_listener, on_close_callback=None):
        super().__init__(master)
        self.config = config_manager
        self.audio = audio_manager
        self.serial = serial_listener
        self.on_close_callback = on_close_callback

        self.title("⚙ Kiosk Admin Panel")
        self.geometry("900x650")
        self.resizable(True, True)
        self.grab_set()  # Modal
        self.focus_force()

        # Prevent accidental close without saving
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()

    # ─────────────────────────────────────────────
    # Build Layout
    # ─────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#0a0a20", corner_radius=0)
        header.pack(fill="x", pady=0)
        ctk.CTkLabel(header, text="⚙  KIOSK CONTROL CENTER",
                     font=ctk.CTkFont(family="Arial Black", size=22, weight="bold"),
                     text_color="#00f7ff").pack(pady=12)

        # Tab view
        self.tabs = ctk.CTkTabview(self, width=880, height=540)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)

        for tab in ["Game", "Input", "Display", "Audio", "Ads", "System"]:
            self.tabs.add(tab)

        self._build_game_tab()
        self._build_input_tab()
        self._build_display_tab()
        self._build_audio_tab()
        self._build_ads_tab()
        self._build_system_tab()

        # Footer buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(footer, text="💾  Save & Apply", command=self._save_and_close,
                       fg_color="#00f7ff", text_color="#000000", hover_color="#00c8d1",
                       font=ctk.CTkFont(weight="bold"), width=160).pack(side="right", padx=6)
        ctk.CTkButton(footer, text="✖  Cancel", command=self._on_close,
                      fg_color="#555555", hover_color="#cc2244",
                      font=ctk.CTkFont(weight="bold"), width=120).pack(side="right", padx=6)
        
        # Exit App Button (on the left)
        ctk.CTkButton(footer, text="🛑  Exit App", command=self._exit_app,
                      fg_color="#aa0000", hover_color="#ff1111",
                      font=ctk.CTkFont(weight="bold"), width=120).pack(side="left", padx=6)

    # ─────────────────────────────────────────────
    # Tab: Game
    # ─────────────────────────────────────────────

    def _build_game_tab(self):
        f = self.tabs.tab("Game")
        self._section_label(f, "Game Executable")

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)
        self._game_path_var = tk.StringVar(value=self.config.get("game", "path", ""))
        ctk.CTkEntry(row, textvariable=self._game_path_var, width=560,
                     placeholder_text="Path to .exe ...").pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Browse", width=90, command=self._browse_game).pack(side="left")

        self._section_label(f, "Session Duration (minutes)")
        self._game_duration_var = tk.IntVar(value=int(self.config.get("game", "duration", 10)))
        ctk.CTkSlider(f, from_=1, to=120, number_of_steps=119,
                      variable=self._game_duration_var).pack(fill="x", padx=20, pady=4)
        self._dur_label = ctk.CTkLabel(f, text="")
        self._dur_label.pack()
        self._game_duration_var.trace_add("write", lambda *_: self._update_dur_label())
        self._update_dur_label()

        self._section_label(f, "Options")
        self._force_kill_var = tk.BooleanVar(value=self.config.get("game", "force_kill", True))
        ctk.CTkCheckBox(f, text="Force kill game on session end (recommended)",
                        variable=self._force_kill_var).pack(anchor="w", padx=20, pady=4)
        self._multi_credit_var = tk.BooleanVar(value=self.config.get("game", "allow_multiple_credits", False))
        ctk.CTkCheckBox(f, text="Allow multiple credits (extend session)",
                        variable=self._multi_credit_var).pack(anchor="w", padx=20, pady=4)

        self._section_label(f, "Game Management Mode")
        self._game_mode_var = tk.StringVar(value=self.config.get("game", "mode", "kill"))
        ctk.CTkRadioButton(f, text="Kill Mode (Launch & Kill process on timeout)",
                           variable=self._game_mode_var, value="kill").pack(anchor="w", padx=20, pady=4)
        ctk.CTkRadioButton(f, text="Minimize Mode (Restore & Minimize process on timeout)",
                           variable=self._game_mode_var, value="minimize").pack(anchor="w", padx=20, pady=4)

        self._section_label(f, "Session Extension")
        self._continue_timeout_var = tk.StringVar(value=self.config.get("game", "continue_timeout", "15"))
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(row, text="Extension Window (seconds):").pack(side="left")
        ctk.CTkEntry(row, textvariable=self._continue_timeout_var, width=60).pack(side="left", padx=10)
    # Tab: Input (Serial & PS/2)
    # ─────────────────────────────────────────────
    def _build_input_tab(self):
        f = self.tabs.tab("Input")
        
        # --- Serial Section ---
        self._section_label(f, "SERIAL CONFIGURATION")
        
        ports = self.serial.list_ports() if self.serial else []
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(grid, text="COM Port:").grid(row=0, column=0, sticky="w", pady=4, padx=4)
        self._com_port_var = tk.StringVar(value=self.config.get("input", "com_port", "COM3"))
        ctk.CTkComboBox(grid, variable=self._com_port_var, values=ports if ports else ["COM1","COM2","COM3"]).grid(row=0, column=1, sticky="w", padx=8)

        ctk.CTkLabel(grid, text="Baudrate:").grid(row=1, column=0, sticky="w", pady=4, padx=4)
        self._baudrate_var = tk.StringVar(value=str(self.config.get("input", "baudrate", 9600)))
        ctk.CTkComboBox(grid, variable=self._baudrate_var, values=["9600", "19200", "38400", "57600", "115200"]).grid(row=1, column=1, sticky="w", padx=8)

        ctk.CTkLabel(grid, text="Signal Byte:").grid(row=2, column=0, sticky="w", pady=4, padx=4)
        self._signal_var = tk.StringVar(value=self.config.get("input", "signal_byte", "C"))
        ctk.CTkEntry(grid, textvariable=self._signal_var, width=80).grid(row=2, column=1, sticky="w", padx=8)

        ctk.CTkLabel(grid, text="Debounce (s):").grid(row=3, column=0, sticky="w", pady=4, padx=4)
        self._serial_debounce_var = tk.StringVar(value=str(self.config.get("input", "serial_debounce", 0.7)))
        ctk.CTkEntry(grid, textvariable=self._serial_debounce_var, width=80).grid(row=3, column=1, sticky="w", padx=8)

        self._serial_enabled_var = tk.BooleanVar(value=self.config.get("input", "serial_enabled", True))
        ctk.CTkCheckBox(f, text="Enable Serial Listener", variable=self._serial_enabled_var).pack(anchor="w", padx=20, pady=5)

        # --- PS/2 Section ---
        self._section_label(f, "PS/2 (KEYBOARD) CONFIGURATION")
        
        ps2_grid = ctk.CTkFrame(f, fg_color="transparent")
        ps2_grid.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(ps2_grid, text="Input Key:").grid(row=0, column=0, sticky="w", pady=4, padx=4)
        self._ps2_key_var = tk.StringVar(value=self.config.get("input", "ps2_key", "space"))
        ctk.CTkEntry(ps2_grid, textvariable=self._ps2_key_var, width=120, placeholder_text="space, enter, 1...").grid(row=0, column=1, sticky="w", padx=8)

        ctk.CTkLabel(ps2_grid, text="Debounce (s):").grid(row=1, column=0, sticky="w", pady=4, padx=4)
        self._ps2_debounce_var = tk.StringVar(value=str(self.config.get("input", "ps2_debounce", 0.7)))
        ctk.CTkEntry(ps2_grid, textvariable=self._ps2_debounce_var, width=80).grid(row=1, column=1, sticky="w", padx=8)

        self._ps2_enabled_var = tk.BooleanVar(value=self.config.get("input", "ps2_enabled", False))
        ctk.CTkCheckBox(f, text="Enable PS/2 (Keyboard) Listener", variable=self._ps2_enabled_var).pack(anchor="w", padx=20, pady=5)

        # Status
        status_color = "#39ff14" if (self.serial and self.serial.connected) else "#ff3355"
        status_text = "● Connected" if (self.serial and self.serial.connected) else "● Disconnected"
        ctk.CTkLabel(f, text=status_text, text_color=status_color,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20)

    # ─────────────────────────────────────────────
    # Tab: Display
    # ─────────────────────────────────────────────

    def _build_display_tab(self):
        f = self.tabs.tab("Display")
        self._section_label(f, "Background Image")
        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=4)
        self._bg_image_var = tk.StringVar(value=self.config.get("display", "background_image", ""))
        ctk.CTkEntry(row1, textvariable=self._bg_image_var, width=520, placeholder_text="Path to image...").pack(side="left", padx=(0, 8))
        ctk.CTkButton(row1, text="Browse", width=90, command=lambda: self._browse_file(
            self._bg_image_var, [("Images", "*.jpg *.jpeg *.png *.bmp *.gif")])).pack(side="left")

        self._section_label(f, "Video Intro")
        row_vid = ctk.CTkFrame(f, fg_color="transparent")
        row_vid.pack(fill="x", padx=20, pady=4)
        self._video_intro_var = tk.StringVar(value=self.config.get("display", "video_intro", ""))
        ctk.CTkEntry(row_vid, textvariable=self._video_intro_var, width=520, placeholder_text="Path to video...").pack(side="left", padx=(0, 8))
        ctk.CTkButton(row_vid, text="Browse", width=90, command=lambda: self._browse_file(
            self._video_intro_var, [("Videos", "*.mp4 *.avi *.mkv *.mov *.wmv")])).pack(side="left")

        self._section_label(f, "Text & Animation")
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(grid, text="Font Size:").grid(row=0, column=0, sticky="w", pady=6, padx=4)
        self._font_size_var = tk.IntVar(value=self.config.get("display", "font_size", 48))
        ctk.CTkSlider(grid, from_=18, to=100, number_of_steps=82,
                      variable=self._font_size_var).grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(grid, text="Neon Accent (HEX):").grid(row=1, column=0, sticky="w", pady=6, padx=4)
        self._accent_neon_var = tk.StringVar(value=self.config.get("display", "accent_neon", "#00f7ff"))
        ctk.CTkEntry(grid, textvariable=self._accent_neon_var, width=120,
                     placeholder_text="#00f7ff").grid(row=1, column=1, sticky="w", padx=8)

        ctk.CTkLabel(grid, text="Violet Accent (HEX):").grid(row=2, column=0, sticky="w", pady=6, padx=4)
        self._accent_violet_var = tk.StringVar(value=self.config.get("display", "accent_violet", "#bd00ff"))
        ctk.CTkEntry(grid, textvariable=self._accent_violet_var, width=120,
                     placeholder_text="#bd00ff").grid(row=2, column=1, sticky="w", padx=8)

        self._neon_var = tk.BooleanVar(value=self.config.get("display", "neon_enabled", True))
        ctk.CTkCheckBox(f, text="Enable neon pulse animation", variable=self._neon_var
                        ).pack(anchor="w", padx=20, pady=8)

    # ─────────────────────────────────────────────
    # Tab: Audio
    # ─────────────────────────────────────────────

    def _build_audio_tab(self):
        f = self.tabs.tab("Audio")
        audio_keys = [
            ("Coin Sound", "coin_sound"),
            ("Start Sound", "start_sound"),
            ("Background Music", "background_music"),
        ]
        self._audio_vars = {}
        for label, key in audio_keys:
            self._section_label(f, label)
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            var = tk.StringVar(value=self.config.get("audio", key, ""))
            self._audio_vars[key] = var
            ctk.CTkEntry(row, textvariable=var, width=490,
                         placeholder_text="Path to audio file...").pack(side="left", padx=(0, 8))
            ctk.CTkButton(row, text="Browse", width=90,
                          command=lambda v=var: self._browse_file(
                              v, [("Audio", "*.mp3 *.wav *.ogg")])).pack(side="left")

        self._section_label(f, "Volume")
        self._volume_var = tk.DoubleVar(value=float(self.config.get("audio", "volume", 0.8)))
        vol_slider = ctk.CTkSlider(f, from_=0.0, to=1.0, number_of_steps=20,
                                   variable=self._volume_var,
                                   command=lambda v: self.audio.set_volume(float(v)))
        vol_slider.pack(fill="x", padx=20, pady=4)

    # ─────────────────────────────────────────────
    # Tab: Ads
    # ─────────────────────────────────────────────

    def _build_ads_tab(self):
        f = self.tabs.tab("Ads")
        self._section_label(f, "Ads Folder")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)
        self._ads_folder_var = tk.StringVar(value=self.config.get("ads", "ads_folder", "ads/"))
        ctk.CTkEntry(row, textvariable=self._ads_folder_var, width=490,
                     placeholder_text="Folder containing ads...").pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Browse", width=90, command=self._browse_ads_folder).pack(side="left")

        self._section_label(f, "Rotation Settings")
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(grid, text="Duration per Ad (s):").grid(row=0, column=0, sticky="w", pady=6, padx=4)
        self._ad_duration_var = tk.IntVar(value=self.config.get("ads", "duration_per_ad", 5))
        ctk.CTkSlider(grid, from_=2, to=30, number_of_steps=28,
                      variable=self._ad_duration_var).grid(row=0, column=1, sticky="ew", padx=8)

        ctk.CTkLabel(grid, text="Mode:").grid(row=1, column=0, sticky="w", pady=6, padx=4)
        self._ad_mode_var = tk.StringVar(value=self.config.get("ads", "mode", "sequential"))
        ctk.CTkComboBox(grid, variable=self._ad_mode_var,
                        values=["sequential", "random"]).grid(row=1, column=1, sticky="w", padx=8)

    # ─────────────────────────────────────────────
    # Tab: System
    # ─────────────────────────────────────────────

    def _build_system_tab(self):
        f = self.tabs.tab("System")
        self._section_label(f, "Stability & Security")

        self._watchdog_var = tk.BooleanVar(value=self.config.get("system", "watchdog", True))
        ctk.CTkCheckBox(f, text="Enable game watchdog (auto-end if game crashes)",
                        variable=self._watchdog_var).pack(anchor="w", padx=20, pady=8)

        self._fullscreen_lock_var = tk.BooleanVar(value=self.config.get("system", "fullscreen_lock", True))
        ctk.CTkCheckBox(f, text="Enable fullscreen lock (block Alt+F4 / window escape)",
                        variable=self._fullscreen_lock_var).pack(anchor="w", padx=20, pady=8)

        self._auto_restart_var = tk.BooleanVar(value=self.config.get("system", "auto_restart", True))
        ctk.CTkCheckBox(f, text="Auto-restart kiosk on crash",
                        variable=self._auto_restart_var).pack(anchor="w", padx=20, pady=8)

        self._section_label(f, "Admin Password")
        pwd_row = ctk.CTkFrame(f, fg_color="transparent")
        pwd_row.pack(fill="x", padx=20, pady=4)
        self._password_var = tk.StringVar(value=self.config.get("admin", "password", "1234"))
        ctk.CTkEntry(pwd_row, textvariable=self._password_var, show="*", width=200,
                     placeholder_text="New password").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(pwd_row, text="(leave blank to keep current)").pack(side="left")

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _update_dur_label(self):
        """Update the duration label to show minutes and a human-readable format."""
        mins = self._game_duration_var.get()
        hours = mins // 60
        remaining = mins % 60
        if hours > 0:
            time_str = f"{hours}h {remaining:02d}m"
        else:
            time_str = f"{remaining}m"
        self._dur_label.configure(text=f"{mins} minutes  ({time_str})")

    def _section_label(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color="#00f7ff").pack(anchor="w", padx=20, pady=(14, 2))

    def _browse_game(self):
        path = filedialog.askopenfilename(
            title="Select Game Executable",
            filetypes=[("Executables", "*.exe *.bat *.sh"), ("All files", "*.*")]
        )
        if path:
            self._game_path_var.set(path)

    def _browse_file(self, var: tk.StringVar, filetypes: list):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def _browse_ads_folder(self):
        folder = filedialog.askdirectory(title="Select Ads Folder")
        if folder:
            self._ads_folder_var.set(folder)

    # ─────────────────────────────────────────────
    # Save / Close
    # ─────────────────────────────────────────────

    def _save_and_close(self):
        self.config.update_section("game", {
            "path": self._game_path_var.get(),
            "duration": self._game_duration_var.get(),
            "force_kill": self._force_kill_var.get(),
            "allow_multiple_credits": self._multi_credit_var.get(),
            "mode": self._game_mode_var.get(),
            "continue_timeout": self._continue_timeout_var.get(),
        })
        try:
            self.config.update_section("input", {
                "com_port": self._com_port_var.get(),
                "baudrate": int(self._baudrate_var.get()),
                "signal_byte": self._signal_var.get(),
                "serial_debounce": float(self._serial_debounce_var.get()),
                "serial_enabled": self._serial_enabled_var.get(),
                "ps2_key": self._ps2_key_var.get(),
                "ps2_debounce": float(self._ps2_debounce_var.get()),
                "ps2_enabled": self._ps2_enabled_var.get(),
            })
        except ValueError:
            messagebox.showerror("Input Error", "Numeric fields (Baudrate, Debounce) must be valid numbers.", parent=self)
            return
        self.config.update_section("display", {
            "background_image": self._bg_image_var.get(),
            "video_intro": self._video_intro_var.get(),
            "neon_enabled": self._neon_var.get(),
            "font_size": self._font_size_var.get(),
            "accent_neon": self._accent_neon_var.get(),
            "accent_violet": self._accent_violet_var.get(),
        })
        self.config.update_section("audio", {
            **{k: v.get() for k, v in self._audio_vars.items()},
            "volume": round(self._volume_var.get(), 2),
        })
        self.config.update_section("ads", {
            "ads_folder": self._ads_folder_var.get(),
            "duration_per_ad": self._ad_duration_var.get(),
            "mode": self._ad_mode_var.get(),
        })
        self.config.update_section("system", {
            "watchdog": self._watchdog_var.get(),
            "fullscreen_lock": self._fullscreen_lock_var.get(),
            "auto_restart": self._auto_restart_var.get(),
        })
        pwd = self._password_var.get().strip()
        if pwd:
            self.config.set("admin", "password", pwd)

        self.config.save()
        print("[Admin] Settings saved.")
        self._on_close()

    def _on_close(self):
        self.grab_release()
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    def _exit_app(self):
        if messagebox.askyesno("Exit", "Are you sure you want to close the Kiosk application?", parent=self):
            print("[Admin] Exit confirmed. Closing application...")
            try:
                # 1. Clean shutdown of hardware listeners and game
                if hasattr(self.master, "_shutdown"):
                    self.master._shutdown()
                else:
                    self.master.destroy()
            except Exception as e:
                print(f"[Admin] Error during shutdown: {e}")
            finally:
                # 2. Force termination of the python process
                import os
                import sys
                os._exit(0) # Immediate termination
