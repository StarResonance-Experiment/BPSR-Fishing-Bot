import sys

from PyQt6.QtWidgets import QApplication
from src.fishbot.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BPSR Fishing Bot")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
