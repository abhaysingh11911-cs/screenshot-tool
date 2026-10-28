from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen


class SelectionOverlay(QWidget):
    # Emits (left, top, width, height) once the user finishes dragging
    area_selected = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        # Cover the entire virtual screen (all monitors combined)
        screen_geometry = QApplication.desktop().geometry()
        self.setGeometry(screen_geometry)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selecting = False

    def paintEvent(self, event):
        painter = QPainter(self)
        # Dim the whole screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.selecting:
            rect = QRect(self.start_point, self.end_point).normalized()
            # Clear the selected area so it looks "cut out"
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)

            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 150, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.start_point = event.pos()
        self.end_point = event.pos()
        self.selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.selecting = False
        rect = QRect(self.start_point, self.end_point).normalized()

        if rect.width() > 5 and rect.height() > 5:  # ignore accidental tiny clicks
            bbox = (rect.left(), rect.top(), rect.width(), rect.height())
            self.area_selected.emit(bbox)

        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()