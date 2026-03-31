import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRect

from src.fishbot.config.detection_config import DetectionConfig

_ROI_COLORS = [
    QColor(255,   0,   0, 180),
    QColor(  0, 255,   0, 180),
    QColor(  0, 120, 255, 180),
    QColor(255, 220,   0, 180),
    QColor(255,   0, 220, 180),
    QColor(  0, 255, 220, 180),
]


class RoiVisualizer(QWidget):
    """Fullscreen transparent overlay that draws ROI rectangles.

    Can be used standalone (loads DetectionConfig itself) or embedded inside
    the GUI app by passing a ``rois`` dict and calling ``update_rois()`` to
    push live changes.
    """

    def __init__(self, rois: dict | None = None):
        super().__init__()
        # If rois are provided externally, use them; otherwise load from config.
        self._rois: dict                = rois if rois is not None else DetectionConfig().rois
        self._confidences: dict[str, float] = {}
        self._precision: float          = 0.60
        self._log_lines: list[str]      = []
        self._status: str               = ""
        self._resolution: str           = ""
        self._stats: dict               = {}
        self._show_status: bool         = True
        self._show_rois: bool           = True

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── Public API ───────────────────────────────────────────────────────────
    def update_rois(self, rois: dict):
        """Replace current ROIs and immediately repaint."""
        self._rois = rois
        self.update()

    def update_confidences(self, confidences: dict[str, float], precision: float = 0.60):
        """Push latest detection confidences and repaint."""
        self._confidences = confidences
        self._precision   = precision
        self.update()

    def update_log_lines(self, lines: list[str]):
        """Replace the log overlay lines and repaint."""
        self._log_lines = lines
        self.update()

    def update_status(self, status: str):
        """Set the bot status string shown in the overlay."""
        self._status = status
        self.update()

    def update_resolution(self, resolution: str):
        """Set the resolution string shown in the overlay."""
        self._resolution = resolution
        self.update()

    def update_stats(self, stats: dict):
        """Push latest bot statistics and repaint."""
        self._stats = stats
        self.update()

    def toggle_rois(self):
        """Show/hide the ROI boxes without affecting the status/log panel."""
        self._show_rois = not self._show_rois
        self.update()

    def toggle_status_overlay(self):
        """Show/hide the top-left status/log panel without affecting ROI boxes."""
        self._show_status = not self._show_status
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._show_rois:
            if self._show_status:
                self._draw_log_overlay(painter)
            return

        for idx, (name, roi) in enumerate(self._rois.items()):
            if not roi:
                continue
            x, y, w, h = roi
            color = _ROI_COLORS[idx % len(_ROI_COLORS)]

            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(x, y, w, h)

            # Template name
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.setPen(QPen(color))
            painter.drawText(x + 5, y + 15, name)

            # Confidence (only shown while bot is running)
            confidence = self._confidences.get(name)
            if confidence is not None:
                is_match   = confidence >= self._precision
                conf_color = QColor(166, 227, 161, 230) if is_match else QColor(243, 139, 168, 230)
                marker     = "✓" if is_match else "✗"
                painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                painter.setPen(QPen(conf_color))
                painter.drawText(x + 5, y + 30, f"{marker} {confidence:.1%}")

        if self._show_status:
            self._draw_log_overlay(painter)

    _HOTKEY_LINES = [
        "F7: Start      F8: Stop",
        "F9: ROI Boxes  F10: Status Overlay",
    ]

    def _draw_log_overlay(self, painter: QPainter):
        if not self._log_lines and not self._status and not self._resolution:
            return

        font_status  = QFont("Consolas", 11, QFont.Weight.Bold)
        font_log     = QFont("Consolas", 10, QFont.Weight.Normal)
        fm_status    = QFontMetrics(font_status)
        fm_log       = QFontMetrics(font_log)

        line_h      = fm_log.height() + 4
        pad         = 8
        margin      = 12
        is_stopped  = bool(self._status and "Running" not in self._status)
        hint_font   = QFont("Consolas", 9, QFont.Weight.Normal)
        fm_hint     = QFontMetrics(hint_font)
        hotkey_font = QFont("Consolas", 9, QFont.Weight.Normal)
        fm_hotkey   = QFontMetrics(hotkey_font)

        font_res   = QFont("Consolas", 9, QFont.Weight.Normal)
        fm_res     = QFontMetrics(font_res)
        font_stats = QFont("Consolas", 10, QFont.Weight.Normal)
        fm_stats   = QFontMetrics(font_stats)

        _STAT_PAIRS = [
            [("Cycles", "cycles"),      ("Fish Caught", "fish_caught")],
            [("Rod Breaks", "rod_breaks"), ("Timeouts", "timeouts")],
        ]
        stat_lines = [
            "  ".join(f"{label}: {self._stats.get(key, 0)}" for label, key in pair)
            for pair in _STAT_PAIRS
        ]

        all_widths = [fm_log.horizontalAdvance(l) for l in self._log_lines]
        if self._status:
            all_widths.append(fm_status.horizontalAdvance(self._status))
        if self._resolution:
            all_widths.append(fm_res.horizontalAdvance(f"Resolution: {self._resolution}"))
        all_widths += [fm_stats.horizontalAdvance(l) for l in stat_lines]
        if is_stopped:
            all_widths += [
                fm_hint.horizontalAdvance("Approach a fishing spot until the interact prompt appears,"),
                fm_hint.horizontalAdvance("or open the fishing UI, then press F7 to start."),
            ]
        all_widths += [fm_hotkey.horizontalAdvance(l) for l in self._HOTKEY_LINES]
        box_w = max(all_widths) + pad * 2

        res_h    = (fm_res.height()   + 3) if self._resolution else 0
        status_h = (fm_status.height() + 6) if self._status else 0
        stats_h  = (fm_stats.height() + 3) * len(_STAT_PAIRS) + 8  # 8 = top divider gap
        hint_h   = (fm_hint.height()  + 3) * 2 + 4 if is_stopped else 0
        hotkey_h = (fm_hotkey.height() + 3) * len(self._HOTKEY_LINES) + 8
        box_h    = status_h + res_h + stats_h + hint_h + len(self._log_lines) * line_h + hotkey_h + pad * 2

        # Semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 170))
        painter.drawRoundedRect(QRect(margin, margin, box_w, box_h), 6, 6)

        y = margin + pad

        # Status line
        if self._status:
            painter.setFont(font_status)
            is_running   = "Running" in self._status
            status_color = QColor(166, 227, 161, 255) if is_running else QColor(243, 139, 168, 255)
            painter.setPen(QPen(status_color))
            y += fm_status.ascent()
            painter.drawText(margin + pad, y, self._status)
            y += fm_status.descent() + 6

            # Resolution line
            if self._resolution:
                painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
                fm_res_bold = QFontMetrics(painter.font())
                label_text  = "Resolution: "
                value_text  = self._resolution
                # Draw label in grey, value in yellow
                painter.setPen(QPen(QColor(150, 150, 150, 220)))
                y += fm_res.ascent()
                painter.drawText(margin + pad, y, label_text)
                label_w = fm_res_bold.horizontalAdvance(label_text)
                painter.setPen(QPen(QColor(249, 226, 175, 255)))
                painter.drawText(margin + pad + label_w, y, value_text)
                y += fm_res.descent() + 3

            # Hint text (when stopped) — above statistics
            if not is_running:
                painter.setFont(hint_font)
                painter.setPen(QPen(QColor(180, 180, 180, 200)))
                for hint in [
                    "Approach a fishing spot until the interact prompt appears,",
                    "or open the fishing UI, then press F7 to start.",
                ]:
                    y += fm_hint.ascent()
                    painter.drawText(margin + pad, y, hint)
                    y += fm_hint.descent() + 3
                y += 4

            # Stats block
            y += 4
            painter.setPen(QPen(QColor(100, 100, 100, 180), 1))
            painter.drawLine(margin + pad, y, margin + box_w - pad, y)
            y += 4
            painter.setFont(font_stats)
            col_gap = fm_stats.horizontalAdvance("    ")
            # Pre-compute per-column label width (max across all rows)
            num_cols = max(len(pair) for pair in _STAT_PAIRS)
            col_label_w = [
                max(fm_stats.horizontalAdvance(f"{pair[c][0]}: ")
                    for pair in _STAT_PAIRS if c < len(pair))
                for c in range(num_cols)
            ]
            # Fixed value column width = 4 digits
            digit_w     = fm_stats.horizontalAdvance("0")
            col_value_w = [digit_w * 4] * num_cols
            col_w = [col_label_w[c] + col_value_w[c] for c in range(num_cols)]

            for pair in _STAT_PAIRS:
                x_off = margin + pad
                y += fm_stats.ascent()
                for c, (label, key) in enumerate(pair):
                    value      = str(self._stats.get(key, 0))
                    label_text = f"{label}: "
                    painter.setPen(QPen(QColor(150, 150, 150, 220)))
                    painter.drawText(x_off, y, label_text)
                    # Value right-aligned within fixed 4-digit column
                    painter.setPen(QPen(QColor(166, 227, 161, 255)))
                    value_x = x_off + col_label_w[c] + col_value_w[c] - fm_stats.horizontalAdvance(value)
                    painter.drawText(value_x, y, value)
                    x_off += col_w[c] + col_gap
                y += fm_stats.descent() + 3

        # Log lines
        painter.setFont(font_log)
        painter.setPen(QPen(QColor(220, 220, 220, 230)))
        for line in self._log_lines:
            y += fm_log.ascent()
            painter.drawText(margin + pad, y, line)
            y += fm_log.descent() + 4

        # Divider
        y += 4
        painter.setPen(QPen(QColor(100, 100, 100, 180), 1))
        painter.drawLine(margin + pad, y, margin + box_w - pad, y)
        y += 4

        # Hotkey hints
        painter.setFont(hotkey_font)
        painter.setPen(QPen(QColor(130, 130, 130, 200)))
        for line in self._HOTKEY_LINES:
            y += fm_hotkey.ascent()
            painter.drawText(margin + pad, y, line)
            y += fm_hotkey.descent() + 3

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# ── Standalone entry point (used by the original hotkey '9' flow) ────────────
def main():
    print("Starting ROI visualizer (PyQt)...")
    print("Press the 'Esc' key to close the window.")
    app = QApplication(sys.argv)
    visualizer = RoiVisualizer()
    visualizer.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()