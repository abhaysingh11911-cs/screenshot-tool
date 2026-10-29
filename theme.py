DARK_QSS = """
QWidget { background-color: #1f2023; color: #e6e6e6; font-size: 10pt; }
QMainWindow, QDialog { background-color: #1a1b1e; }
QLabel { background: transparent; }

QFrame#TopBar, QFrame#SidePanel { background: #25272b; border-radius: 10px; }

QPushButton#TopButton { background: transparent; border: none; border-radius: 8px; padding: 0; }
QPushButton#TopButton:hover { background: #34373d; }
QPushButton#TopButton:pressed { background: #2f6fed; }

QPushButton#ToolBtn { background: transparent; border: none; border-radius: 6px; padding: 7px 10px; text-align: left; }
QPushButton#ToolBtn:hover { background: #2d3036; }
QPushButton#ToolBtn:checked { background: #2f6fed; color: white; }

QPushButton { background: #2d3036; border: 1px solid #3a3d44; border-radius: 6px; padding: 7px 10px; text-align: left; }
QPushButton:hover { background: #3a3e46; }
QPushButton:pressed { background: #2f6fed; }
QPushButton:disabled { color: #777777; }

QLineEdit, QComboBox { background: #2a2c31; border: 1px solid #3a3d44; border-radius: 6px; padding: 6px; selection-background-color: #2f6fed; }
QComboBox QAbstractItemView { background: #2a2c31; selection-background-color: #2f6fed; }

QSlider::groove:horizontal { height: 6px; background: #3a3d44; border-radius: 3px; }
QSlider::handle:horizontal { background: #2f6fed; width: 14px; margin: -5px 0; border-radius: 7px; }

QScrollArea { border: none; }
QScrollBar:vertical { background: #1f2023; width: 12px; }
QScrollBar::handle:vertical { background: #3a3d44; border-radius: 6px; min-height: 24px; }
QScrollBar:horizontal { background: #1f2023; height: 12px; }
QScrollBar::handle:horizontal { background: #3a3d44; border-radius: 6px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

QStatusBar { background: #25272b; color: #9aa0a6; }
QToolTip { background: #2d3036; color: #e6e6e6; border: 1px solid #3a3d44; }
"""