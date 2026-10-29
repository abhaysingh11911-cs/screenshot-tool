import json
import os
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QFrame, QSlider, QLabel, QScrollArea, QFileDialog, QMessageBox, QLineEdit,
    QApplication, QComboBox, QInputDialog, QButtonGroup, QShortcut
)
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from annotation_canvas import AnnotationCanvas
from ocr_engine import extract_text_with_positions
from ai_engine import get_actions
from capture import capture_full_screen, capture_area
from selection_overlay import SelectionOverlay
from settings_dialog import SettingsDialog
from database import log_capture, log_prompt, add_template, list_templates


TOOL_LABELS = {
    "pen": "✏  Pen",
    "arrow": "➚  Arrow",
    "rectangle": "▭  Rectangle",
    "circle": "◯  Circle",
    "text": "T  Text",
    "highlight": "▮  Highlight",
    "eraser": "🧹  Eraser",
    "blur": "◐  Blur",
    "number": "①  Number",
}

COLORS = [
    ("Red", "#ff0000"),
    ("Green", "#00aa00"),
    ("Teal", "#1fb5a8"),
    ("Blue", "#0064ff"),
    ("White", "#ffffff"),
    ("Yellow", "#ffd200"),
    ("Black", "#000000"),
]


def section_label(text):
    label = QLabel(text)
    label.setStyleSheet("color: #cfd2d8; font-size: 9pt; font-weight: bold;")
    return label


