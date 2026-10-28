from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QToolBar, QAction, QActionGroup, QSlider, QLabel, QScrollArea,
    QFileDialog, QMessageBox, QLineEdit, QApplication, QDockWidget
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from annotation_canvas import AnnotationCanvas
from ocr_engine import extract_text_with_positions
from ai_engine import get_actions
import os


TOOL_LABELS = {
    "pen": "✏ Pen",
    "arrow": "➚ Arrow",
    "rectangle": "▭ Rectangle",
    "circle": "◯ Circle",
    "text": "T Text",
    "highlight": "▮ Highlight",
    "eraser": "🧹 Eraser",
    "blur": "◐ Blur",
    "number": "① Number",
}

COLOR_OPTIONS = [
    ("Red", QColor(255, 0, 0)),
    ("Green", QColor(0, 170, 0)),
    ("Blue", QColor(0, 100, 255)),
    ("Black", QColor(0, 0, 0)),
    ("White", QColor(255, 255, 255)),
    ("Yellow", QColor(255, 210, 0)),
]


class AIWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, prompt, image_path, width, height):
        super().__init__()
        self.prompt = prompt
        self.image_path = image_path
        self.width = width
        self.height = height

    def run(self):
        try:
            ocr_items = extract_text_with_positions(self.image_path)
            actions = get_actions(self.prompt, ocr_items, self.width, self.height)
            self.done.emit(actions)
        except Exception as e:
            self.failed.emit(str(e))


class EditorWindow(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.worker = None
        self.setWindowTitle("Editor - Screenshot Capture & Annotation Utility")
        self.resize(1100, 750)

        self.canvas = AnnotationCanvas(image_path)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setAlignment(Qt.AlignCenter)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(scroll_area)
        layout.addWidget(self._build_prompt_bar())
        self.setCentralWidget(central)

        self._build_toolbar()

    # ---------- AI prompt bar ----------
    def _build_prompt_bar(self):
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Tell the AI what to do, e.g. blur the email address")
        self.prompt_input.returnPressed.connect(self.run_ai_prompt)
        row.addWidget(self.prompt_input)

        self.ai_btn = QPushButton("✨ Apply AI")
        self.ai_btn.clicked.connect(self.run_ai_prompt)
        row.addWidget(self.ai_btn)

        self.ai_status = QLabel("")
        row.addWidget(self.ai_status)
        return bar

    def run_ai_prompt(self):
        prompt = self.prompt_input.text().strip()
        if not prompt:
            return
        self.ai_btn.setEnabled(False)
        self.ai_status.setText("AI is working...")

        width = self.canvas.original_pixmap.width()
        height = self.canvas.original_pixmap.height()
        self.worker = AIWorker(prompt, self.image_path, width, height)
        self.worker.done.connect(self.on_ai_done)
        self.worker.failed.connect(self.on_ai_failed)
        self.worker.start()

    def on_ai_done(self, actions):
        self.ai_btn.setEnabled(True)
        if not actions:
            self.ai_status.setText("AI found nothing to change.")
            return
        self.canvas.apply_ai_actions(actions)
        self.ai_status.setText(f"Applied {len(actions)} edit(s). Use Undo to revert.")

    def on_ai_failed(self, message):
        self.ai_btn.setEnabled(True)
        self.ai_status.setText("AI failed. Manual tools still work.")
        QMessageBox.warning(self, "AI error", message)

    # ---------- Toolbar ----------
    def _build_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        toolbar.setOrientation(Qt.Vertical)

        tool_group = QActionGroup(self)
        tool_group.setExclusive(True)

        for tool_key, label in TOOL_LABELS.items():
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=tool_key: self.canvas.set_tool(t))
            tool_group.addAction(action)
            toolbar.addAction(action)
            if tool_key == "pen":
                action.setChecked(True)

        toolbar.addSeparator()

        for name, color in COLOR_OPTIONS:
            color_btn = QAction(name, self)
            color_btn.triggered.connect(lambda checked, c=color: self.canvas.set_color(c))
            toolbar.addAction(color_btn)

        side_panel = QWidget()
        side_layout = QVBoxLayout()

        side_layout.addWidget(QLabel("Thickness"))
        thickness_slider = QSlider(Qt.Horizontal)
        thickness_slider.setMinimum(1)
        thickness_slider.setMaximum(20)
        thickness_slider.setValue(4)
        thickness_slider.valueChanged.connect(self.canvas.set_thickness)
        side_layout.addWidget(thickness_slider)

        undo_btn = QPushButton("↶ Undo")
        undo_btn.clicked.connect(self.canvas.undo)
        side_layout.addWidget(undo_btn)

        redo_btn = QPushButton("↷ Redo")
        redo_btn.clicked.connect(self.canvas.redo)
        side_layout.addWidget(redo_btn)

        save_btn = QPushButton("💾 Save As...")
        save_btn.clicked.connect(self.save_image)
        side_layout.addWidget(save_btn)

        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        side_layout.addWidget(copy_btn)

        side_layout.addStretch()
        side_panel.setLayout(side_layout)
        side_panel.setFixedWidth(150)

        dock = QDockWidget("Options", self)
        dock.setWidget(side_panel)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    # ---------- Save / Copy ----------
    def save_image(self):
        default_name = os.path.splitext(os.path.basename(self.image_path))[0] + "_edited.png"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotated Screenshot", default_name,
            "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        if save_path:
            self.canvas.get_result_pixmap().save(save_path)
            QMessageBox.information(self, "Saved", f"Saved to:\n{save_path}")

    def copy_to_clipboard(self):
        QApplication.clipboard().setPixmap(self.canvas.get_result_pixmap())
        QMessageBox.information(self, "Copied", "Annotated screenshot copied to clipboard!")