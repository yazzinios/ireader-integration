# 🎰 Arcade Kiosk Controller & Game Launcher

A premium, open-source gaming kiosk management system designed for arcade machines, coin-operated stations, and private gaming zones. Supporting both low-latency hardware keyboard hacks and traditional serial coin acceptors.


## 🔌 Hardware Configuration

The system is designed to interface with physical coin acceptors or card readers (such as iReader) using a creative hardware "keyboard hack."

### Step-by-Step Setup:
1.  **Select a Keyboard**: Use any standard USB or PS/2 keyboard.
2.  **Identify the Key**: Short two pads on the keyboard's internal circuit board to find which corresponds to a specific key (e.g., 'Space' or 'Enter').
3.  **Wired Connection**: Solder two wires from these identified pads.
4.  **Interface with Coin Acceptor**: Connect these two wires to the **Relay Output** (NO/COM) of your Coin Acceptor or iReader.
5.  **Operation**: When a coin is inserted or a card is tapped, the device shorts the wires, simulating a physical key press which the software detects instantly as a credit.



## 💻 Software Architecture

The kiosk software is built on a high-performance Python foundation using `CustomTkinter` for a stunning visual experience and `OpenCV` for cinematic video playback.

### Core Input Methods:
*   **Keyboard Emulation (PS/2 or USB)**: Detects physical key presses from your hardware hack (e.g., wires triggered by a card reader).
*   **Serial Feed (TTL/COM)**: Supports standard coin acceptor signals directly via a COM port.

Once an input is detected, the software converts it to a credit, triggers professional audio feedback, and automatically manages the game lifecycle.

## 🚀 Key Features

*   **Cinematic Attract Mode**: Seamlessly loops 4K video intros or cinematic advertisements when the kiosk is idle. Always replays after every session.
*   **Intelligent Launcher**: Automatically opens, focuses, and (optionally) terminates gaming applications on session timeout.
*   **Dynamic UI Engine**: Neon-pulse aesthetic with glassmorphism effects, providing a "premium gaming" look and feel.
*   **Flexible Session Timer**: Configurable session durations (1 minute to 120 minutes) with a "Tap to Continue" countdown extension.
*   **Secure Admin Panel**: A hidden, password-protected dashboard to configure hardware, media, and game paths in real-time.
*   **High Stability**: Includes a session watchdog that ends gameplay if the target process crashes or is manually closed.
*   **One-Click Deployment**: Automated `install.bat` that handles Python setup and dependency management via `winget`.

## 🛠️ Installation

1.  Clone this repository.
2.  Run `install.bat` as Administrator to install Python and all required libraries.
3.  Launch via `run.bat`.
4.  Access the **Admin Panel** by clicking the **Top-Right Corner** 5 times and entering your password.

## 📦 Dependencies
*   Python 3.10+
*   CustomTkinter (Modern UI)
*   OpenCV (Video Processing)
*   Pygame (Audio Engine)
*   Pynput (Low-latency Input)
*   Pyserial (Hardware Comms)

---
*Created with Yazzine❤️ for the arcade and gaming community.*
https://ma.linkedin.com/in/yazzine/fr