class TopButton(QPushButton):
    def __init__(self, icon_text, label, tip=""):
        super().__init__()
        self.setObjectName("TopButton")
        self.setFixedSize(76, 60)
        if tip:
            self.setToolTip(tip)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(0)
        icon = QLabel(icon_text)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 17pt; background: transparent;")
        text = QLabel(label)
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet("font-size: 8pt; color: #cfd2d8; background: transparent;")
        for w in (icon, text):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)


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
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.capture_id = None
        self.worker = None
        self.overlay = None
        self.last_prompt = ""
        self.setWindowTitle("AI-Powered Screenshot Capture & Annotation Utility")
        self.resize(1250, 800)

        self.canvas = AnnotationCanvas(None)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setAlignment(Qt.AlignCenter)
        scroll_area.setStyleSheet("QScrollArea { background: #141517; border-radius: 10px; }")
        scroll_area.viewport().setStyleSheet("background: #141517;")

        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(scroll_area, 1)
        right_layout.addWidget(self._build_prompt_bar())

        body = QHBoxLayout()
        body.addWidget(self._build_left_panel())
        body.addWidget(right_area, 1)

        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 6)
        main_layout.setSpacing(8)
        main_layout.addWidget(self._build_top_bar())
        main_layout.addLayout(body, 1)
        self.setCentralWidget(central)

        for seq, handler in (("Ctrl+Z", self.canvas.undo), ("Ctrl+Y", self.canvas.redo),
                             ("Ctrl+S", self.save_image), ("Ctrl+Shift+C", self.copy_to_clipboard)):
            QShortcut(QKeySequence(seq), self).activated.connect(handler)

        self.statusBar().showMessage("Ready. Click Capture or Area Select to begin.")

    # ---------- Top bar ----------
    def _build_top_bar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(4)

        def add(icon, label, handler, tip=""):
            button = TopButton(icon, label, tip)
            button.clicked.connect(handler)
            row.addWidget(button)

        def separator():
            line = QFrame()
            line.setFixedSize(1, 40)
            line.setStyleSheet("background: #3a3d44;")
            row.addWidget(line)

        add("📷", "Capture", self.do_full_capture, "Capture the full screen")
        add("✂", "Area Select", self.do_area_capture, "Capture a selected area")
        add("✨", "AI Edit", self.focus_prompt, "Jump to the AI prompt bar")
        separator()
        add("💾", "Save", self.save_image, "Save as image (Ctrl+S)")
        add("📋", "Copy", self.copy_to_clipboard, "Copy to clipboard (Ctrl+Shift+C)")
        row.addStretch()
        add("↶", "Undo", self.canvas.undo, "Undo (Ctrl+Z)")
        add("↷", "Redo", self.canvas.redo, "Redo (Ctrl+Y)")
        add("🗑", "Clear", self.clear_all, "Remove all annotations")
        add("⚙", "Settings", self.open_settings, "Settings")
        return bar

    # ---------- Left panel ----------
    def _build_left_panel(self):
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setFixedWidth(170)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(section_label("Tools"))
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        for key, label in TOOL_LABELS.items():
            btn = QPushButton(label)
            btn.setObjectName("ToolBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key, l=label: self.select_tool(k, l))
            self.tool_group.addButton(btn)
            layout.addWidget(btn)
            if key == "pen":
                btn.setChecked(True)

        layout.addSpacing(8)
        layout.addWidget(section_label("Color"))
        grid = QGridLayout()
        grid.setSpacing(8)
        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        for i, (name, hex_value) in enumerate(COLORS):
            swatch = QPushButton()
            swatch.setFixedSize(26, 26)
            swatch.setCheckable(True)
            swatch.setToolTip(name)
            swatch.setStyleSheet(
                f"QPushButton {{ background: {hex_value}; border: 2px solid #3a3d44;"
                f" border-radius: 13px; padding: 0; }}"
                f"QPushButton:checked {{ border: 3px solid #ffffff; }}")
            swatch.clicked.connect(lambda checked, c=hex_value: self.canvas.set_color(QColor(c)))
            self.color_group.addButton(swatch)
            grid.addWidget(swatch, i // 4, i % 4)
            if i == 0:
                swatch.setChecked(True)
        layout.addLayout(grid)

        layout.addSpacing(8)
        thickness_row = QHBoxLayout()
        thickness_row.addWidget(section_label("Thickness"))
        thickness_row.addStretch()
        self.thickness_value = QLabel("4px")
        thickness_row.addWidget(self.thickness_value)
        layout.addLayout(thickness_row)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(20)
        slider.setValue(4)
        slider.valueChanged.connect(self.change_thickness)
        layout.addWidget(slider)

        layout.addStretch()
        return panel

    def select_tool(self, key, label):
        self.canvas.set_tool(key)
        self.statusBar().showMessage("Tool: " + label.strip())

    def change_thickness(self, value):
        self.canvas.set_thickness(value)
        self.thickness_value.setText(f"{value}px")

    # ---------- Capture ----------
    def do_full_capture(self):
        self.hide()
        QApplication.processEvents()
        time.sleep(0.3)
        path = capture_full_screen()
        self.show()
        self.load_capture(path, "full")

    def do_area_capture(self):
        self.hide()
        QApplication.processEvents()
        time.sleep(0.2)
        self.overlay = SelectionOverlay()
        self.overlay.setAttribute(Qt.WA_DeleteOnClose)
        self.overlay.area_selected.connect(self.on_area_selected)
        self.overlay.destroyed.connect(self.show)
        self.overlay.showFullScreen()

    def on_area_selected(self, bbox):
        path = capture_area(bbox)
        self.load_capture(path, "area")

    def load_capture(self, path, capture_type):
        self.image_path = path
        self.canvas.load_image(path)
        pixmap = self.canvas.original_pixmap
        self.capture_id = log_capture(path, capture_type, pixmap.width(), pixmap.height())
        self.statusBar().showMessage(f"Captured: {path}")
        self.raise_()
        self.activateWindow()

    def has_image(self):
        if not self.image_path:
            QMessageBox.information(self, "No screenshot", "Capture a screenshot first.")
            return False
        return True

    def clear_all(self):
        if not self.has_image():
            return
        answer = QMessageBox.question(
            self, "Clear", "Remove all annotations? You can still press Undo.")
        if answer != QMessageBox.Yes:
            return
        self.canvas.base_pixmap = self.canvas.original_pixmap.copy()
        self.canvas.number_counter = 1
        self.canvas._push_undo_snapshot()
        self.canvas.update()

    # ---------- AI prompt bar ----------
    def _build_prompt_bar(self):
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)

        self.template_box = QComboBox()
        self.template_box.activated.connect(self.use_template)
        row.addWidget(self.template_box)
        self._refresh_templates()

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Tell the AI what to do, e.g. blur the email address")
        self.prompt_input.returnPressed.connect(self.run_ai_prompt)
        row.addWidget(self.prompt_input, 1)

        save_tpl_btn = QPushButton("★ Save template")
        save_tpl_btn.clicked.connect(self.save_template)
        row.addWidget(save_tpl_btn)

        self.ai_btn = QPushButton("✨ Apply AI")
        self.ai_btn.clicked.connect(self.run_ai_prompt)
        row.addWidget(self.ai_btn)

        self.ai_status = QLabel("")
        row.addWidget(self.ai_status)
        return bar

    def focus_prompt(self):
        self.prompt_input.setFocus()

    def _refresh_templates(self):
        self.template_box.clear()
        self.template_box.addItem("Templates...", "")
        for template_id, name, content in list_templates("prompt"):
            self.template_box.addItem(name, content)

    def use_template(self, index):
        content = self.template_box.itemData(index)
        if not content:
            return
        self.prompt_input.setText(content)
        self.prompt_input.setFocus()
        self.ai_status.setText("Template loaded. Press Apply AI to run it.")
        self.template_box.setCurrentIndex(0)

    def save_template(self):
        text = self.prompt_input.text().strip()
        if not text:
            QMessageBox.information(
                self, "Save template", "Type a prompt in the box first, then press Save template.")
            return
        name, ok = QInputDialog.getText(
            self, "Save template", "Template name:", QLineEdit.Normal, text[:30])
        if ok and name.strip():
            add_template(name.strip(), "prompt", text)
            self._refresh_templates()
            self.ai_status.setText(f"Template '{name.strip()}' saved.")

    def run_ai_prompt(self):
        prompt = self.prompt_input.text().strip()
        if not prompt or not self.has_image():
            return
        self.last_prompt = prompt
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
        log_prompt(self.capture_id, self.last_prompt, json.dumps(actions), "ok")
        if not actions:
            self.ai_status.setText("AI found nothing to change.")
            return
        self.canvas.apply_ai_actions(actions)
        self.ai_status.setText(f"Applied {len(actions)} edit(s). Use Undo to revert.")

    def on_ai_failed(self, message):
        self.ai_btn.setEnabled(True)
        log_prompt(self.capture_id, self.last_prompt, message, "error")
        self.ai_status.setText("AI failed. Manual tools still work.")
        QMessageBox.warning(self, "AI error", message)

    def open_settings(self):
        SettingsDialog(self).exec_()

    # ---------- Save / Copy ----------
    def save_image(self):
        if not self.has_image():
            return
        default_name = os.path.splitext(os.path.basename(self.image_path))[0] + "_edited.png"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotated Screenshot", default_name,
            "PNG Files (*.png);;JPEG Files (*.jpg)")
        if save_path:
            self.canvas.get_result_pixmap().save(save_path)
            QMessageBox.information(self, "Saved", f"Saved to:\n{save_path}")

    def copy_to_clipboard(self):
        if not self.has_image():
            return
        QApplication.clipboard().setPixmap(self.canvas.get_result_pixmap())
        QMessageBox.information(self, "Copied", "Annotated screenshot copied to clipboard!")