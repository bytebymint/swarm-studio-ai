from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.blueprint import COLORS, NAMES


class Timeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(95)
        self.setAccessibleName('Agent activity timeline')
        self.events = []
        self.time = 0
        self.active = {}
        self.agents = {}

    def reset(self):
        self.events.clear()
        self.active.clear()
        self.agents.clear()
        self.time = 0
        self.update()
