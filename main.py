"""
main.py – Arcade Kiosk Application Entry Point
Fullscreen attract mode with coin detection, ad rotation, and admin panel.
"""

import os
import sys
import random
import threading
import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
try:
    import cv2
except ImportError:
    cv2 = None

# ── Local Modules ──────────────────────────────────────────────────────────────
from config_manager import ConfigManager
from serial_listener import SerialListener
from keyboard_listener import KeyboardListener
from game_launcher import GameLauncher
from audio_manager import AudioManager
from admin_panel import AdminPanel

# ── Constants ──────────────────────────────────────────────────────────────────
SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
NEON_COLORS = ["#39ff14", "#00ffff", "#ff00ff", "#ffff00", "#ff6600"]
ADMIN_HIDDEN_CLICKS = 5   # Clicks on corner to open admin
ADMIN_CORNER_SIZE = 60    # Pixels in top-right corner

# ── UI Theme (Defaults) ────────────────────────────────────────────────────────
UI_THEME = {
    "bg_dark": "#0a0a20",
    "accent_neon": "#00f7ff",
    "accent_violet": "#bd00ff",
    "text_main": "#ffffff",
    "glass_bg": "#1a1a3a",
    "font_header": "Arial Black",
    "font_body": "Segoe UI"
}


class KioskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── Core Services ──────────────────────────────────────────────────────
        self.config = ConfigManager()
        self.audio = AudioManager(self.config)
        self.launcher = GameLauncher(self.config, on_game_ended_callback=self._on_game_ended)
        self.serial = SerialListener(self.config, on_coin_callback=self._on_coin_detected)
        self.keyboard = KeyboardListener(self.config, on_coin_callback=self._on_coin_detected)

        # ── State ──────────────────────────────────────────────────────────────
        self.credits = 0
        self.game_running = False
        self._ad_index = 0
        self._ad_files: list[str] = []
        self._ad_after_id = None
        self._neon_after_id = None
        self._timer_after_id = None
        self._corner_click_count = 0
        self._corner_click_reset_id = None
        self._admin_open = False
        self._bg_photo = None    # Keep reference to avoid GC
        self._ad_photo = None
        self._video_capture = None
        self._video_after_id = None
        self._video_fps_delay = 33 
        self._video_start_time = 0
        self._intro_played = False

        # ── Window Setup ───────────────────────────────────────────────────────
        self._setup_window()
        self._load_theme()
        self._build_ui()
        self._load_ads()

        # ── Start Services ─────────────────────────────────────────────────────
        self.serial.start()
        self.keyboard.start()
        self.after(200, self._start_attract_mode)

        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _load_theme(self):
        """Update UI_THEME with values from config."""
        UI_THEME["accent_neon"] = self.config.get("display", "accent_neon", "#00f7ff")
        UI_THEME["accent_violet"] = self.config.get("display", "accent_violet", "#bd00ff")

    # ═══════════════════════════════════════════════════════════════════════════
    # Window Setup
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_window(self):
        self.title("Kiosk")
        self.attributes("-fullscreen", True)
        self.configure(bg=UI_THEME["bg_dark"])

        fs_lock = self.config.get("system", "fullscreen_lock", True)
        if fs_lock:
            self.attributes("-topmost", True)
            self.bind("<Alt-F4>", lambda e: "break")
            self.bind("<Escape>", lambda e: "break")
        
        # Force to foreground
        self.lift()
        self.focus_force()
        self.after(500, lambda: [self.lift(), self.focus_force()]) # Double check after initial render

        self.bind("<Configure>", self._on_resize)

    def _on_close_request(self):
        fs_lock = self.config.get("system", "fullscreen_lock", True)
        if not fs_lock:
            self._shutdown()

    def _on_resize(self, event=None):
        if event and event.widget is self:
            self.after_idle(self._refresh_background)

    # ═══════════════════════════════════════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── Background canvas ─────────────────────────────────────────────────
        self.canvas = tk.Canvas(self, bg=UI_THEME["bg_dark"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Background image item
        self._bg_canvas_item = self.canvas.create_image(0, 0, anchor="nw", tags="bg")

        # Ad image item (shown on top of bg)
        self._ad_canvas_item = self.canvas.create_image(0, 0, anchor="nw", tags="ad")

        # ── (Removed "Glass Container" as requested) ──────────────────────────

        # ── (Removed "TAP YOUR CARD" as requested) ────────────────────────────

        # ── Credit counter (Modern Badge) ─────────────────────────────────────
        self.credit_container = ctk.CTkFrame(
            self.canvas,
            fg_color=UI_THEME["accent_violet"],
            corner_radius=15
        )
        self.credit_container.place(relx=0.02, rely=0.96, anchor="sw")

        self.credit_label = ctk.CTkLabel(
            self.credit_container,
            text="CREDITS: 0",
            font=ctk.CTkFont(family=UI_THEME["font_body"], size=22, weight="bold"),
            text_color="#ffffff", # Explicitly white
            padx=15, pady=5
        )
        self.credit_label.pack()

        # ── (Removed "Zone Text" / Status label as requested) ──────────────────

        # ── Timer label ───────────────────────────────────────────────────────
        self.timer_label = ctk.CTkLabel(
            self.canvas,
            text="",
            font=ctk.CTkFont(family=UI_THEME["font_header"], size=48, weight="bold"),
            text_color=UI_THEME["accent_violet"],
            fg_color="transparent"
        )
        self.timer_label.place(relx=0.5, rely=0.1, anchor="center")

        # ── (Removed visible Config button as requested) ──────────────────────

        # ── Hidden admin corner binding (Global on canvas) ──
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.game_overlay = ctk.CTkFrame(
            self.canvas,
            fg_color="#000000",
            corner_radius=0
        )
        self.game_running_label = ctk.CTkLabel(
            self.game_overlay,
            text="🎮  GAME IN PROGRESS",
            font=ctk.CTkFont(family=UI_THEME["font_header"], size=64, weight="bold"),
            text_color=UI_THEME["accent_neon"]
        )
        self.game_running_label.pack(expand=True)

        # ── "CONTINUE?" extension overlay ──────────────────
        self.extension_overlay = ctk.CTkFrame(
            self.canvas,
            fg_color="#000000",
            corner_radius=0
        )
        self.ext_label = ctk.CTkLabel(
            self.extension_overlay,
            text="TAP TO CONTINUE?",
            font=ctk.CTkFont(family=UI_THEME["font_header"], size=56, weight="bold"),
            text_color="#ffffff"
        )
        self.ext_label.pack(expand=True, pady=(20, 0))
        
        self.ext_timer_label = ctk.CTkLabel(
            self.extension_overlay,
            text="15",
            font=ctk.CTkFont(family=UI_THEME["font_header"], size=120, weight="bold"),
            text_color=UI_THEME["accent_neon"]
        )
        self.ext_timer_label.pack(expand=True, pady=(0, 20))

        self._in_extension_period = False
        self._extension_countdown = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # Background Image
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_background(self):
        bg_path = self.config.get("display", "background_image", "")
        w = self.winfo_width() or self.winfo_screenwidth()
        h = self.winfo_height() or self.winfo_screenheight()
        print(f"[UI] Refreshing background. Path: {bg_path!r}, Size: {w}x{h}")
        if bg_path and os.path.exists(bg_path):
            try:
                img = Image.open(bg_path).resize((w, h), Image.LANCZOS)
                self._bg_photo = ImageTk.PhotoImage(img)
                self.canvas.itemconfig(self._bg_canvas_item, image=self._bg_photo)
                print(f"[UI] Background image loaded successfully: {bg_path}")
                return
            except Exception as e:
                print(f"[UI] BG image error: {e}")
        else:
            print(f"[UI] Background image path not found or empty: {bg_path}")

        self.canvas.itemconfig(self._bg_canvas_item, image="")
        self.canvas.configure(bg="#0a0a1a")

    # ═══════════════════════════════════════════════════════════════════════════
    # Attract Mode
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_attract_mode(self):
        self._load_theme()
        self._refresh_ui_colors()
        self._refresh_background()
        self.audio.play_music()

        # Always (re)play video intro in attract mode if configured
        video_path = self.config.get("display", "video_intro", "")
        if video_path and os.path.exists(video_path):
            # Stop any previous video playback cleanly before restarting
            self._stop_video_intro()
            self.after(500, lambda: self._play_video_intro(video_path))
        else:
            self._load_ads()
            self._start_ad_rotation()
            
        self._update_credit_display()
        self.game_overlay.place_forget()

    def _refresh_ui_colors(self):
        """Update existing UI elements with the latest theme colors."""
        # self.glass_frame (Removed)
        self.credit_container.configure(fg_color=UI_THEME["accent_violet"])
        self.timer_label.configure(text_color=UI_THEME["accent_violet"])
        # self.config_btn (Removed)
        self.game_running_label.configure(text_color=UI_THEME["accent_neon"])
        self.ext_timer_label.configure(text_color=UI_THEME["accent_neon"])

    def _load_ads(self):
        folder = self.config.get("ads", "ads_folder", "ads/")
        base = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(folder):
            folder = os.path.join(base, folder)
        self._ad_files = []
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_IMAGE_EXT:
                    self._ad_files.append(os.path.join(folder, f))
        mode = self.config.get("ads", "mode", "sequential")
        if mode == "random":
            random.shuffle(self._ad_files)
        print(f"[Ads] Loaded {len(self._ad_files)} ad file(s) from {folder}")

    def _start_ad_rotation(self):
        if self._ad_after_id:
            self.after_cancel(self._ad_after_id)
        self._ad_index = 0
        self._show_next_ad()

    def _show_next_ad(self):
        """Ads disabled as requested - only background is shown."""
        self.canvas.itemconfig(self._ad_canvas_item, image="")
        return

    def _stop_ad_rotation(self):
        if self._ad_after_id:
            self.after_cancel(self._ad_after_id)
            self._ad_after_id = None
        self.canvas.itemconfig(self._ad_canvas_item, image="")

    # ═══════════════════════════════════════════════════════════════════════════
    # Video Intro
    # ═══════════════════════════════════════════════════════════════════════════

    def _play_video_intro(self, path):
        if not cv2:
            print("[Video] OpenCV not installed, skipping intro.")
            self._start_ad_rotation()
            return

        print(f"[Video] Starting intro: {path}")
        self._video_capture = cv2.VideoCapture(path)
        if not self._video_capture.isOpened():
            print("[Video] Could not open video file.")
            self._load_ads()
            self._start_ad_rotation()
            return

        # Get FPS
        fps = self._video_capture.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self._video_fps_delay = int(1000 / fps)
            print(f"[Video] Detected FPS: {fps}, Delay: {self._video_fps_delay}ms")
        else:
            self._video_fps_delay = 33
            fps = 30.0

        self._video_start_time = time.time()
        self._video_fps = fps

        # Try to play audio (Pygame can often handle common video audio tracks on Windows)
        try:
            import pygame
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            print("[Video] Audio track started via pygame.")
        except Exception as e:
            print(f"[Video] Audio playback failed: {e}")

        self._stop_ad_rotation()
        self._update_video_frame()

    def _stop_video_intro(self):
        """Cleanly stop video playback and release resources."""
        if self._video_after_id:
            self.after_cancel(self._video_after_id)
            self._video_after_id = None
        
        if self._video_capture:
            self._video_capture.release()
            self._video_capture = None
            try:
                import pygame
                pygame.mixer.music.stop()
            except:
                pass
            print("[Video] Intro playback stopped.")

        self.canvas.itemconfig(self._ad_canvas_item, image="")

    def _update_video_frame(self):
        if not self._video_capture: return

        # Sync logic: Calculate which frame we SHOULD be on
        elapsed = time.time() - self._video_start_time
        target_frame = int(elapsed * self._video_fps)
        current_frame = int(self._video_capture.get(cv2.CAP_PROP_POS_FRAMES))

        # Skip frames if falling behind
        while current_frame < target_frame:
            ret, _ = self._video_capture.read()
            if not ret: break
            current_frame += 1

        ret, frame = self._video_capture.read()
        if ret:
            # Resize with OpenCV (much faster)
            w = self.winfo_width() or self.winfo_screenwidth()
            h = self.winfo_height() or self.winfo_screenheight()
            
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
            
            # Convert frame from BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            img = Image.fromarray(frame)
            self._ad_photo = ImageTk.PhotoImage(img) # Reusing ad_photo slot
            self.canvas.itemconfig(self._ad_canvas_item, image=self._ad_photo)
            
            self._video_after_id = self.after(10, self._update_video_frame)
        else:
            print("[Video] Intro finished, looping...")
            self._video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._video_start_time = time.time()
            try:
                import pygame
                pygame.mixer.music.play()
            except:
                pass
            self._update_video_frame()

    # ═══════════════════════════════════════════════════════════════════════════
    # Neon Pulse Animation
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_neon_pulse(self):
        # (Animation logic for removed label removed)
        pass

    def _animate_neon(self):
        pass

    # ═══════════════════════════════════════════════════════════════════════════
    # Coin Detection (called from serial thread via after())
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_coin_detected(self):
        """Thread-safe coin callback – schedule onto main Tkinter thread."""
        self.after(0, self._handle_coin)

    def _handle_coin(self):
        # Stop video intro if playing
        self._stop_video_intro()

        # If in extension period, just stop the extension and reset the game timer
        if self._in_extension_period:
            print("[Kiosk] Coin detected during extension! Extending session...")
            self._stop_extension(success=True)
            return

        # Stop detecting/processing coins if game is already running or a credit is already pending
        if self.game_running or self.credits >= 1:
            print("[Kiosk] Coin signal ignored - game running or credit already stored.")
            return

        self.audio.play_coin_sound()
        self.credits += 1
        print(f"[Kiosk] Coin inserted. Credits: {self.credits}")
        self._update_credit_display()
        
        self._launch_game_session()

    def _launch_game_session(self):
        if self.credits <= 0 or self.game_running:
            return
        
        self._stop_video_intro()
        self.credits -= 1
        self._update_credit_display()

        self.audio.play_start_sound()
        self.audio.stop_music()
        self._stop_ad_rotation()

        # Show "GAME RUNNING" overlay
        self.game_overlay.place(relx=0, rely=0.1, relwidth=1, relheight=0.5)

        # Disable topmost to allow game to show on front
        self.attributes("-topmost", False)
        self.lower() # Push kiosk to back
        print("[Kiosk] Disabled topmost for game launch")

        success = self.launcher.launch()
        if success:
            self.game_running = True
            self._poll_timer()
        else:
            # Restore if launch failed
            self.credits += 1  # refund
            self._update_credit_display()
            self.game_overlay.place_forget()
            self.audio.play_music()
            self._start_ad_rotation()

    def _poll_timer(self):
        if self.launcher.running:
            remaining = self.launcher.time_remaining
            mins, secs = divmod(remaining, 60)
            self.timer_label.configure(text=f"⏱  {mins:02d}:{secs:02d}")
            self._timer_after_id = self.after(500, self._poll_timer)
        else:
            self.timer_label.configure(text="")

    def _on_game_ended(self):
        """Called by GameLauncher when session ends (from background thread)."""
        print("[Kiosk] Game session ended callback received.")
        # Instead of immediate restore, go to extension period
        self.after(0, self._start_extension_period)

    def _start_extension_period(self):
        if self._in_extension_period: return
        
        self._in_extension_period = True
        self.game_running = False
        self._extension_countdown = int(self.config.get("game", "continue_timeout", 15))
        
        self.extension_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self._update_extension_timer()

    def _update_extension_timer(self):
        if not self._in_extension_period: return
        
        if self._extension_countdown <= 0:
            self._stop_extension(success=False)
            return
            
        self.ext_timer_label.configure(text=str(self._extension_countdown))
        self._extension_countdown -= 1
        self.after(1000, self._update_extension_timer)

    def _stop_extension(self, success=False):
        self._in_extension_period = False
        self.extension_overlay.place_forget()
        
        if success:
            # Check if we have credits (though coin detection should have handled it)
            # The most robust way is to pretend a new coin was inserted.
            self.credits = 1 # Force 1 credit for the extension
            self._launch_game_session()
        else:
            # Full cleanup - explicitly terminate game now
            self.launcher.terminate()
            self._restore_attract_mode()

    def _restore_attract_mode(self):
        self.game_running = False
        if self._timer_after_id:
            self.after_cancel(self._timer_after_id)
        self.timer_label.configure(text="")
        self.game_overlay.place_forget()
        
        # Clean up any lingering video state
        self._stop_video_intro()
        
        # Restore topmost if lock is enabled
        fs_lock = self.config.get("system", "fullscreen_lock", True)
        if fs_lock:
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()

        print("[Kiosk] Attract mode restored. Video will replay.")
        self._start_attract_mode()

    # ═══════════════════════════════════════════════════════════════════════════
    # Credits Display
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_credit_display(self):
        self.credit_label.configure(text=f"CREDITS: {self.credits}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Hidden Admin Access (corner clicks)
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_canvas_click(self, event):
        # Check if click is in top-right corner
        w = self.winfo_width()
        if event.x > (w - ADMIN_CORNER_SIZE) and event.y < ADMIN_CORNER_SIZE:
             self._on_corner_click()

    def _on_corner_click(self, event=None):
        self._corner_click_count += 1
        if self._corner_click_reset_id:
            self.after_cancel(self._corner_click_reset_id)
        self._corner_click_reset_id = self.after(3000, self._reset_corner_clicks)

        if self._corner_click_count >= ADMIN_HIDDEN_CLICKS:
            self._corner_click_count = 0
            self._open_admin()

    def _reset_corner_clicks(self):
        self._corner_click_count = 0

    def _open_admin(self):
        if self._admin_open:
            return

        # Stop intro instantly if playing
        self._stop_video_intro()

        # Temporarily disable topmost to allow dialogs to show up front
        self.attributes("-topmost", False)

        # Password check
        pwd = self.config.get("admin", "password", "1234")
        dialog = PasswordDialog(self, correct_password=pwd)
        self.wait_window(dialog)
        
        if not dialog.accepted:
            # Re-enable topmost if dialog cancelled
            fs_lock = self.config.get("system", "fullscreen_lock", True)
            self.attributes("-topmost", fs_lock)
            return

        self._admin_open = True
        # Keep topmost False while AdminPanel is open
        admin = AdminPanel(
            self,
            config_manager=self.config,
            audio_manager=self.audio,
            serial_listener=self.serial,
            on_close_callback=self._on_admin_closed,
        )
        admin.lift()
        admin.focus_force()

    def _on_admin_closed(self):
        self._admin_open = False
        fs_lock = self.config.get("system", "fullscreen_lock", True)
        self.attributes("-topmost", fs_lock)
        # Reload attract mode with new settings
        self._start_attract_mode()

    # ═══════════════════════════════════════════════════════════════════════════
    # Shutdown
    # ═══════════════════════════════════════════════════════════════════════════

    def _shutdown(self):
        print("[Kiosk] Shutting down...")
        self.serial.stop()
        self.keyboard.stop()
        self.launcher.terminate()
        self.audio.shutdown()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# Password Dialog
# ═══════════════════════════════════════════════════════════════════════════════

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, correct_password: str):
        super().__init__(master)
        self.correct_password = correct_password
        self.accepted = False

        self.title("Admin Access")
        self.geometry("450x650") # Taller for numpad
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=UI_THEME["bg_dark"])
        self.grab_set()
        self.focus_force()

        ctk.CTkLabel(self, text="🔒  ADMIN ACCESS",
                     font=ctk.CTkFont(family=UI_THEME["font_header"], size=24, weight="bold"),
                     text_color=UI_THEME["accent_neon"]).pack(pady=(30, 5))
        
        self._var = tk.StringVar()
        self._entry = ctk.CTkEntry(self, textvariable=self._var, show="*",
                                   width=320, height=50,
                                   fg_color="#1a1a3a",
                                   border_color=UI_THEME["accent_neon"],
                                   font=ctk.CTkFont(size=24), justify="center")
        self._entry.pack(pady=20)

        # ── Numpad ───────────────────────────────────────────────────────────
        pad_frame = ctk.CTkFrame(self, fg_color="transparent")
        pad_frame.pack(pady=10)

        buttons = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            'C', '0', '✓'
        ]

        def create_lambda(x):
            return lambda: self._on_key(x)

        for i, b_text in enumerate(buttons):
            row, col = i // 3, i % 3
            btn = ctk.CTkButton(
                pad_frame, text=b_text, 
                width=80, height=80,
                corner_radius=40,
                font=ctk.CTkFont(size=24, weight="bold"),
                fg_color="#1a1a3a",
                hover_color=UI_THEME["accent_violet"],
                command=create_lambda(b_text)
            )
            btn.grid(row=row, column=col, padx=8, pady=8)

        self._err_label = ctk.CTkLabel(self, text="", text_color="#ff3355")
        self._err_label.pack(pady=5)

        ctk.CTkButton(self, text="CANCEL", command=self.destroy, width=200, height=40,
                      fg_color="#333333", hover_color="#555555",
                      font=ctk.CTkFont(weight="bold")).pack(pady=10)

    def _on_key(self, char):
        if char == 'C':
            self._var.set("")
        elif char == '✓':
            self._check()
        else:
            self._var.set(self._var.get() + char)

    def _check(self):
        if self._var.get() == self.correct_password:
            self.accepted = True
            self.destroy()
        else:
            self._err_label.configure(text="Incorrect password. Try again.")
            self._var.set("")
            self.after(1500, lambda: self._err_label.configure(text=""))


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()
