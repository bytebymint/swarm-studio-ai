from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QFileDialog,QFormLayout,
    QHBoxLayout,QLabel,QProgressBar,QPushButton,QVBoxLayout)

from app.recording import RecordingWorker


class RecordingDialog(QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio=studio
        self.project=studio.project
        self.viewport=studio.metadata['viewport'].copy()
        self.settings=studio.settings.values.copy()
        self.worker=None;self.pending_close=False;self.saved=None
        self.setWindowTitle('Cinematic recording')
        self.resize(490,380)
        layout=QVBoxLayout(self)
        description=QLabel('Follow the agents as they build. The camera eases into details, pulls back, and glides to the next section.')
        description.setWordWrap(True);layout.addWidget(description)
        form=QFormLayout()
        self.resolution=QComboBox();self.resolution.addItem('1080p · 1920 × 1080',(1920,1080));self.resolution.addItem('720p · 1280 × 720',(1280,720))
        self.fps=QComboBox();self.fps.addItem('60 fps · smoothest',60);self.fps.addItem('30 fps · faster export',30)
        self.zoom=QComboBox();self.zoom.addItem('Up to 3× · cinematic',3);self.zoom.addItem('Up to 2× · gentle',2);self.zoom.addItem('Wide view',1)
        self.speed=QComboBox()
        for speed in (.5,1,2,3,5):self.speed.addItem(f'{speed:g}×',speed)
        self.speed.setCurrentIndex(1)
        self.sound=QCheckBox('Include agent sounds');self.sound.setChecked(studio.audio.isChecked())
        for label,control in [('Video',self.resolution),('Frame rate',self.fps),('Camera zoom',self.zoom),('Build speed',self.speed),('',self.sound)]:form.addRow(label,control)
        layout.addLayout(form)
        self.message=QLabel('Exports only the canvas as an MP4. Each frame is rendered individually; export can take longer than playback.')
        self.message.setWordWrap(True);layout.addWidget(self.message)
        self.progress=QProgressBar();self.progress.setRange(0,100);layout.addWidget(self.progress)
        actions=QHBoxLayout()
        self.record=QPushButton('Save MP4…');self.record.setObjectName('primary');self.record.clicked.connect(self.choose)
        self.open=QPushButton('Play video');self.open.setEnabled(False);self.open.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.saved))))
        self.cancel=QPushButton('Close');self.cancel.clicked.connect(self.cancel_or_close)
        actions.addWidget(self.record);actions.addWidget(self.open);actions.addStretch();actions.addWidget(self.cancel);layout.addLayout(actions)

    def choose(self):
        destination,_=QFileDialog.getSaveFileName(self,'Save cinematic recording',str(Path.home()/'Videos'/'swarm-recording.mp4'),'MP4 video (*.mp4)')
        if destination:self.start(destination)

    def start(self,destination):
        if self.worker and self.worker.isRunning():return
        destination=Path(destination)
        if destination.suffix.lower()!='.mp4':destination=destination.with_suffix('.mp4')
        width,height=self.resolution.currentData()
        options=dict(output_width=width,output_height=height,fps=self.fps.currentData(),zoom=self.zoom.currentData(),speed=self.speed.currentData(),sound=self.sound.isChecked(),**self.viewport)
        project_url=self.studio.server.url(self.project.relative_to(self.studio.root).as_posix())+'/'
        self.worker=RecordingWorker(self.studio.server.url('ui/player.html'),project_url,destination,self.settings.copy(),options,self)
        self.studio.recording_worker=self.worker
        self.worker.progress.connect(self.update_progress)
        self.worker.ready.connect(self.complete)
        self.worker.error.connect(self.message.setText)
        self.worker.finished.connect(self.finished_render)
        for control in [self.record,self.open,self.resolution,self.fps,self.zoom,self.speed,self.sound]:control.setEnabled(False)
        self.progress.setValue(0);self.message.setText('Opening the local movie renderer…');self.cancel.setText('Cancel render')
        self.worker.start()

    def update_progress(self,value,message):
        self.progress.setValue(value);self.message.setText(message)

    def complete(self,path,result):
        self.saved=Path(path);self.message.setText(f'Saved {result["duration"]:.1f}s · {result["fps"]} fps · {result["width"]} × {result["height"]}\n{path}')
        self.studio.status('Cinematic recording saved: '+path)

    def finished_render(self):
        for control in [self.record,self.resolution,self.fps,self.zoom,self.speed,self.sound]:control.setEnabled(True)
        self.open.setEnabled(self.saved is not None);self.cancel.setEnabled(True);self.cancel.setText('Close')
        if self.pending_close:self.close()

    def cancel_or_close(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set();self.message.setText('Cancelling and cleaning up the partial movie…');self.cancel.setEnabled(False)
        else:self.close()

    def reject(self):self.close()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.pending_close=True;self.cancel_or_close();event.ignore()
        else:event.accept()
