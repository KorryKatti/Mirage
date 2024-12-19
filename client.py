import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window title and icon
        self.setWindowTitle("Mirage v0.0.2")
        self.setWindowIcon(QIcon("assets/img/icon.png"))

        # Main widget
        main_widget = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(main_widget)

        # Left column (20%)
        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #1f1d2e; color: #e0def4;")
        main_widget.addWidget(left_widget)

        # Right column (80%) with centered content
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: #191724; color: #e0def4;")
        main_widget.addWidget(right_widget)

        # Explicitly set initial sizes for the columns (20:80 ratio)
        main_widget.setSizes([200, 800])  # Adjust pixel sizes based on desired proportions

        # Center content in right column
        right_layout = QVBoxLayout(right_widget)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add title
        title_label = QLabel("Mirage")
        title_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #e0def4;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(title_label)

        # Add subtitle
        subtitle_label = QLabel("Your go-to chat app")
        subtitle_label.setStyleSheet("font-size: 18px; color: #9ccfd8;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(subtitle_label)

        # Add button linking to source code
        source_button = QPushButton("Source Code")
        source_button.setStyleSheet("""
            background-color: #9ccfd8;
            color: #191724;
            border: none;
            font-size: 16px;
            padding: 8px 16px;
            border-radius: 4px;
        """)
        source_button.clicked.connect(self.open_source_code)
        right_layout.addWidget(source_button)

    def open_source_code(self):
        # Open GitHub link in the default web browser
        QDesktopServices.openUrl(QUrl("https://github.com/korrykatti/mirage"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)  # Adjusted to match initial splitter sizes
    window.show()
    sys.exit(app.exec())
