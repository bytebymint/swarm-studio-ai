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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#191c22'))
        width = self.width() - 95
        extent = max(30, self.time + 10)
        scale = width / extent
        painter.setPen(QColor('#a6afbd'))
        tracks = sorted(self.agents)
        row_by_agent = {agent: row for row, agent in enumerate(tracks)}
        for i, agent in enumerate(tracks):
            name = self.agents[agent]
            painter.drawText(10, 35 + i * 15, name)
            painter.setPen(QColor('#2b313a'))
            painter.drawLine(85, 30 + i * 15, self.width() - 5, 30 + i * 15)
            painter.setPen(QColor('#a6afbd'))
        for sec in range(0, int(extent), 5):
            x = int(85 + sec * scale)
            painter.drawText(x, 14, f'{sec}s')
        for agent, start, end in self.events + [(a, s, self.time) for a, s in self.active.values()]:
            painter.fillRect(QRectF(85 + start * scale, 24 + row_by_agent.get(agent, 0) * 15, max(3, (end-start)*scale), 10), QColor(COLORS[agent % len(COLORS)]))
        painter.setPen(QPen(QColor('#d9e4f5'), 1))
        x = int(85 + self.time * scale)
        painter.drawLine(x, 19, x, self.height())
