import sys
from PyQt5.QtWidgets import QApplication
from editor import EditorWindow
from database import init_db
from theme import DARK_QSS


if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec_())