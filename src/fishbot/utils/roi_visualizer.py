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

    # ── Paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

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

        self._draw_log_overlay(painter)

    def _draw_log_overlay(self, painter: QPainter):
        if not self._log_lines and not self._status:
            return

        font_status = QFont("Consolas", 11, QFont.Weight.Bold)
        font_log    = QFont("Consolas", 10, QFont.Weight.Normal)
        fm_status   = QFontMetrics(font_status)
        fm_log      = QFontMetrics(font_log)

        line_h     = fm_log.height() + 4
        pad        = 8
        margin     = 12
        is_stopped = bool(self._status and "Running" not in self._status)
        hint_font  = QFont("Consolas", 9, QFont.Weight.Normal)
        fm_hint    = QFontMetrics(hint_font)

        all_widths = [fm_log.horizontalAdvance(l) for l in self._log_lines]
        if self._status:
            all_widths.append(fm_status.horizontalAdvance(self._status))
        if is_stopped:
            all_widths += [
                fm_hint.horizontalAdvance("Approach a fishing spot until the interact prompt appears,"),
                fm_hint.horizontalAdvance("or open the fishing UI, then press F7 to start."),
            ]
        box_w = max(all_widths) + pad * 2

        status_h = (fm_status.height() + 6) if self._status else 0
        hint_h   = (fm_hint.height() + 3) * 2 + 4 if is_stopped else 0
        box_h    = status_h + hint_h + len(self._log_lines) * line_h + pad * 2

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

        # Log lines
        painter.setFont(font_log)
        painter.setPen(QPen(QColor(220, 220, 220, 230)))
        for line in self._log_lines:
            y += fm_log.ascent()
            painter.drawText(margin + pad, y, line)
            y += fm_log.descent() + 4

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