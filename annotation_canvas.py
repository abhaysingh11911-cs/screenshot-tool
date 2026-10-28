from PyQt5.QtWidgets import QWidget, QInputDialog
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QFont, QPolygon
from PyQt5.QtCore import Qt, QPoint, QRect
from PIL import Image, ImageFilter
from PyQt5.QtCore import QBuffer, QByteArray
import io


def qpixmap_to_pil(pixmap):
    qimage = pixmap.toImage()
    buffer = io.BytesIO()
    qimage.save_buffer = None
    from PyQt5.QtCore import QBuffer
    qbuffer = QBuffer()
    qbuffer.open(QBuffer.ReadWrite)
    qimage.save(qbuffer, "PNG")
    pil_image = Image.open(io.BytesIO(qbuffer.data()))
    return pil_image.convert("RGB")


def pil_to_qpixmap(pil_image):
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    qpixmap = QPixmap()
    qpixmap.loadFromData(buffer.getvalue())
    return qpixmap


class AnnotationCanvas(QWidget):
    TOOLS = ["pen", "arrow", "rectangle", "circle", "text",
             "highlight", "eraser", "blur", "number"]

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.original_pixmap = QPixmap(image_path)
        self.base_pixmap = self.original_pixmap.copy()  # what's actually "saved"

        self.setFixedSize(self.base_pixmap.size())

        self.current_tool = "pen"
        self.pen_color = QColor(255, 0, 0)  # default red
        self.thickness = 4

        self.drawing = False
        self.start_pos = QPoint()
        self.last_pos = QPoint()
        self.current_pos = QPoint()

        self.number_counter = 1

        # Undo/redo history (list of pixmap snapshots)
        self.undo_stack = [self.base_pixmap.copy()]
        self.redo_stack = []

    # ---------- Tool/color/thickness setters (called from toolbar) ----------
    def set_tool(self, tool_name):
        self.current_tool = tool_name

    def set_color(self, qcolor):
        self.pen_color = qcolor

    def set_thickness(self, value):
        self.thickness = value

    # ---------- Painting ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.base_pixmap)

        # Draw a live preview for shape tools while dragging
        if self.drawing and self.current_tool in ("arrow", "rectangle", "circle", "blur"):
            pen = QPen(self.pen_color, self.thickness)
            painter.setPen(pen)
            if self.current_tool == "rectangle" or self.current_tool == "blur":
                rect = QRect(self.start_pos, self.current_pos).normalized()
                painter.drawRect(rect)
            elif self.current_tool == "circle":
                rect = QRect(self.start_pos, self.current_pos).normalized()
                painter.drawEllipse(rect)
            elif self.current_tool == "arrow":
                self._draw_arrow(painter, self.start_pos, self.current_pos)

    # ---------- Mouse events ----------
    def mousePressEvent(self, event):
        self.start_pos = event.pos()
        self.last_pos = event.pos()
        self.current_pos = event.pos()
        self.drawing = True

        if self.current_tool == "text":
            self._handle_text_click(event.pos())
            self.drawing = False
        elif self.current_tool == "number":
            self._handle_number_click(event.pos())
            self.drawing = False

    def mouseMoveEvent(self, event):
        if not self.drawing:
            return

        self.current_pos = event.pos()

        if self.current_tool in ("pen", "highlight", "eraser"):
            self._draw_freehand_segment(self.last_pos, event.pos())
            self.last_pos = event.pos()

        self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing:
            return
        self.drawing = False
        self.current_pos = event.pos()

        if self.current_tool == "rectangle":
            self._commit_rectangle(self.start_pos, event.pos())
        elif self.current_tool == "circle":
            self._commit_circle(self.start_pos, event.pos())
        elif self.current_tool == "arrow":
            self._commit_arrow(self.start_pos, event.pos())
        elif self.current_tool == "blur":
            self._commit_blur(self.start_pos, event.pos())
        elif self.current_tool in ("pen", "highlight", "eraser"):
            self._push_undo_snapshot()  # freehand already drawn live; just checkpoint it

        self.update()

    # ---------- Tool implementations ----------
    def _draw_freehand_segment(self, p1, p2):
        painter = QPainter(self.base_pixmap)
        if self.current_tool == "pen":
            pen = QPen(self.pen_color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif self.current_tool == "highlight":
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            color = QColor(self.pen_color)
            color.setAlpha(180)
            pen = QPen(color, max(self.thickness * 3, 12), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif self.current_tool == "eraser":
            # "Erase" by restoring the original screenshot pixels in this area
            eraser_size = max(self.thickness * 3, 16)
            rect = QRect(p2.x() - eraser_size // 2, p2.y() - eraser_size // 2,
                         eraser_size, eraser_size)
            painter.drawPixmap(rect, self.original_pixmap, rect)
        painter.end()

    def _commit_rectangle(self, p1, p2):
        painter = QPainter(self.base_pixmap)
        pen = QPen(self.pen_color, self.thickness)
        painter.setPen(pen)
        painter.drawRect(QRect(p1, p2).normalized())
        painter.end()
        self._push_undo_snapshot()

    def _commit_circle(self, p1, p2):
        painter = QPainter(self.base_pixmap)
        pen = QPen(self.pen_color, self.thickness)
        painter.setPen(pen)
        painter.drawEllipse(QRect(p1, p2).normalized())
        painter.end()
        self._push_undo_snapshot()

    def _draw_arrow(self, painter, p1, p2):
        pen = QPen(self.pen_color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(self.pen_color)
        painter.drawLine(p1, p2)

        # Arrowhead
        import math
        angle = math.atan2(p1.y() - p2.y(), p1.x() - p2.x())
        arrow_size = 12 + self.thickness

        p3 = QPoint(
            int(p2.x() + arrow_size * math.cos(angle + math.pi / 6)),
            int(p2.y() + arrow_size * math.sin(angle + math.pi / 6)),
        )
        p4 = QPoint(
            int(p2.x() + arrow_size * math.cos(angle - math.pi / 6)),
            int(p2.y() + arrow_size * math.sin(angle - math.pi / 6)),
        )
        painter.drawPolygon(QPolygon([p2, p3, p4]))

    def _commit_arrow(self, p1, p2):
        painter = QPainter(self.base_pixmap)
        self._draw_arrow(painter, p1, p2)
        painter.end()
        self._push_undo_snapshot()

    def _commit_blur(self, p1, p2):
        rect = QRect(p1, p2).normalized()
        if rect.width() < 4 or rect.height() < 4:
            return

        pil_image = qpixmap_to_pil(self.base_pixmap)
        region = pil_image.crop((rect.left(), rect.top(), rect.right(), rect.bottom()))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=12))
        pil_image.paste(blurred, (rect.left(), rect.top()))

        self.base_pixmap = pil_to_qpixmap(pil_image)
        self._push_undo_snapshot()

    def _handle_text_click(self, pos):
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text:
            painter = QPainter(self.base_pixmap)
            painter.setPen(QPen(self.pen_color))
            font = QFont("Arial", 14 + self.thickness)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_pos = QPoint(pos.x(), pos.y() + metrics.ascent())
            painter.drawText(text_pos, text)
            painter.end()
            self._push_undo_snapshot()
            self.update()    

    def _handle_number_click(self, pos):
        painter = QPainter(self.base_pixmap)
        radius = 14
        painter.setBrush(self.pen_color)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(pos, radius, radius)

        painter.setPen(QPen(Qt.white))
        font = QFont("Arial", 12)
        font.setBold(True)
        painter.setFont(font)
        text_rect = QRect(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
        painter.drawText(text_rect, Qt.AlignCenter, str(self.number_counter))
        painter.end()

        self.number_counter += 1
        self._push_undo_snapshot()
        self.update()
    def apply_ai_actions(self, actions):
        colors = {
            "red": QColor(255, 0, 0), "green": QColor(0, 170, 0),
            "blue": QColor(0, 100, 255), "yellow": QColor(255, 210, 0),
            "black": QColor(0, 0, 0), "white": QColor(255, 255, 255),
        }
        original_color = self.pen_color

        for a in actions:
            x, y, w, h = a["x"], a["y"], a["w"], a["h"]
            p1, p2 = QPoint(x, y), QPoint(x + w, y + h)
            self.pen_color = colors.get(a["color"], original_color)
            tool = a["tool"]

            if tool == "blur":
                self._commit_blur(p1, p2)
            elif tool == "rectangle":
                self._commit_rectangle(p1, p2)
            elif tool == "circle":
                self._commit_circle(p1, p2)
            elif tool == "highlight":
                painter = QPainter(self.base_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                color = QColor(self.pen_color)
                color.setAlpha(180)
                painter.fillRect(QRect(p1, p2).normalized(), color)
                painter.end()
                self._push_undo_snapshot()
            elif tool == "arrow":
                start = QPoint(max(x - 90, 0), max(y - 60, 0))
                painter = QPainter(self.base_pixmap)
                self._draw_arrow(painter, start, p1)
                painter.end()
                self._push_undo_snapshot()
            elif tool == "text":
                painter = QPainter(self.base_pixmap)
                painter.setPen(QPen(self.pen_color))
                font = QFont("Arial", 14 + self.thickness)
                painter.setFont(font)
                ascent = painter.fontMetrics().ascent()
                painter.drawText(QPoint(x, y + h + ascent + 2), a["text"])
                painter.end()
                self._push_undo_snapshot()
            elif tool == "number":
                self._handle_number_click(QPoint(x, y))

        self.pen_color = original_color
        self.update()
    # ---------- Undo / Redo ----------
    def _push_undo_snapshot(self):
        self.undo_stack.append(self.base_pixmap.copy())
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.base_pixmap = self.undo_stack[-1].copy()
            self.update()

    def redo(self):
        if self.redo_stack:
            pixmap = self.redo_stack.pop()
            self.undo_stack.append(pixmap.copy())
            self.base_pixmap = pixmap.copy()
            self.update()

    def get_result_pixmap(self):
        return self.base_pixmap