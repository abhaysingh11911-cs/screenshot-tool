from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from database import get_setting, set_setting


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Gemini API key"))
        self.key_input = QLineEdit(get_setting("api_key"))
        self.key_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.key_input)

        layout.addWidget(QLabel("Gemini model name"))
        self.model_input = QLineEdit(get_setting("model", "gemini-3.5-flash"))
        layout.addWidget(self.model_input)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

    def save(self):
        set_setting("api_key", self.key_input.text().strip())
        set_setting("model", self.model_input.text().strip())
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.accept()