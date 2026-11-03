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

    def record_event(self, data):
        if data['type'] == 'assigned':
            self.agents[data['agent']] = data['name']
            self.setMinimumHeight(max(95, 26 + len(self.agents) * 15))
            self.active[data['task']] = (data['agent'], self.time)
        if data['type'] == 'completed' and data['task'] in self.active:
            agent, started = self.active.pop(data['task'])
            self.events.append((agent, started, max(self.time, started + .15)))
        if data['type'] == 'progress':
            if data['time'] < self.time:
                self.events = [e for e in self.events if e[2] <= data['time']]
                self.active.clear()
            self.time = data['time']
        self.update()
