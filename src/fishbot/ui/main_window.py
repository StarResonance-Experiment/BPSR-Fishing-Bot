import ctypes
import json
import platform
import re
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import keyboard
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QSizePolicy, QComboBox, QLineEdit,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from src.fishbot.config import Config
from src.fishbot.core.fishing_bot import FishingBot
from src.fishbot.utils.logger import set_log_callback
from src.fishbot.utils.roi_visualizer import RoiVisualizer
from src.fishbot.config.user_config import (
    save_config, load_config, save_rois,
    rois_save_path, templates_user_dir, templates_base_user_dir,
)
from src.fishbot.config.paths import TEMPLATES_PATH


# ── Catppuccin Mocha palette ────────────────────────────────────────────────
STATE_COLORS = {
    "STARTING":         "#89b4fa",
    "CHECKING_ROD":     "#fab387",
    "CASTING_BAIT":     "#f9e2af",
    "WAITING_FOR_BITE": "#94e2d5",
    "PLAYING_MINIGAME": "#a6e3a1",
    "FINISHING":        "#cba6f7",
}

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 7px 14px;
    color: #cdd6f4;
}
QPushButton:hover  { background-color: #45475a; }
QPushButton:pressed { background-color: #585b70; }
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #45475a;
    border-color: #313244;
}
QPushButton#start_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#start_btn:hover  { background-color: #b4efb0; }
QPushButton#start_btn:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#stop_btn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#stop_btn:hover     { background-color: #f5a0b5; }
QPushButton#stop_btn:disabled  {
    background-color: #45475a;
    color: #6c7086;
}
QTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: #cdd6f4;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 4px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 6px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}
QTabBar::tab:hover:!selected { background-color: #45475a; }
QSpinBox, QDoubleSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
    color: #cdd6f4;
    min-width: 90px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #89b4fa; }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #585b70;
}
QCheckBox { color: #cdd6f4; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
    image: url(none);
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QTableWidget {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    gridline-color: #313244;
    color: #cdd6f4;
}
QTableWidget::item:selected {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    border: none;
    border-right: 1px solid #45475a;
    border-bottom: 1px solid #45475a;
    padding: 4px 8px;
    font-weight: bold;
}
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    border-top: 1px solid #313244;
    font-size: 12px;
}
QLabel#section_label {
    color: #6c7086;
    font-size: 11px;
}
"""


# ── Global hotkey → Qt signal bridge ────────────────────────────────────────
# keyboard callbacks fire on a background thread; signals safely cross to Qt.
class _HotkeySignals(QObject):
    start_pressed      = pyqtSignal()
    stop_pressed       = pyqtSignal()
    visualizer_toggled = pyqtSignal()
    status_toggled     = pyqtSignal()


# ── Bot worker thread ────────────────────────────────────────────────────────
class BotThread(QThread):
    log_emitted          = pyqtSignal(str)
    stats_updated        = pyqtSignal(dict)
    state_changed        = pyqtSignal(str)
    confidence_updated   = pyqtSignal(dict)
    bot_stopped          = pyqtSignal()

    def __init__(self, config_data: dict):
        super().__init__()
        self.config_data   = config_data
        self._should_stop  = False
        self.bot           = None

    # ── thread body ──────────────────────────────────────────────────────────
    def run(self):
        set_log_callback(lambda msg: self.log_emitted.emit(msg))

        # Build and patch Config *before* FishingBot so Detector picks up the
        # correct templates_path and screen resolution on first load.
        config = Config()
        self._apply_config(config)
        self.bot = FishingBot(config)
        # Honour target_fps now that bot exists
        fps = config.bot.target_fps
        self.bot.target_delay = (1.0 / fps) if fps > 0 else 0
        self.bot.start()

        while not self.bot.is_stopped() and not self._should_stop:
            self.bot.update()

            self.stats_updated.emit(self.bot.stats.stats.copy())
            if self.bot.state_machine.current_state_name:
                self.state_changed.emit(
                    self.bot.state_machine.current_state_name.name
                )
            if self.bot.detector.last_confidences:
                self.confidence_updated.emit(
                    self.bot.detector.last_confidences.copy()
                )
            time.sleep(0.05)

        if not self.bot.is_stopped():
            self.bot.stop()

        set_log_callback(None)
        self.bot_stopped.emit()

    # ── config ───────────────────────────────────────────────────────────────
    def _apply_config(self, config: Config):
        d   = self.config_data
        cfg = config.bot

        cfg.debug_mode            = d.get("debug_mode",            cfg.debug_mode)
        cfg.quick_finish_enabled  = d.get("quick_finish_enabled",  cfg.quick_finish_enabled)
        cfg.target_fps            = d.get("target_fps",            cfg.target_fps)
        cfg.default_delay         = d.get("default_delay",         cfg.default_delay)
        cfg.casting_delay         = d.get("casting_delay",         cfg.casting_delay)
        cfg.finish_wait_delay     = d.get("finish_wait_delay",     cfg.finish_wait_delay)
        cfg.detection.precision   = d.get("precision",             cfg.detection.precision)
        if "templates_path" in d:
            cfg.detection.templates_path = d["templates_path"]
        if "templates_user_path" in d:
            cfg.detection.templates_user_path = d["templates_user_path"]

        for state_name, timeout in d.get("state_timeouts", {}).items():
            cfg.state_timeouts[state_name] = timeout

        screen = cfg.screen
        screen.monitor_x      = d.get("monitor_x",      screen.monitor_x)
        screen.monitor_y      = d.get("monitor_y",      screen.monitor_y)
        screen.monitor_width  = d.get("monitor_width",  screen.monitor_width)
        screen.monitor_height = d.get("monitor_height", screen.monitor_height)

        for name, roi in d.get("rois", {}).items():
            cfg.detection.rois[name] = tuple(roi)

    # ── control ──────────────────────────────────────────────────────────────
    def stop_bot(self):
        self._should_stop = True
        if self.bot:
            self.bot.stop()


# ── Main window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread        = None
        self.roi_overlay       = None   # RoiVisualizer widget (in-process)
        self._current_state    = None
        self._state_start_time = None
        self._loading          = False  # suppresses auto-save while applying loaded data
        self._recent_logs: deque[str] = deque(maxlen=3)

        self.setWindowTitle("BPSR Fishing Bot")
        self.setMinimumSize(920, 580)
        self.resize(1100, 700)
        self.setStyleSheet(DARK_STYLE)

        # Initialize early — _on_resolution_changed runs during _build_bot_cfg_tab
        # (before _build_detect_tab creates these), so they must exist first.
        self.roi_spinboxes:   dict[str, list[QSpinBox]] = {}
        self.roi_checkboxes:  dict[str, QCheckBox]      = {}

        # Debounced auto-save (fires 600 ms after the last widget change)
        # Must be created before _build_ui so _on_resolution_changed can reference it
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        self._connect_autosave()

        # Global hotkeys (work even when the game window is focused)
        self._hotkey_signals = _HotkeySignals()
        self._hotkey_signals.start_pressed.connect(self._on_start)
        self._hotkey_signals.stop_pressed.connect(self._on_stop)
        self._hotkey_signals.visualizer_toggled.connect(self._toggle_visualizer)
        self._hotkey_signals.status_toggled.connect(self._toggle_status_overlay)
        keyboard.add_hotkey("f7", lambda: self._hotkey_signals.start_pressed.emit())
        keyboard.add_hotkey("f8", lambda: self._hotkey_signals.stop_pressed.emit())
        keyboard.add_hotkey("f9", lambda: self._hotkey_signals.visualizer_toggled.emit())
        keyboard.add_hotkey("f10", lambda: self._hotkey_signals.status_toggled.emit())

        # Status bar refresh timer
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._refresh_statusbar)
        self._elapsed_timer.start(500)

        # Restore saved config (if any)
        self._load_config()

        # Auto-open the status overlay on startup
        QTimer.singleShot(200, self._toggle_status_overlay)

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_left_panel())
        root.addWidget(self._build_right_panel(), stretch=1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    # ── Left panel ───────────────────────────────────────────────────────────
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(210)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_status_group())
        layout.addWidget(self._build_controls_group())
        layout.addWidget(self._build_stats_group())

        layout.addStretch()
        return panel

    def _build_status_group(self) -> QGroupBox:
        grp = QGroupBox("Status")
        lay = QVBoxLayout(grp)
        lay.setSpacing(4)

        self.status_dot = QLabel("● Stopped")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.status_dot.setFont(font)
        self.status_dot.setStyleSheet("color: #f38ba8;")

        self.state_label = QLabel("—")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("color: #6c7086; font-size: 11px;")

        lay.addWidget(self.status_dot)
        lay.addWidget(self.state_label)
        return grp

    def _build_controls_group(self) -> QGroupBox:
        grp = QGroupBox("Controls")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        self.start_btn = QPushButton("▶   Start")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self._on_start)

        self.stop_btn = QPushButton("■   Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)

        lay.addWidget(self.start_btn)
        lay.addWidget(self.stop_btn)

        hotkey_hint = QLabel("F7: Start  |  F8: Stop\nF9: ROI Visualizer\nF10: Status Overlay")
        hotkey_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hotkey_hint.setStyleSheet("color: #585b70; font-size: 12px; padding-top: 4px;")
        lay.addWidget(hotkey_hint)
        return grp

    def _build_stats_group(self) -> QGroupBox:
        grp = QGroupBox("Statistics")
        lay = QFormLayout(grp)
        lay.setSpacing(6)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        def stat_label():
            lbl = QLabel("0")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            lbl.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 14px;")
            return lbl

        self.cycles_lbl    = stat_label()
        self.caught_lbl    = stat_label()
        self.rod_lbl       = stat_label()
        self.timeouts_lbl  = stat_label()

        lay.addRow("Cycles:",       self.cycles_lbl)
        lay.addRow("Fish Caught:",  self.caught_lbl)
        lay.addRow("Rod Breaks:",   self.rod_lbl)
        lay.addRow("Timeouts:",     self.timeouts_lbl)
        return grp

    # ── Right panel (save/load toolbar + tabs) ──────────────────────────────
    def _build_right_panel(self) -> QWidget:
        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        # ── Config toolbar ──
        toolbar = QWidget()
        toolbar.setStyleSheet(
            "background-color: #181825; border-radius: 4px; padding: 2px 4px;"
        )
        tlay = QHBoxLayout(toolbar)
        tlay.setContentsMargins(6, 4, 6, 4)
        tlay.setSpacing(8)

        save_btn = QPushButton("💾  Save Config")
        save_btn.setFixedWidth(130)
        save_btn.clicked.connect(self._manual_save)

        load_btn = QPushButton("📂  Load Config")
        load_btn.setFixedWidth(130)
        load_btn.clicked.connect(self._manual_load)

        self._save_status_lbl = QLabel("No config file yet")
        self._save_status_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")

        tlay.addWidget(save_btn)
        tlay.addWidget(load_btn)
        tlay.addStretch()
        tlay.addWidget(self._save_status_lbl)

        vbox.addWidget(toolbar)

        # ── Tabs ──
        tabs = QTabWidget()
        tabs.addTab(self._build_log_tab(),       "  Logs  ")
        tabs.addTab(self._build_bot_cfg_tab(),   "  Bot Config  ")
        tabs.addTab(self._build_detect_tab(),    "  Developer  ")
        vbox.addWidget(tabs)

        return wrapper

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        lay.addWidget(self.log_text)

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setFixedWidth(100)
        clear_btn.clicked.connect(self.log_text.clear)
        lay.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return w

    def _build_bot_cfg_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        # ── Flags ──
        flags_grp = QGroupBox("Options")
        flags_lay = QFormLayout(flags_grp)

        self.quick_finish_chk = QCheckBox("Enable Quick Finish")
        flags_lay.addRow(self.quick_finish_chk)

        self.game_window_edit = QLineEdit("Blue Protocol: Star Resonance")
        self.game_window_edit.setPlaceholderText("Game window title")
        flags_lay.addRow("Game Window:", self.game_window_edit)
        lay.addWidget(flags_grp)

        # ── Performance ──
        perf_grp = QGroupBox("Performance")
        perf_lay = QFormLayout(perf_grp)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(0, 120)
        self.fps_spin.setValue(0)
        self.fps_spin.setSpecialValueText("Unlimited")
        perf_lay.addRow("Target FPS:", self.fps_spin)
        lay.addWidget(perf_grp)

        # ── Detection Precision ──
        prec_grp = QGroupBox("Detection Precision")
        prec_lay = QFormLayout(prec_grp)

        self.precision_spin = QDoubleSpinBox()
        self.precision_spin.setRange(0.05, 1.00)
        self.precision_spin.setSingleStep(0.05)
        self.precision_spin.setDecimals(2)
        self.precision_spin.setValue(0.60)
        prec_lay.addRow("Confidence Threshold:", self.precision_spin)

        prec_hint = QLabel("Lower = more detections (risk: false positives) | Higher = stricter matching")
        prec_hint.setStyleSheet("color: #6c7086; font-size: 11px;")
        prec_hint.setWordWrap(True)
        prec_lay.addRow(prec_hint)
        lay.addWidget(prec_grp)

        # ── Monitor Settings ──
        mon_grp  = QGroupBox("Monitor Settings")
        mon_form = QFormLayout(mon_grp)

        # Resolution dropdown
        self.resolution_combo = QComboBox()
        self.resolution_combo.setStyleSheet(
            "QComboBox { background:#313244; border:1px solid #45475a; "
            "border-radius:4px; padding:4px 8px; color:#cdd6f4; }"
            "QComboBox::drop-down { border:none; }"
            "QComboBox QAbstractItemView { background:#313244; color:#cdd6f4; "
            "selection-background-color:#45475a; border:1px solid #45475a; }"
        )
        # Create status label before populate (which triggers _on_resolution_changed)
        self._res_status_lbl = QLabel("")
        self._res_status_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
        self._res_status_lbl.setWordWrap(True)

        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self._populate_resolution_combo()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.setToolTip("Rescan template folders for new resolutions")
        refresh_btn.clicked.connect(lambda: self._populate_resolution_combo(keep_selection=True))

        res_row = QHBoxLayout()
        res_row.setSpacing(4)
        res_row.addWidget(self.resolution_combo)
        res_row.addWidget(refresh_btn)
        mon_form.addRow("Resolution:", res_row)

        def make_mon_spin(lo, hi, val):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            return s

        self.mon_x_spin = make_mon_spin(-7680, 7680, 0)
        self.mon_y_spin = make_mon_spin(-4320, 4320, 0)
        mon_form.addRow("Monitor X:", self.mon_x_spin)
        mon_form.addRow("Monitor Y:", self.mon_y_spin)
        mon_form.addRow(self._res_status_lbl)

        mon_note = QLabel(
            "Resolutions are discovered from folders named {width}_{height}\n"
            "in the internal bundle and beside the exe (templates/ folder).\n"
            "Add your own folder and press Refresh to reload the list."
        )
        mon_note.setStyleSheet("color: #6c7086; font-size: 11px;")
        mon_form.addRow(mon_note)
        lay.addWidget(mon_grp)

        # ── Delays ──
        delays_grp = QGroupBox("Delays (seconds)")
        delays_lay = QFormLayout(delays_grp)

        def make_dspin(val):
            s = QDoubleSpinBox()
            s.setRange(0.0, 10.0)
            s.setSingleStep(0.1)
            s.setDecimals(2)
            s.setValue(val)
            return s

        self.default_delay_spin  = make_dspin(0.5)
        self.casting_delay_spin  = make_dspin(0.5)
        self.finish_wait_spin    = make_dspin(0.5)

        delays_lay.addRow("Default Delay:",      self.default_delay_spin)
        delays_lay.addRow("Casting Delay:",      self.casting_delay_spin)
        delays_lay.addRow("Finish Wait Delay:",  self.finish_wait_spin)
        lay.addWidget(delays_grp)

        # ── State Timeouts ──
        timeouts_grp = QGroupBox("State Timeouts (seconds)")
        timeouts_lay = QFormLayout(timeouts_grp)

        defaults = {
            "STARTING":         10,
            "CHECKING_ROD":     15,
            "CASTING_BAIT":     15,
            "WAITING_FOR_BITE": 25,
            "PLAYING_MINIGAME": 30,
            "FINISHING":        10,
        }
        self.timeout_spins = {}
        for name, val in defaults.items():
            s = QSpinBox()
            s.setRange(1, 300)
            s.setValue(val)
            self.timeout_spins[name] = s
            timeouts_lay.addRow(f"{name}:", s)
        lay.addWidget(timeouts_grp)

        note = QLabel("Config changes take effect on the next Start.")
        note.setObjectName("section_label")
        note.setStyleSheet("color: #6c7086; font-size: 11px; padding-top: 4px;")
        lay.addWidget(note)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_detect_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)


        # ── Debug ──
        dbg_grp = QGroupBox("Debug")
        dbg_lay = QVBoxLayout(dbg_grp)
        self.debug_mode_chk = QCheckBox("Debug Mode")
        self.debug_mode_chk.setChecked(False)
        dbg_lay.addWidget(self.debug_mode_chk)
        lay.addWidget(dbg_grp)

        # ── ROI Table ──
        roi_grp = QGroupBox("Region of Interest (ROI)")
        roi_lay = QVBoxLayout(roi_grp)

        hint2 = QLabel("Default values are calibrated for Full HD (1920×1080). "
                        "Adjust if your game runs at a different resolution.")
        hint2.setStyleSheet("color: #6c7086; font-size: 11px;")
        hint2.setWordWrap(True)
        roi_lay.addWidget(hint2)

        self.roi_table = QTableWidget()
        self.roi_table.setColumnCount(7)
        self.roi_table.setHorizontalHeaderLabels(
            ["", "Template", "X", "Y", "Width", "Height", "Result"]
        )
        hdr = self.roi_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # checkbox
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)            # name
        for i in range(2, 7):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.roi_table.verticalHeader().setVisible(False)
        self.roi_table.setShowGrid(True)
        self.roi_table.setAlternatingRowColors(False)

        default_rois = {
            "fishing_spot_btn": (1400, 540, 121,  55),
            "broken_rod":       (1635, 982, 250,  63),
            "new_rod":          (1624, 563, 185,  65),
            "exclamation":      ( 929, 438,  52, 142),
            "left_arrow":       ( 740, 490, 220, 100),
            "right_arrow":      ( 960, 490, 220, 100),
            "success":          ( 710, 620, 570, 130),
            "continue":         (1439, 942, 306,  75),
            "level_check":      (1101, 985, 131,  57),
        }

        self.roi_table.setRowCount(len(default_rois))
        self.roi_spinboxes:   dict[str, list[QSpinBox]]     = {}
        self.roi_checkboxes:  dict[str, QCheckBox]          = {}
        self.roi_result_items: dict[str, QTableWidgetItem]  = {}

        for row, (name, (x, y, w, h)) in enumerate(default_rois.items()):
            # ── Col 0: checkbox ──
            chk = QCheckBox()
            chk.setChecked(True)
            cell = QWidget()
            cell_lay = QHBoxLayout(cell)
            cell_lay.addWidget(chk)
            cell_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_lay.setContentsMargins(0, 0, 0, 0)
            self.roi_table.setCellWidget(row, 0, cell)
            self.roi_checkboxes[name] = chk

            # ── Col 1: template name ──
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor("#cba6f7")
            )
            self.roi_table.setItem(row, 1, name_item)

            # ── Cols 2-5: X, Y, W, H spinboxes ──
            spins = []
            for col, (val, max_val) in enumerate(
                [(x, 3840), (y, 2160), (w, 3840), (h, 2160)]
            ):
                spin = QSpinBox()
                spin.setRange(0, max_val)
                spin.setValue(val)
                spin.setFrame(False)
                spin.setStyleSheet(
                    "background:transparent; border:none; color:#cdd6f4;"
                )
                self.roi_table.setCellWidget(row, col + 2, spin)
                spins.append(spin)

            self.roi_spinboxes[name] = spins
            for spin in spins:
                spin.valueChanged.connect(self._sync_roi_overlay)

            # ── Col 6: result placeholder ──
            result_item = QTableWidgetItem("—")
            result_item.setFlags(result_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            result_item.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor("#585b70")
            )
            self.roi_table.setItem(row, 6, result_item)
            self.roi_result_items[name] = result_item

        self.roi_table.setMinimumHeight(300)
        roi_lay.addWidget(self.roi_table)

        # ── Capture button row ──
        cap_row = QHBoxLayout()

        sel_all_btn = QPushButton("☑ All")
        sel_all_btn.setFixedWidth(60)
        sel_all_btn.setToolTip("Select all ROIs")
        sel_all_btn.clicked.connect(lambda: self._set_all_roi_checks(True))

        sel_none_btn = QPushButton("☐ None")
        sel_none_btn.setFixedWidth(85)
        sel_none_btn.setToolTip("Deselect all ROIs")
        sel_none_btn.clicked.connect(lambda: self._set_all_roi_checks(False))

        cap_btn = QPushButton("📷  Capture Selected")
        cap_btn.setFixedWidth(155)
        cap_btn.clicked.connect(self._capture_rois)

        test_btn = QPushButton("🔍  Test Detection")
        test_btn.setFixedWidth(145)
        test_btn.clicked.connect(self._test_roi_detection)

        save_roi_btn = QPushButton("💾  Save ROIs")
        save_roi_btn.setFixedWidth(130)
        save_roi_btn.setToolTip("Save current ROI values to the external rois.json")
        save_roi_btn.clicked.connect(self._save_rois)

        load_roi_btn = QPushButton("📂  Load ROIs")
        load_roi_btn.setFixedWidth(130)
        load_roi_btn.setToolTip("Reload ROIs from external rois.json, or internal preset if not found")
        load_roi_btn.clicked.connect(self._on_resolution_changed)

        self._capture_status_lbl = QLabel("")
        self._capture_status_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")

        cap_row.addWidget(sel_all_btn)
        cap_row.addWidget(sel_none_btn)
        cap_row.addWidget(cap_btn)
        cap_row.addWidget(save_roi_btn)
        cap_row.addWidget(load_roi_btn)
        cap_row.addWidget(test_btn)
        cap_row.addStretch()
        roi_lay.addLayout(cap_row)
        roi_lay.addWidget(self._capture_status_lbl)

        lay.addWidget(roi_grp)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    # ── Resolution helpers ────────────────────────────────────────────────────
    def _templates_dir(self, width: int, height: int) -> Path:
        subdir = TEMPLATES_PATH / f"{width}_{height}"
        if subdir.is_dir():
            return subdir
        # Fallback: if no resolution subdir exists, use the base templates folder
        return TEMPLATES_PATH

    def _scan_resolutions(self) -> list[tuple[int, int]]:
        """Scan internal and external template folders for {width}_{height} dirs.

        If templates exist directly in the base folder (no resolution subdirs),
        use the primary screen resolution as a fallback entry so the combo is
        never empty.
        """
        pattern = re.compile(r'^(\d+)_(\d+)$')
        found: set[tuple[int, int]] = set()
        for base in [TEMPLATES_PATH, templates_base_user_dir()]:
            if not base.exists():
                continue
            for folder in base.iterdir():
                if not folder.is_dir():
                    continue
                m = pattern.match(folder.name)
                if m:
                    found.add((int(m.group(1)), int(m.group(2))))

        # Fallback: if no resolution subdirs found but templates exist in base dir,
        # add the primary screen resolution so the user can still operate.
        if not found:
            has_templates = TEMPLATES_PATH.exists() and any(
                f.suffix.lower() == ".png" for f in TEMPLATES_PATH.iterdir() if f.is_file()
            )
            if has_templates:
                screen = QApplication.primaryScreen()
                if screen:
                    sz = screen.size()
                    found.add((sz.width(), sz.height()))
                else:
                    found.add((1920, 1080))

        return sorted(found, key=lambda r: r[0] * r[1])

    def _populate_resolution_combo(self, keep_selection: bool = False):
        """Fill the resolution combo from scanned folders. Optionally preserve current selection."""
        current = self.resolution_combo.currentData() if keep_selection else None
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.clear()
        resolutions = self._scan_resolutions()
        for ww, hh in resolutions:
            self.resolution_combo.addItem(f"{ww} × {hh}", (ww, hh))
        self.resolution_combo.blockSignals(False)

        # Restore previous selection
        restored = False
        if current:
            for i in range(self.resolution_combo.count()):
                if self.resolution_combo.itemData(i) == current:
                    self.resolution_combo.setCurrentIndex(i)
                    restored = True
                    break
        if not restored and self.resolution_combo.count() > 0:
            # Default to 1920×1080 if available, otherwise first entry
            default = (1920, 1080)
            default_idx = 0
            for i in range(self.resolution_combo.count()):
                if self.resolution_combo.itemData(i) == default:
                    default_idx = i
                    break
            self.resolution_combo.setCurrentIndex(default_idx)

        # Trigger ROI load for the selected entry
        if self.resolution_combo.count() > 0:
            self._on_resolution_changed()

    def _on_resolution_changed(self):
        width, height = self.resolution_combo.currentData()
        # User-saved ROIs take priority; fall back to the bundled preset.
        writable = rois_save_path(width, height)
        bundled  = self._templates_dir(width, height) / "rois.json"
        rois_file = writable if writable.exists() else bundled

        if not rois_file.exists():
            # No saved rois.json — use hardcoded 1080p defaults, scaled to current res
            from src.fishbot.config.detection_config import DetectionConfig
            base_rois = DetectionConfig().rois
            base_w, base_h = 1920, 1080
            scale_x = width / base_w
            scale_y = height / base_h
            rois = {}
            for name, roi in base_rois.items():
                if roi and len(roi) == 4:
                    x, y, w, h = roi
                    rois[name] = (
                        round(x * scale_x),
                        round(y * scale_y),
                        round(w * scale_x),
                        round(h * scale_y),
                    )
                else:
                    rois[name] = roi
            self._res_status_lbl.setText(
                f"Using scaled default ROIs for {width}×{height} (from 1080p)"
            )
            self._res_status_lbl.setStyleSheet("color: #f9e2af; font-size: 11px;")
        else:
            try:
                rois = json.loads(rois_file.read_text(encoding="utf-8"))
            except Exception as e:
                self._res_status_lbl.setText(f"Failed to load rois.json: {e}")
                self._res_status_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")
                return

        # Apply to ROI spinboxes (block saves during load)
        self._loading = True
        try:
            for name, spins in self.roi_spinboxes.items():
                roi = rois.get(name)
                if roi and len(roi) == 4:
                    for spin, val in zip(spins, roi):
                        spin.setValue(int(val))
        finally:
            self._loading = False

        source = "user-saved" if rois_file == writable else f"{width}×{height} preset"
        self._res_status_lbl.setText(f"Loaded ROIs from {source}")
        self._res_status_lbl.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        self._sync_roi_overlay()
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_resolution(self.resolution_combo.currentText())
        self._schedule_save()

    # ── Config snapshot ──────────────────────────────────────────────────────
    def _get_config_data(self) -> dict:
        return {
            "debug_mode":           self.debug_mode_chk.isChecked(),
            "quick_finish_enabled": self.quick_finish_chk.isChecked(),
            "game_window_title":    self.game_window_edit.text().strip(),
            "target_fps":           self.fps_spin.value(),
            "default_delay":        self.default_delay_spin.value(),
            "casting_delay":        self.casting_delay_spin.value(),
            "finish_wait_delay":    self.finish_wait_spin.value(),
            "precision":            self.precision_spin.value(),
            "state_timeouts":       {n: s.value() for n, s in self.timeout_spins.items()},
            "monitor_x":       self.mon_x_spin.value(),
            "monitor_y":       self.mon_y_spin.value(),
            "monitor_width":   self.resolution_combo.currentData()[0],
            "monitor_height":  self.resolution_combo.currentData()[1],
            "templates_path":      str(self._templates_dir(
                                        *self.resolution_combo.currentData())),
            "templates_user_path": str(templates_user_dir(
                                        *self.resolution_combo.currentData())),
            "rois":            {
                name: [s.value() for s in spins]
                for name, spins in self.roi_spinboxes.items()
            },
        }

    def _get_save_data(self) -> dict:
        """Config data without ROIs or derived paths — those are computed at runtime."""
        data = self._get_config_data()
        data.pop("rois", None)
        data.pop("templates_path", None)
        return data

    # ── Game window focus ─────────────────────────────────────────────────────
    @property
    def _GAME_WINDOW_TITLE(self) -> str:
        return self.game_window_edit.text().strip() or "Blue Protocol: Star Resonance"

    def _focus_game_window(self) -> bool:
        """Bring the game window to the foreground. Returns True if found."""
        if platform.system() == "Windows":
            try:
                FindWindow      = ctypes.windll.user32.FindWindowW
                ShowWindow      = ctypes.windll.user32.ShowWindow
                SetForeground   = ctypes.windll.user32.SetForegroundWindow
                IsIconic        = ctypes.windll.user32.IsIconic

                hwnd = FindWindow(None, self._GAME_WINDOW_TITLE)
                if not hwnd:
                    return False

                if IsIconic(hwnd):
                    ShowWindow(hwnd, 9)   # SW_RESTORE

                SetForeground(hwnd)
                return True
            except AttributeError:
                return False
        else:
            # Linux: use wmctrl or xdotool to focus the window
            title = self._GAME_WINDOW_TITLE
            for cmd in [
                ["wmctrl", "-a", title],
                ["xdotool", "search", "--name", title, "windowactivate"],
            ]:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return True
                except FileNotFoundError:
                    continue
                except subprocess.TimeoutExpired:
                    continue
            return False

    # ── Button handlers ──────────────────────────────────────────────────────
    def _on_start(self):
        if self.bot_thread and self.bot_thread.isRunning():
            return

        found = self._focus_game_window()
        if not found:
            self._append_log(
                f"[WARN] Window \"{self._GAME_WINDOW_TITLE}\" not found — "
                "make sure the game is running. Starting anyway..."
            )

        # Disable Start immediately so double-presses are ignored
        self.start_btn.setEnabled(False)
        self._set_status("● Starting…", "#f9e2af")

        # Give the OS ~500 ms to actually switch focus before the bot runs
        QTimer.singleShot(500, self._start_bot_thread)

    def _start_bot_thread(self):
        self.bot_thread = BotThread(self._get_config_data())
        self.bot_thread.log_emitted.connect(self._append_log)
        self.bot_thread.stats_updated.connect(self._update_stats)
        self.bot_thread.state_changed.connect(self._on_state_changed)
        self.bot_thread.confidence_updated.connect(self._on_confidence_updated)
        self.bot_thread.bot_stopped.connect(self._on_bot_stopped)
        self.bot_thread.start()

        self.stop_btn.setEnabled(True)
        self._set_status("● Running", "#a6e3a1")
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_status("● Running")

    def _on_stop(self):
        if self.bot_thread:
            self.bot_thread.stop_bot()

    def _on_bot_stopped(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_status("● Stopped", "#f38ba8")
        self.state_label.setText("—")
        self.state_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        self._current_state    = None
        self._state_start_time = None
        self.statusBar().showMessage("Bot stopped")
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_confidences({})
            self.roi_overlay.update_status("● Stopped")

    # ── Signal handlers ──────────────────────────────────────────────────────
    def _append_log(self, message: str):
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

        self._recent_logs.append(message)
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_log_lines(list(self._recent_logs))

    def _update_stats(self, stats: dict):
        self.cycles_lbl.setText(str(stats.get("cycles",     0)))
        self.caught_lbl.setText(str(stats.get("fish_caught", 0)))
        self.rod_lbl.setText(   str(stats.get("rod_breaks",  0)))
        self.timeouts_lbl.setText(str(stats.get("timeouts",  0)))
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_stats(stats)

    def _on_confidence_updated(self, confidences: dict):
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_confidences(
                confidences, precision=self.precision_spin.value()
            )

    def _on_state_changed(self, state_name: str):
        if state_name != self._current_state:
            self._current_state    = state_name
            self._state_start_time = time.time()

        color = STATE_COLORS.get(state_name, "#cdd6f4")
        display = state_name.replace("_", " ")
        self.state_label.setText(display)
        self.state_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;"
        )

    def _refresh_statusbar(self):
        if self._current_state and self._state_start_time:
            elapsed = time.time() - self._state_start_time
            self.statusBar().showMessage(
                f"State: {self._current_state}  |  Elapsed: {elapsed:.1f}s"
            )

    # ── ROI Visualizer ───────────────────────────────────────────────────────
    def _show_overlay_fullscreen(self):
        """Show the overlay covering the full screen.

        With X11BypassWindowManagerHint, showFullScreen() doesn't work because
        the WM isn't managing the window. Instead, manually set geometry to the
        full screen size and call show().
        """
        screen = QApplication.primaryScreen()
        if screen:
            self.roi_overlay.setGeometry(screen.geometry())
        self.roi_overlay.show()
        self.roi_overlay.raise_()

    def _ensure_overlay(self):
        """Create and show the overlay if it doesn't exist yet."""
        if not (self.roi_overlay and self.roi_overlay.isVisible()):
            self.roi_overlay = RoiVisualizer(rois=self._current_rois())
            self.roi_overlay._show_rois   = False
            self.roi_overlay._show_status = True
            self.roi_overlay.update_log_lines(list(self._recent_logs))
            is_running = bool(self.bot_thread and self.bot_thread.isRunning())
            self.roi_overlay.update_status("● Running" if is_running else "● Stopped")
            self.roi_overlay.update_resolution(self.resolution_combo.currentText())
            self._show_overlay_fullscreen()

    def _close_overlay_if_empty(self):
        """Close the overlay when both ROIs and status are hidden."""
        if self.roi_overlay and not self.roi_overlay._show_rois and not self.roi_overlay._show_status:
            self.roi_overlay.close()
            self.roi_overlay = None

    def _toggle_visualizer(self):
        """F9 — toggle ROI boxes only."""
        already_open = bool(self.roi_overlay and self.roi_overlay.isVisible())
        self._ensure_overlay()
        if already_open:
            self.roi_overlay.toggle_rois()
        else:
            self.roi_overlay._show_rois = True
        self._close_overlay_if_empty()

    def _toggle_status_overlay(self):
        """F10 — toggle top-left status/log panel only."""
        already_open = bool(self.roi_overlay and self.roi_overlay.isVisible())
        self._ensure_overlay()
        if already_open:
            self.roi_overlay.toggle_status_overlay()
        # If just opened, _show_status is already True — nothing extra needed
        self._close_overlay_if_empty()

    def _current_rois(self) -> dict:
        """Collect current ROI values from the spinboxes as a plain dict."""
        return {
            name: tuple(s.value() for s in spins)
            for name, spins in self.roi_spinboxes.items()
        }

    def _sync_roi_overlay(self):
        """Push latest spinbox values to the overlay if it's open."""
        if self.roi_overlay and self.roi_overlay.isVisible():
            self.roi_overlay.update_rois(self._current_rois())

    # ── Save / Load ──────────────────────────────────────────────────────────
    def _connect_autosave(self):
        """Connect every config widget so changes trigger a debounced save."""
        widgets = [
            self.debug_mode_chk, self.quick_finish_chk,
            self.fps_spin, self.default_delay_spin,
            self.casting_delay_spin, self.finish_wait_spin,
            self.precision_spin,
            self.mon_x_spin, self.mon_y_spin,
            *self.timeout_spins.values(),
        ]
        for w in widgets:
            sig = getattr(w, "toggled", None) or w.valueChanged
            sig.connect(self._schedule_save)
        self.game_window_edit.textChanged.connect(self._schedule_save)
        # Combo uses currentIndexChanged
        self.resolution_combo.currentIndexChanged.connect(self._schedule_save)

    def _schedule_save(self):
        if not self._loading:
            self._save_timer.start(600)

    def _do_save(self):
        try:
            save_config(self._get_save_data())
            ts = time.strftime("%H:%M:%S")
            self._save_status_lbl.setText(f"Auto-saved at {ts}")
            self._save_status_lbl.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception as e:
            self._save_status_lbl.setText(f"Save failed: {e}")
            self._save_status_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _save_rois(self):
        """Save current ROI spinbox values to the writable rois.json for this resolution."""
        width, height = self.resolution_combo.currentData()
        rois_file = rois_save_path(width, height)
        data = {name: [s.value() for s in spins]
                for name, spins in self.roi_spinboxes.items()}
        try:
            save_rois(rois_file, data)
            ts = time.strftime("%H:%M:%S")
            self._capture_status_lbl.setText(f"ROIs saved at {ts}")
            self._capture_status_lbl.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception as e:
            self._capture_status_lbl.setText(f"ROI save failed: {e}")
            self._capture_status_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _manual_save(self):
        self._save_timer.stop()
        self._do_save()

    def _manual_load(self):
        data = load_config()
        if data:
            self._apply_config_to_widgets(data)
            ts = time.strftime("%H:%M:%S")
            self._save_status_lbl.setText(f"Loaded at {ts}")
            self._save_status_lbl.setStyleSheet("color: #89b4fa; font-size: 11px;")
        else:
            self._save_status_lbl.setText("No config file found")
            self._save_status_lbl.setStyleSheet("color: #f9e2af; font-size: 11px;")

    def _load_config(self):
        """Called once on startup to restore the last saved config."""
        data = load_config()
        if data:
            self._apply_config_to_widgets(data)
            self._save_status_lbl.setText("Config restored from file")
            self._save_status_lbl.setStyleSheet("color: #89b4fa; font-size: 11px;")

    def _apply_config_to_widgets(self, data: dict):
        """Apply a config dict to all GUI widgets without triggering auto-save."""
        self._loading = True
        try:
            self.debug_mode_chk.setChecked(data.get("debug_mode", False))
            self.quick_finish_chk.setChecked(data.get("quick_finish_enabled", False))
            self.game_window_edit.setText(data.get("game_window_title", "Blue Protocol: Star Resonance"))
            self.fps_spin.setValue(data.get("target_fps", 0))
            self.default_delay_spin.setValue(data.get("default_delay", 0.5))
            self.casting_delay_spin.setValue(data.get("casting_delay", 0.5))
            self.finish_wait_spin.setValue(data.get("finish_wait_delay", 0.5))
            self.precision_spin.setValue(data.get("precision", 0.60))

            for name, spin in self.timeout_spins.items():
                spin.setValue(data.get("state_timeouts", {}).get(name, spin.value()))

            self.mon_x_spin.setValue(data.get("monitor_x", 0))
            self.mon_y_spin.setValue(data.get("monitor_y", 0))
            target = (data.get("monitor_width", 1920), data.get("monitor_height", 1080))
            for i in range(self.resolution_combo.count()):
                if self.resolution_combo.itemData(i) == target:
                    self.resolution_combo.setCurrentIndex(i)
                    break

        finally:
            self._loading = False

    # ── ROI Detection Test ────────────────────────────────────────────────────
    def _test_roi_detection(self):
        import mss
        import cv2
        import numpy as np
        from src.fishbot.config.detection_config import DetectionConfig

        rois = {
            name: roi for name, roi in self._current_rois().items()
            if self.roi_checkboxes.get(name, QCheckBox()).isChecked()
        }
        if not rois:
            self._capture_status_lbl.setText("No ROIs selected")
            self._capture_status_lbl.setStyleSheet("color: #f9e2af; font-size: 11px;")
            return

        templates_path = Path(
            self._get_config_data().get("templates_path", str(TEMPLATES_PATH))
        )
        template_filenames = DetectionConfig().templates  # {name: filename}
        precision  = self.precision_spin.value()
        mon_x      = self.mon_x_spin.value()
        mon_y      = self.mon_y_spin.value()

        # Hide overlay so its borders don't affect detection
        overlay_was_visible = bool(self.roi_overlay and self.roi_overlay.isVisible())
        if overlay_was_visible:
            self.roi_overlay.hide()
            QApplication.processEvents()

        with mss.mss() as sct:
            for name, (x, y, w, h) in rois.items():
                if w <= 0 or h <= 0:
                    self._set_roi_result(name, None, precision, "invalid size")
                    continue

                # Load template image
                filename = template_filenames.get(name)
                if not filename:
                    self._set_roi_result(name, None, precision, "no filename")
                    continue
                tmpl_path = templates_path / filename
                if not tmpl_path.exists():
                    self._set_roi_result(name, None, precision, "file missing")
                    continue

                tmpl_img = cv2.imread(str(tmpl_path), cv2.IMREAD_UNCHANGED)
                if tmpl_img is None:
                    self._set_roi_result(name, None, precision, "load error")
                    continue

                if tmpl_img.shape[2] == 4:
                    mask = tmpl_img[:, :, 3]
                    tmpl_bgr = cv2.cvtColor(tmpl_img, cv2.COLOR_BGRA2BGR)
                else:
                    mask    = None
                    tmpl_bgr = tmpl_img

                # Capture the ROI region from screen
                region = {
                    "left": mon_x + x, "top": mon_y + y,
                    "width": w,        "height": h,
                }
                screen = cv2.cvtColor(
                    np.array(sct.grab(region)), cv2.COLOR_BGRA2BGR
                )

                s_gray = cv2.cvtColor(screen,   cv2.COLOR_BGR2GRAY)
                t_gray = cv2.cvtColor(tmpl_bgr, cv2.COLOR_BGR2GRAY)

                if s_gray.shape[0] < t_gray.shape[0] or s_gray.shape[1] < t_gray.shape[1]:
                    self._set_roi_result(name, None, precision, "ROI < template")
                    continue

                _, confidence, _, _ = cv2.minMaxLoc(
                    cv2.matchTemplate(s_gray, t_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
                )
                self._set_roi_result(name, confidence, precision)

        if overlay_was_visible:
            self._show_overlay_fullscreen()

        self._capture_status_lbl.setText(f"Detection tested for {len(rois)} ROI(s)")
        self._capture_status_lbl.setStyleSheet("color: #89b4fa; font-size: 11px;")

    def _set_roi_result(
        self,
        name: str,
        confidence: float | None,
        precision: float,
        error: str = "",
    ):
        from PyQt6.QtGui import QColor
        item = self.roi_result_items.get(name)
        if item is None:
            return

        if confidence is None:
            item.setText(f"N/A ({error})" if error else "N/A")
            item.setForeground(QColor("#585b70"))
        elif confidence >= precision:
            item.setText(f"✓  {confidence:.1%}")
            item.setForeground(QColor("#a6e3a1"))
        else:
            item.setText(f"✗  {confidence:.1%}")
            item.setForeground(QColor("#f38ba8"))

    # ── ROI Capture ──────────────────────────────────────────────────────────
    def _set_all_roi_checks(self, checked: bool):
        for chk in self.roi_checkboxes.values():
            chk.setChecked(checked)

    def _capture_rois(self):
        import mss
        import cv2
        import numpy as np

        # Save into the external templates folder for the selected resolution
        width, height = self.resolution_combo.currentData()
        capture_dir = templates_user_dir(width, height)
        capture_dir.mkdir(parents=True, exist_ok=True)

        all_rois = self._current_rois()
        # Only capture ROIs whose checkbox is ticked
        rois = {
            name: roi for name, roi in all_rois.items()
            if self.roi_checkboxes.get(name, QCheckBox()).isChecked()
        }

        if not rois:
            self._capture_status_lbl.setText("No ROIs selected")
            self._capture_status_lbl.setStyleSheet("color: #f9e2af; font-size: 11px;")
            return

        mon_x  = self.mon_x_spin.value()
        mon_y  = self.mon_y_spin.value()
        saved, failed = [], []

        from src.fishbot.config.detection_config import DetectionConfig
        template_filenames = DetectionConfig().templates  # {key: filename}

        # Hide the ROI overlay so its borders don't appear in the captures,
        # then restore it afterwards.
        overlay_was_visible = bool(self.roi_overlay and self.roi_overlay.isVisible())
        if overlay_was_visible:
            self.roi_overlay.hide()
            QApplication.processEvents()  # flush the hide before grabbing

        with mss.mss() as sct:
            for name, (x, y, w, h) in rois.items():
                if w <= 0 or h <= 0:
                    failed.append(f"{name} (invalid size)")
                    continue
                region = {
                    "left":   mon_x + x,
                    "top":    mon_y + y,
                    "width":  w,
                    "height": h,
                }
                try:
                    img = np.array(sct.grab(region))
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    filename = template_filenames.get(name, f"{name}.png")
                    cv2.imwrite(str(capture_dir / filename), img)
                    saved.append(name)
                except Exception as e:
                    failed.append(f"{name} ({e})")

        # Update inline status label
        if saved:
            self._capture_status_lbl.setText(
                f"{len(saved)} saved → {capture_dir.name}/"
            )
            self._capture_status_lbl.setStyleSheet(
                "color: #a6e3a1; font-size: 11px;"
            )
        if failed:
            self._capture_status_lbl.setText(
                self._capture_status_lbl.text() +
                f"  {len(failed)} failed"
            )
            self._capture_status_lbl.setStyleSheet(
                "color: #f38ba8; font-size: 11px;"
            )

        # Also log details
        self._append_log(
            f"[CAPTURE] {len(saved)}/{len(rois)} selected ROIs saved to: {capture_dir}"
        )
        for name in failed:
            self._append_log(f"[CAPTURE] Failed: {name}")

        if overlay_was_visible:
            self._show_overlay_fullscreen()

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _set_status(self, text: str, color: str):
        self.status_dot.setText(text)
        self.status_dot.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
        )

    def closeEvent(self, event):
        keyboard.remove_hotkey("f7")
        keyboard.remove_hotkey("f8")
        keyboard.remove_hotkey("f9")
        if self.roi_overlay:
            self.roi_overlay.close()
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop_bot()
            self.bot_thread.wait(3000)
        event.accept()
