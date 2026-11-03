from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget


class ComparisonCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.original = self.clone = self.diff = None
        self.mode = 'Before / after slider'
        self.split = .5
        self.setMinimumSize(300, 250)
        self.setAccessibleName('Website screenshot comparison')
