import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
)
from capture import capture_full_screen, capture_area
from selection_overlay import SelectionOverlay
from editor import EditorWindow


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot Capture & Annotation Utility")
        self.setFixedSize(320, 160)

        layout = QVBoxLayout()

        self.status_label = QLabel("Ready to capture.")
        layout.addWidget(self.status_label)

        full_screen_btn = QPushButton("📷 Capture Full Screen")
        full_screen_btn.clicked.connect(self.handle_full_screen_capture)
        layout.addWidget(full_screen_btn)

        area_btn = QPushButton("◻ Capture Area")
        area_btn.clicked.connect(self.handle_area_capture)
        layout.addWidget(area_btn)

        self.setLayout(layout)

        self.overlay = None
        self.editor = None

    def handle_full_screen_capture(self):
        self.hide()
        QApplication.processEvents()

        import time
        time.sleep(0.3)

        filepath = capture_full_screen()
        self.open_editor(filepath)

    def handle_area_capture(self):
        self.hide()
        QApplication.processEvents()

        import time
        time.sleep(0.2)

        self.overlay = SelectionOverlay()
        self.overlay.area_selected.connect(self.on_area_selected)
        self.overlay.destroyed.connect(self.show)
        self.overlay.showFullScreen()

    def on_area_selected(self, bbox):
        filepath = capture_area(bbox)
        self.open_editor(filepath)

    def open_editor(self, filepath):
        self.editor = EditorWindow(filepath)
        self.editor.show()
        self.status_label.setText(f"Saved: {filepath}")
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())