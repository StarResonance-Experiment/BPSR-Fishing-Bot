<p align="right">
  <a href="./README.md">English</a> |
  <a href="./README.pt-BR.md">Português (Brasil)</a>
</p>

<p align="left">
    <a href="./LICENSE"><img alt="License" src="https://img.shields.io/badge/license-GPL--3.0-brightgreen"></a>
    <a href="https://www.python.org"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python"></a>
    <a href="https://opencv.org"><img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv"></a>
    <a href="https://www.riverbankcomputing.com/software/pyqt/"><img alt="PyQt6" src="https://img.shields.io/badge/PyQt6-6.x-41CD52?logo=qt"></a>
</p>

# BPSR Fishing Bot

An automated, open-source fishing bot for Blue Protocol: Star Resonance, built in Python with a PyQt6 GUI. It uses OpenCV template matching to identify on-screen events and automates the entire fishing minigame loop.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [Pre-built Executable](#option-a-pre-built-executable-recommended)
  - [Run from Source](#option-b-run-from-source)
- [Usage](#usage)
  - [Hotkeys](#hotkeys)
  - [Getting Started](#getting-started)
- [Configuration](#configuration)
  - [Bot Config Tab](#bot-config-tab)
  - [Developer Tab](#developer-tab)
- [Custom Resolutions & Templates](#custom-resolutions--templates)
- [Building from Source](#building-from-source)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Project Structure](#project-structure)

---

## Features

- **Graphical User Interface** — PyQt6-based GUI with tabbed settings, live log output, and a fullscreen ROI overlay.
- **Fully Automated Fishing Loop** — Casts, detects bites, plays the minigame, collects rewards, and loops.
- **Smart Minigame Player** — Tracks the exclamation marker and steers left/right accordingly.
- **Automatic Rod Swapping** — Detects a broken rod and equips a new one without interruption.
- **Multi-Resolution Support** — Ships with templates for 1280×720, 1920×1080, and 2560×1440. Users can add their own resolution folders.
- **External Template System** — User-calibrated ROIs and custom screenshots are saved beside the executable and take precedence over bundled defaults.
- **Hotkey Control** — Start, stop, and toggle the ROI overlay without touching the mouse.
- **ROI Overlay** — Transparent fullscreen overlay shows all detection regions, live confidence scores, and bot status.
- **Debug Mode** — Saves annotated screenshots of every detection attempt to the `capture/` folder.

---

## Quick Start

### Option A: Pre-built Executable (recommended)

1. Download the latest `BPSR-Fishing-Bot.exe` from the [Releases](../../releases) page.
2. Run the exe — Windows will ask for administrator permission (required for global hotkeys).
3. Jump to [Usage](#usage).

### Option B: Run from Source

**Requirements:** Python 3.10+

```bash
git clone https://github.com/your-username/BPSR-Fishing-Bot.git
cd BPSR-Fishing-Bot
pip install -r requirements.txt
python gui.py
```

---

## Usage

### Hotkeys

| Key | Action |
|-----|--------|
| **F7** | Start the bot |
| **F8** | Stop the bot |
| **F9** | Toggle the ROI overlay |

### Getting Started

1. Launch the bot (exe or `python gui.py`).
2. Open Blue Protocol: Star Resonance and go to a fishing location.
3. Either **approach a fishing spot** until the interact prompt (`F`) appears, or **open the fishing UI** manually.
4. Press **F7** to start. The overlay will turn green and show **● Running**.
5. Press **F8** to stop at any time.

> **Tip:** Make sure the correct screen resolution is selected in the **Bot Config → Monitor Settings** dropdown before starting.

---

## Configuration

All settings are saved to `config.json` in the same folder as the exe (or project root when running from source). ROIs are saved separately to `templates/{width}_{height}/rois.json`.

### Bot Config Tab

| Group | Setting | Description |
|-------|---------|-------------|
| **Options** | Game Window Title | Window title used to locate the game on screen (default: `Blue Protocol: Star Resonance`) |
| **Performance** | Target FPS | Screen capture rate. `0` = unlimited |
| **Detection Precision** | Precision | Minimum match confidence (0.0–1.0, default `0.60`) |
| **Monitor Settings** | Resolution | Select screen resolution; loads matching templates and ROIs |
| **Delays** | Default Delay | Pause between most actions (seconds) |
| | Casting Delay | Pause before each cast |
| | Finish Wait Delay | Pause after collecting rewards |
| **State Timeouts** | Per-state timeout | How long (seconds) before the bot gives up and resets a state |

### Developer Tab

| Setting | Description |
|---------|-------------|
| **Debug Mode** | Saves annotated detection screenshots to `capture/` |
| **ROI Table** | Edit the detection regions for each template |
| **Capture Selected** | Take a fresh screenshot of the checked ROI and save it to the external templates folder |
| **Save ROIs** | Persist the current ROI values to `templates/{w}_{h}/rois.json` |
| **Load ROIs** | Reload ROIs from file (external first, then bundled) |
| **Test Detection** | Run a one-shot detection pass and display confidence scores in the overlay |

---

## Custom Resolutions & Templates

The bot discovers resolutions dynamically by scanning for folders named `{width}_{height}` in two locations:

| Location | Purpose |
|----------|---------|
| `templates/` (beside the exe) | **User-writable.** Custom screenshots and calibrated ROIs go here. |
| Bundled assets (inside exe / `src/fishbot/assets/templates/`) | Shipped defaults. Read-only when running as an exe. |

**To add a new resolution:**

1. Create a folder named `{width}_{height}` (e.g., `3440_1440`) in the `templates/` folder beside the exe.
2. Copy the template PNGs from an existing resolution folder and replace them with screenshots taken at your resolution.
3. Create a `rois.json` in that folder with your calibrated ROI values, or use the **Developer** tab to set and save them.
4. Select your resolution in **Bot Config → Monitor Settings** and press **Refresh**.

---

## Building from Source

Requires [PyInstaller](https://pyinstaller.org/) and [UPX](https://upx.github.io/) (optional, for compression).

```bash
pip install pyinstaller
pyinstaller build.spec --clean
```

The executable is output to `dist/BPSR-Fishing-Bot.exe`. It requests administrator privileges on launch (required for global hotkeys via the `keyboard` library).

---

## Troubleshooting

### Bot not detecting events / wrong area

- Open the **ROI overlay** (F9) while in the fishing UI to visually confirm each region is positioned correctly.
- Select your actual screen resolution in **Bot Config → Monitor Settings**.
- Use the **Developer tab** to adjust ROIs, then **Save ROIs**.

### Detection confidence is low / bot misses events

- Lower the **Precision** slider in **Bot Config → Detection Precision** (try `0.55`–`0.65`).
- Enable **Debug Mode** and check the `capture/` folder for annotated screenshots to see what the bot is actually seeing.
- Re-capture templates using **Capture Selected** in the Developer tab if the game UI has been updated.

### Hotkeys not working

- The exe must be run as administrator. Windows UAC will prompt on launch.
- When running from source, run the terminal as administrator.

### Bot exits fishing UI unexpectedly

- This can happen if the fish escapes during the minigame and a state timeout triggers. Move your character back to an interactable fishing spot — the bot will resume automatically once the interact prompt appears.

---

## Architecture

The bot uses a **Finite State Machine (FSM)** with six states:

```
STARTING → CHECKING_ROD → CASTING_BAIT → WAITING_FOR_BITE → PLAYING_MINIGAME → FINISHING → (loop)
```

| State | Responsibility |
|-------|---------------|
| `StartingState` | Detects whether the fishing UI is already open or waits for the interact prompt |
| `CheckingRodState` | Checks rod durability; swaps to a new rod if broken |
| `CastingBaitState` | Casts the fishing line |
| `WaitingForBiteState` | Polls for the exclamation bite indicator |
| `PlayingMinigameState` | Steers the minigame marker left/right until success or failure |
| `FinishingState` | Dismisses reward dialogs and loops back |

Key modules:

- **`src/fishbot/core/game/detector.py`** — Screen capture (`mss`) and template matching (`OpenCV`).
- **`src/fishbot/core/game/controller.py`** — Keyboard/mouse input simulation (`pyautogui`, `keyboard`).
- **`src/fishbot/config/`** — All configuration classes and persistence helpers.
- **`src/fishbot/ui/main_window.py`** — PyQt6 GUI, hotkey bridge, bot thread, ROI overlay.
- **`src/fishbot/utils/roi_visualizer.py`** — Standalone/embedded transparent overlay widget.

---

## Project Structure

```
BPSR-Fishing-Bot/
├── gui.py                          # Application entry point (GUI)
├── build.spec                      # PyInstaller build specification
├── config.json                     # Runtime config (auto-generated)
├── templates/                      # User-writable external templates
│   └── {width}_{height}/
│       ├── *.png                   # Custom template screenshots
│       └── rois.json               # Calibrated ROI values
├── src/
│   └── fishbot/
│       ├── assets/
│       │   ├── app.ico
│       │   └── templates/
│       │       ├── 1280_720/       # Bundled templates + rois.json
│       │       ├── 1920_1080/
│       │       └── 2560_1440/
│       ├── config/
│       │   ├── __init__.py         # AppConfig + get_template_path
│       │   ├── bot_config.py       # Timing, FPS, debug settings
│       │   ├── detection_config.py # Templates map, ROIs, precision
│       │   ├── paths.py            # TEMPLATES_PATH (frozen-aware)
│       │   ├── screen_config.py    # Monitor dimensions
│       │   └── user_config.py      # Config persistence helpers
│       ├── core/
│       │   ├── fishing_bot.py      # Main bot loop
│       │   ├── game/
│       │   │   ├── detector.py     # Screen capture + template matching
│       │   │   └── controller.py   # Input simulation
│       │   └── state/
│       │       ├── state_machine.py
│       │       └── impl/           # One file per FSM state
│       ├── ui/
│       │   └── main_window.py      # PyQt6 GUI
│       └── utils/
│           ├── logger.py
│           └── roi_visualizer.py   # Transparent overlay widget
├── requirements.txt
└── README.md
```

---

Feel free to open an *issue* or submit a *pull request*!
