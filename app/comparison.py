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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#111318'))
        if not self.original:
            painter.setPen(QColor('#c5cbd5'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Capture a page and run comparison to inspect differences.')
            return
        def draw(pixmap, target):
            size = pixmap.size().scaled(target.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
            rect = QRectF(target.x() + (target.width()-size.width())/2, target.y(), size.width(), size.height())
            painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
            return rect
        full = QRectF(0, 0, self.width(), self.height())
        if self.mode == 'Side by side':
            draw(self.original, QRectF(0, 25, self.width()/2-5, self.height()-25))
            draw(self.clone, QRectF(self.width()/2+5, 25, self.width()/2-5, self.height()-25))
            painter.setPen(QColor('#c5cbd5'))
            painter.drawText(10, 17, 'Original')
            painter.drawText(self.width()//2+15, 17, 'Reconstruction')
        elif self.mode == 'Difference heatmap':
            if self.diff:
                draw(self.diff, full)
        elif self.mode == 'Original':
            draw(self.original, full)
        elif self.mode == 'Reconstruction':
            draw(self.clone, full)
        else:
            draw(self.clone, full)
            painter.save()
            painter.setClipRect(QRectF(0,0,self.width()*self.split,self.height()))
            draw(self.original, full)
            painter.restore()
            painter.setPen(QPen(QColor('#60acff'), 2))
            painter.drawLine(int(self.width()*self.split),0,int(self.width()*self.split),self.height())


class ComparisonPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(['Before / after slider', 'Side by side', 'Original', 'Reconstruction', 'Difference heatmap'])
        self.mode.setAccessibleName('Comparison mode')
        self.label = QLabel('Same-viewport screenshot comparison')
        top.addWidget(self.mode)
        top.addWidget(self.label, 1)
        layout.addLayout(top)
        self.canvas = ComparisonCanvas()
        layout.addWidget(self.canvas, 1)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0,100)
        self.slider.setValue(50)
        self.slider.setAccessibleName('Before and after split position')
        layout.addWidget(self.slider)
        self.mode.currentTextChanged.connect(self.change_mode)
        self.slider.valueChanged.connect(self.change_split)

    def change_mode(self, text):
        self.canvas.mode = text
        self.slider.setEnabled(text == 'Before / after slider')
        self.canvas.update()
