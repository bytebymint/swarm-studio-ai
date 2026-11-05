import json
import logging
import shutil
import re
from pathlib import Path
from urllib.parse import urlsplit, urldefrag

from PySide6.QtCore import QEvent, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTabBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from app.blueprint import COLORS, NAMES, ROLES
from app.browser import BrowserController, make_player
from app.comparison import ComparisonPanel
from app.config import Settings, WEB
from app.projects import ProjectStore
from app.server import PreviewServer
from app.settings_dialog import SettingsDialog
from app.timeline import Timeline
from app.urls import normalize_url
from app.validation import quality_report
from app.workers import BuildWorker, ExportWorker


def button(text, callback, tooltip=None, primary=False):
    control = QPushButton(text)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    control.setAccessibleName(tooltip or text)
    if tooltip:
        control.setToolTip(tooltip)
    if primary:
        control.setObjectName('primary')
    control.clicked.connect(callback)
    return control


class NoticeLabel(QLabel):
    message = Signal(str)

    def setText(self, text):
        super().setText(text)
        self.message.emit(text)


class MainWindow(QMainWindow):
    def __init__(self, data_root):
        super().__init__()
        self.root = Path(data_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings = Settings(self.root / 'settings.json')
        self.store = ProjectStore(self.root)
        ui = self.root / 'ui'
        shutil.copytree(WEB, ui, dirs_exist_ok=True)
        self.server = PreviewServer(self.root)
        self.browser = BrowserController(self)
        self.source = self.browser.source
        self.player = make_player(self.browser.profile, self.server.origin)
        self.player.bridge.received.connect(self.engine_event)
        self.player.loadFinished.connect(self.player_loaded)
        self.player.page().renderProcessTerminated.connect(lambda *_: self.fail('The animation renderer stopped. Open the project again to recover.'))
        self.project = None
        self.blueprint = None
        self.metadata = None
        self.worker = self.export_worker = self.recording_worker = None
        self.pending_load = False
        self.loading_player = False
        self.engine_ready = False
        self.pending_comparison = False
        self.player_ready = False
        self.busy = False
        self.paused = False
        self.closing = False
        self.fit = True
        self.compare_busy = False
        self.comparison_viewport = False
        self.crawling = False
        self.setWindowTitle('SWARM STUDIO | Website reconstruction desk')
        self.setWindowIcon(QIcon(str(WEB/'studio.svg')))
        self.resize(1600, 1000)
        self.setMinimumSize(960, 540)
        self.setStyleSheet((WEB / 'application.qss').read_text('utf-8'))
        self.build_ui()
        self.browser.error.connect(self.browser_error)
        self.browser.phase.connect(self.status)
        self.browser.capture_ready.connect(self.captured)
        self.browser.navigated.connect(self.navigation_finished)
        self.source.urlChanged.connect(lambda url: self.url.setText(url.toString()))
        self.source.iconChanged.connect(lambda icon: self.go.setIcon(icon))
        self.player.setUrl(QUrl(self.server.url('ui/player.html')))
        self.load_recent()
        self.shortcuts()

    def build_ui(self):
        self.build_supporting_widgets()
        # Keep the existing project and diagnostic widgets available on demand,
        # but give the entire main workspace to the browser and one bottom dock.
        self.utility = self.takeCentralWidget()
        self.utility.setParent(self)
        self.utility.hide()
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, 1)
        self.stack.installEventFilter(self)
        self.stack.currentChanged.connect(lambda _: QTimer.singleShot(0, self.resize_canvases))

        self.diagnostics = QDialog(self)
        self.diagnostics.setWindowTitle('Project diagnostics')
        self.diagnostics.resize(820, 620)
        details = QHBoxLayout(self.diagnostics)
        details.addWidget(self.left, 1)
        details.addWidget(self.right, 2)
        self.left.show()
        self.right.show()

        self.canvas_options = QDialog(self)
        self.canvas_options.setWindowTitle('Canvas options')
        self.canvas_options.resize(780, 150)
        options = QVBoxLayout(self.canvas_options)
        options.addWidget(self.center)
        self.tabs.hide()
        self.viewport.addItem('Window · fill available space')
        self.viewport.setCurrentIndex(5 if self.settings.values['viewport_mode'] == 'window' else 4)
        self.zoom.currentTextChanged.connect(self.resize_canvases)

        self.bottom = QFrame()
        self.bottom.setObjectName('focusdock')
        dock = QVBoxLayout(self.bottom)
        dock.setContentsMargins(8, 5, 8, 4)
        dock.setSpacing(3)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.studio_button = QPushButton('Studio')
        self.studio_button.setAccessibleName('Studio menu: projects, settings, canvas and diagnostics')
        self.studio_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.studio_menu = QMenu(self.studio_button)
        self.studio_button.setMenu(self.studio_menu)
        self.studio_menu.addAction('Try offline demo', self.open_demo)
        self.studio_menu.addSeparator()
        self.studio_menu.addAction('New project', self.new_project)
        self.studio_menu.addAction('Open saved project…', self.open_project)
        self.studio_menu.addAction('Settings…', self.show_settings)
        self.studio_menu.addAction('Canvas options…', self.canvas_options.show)
        self.studio_menu.addAction('Project diagnostics…', self.diagnostics.show)
        self.timeline_action = self.studio_menu.addAction('Show activity timeline')
        self.timeline_action.setCheckable(True)
        self.timeline_action.toggled.connect(self.toggle_timeline)
        playback = self.studio_menu.addMenu('Playback')
        playback.addAction('Step back two seconds', self.step_back.click)
        playback.addAction('Step forward half a second', self.step_forward.click)
        playback.addAction('Stop / cancel', self.cancel)
        playback.addAction('Run comparison', self.compare_button.click)
        navigation = self.studio_menu.addMenu('Navigation')
        navigation.addAction('Back', self.back.click)
        navigation.addAction('Forward', self.forward.click)
        navigation.addAction('Reload website', self.reload.click)
        self.studio_menu.addAction('Fullscreen (F11)', self.toggle_presentation)
        self.studio_menu.addAction('Cinematic recording…', self.show_recording)
        row.addWidget(self.studio_button)
        self.url.setMinimumWidth(120)
        row.addWidget(self.url, 1)
        self.go.setText('Open')
        row.addWidget(self.go)
        row.addWidget(self.initialize)
        self.mode = QComboBox()
        self.mode.addItems(['Original', 'Swarm', 'Reconstruction', 'Comparison'])
        self.mode.setAccessibleName('Canvas mode')
        self.mode.setFixedWidth(132)
        self.mode.currentIndexChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.mode.setCurrentIndex)
        row.addWidget(self.mode)
        row.addWidget(self.play_button)
        row.addWidget(self.replay_button)
        self.speed.setFixedWidth(62)
        row.addWidget(self.speed)
        self.tour.setText('Tour')
        self.tour.setToolTip('Cinematic Auto Tour follows construction through the whole page')
        row.addWidget(self.tour)
        row.addWidget(self.audio)
        self.record_button=button('Record',self.show_recording,'Save a cinematic MP4 with smooth automatic zoom')
        self.record_button.setEnabled(False)
        row.addWidget(self.record_button)
        row.addWidget(self.export_button)
        dock.addLayout(row)
        self.status_text = QLabel('Open a website, or choose Studio > Try offline demo.')
        self.status_text.setObjectName('muted')
        self.status_text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        footer.addWidget(self.status_text, 1)
        footer.addWidget(self.position)
        dock.addLayout(footer)
        dock.addWidget(self.progress)
        dock.addWidget(self.timeline)
        self.timeline.hide()
        layout.addWidget(self.bottom)
        # The old banner becomes a message source for the compact dock instead
        # of permanently consuming a row above the canvas.
        self.notice = NoticeLabel(self.utility)
        self.notice.message.connect(self.status)
        self.notice.hide()
        self.statusBar().hide()
        QTimer.singleShot(0, self.resize_canvases)

    def toggle_timeline(self, visible):
        self.timeline.setVisible(visible)
        QTimer.singleShot(0, self.resize_canvases)

    def build_supporting_widgets(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 10, 12, 6)
        outer.setSpacing(10)
        self.topbar = QFrame()
        self.topbar.setObjectName('topbar')
        top = QHBoxLayout(self.topbar)
        top.setContentsMargins(8,4,8,10)
        brand = QLabel('↖  SWARM STUDIO')
        brand.setObjectName('brand')
        top.addWidget(brand)
        subtitle = QLabel('Watch a swarm rebuild the web.')
        subtitle.setObjectName('muted')
        top.addWidget(subtitle)
        top.addStretch()
        self.recents = QComboBox()
        self.recents.setMinimumWidth(190)
        self.recents.setMaximumWidth(270)
        self.recents.setAccessibleName('Recent projects')
        self.recents.activated.connect(self.recent_selected)
        top.addWidget(self.recents)
        top.addWidget(button('New', self.new_project, 'New project (Ctrl+N)'))
        top.addWidget(button('Open', self.open_project, 'Open a saved project (Ctrl+O)'))
        top.addWidget(button('Settings', self.show_settings))
        outer.addWidget(self.topbar)
        self.navbar = QWidget()
        nav = QHBoxLayout(self.navbar)
        nav.setContentsMargins(0,0,0,0)
        nav.setSpacing(7)
        self.back = button('‹', self.source.back, 'Back')
        self.forward = button('›', self.source.forward, 'Forward')
        self.reload = button('↻', self.source.reload, 'Reload website')
        nav.addWidget(self.back);nav.addWidget(self.forward);nav.addWidget(self.reload)
        self.url = QLineEdit()
        self.url.setPlaceholderText('Enter a website URL or localhost address')
        self.url.setAccessibleName('Website URL')
        self.url.returnPressed.connect(self.navigate)
        nav.addWidget(self.url,1)
        self.go = button('Open website',self.navigate)
        nav.addWidget(self.go)
        self.initialize = button('Initialize Swarm',self.start_capture,primary=True)
        self.initialize.setEnabled(False)
        nav.addWidget(self.initialize)
        self.cancel_button = button('Cancel',self.cancel)
        self.cancel_button.setEnabled(False)
        nav.addWidget(self.cancel_button)
        self.export_button = button('Export',self.export_project,'Export the reconstructed project as ZIP (Ctrl+E)')
        self.export_button.setEnabled(False)
        nav.addWidget(self.export_button)
        outer.addWidget(self.navbar)
        self.notice = QLabel('Capture websites you own or have permission to reproduce. Form values and source scripts are excluded.')
        self.notice.setObjectName('notice')
        self.notice.setWordWrap(True)
        outer.addWidget(self.notice)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self.splitter,1)
        self.left = QFrame();self.left.setObjectName('panel')
        left = QVBoxLayout(self.left)
        title = QLabel('SWARM CONTROL');title.setObjectName('section');left.addWidget(title)
        self.agent_summary = QLabel('Crew ready')
        self.agent_summary.setObjectName('muted');self.agent_summary.setWordWrap(True);left.addWidget(self.agent_summary)
        self.agents = QTreeWidget()
        self.agents.setColumnCount(2)
        self.agents.setHeaderLabels(['Agent / responsibility','Tasks'])
        self.agents.setRootIsDecorated(False)
        self.agents.setColumnWidth(0,155)
        self.agents.setIndentation(0)
        self.agents.setAccessibleName('Simulated agents and current task status')
        left.addWidget(self.agents,1)
        self.left.setMinimumWidth(190)
        self.populate_agents()
        agent_note = QLabel('Simulated personas. Every action follows the captured task graph.')
        agent_note.setObjectName('muted');agent_note.setWordWrap(True);left.addWidget(agent_note)
        self.splitter.addWidget(self.left)
        self.center = QWidget()
        center = QVBoxLayout(self.center)
        center.setContentsMargins(0,0,0,0)
        center.setSpacing(8)
        viewbar=QHBoxLayout()
        self.tabs=QTabBar();self.tabs.setAccessibleName('Canvas mode')
        for label in ['Original','Swarm','Reconstruction','Comparison']:self.tabs.addTab(label)
        self.tabs.currentChanged.connect(self.switch_tab)
        viewbar.addWidget(self.tabs)
        viewbar.addStretch()
        self.presentation = button('Present',self.toggle_presentation,'Toggle presentation mode (F11)')
        viewbar.addWidget(self.presentation)
        center.addLayout(viewbar)
        viewcontrols=QHBoxLayout()
        self.viewport=QComboBox();self.viewport.addItems(['Desktop · 1280 × 800','Laptop · 1440 × 900','Tablet · 768 × 1024','Mobile · 390 × 844','Custom settings'])
        self.viewport.setAccessibleName('Browser viewport preset');self.viewport.activated.connect(self.change_viewport)
        viewcontrols.addWidget(self.viewport)
        self.zoom=QComboBox();self.zoom.addItems(['Fit','50%','75%','100%','125%']);self.zoom.setAccessibleName('Canvas zoom');self.zoom.activated.connect(self.resize_canvases)
        viewcontrols.addWidget(self.zoom)
        self.dimensions=QLabel();self.dimensions.setObjectName('muted');viewcontrols.addWidget(self.dimensions)
        viewcontrols.addStretch()
        self.compare_button=button('Run comparison',self.run_comparison);self.compare_button.setEnabled(False);viewcontrols.addWidget(self.compare_button)
        center.addLayout(viewcontrols)
        self.stack=QStackedWidget()
        self.welcome=self.make_welcome()
        self.stack.addWidget(self.welcome)
        self.source_area=self.wrap_view(self.source)
        self.player_area=self.wrap_view(self.player)
        self.stack.addWidget(self.source_area)
        self.stack.addWidget(self.player_area)
        self.comparison=ComparisonPanel();self.stack.addWidget(self.comparison)
        center.addWidget(self.stack,1)
        self.splitter.addWidget(self.center)
        self.right=QFrame();self.right.setObjectName('panel')
        right=QVBoxLayout(self.right)
        title=QLabel('INSPECTOR');title.setObjectName('section');right.addWidget(title)
        self.stats=QTreeWidget();self.stats.setRootIsDecorated(False);self.stats.setHeaderLabels(['Capture','Value']);self.stats.setColumnWidth(0,150);self.stats.setMaximumHeight(285)
        self.stat_items={}
        for text in ['Elements captured','Images / media','Fonts detected','Assets saved','Style rules','Reconstruction tasks','Active agents','Completed tasks','Pending tasks','Capture warnings']:
            item=QTreeWidgetItem([text,'0']);self.stats.addTopLevelItem(item);self.stat_items[text]=item
        right.addWidget(self.stats)
        self.quality_label=QLabel('Quality: no comparison yet');self.quality_label.setWordWrap(True);self.quality_label.setObjectName('muted');right.addWidget(self.quality_label)
        title=QLabel('ACTIVITY');title.setObjectName('section');right.addWidget(title)
        self.feed=QListWidget();self.feed.setWordWrap(True);self.feed.setAccessibleName('Capture and reconstruction activity');right.addWidget(self.feed,1)
        self.right.setMinimumWidth(220)
        self.splitter.addWidget(self.right)
        self.splitter.setSizes([225,1080,260])
        self.bottom=QFrame();self.bottom.setObjectName('panel')
        bottom=QVBoxLayout(self.bottom);bottom.setContentsMargins(10,7,10,5)
        playbar=QHBoxLayout()
        self.play_button=button('Pause',self.toggle_pause);self.play_button.setEnabled(False);playbar.addWidget(self.play_button)
        self.replay_button=button('Replay',self.replay);self.replay_button.setEnabled(False);playbar.addWidget(self.replay_button)
        self.step_back=button('−2s',lambda:self.js('back()'),'Step back two simulation seconds');self.step_back.setEnabled(False);playbar.addWidget(self.step_back)
        self.step_forward=button('+0.5s',lambda:self.js('step()'),'Step forward half a simulation second');self.step_forward.setEnabled(False);playbar.addWidget(self.step_forward)
        self.speed=QComboBox();self.speed.addItems(['0.5×','1×','2×','3×','5×']);self.speed.setCurrentText(f"{self.settings.values['speed']:g}×");self.speed.setAccessibleName('Playback speed');self.speed.currentTextChanged.connect(self.speed_changed);playbar.addWidget(self.speed)
        self.tour=QCheckBox('Auto Tour');self.tour.setChecked(self.settings.values['auto_tour']);self.tour.toggled.connect(lambda v:self.js('setOptions('+json.dumps({'auto_tour':v})+')'));playbar.addWidget(self.tour)
        self.audio=QCheckBox('Sound');self.audio.setChecked(self.settings.values['sound']);self.audio.toggled.connect(lambda v:self.js('setOptions('+json.dumps({'sound':v})+')'));playbar.addWidget(self.audio)
        playbar.addStretch()
        self.position=QLabel('00:00  ·  No tasks yet');self.position.setObjectName('muted');playbar.addWidget(self.position)
        bottom.addLayout(playbar)
        self.progress=QProgressBar();self.progress.setRange(0,1000);bottom.addWidget(self.progress)
        self.timeline=Timeline();bottom.addWidget(self.timeline)
        outer.addWidget(self.bottom)
        self.statusBar().showMessage('Ready. Open your website or try the offline demo.')
        self.runtime_label=QLabel('LOCAL ENGINE  ·  NO AI API');self.runtime_label.setObjectName('muted');self.statusBar().addPermanentWidget(self.runtime_label)
        QTimer.singleShot(0,self.resize_canvases)

    def make_welcome(self):
        widget=QWidget();layout=QVBoxLayout(widget);layout.setContentsMargins(60,50,60,50);layout.addStretch()
        eyebrow=QLabel('THE RECONSTRUCTION DESK');eyebrow.setObjectName('section');layout.addWidget(eyebrow)
        title=QLabel('One website.\nA whole swarm.');title.setObjectName('hero');layout.addWidget(title)
        description=QLabel('Open a page you have permission to reproduce.\nWatch named cursors build a real local copy from its rendered DOM.');description.setObjectName('muted');description.setWordWrap(True);layout.addWidget(description)
        row=QHBoxLayout();row.addWidget(button('Try offline demo',self.open_demo,primary=True));row.addWidget(button('Focus website URL',lambda:self.url.setFocus()));row.addStretch();layout.addLayout(row)
        layout.addSpacing(20)
        note=QLabel('Captured HTML + CSS + assets\nTask-driven motion · Replayable projects · Visual comparison');note.setObjectName('muted');layout.addWidget(note);layout.addStretch()
        return widget

    def wrap_view(self,view):
        area=QScrollArea();area.setWidgetResizable(False);area.setAlignment(Qt.AlignmentFlag.AlignCenter);area.setWidget(view)
        return area

    def populate_agents(self):
        self.agents.clear()
        count=self.settings.values['agents']
        for i in range(count):
            name=NAMES[i%len(NAMES)]+(f' {i+1}' if i>=len(NAMES) else '')
            item=QTreeWidgetItem([f'● {name}\n{ROLES[i%len(ROLES)]}', '0'])
            item.setForeground(0,QColor(COLORS[i%len(COLORS)]))
            item.setToolTip(0,'Waiting for capture')
            self.agents.addTopLevelItem(item)
        self.agent_summary.setText(f'{count} simulated agents · waiting')

    def shortcuts(self):
        for key,callback in [('Ctrl+L',lambda:self.url.setFocus()),('Ctrl+N',self.new_project),('Ctrl+O',self.open_project),('Ctrl+E',self.export_project),('F11',self.toggle_presentation)]:
            action=QAction(self);action.setShortcut(QKeySequence(key));action.triggered.connect(callback);self.addAction(action)

    def status(self,text):
        self.statusBar().showMessage(text)
        if hasattr(self, 'status_text'):
            self.status_text.setText(text)
            self.status_text.setToolTip(text)

    def log(self,text,color=None):
        item=QListWidgetItem(text)
        if color:item.setForeground(QColor(color))
        self.feed.addItem(item)
        while self.feed.count()>150:self.feed.takeItem(0)
        self.feed.scrollToBottom()

    def fail(self,message):
        logging.error(message)
        self.notice.setText(message)
        self.status(message)
        self.log(message,'#f3aa9d')
        self.set_busy(False)
        if self.compare_busy:
            self.compare_busy=False

    def browser_error(self,message):
        if self.crawling and self.captures:
            self.captures[0]['warnings'].append('Linked page skipped: '+message)
            self.log('Linked page skipped: '+message,'#e9be83')
            QTimer.singleShot(0,self.next_capture)
        else:
            self.crawling=False
            self.fail(message)

    def set_busy(self,value):
        self.busy=value
        self.initialize.setEnabled(not value and self.browser.ready)
        self.cancel_button.setEnabled(value or self.project is not None)
        self.go.setEnabled(not value)
        self.back.setEnabled(not value)
        self.forward.setEnabled(not value)
        self.reload.setEnabled(not value)
        self.viewport.setEnabled(not value)
        self.export_button.setEnabled(not value and self.project is not None)
        self.record_button.setEnabled(not value and self.project is not None)

    def navigate(self):
        if self.busy:return
        try:url=normalize_url(self.url.text())
        except ValueError as exc:self.fail(str(exc));return
        self.tabs.setCurrentIndex(0);self.stack.setCurrentWidget(self.source_area)
        self.browser.navigate(url)

    def navigation_finished(self,ok):
        if ok and self.crawling and self.crawl_target:
            redirected=urlsplit(self.source.url().toString())
            if (redirected.scheme,redirected.netloc) != self.crawl_origin:
                self.browser_error('Linked page redirected outside the capture origin.')
                return
            self.crawl_target=None
            QTimer.singleShot(180,lambda:self.browser.capture(self.settings.values) if self.crawling else None)
            return
        self.initialize.setEnabled(ok and not self.busy)
        if ok:self.notice.setText('Website loaded. Initialize Swarm captures this page without copying scripts or form values.')

    def open_demo(self):
        if self.busy:return
        self.url.setText(self.server.url('ui/demo/index.html'))
        self.navigate()

    def start_capture(self):
        if self.busy:return
        self.project=None;self.metadata=None;self.blueprint=None
        self.engine_ready=False;self.pending_comparison=False
        self.resize_canvases()
        self.js('stop()')
        self.feed.clear();self.timeline.reset();self.progress.setValue(0)
        self.populate_agents()
        self.tabs.setCurrentIndex(0);self.stack.setCurrentWidget(self.source_area)
        self.set_busy(True)
        self.crawling=True;self.captures=[];self.crawl_queue=[];self.crawl_depth=0;self.crawl_target=None
        original=urlsplit(self.source.url().toString())
        self.crawl_origin=(original.scheme,original.netloc)
        self.crawl_seen={urldefrag(self.source.url().toString())[0]}
        self.notice.setText('Capturing rendered DOM and discovering lazy content. Cancel stops the current operation.')
        self.browser.capture(self.settings.values)

    def captured(self,capture):
        if not self.crawling:return
        if not self.captures:self.root_shot=self.source.grab()
        self.captures.append(capture)
        values=self.settings.values
        if self.crawl_depth < values['crawl_depth']:
            for raw in capture.get('links',[]):
                url=urldefrag(raw)[0]
                parts=urlsplit(url)
                if (parts.scheme,parts.netloc) != self.crawl_origin or url in self.crawl_seen or re.search(r'login|logout|sign.?in|sign.?out|checkout|payment|delete|remove|unsubscribe|account|oauth|auth/',parts.path,re.I):continue
                try:normalize_url(url)
                except ValueError:continue
                if len(self.crawl_seen)>=values['page_limit']:break
                self.crawl_seen.add(url);self.crawl_queue.append((url,self.crawl_depth+1))
        self.next_capture()

    def next_capture(self):
        if not self.crawling:return
        if self.crawl_queue and len(self.captures)<self.settings.values['page_limit']:
            url,self.crawl_depth=self.crawl_queue.pop(0)
            self.crawl_target=url
            self.log(f'Capturing linked page {len(self.captures)+1} at depth {self.crawl_depth}.')
            self.browser.navigate(url)
            return
        self.crawling=False
        self.finish_captures()

    def finish_captures(self):
        capture=self.captures[0]
        self.project_id,self.pending_path=self.store.allocate()
        (self.pending_path/'screenshots').mkdir()
        self.root_shot.save(str(self.pending_path/'screenshots/original.png'))
        self.log(f"Captured {len(capture['elements'])} elements at {capture['viewport']['width']} × {capture['viewport']['height']}.")
        self.notice.setText('Saving semantic HTML, styles and local assets…')
        self.worker=BuildWorker(self.captures,self.pending_path,self.settings.values.copy())
        self.worker.progress.connect(lambda kind,path:self.log(f'Saved {path}'))
        self.worker.error.connect(self.fail)
        self.worker.ready.connect(self.built)
        self.worker.start()

    def built(self,metadata,blueprint):
        self.project=self.pending_path;self.metadata=metadata;self.blueprint=blueprint
        self.store.register(self.project_id,metadata)
        self.load_recent()
        self.update_stats()
        self.set_busy(False)
        self.initialize.setEnabled(self.browser.ready)
        self.compare_button.setEnabled(True)
        self.notice.setText(f"Local reconstruction saved. {len(metadata['warnings'])} capture warnings. Simulated agents follow {len(blueprint['tasks'])} discovered tasks.")
        for warning in metadata['warnings']:self.log(warning,'#e9be83')
        self.pending_load=True
        self.load_player()

    def update_stats(self):
        if not self.blueprint:return
        values={'Elements captured':len(self.blueprint['elements']),'Images / media':self.blueprint['counts'].get('image',0)+self.blueprint['counts'].get('media',0),'Fonts detected':len(self.blueprint.get('fonts',[])),'Assets saved':self.metadata['assets'],'Style rules':(self.project/'styles/reconstructed.css').read_text('utf-8').count('{'),'Reconstruction tasks':len(self.blueprint['tasks']),'Capture warnings':len(self.metadata.get('warnings',[]))}
        for key,value in values.items():self.stat_items[key].setText(1,str(value))

    def player_loaded(self,ok):
        self.player_ready=ok
        if ok and self.pending_load:self.load_player()
        elif not ok:self.fail('The local playback document failed to load.')

    def load_player(self):
        if not self.project:return
        self.record_button.setEnabled(True)
        if not self.player_ready:
            self.pending_load=True
            if self.player.url().isEmpty():self.player.setUrl(QUrl(self.server.url('ui/player.html')))
            return
        self.pending_load=False
        self.loading_player=True
        self.engine_ready=False
        self.compare_button.setEnabled(False)
        self.timeline.reset();self.progress.setValue(0);self.paused=False;self.play_button.setText('Pause')
        self.resize_canvases()
        self.tabs.setCurrentIndex(1);self.stack.setCurrentWidget(self.player_area)
        url=self.server.url(self.project.relative_to(self.root).as_posix())+'/'
        options=dict(self.settings.values,auto_tour=self.tour.isChecked(),sound=self.audio.isChecked(),speed=float(self.speed.currentText().replace('×','')))
        code='window.Studio.load('+json.dumps(url)+','+json.dumps(options)+').catch(error=>window.Studio.emit("error",{message:error.message}));'
        self.player.page().runJavaScript(code)
        for control in [self.play_button,self.replay_button,self.step_back,self.step_forward]:control.setEnabled(True)

    def js(self,call):
        if self.player_ready:self.player.page().runJavaScript('window.Studio?.'+call+';')

    def engine_event(self,data):
        kind=data['type']
        if kind=='media-warning':
            self.log('Video fallback: '+data.get('message','Media could not be decoded.'))
            self.status('A video could not be decoded; a poster or placeholder is shown.')
        self.timeline.record_event(data)
        if kind=='ready':
            self.loading_player=False
            self.engine_ready=True
            self.compare_button.setEnabled(True)
            if self.pending_comparison:
                self.pending_comparison=False
                QTimer.singleShot(0,self.run_comparison)
        elif kind=='assigned':self.log(f"[{data['name']}] {data['label']}",COLORS[data['agent']%len(COLORS)])
        elif kind=='task-error':self.log(f"Task blocked: {data.get('label',data.get('task'))}",'#f3aa9d')
        elif kind=='progress':
            total=data['total'];completed=data['completed'];failed=data.get('failed',0)
            self.progress.setValue(int((completed+failed)/max(1,total)*1000))
            sec=int(data['time']);self.position.setText(f'{sec//60:02}:{sec%60:02}  ·  {completed} / {total} tasks')
            active=sum(1 for agent in data['agents'] if agent['task'])
            self.agent_summary.setText(f"{len(data['agents'])} simulated agents · {active} active")
            for key,value in [('Active agents',active),('Completed tasks',completed),('Pending tasks',max(0,total-completed-failed-active))]:self.stat_items[key].setText(1,str(value))
            for agent in data['agents']:
                item=self.agents.topLevelItem(agent['id'])
                if item:
                    name=NAMES[agent['id']%len(NAMES)]
                    item.setText(0,f"● {name}\n{agent['status']}")
                    item.setText(1,str(agent['completed']))
                    item.setToolTip(0,f"{ROLES[agent['id']%len(ROLES)]}: {agent['status']}")
            self.paused=data['paused'];self.play_button.setText('Resume' if self.paused else 'Pause')
        elif kind=='finished':
            text=f"Reconstruction finished: {data['completed']} tasks complete, {data['failed']} failed. Explore the clone or run a comparison."
            self.notice.setText(text);self.log(text);self.status(text)
        elif kind=='error':self.fail(data.get('message','Animation failed.'))
        elif kind=='compare':self.run_comparison()
        elif kind=='explore':self.tabs.setCurrentIndex(2)
        elif kind=='replayed':self.timeline.reset()

    def switch_tab(self,index):
        if index==0:
            self.stack.setCurrentWidget(self.source_area if self.browser.ready or not self.source.url().isEmpty() else self.welcome)
            if self.project:self.js('pause(true)')
        elif index==1:
            if self.project:
                self.stack.setCurrentWidget(self.player_area)
                self.js('pause(false)')
                if not self.loading_player:self.player.page().runJavaScript('if(window.Studio?.model&&!window.Studio.running)window.Studio.replay();')
            else:self.stack.setCurrentWidget(self.welcome)
        elif index==2:
            if self.project:self.stack.setCurrentWidget(self.player_area);self.js('showClone()')
            else:self.stack.setCurrentWidget(self.welcome)
        else:
            self.stack.setCurrentWidget(self.comparison)
            self.js('pause(true)')

    def toggle_pause(self):
        if self.project:self.js('pause('+('false' if self.paused else 'true')+')')

    def replay(self):
        if not self.project:return
        self.timeline.reset()
        self.tabs.setCurrentIndex(1);self.stack.setCurrentWidget(self.player_area);self.js('replay()')

    def speed_changed(self,text):
        self.js('setSpeed('+text.replace('×','')+')')

    def cancel(self):
        self.crawling=False
        self.browser.cancel()
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.notice.setText('Cancelling asset work. Waiting for active bounded requests to stop…')
        else:self.set_busy(False)
        self.js('stop()')
        self.status('Stopped. Replay a saved capture or initialize again.')

    def resize_canvases(self,*_):
        if not hasattr(self,'zoom'):return
        values=self.settings.values
        width,height=values['width'],values['height']
        # Hidden QScrollAreas retain stale viewport sizes. Always size from the
        # live canvas stack, which is shared by Original and Swarm modes.
        available=self.stack.contentsRect().size()
        available_width=max(1,available.width())
        available_height=max(1,available.height())
        if values['viewport_mode']=='window' and not self.comparison_viewport:
            width,height=available_width,available_height
        elif self.project and self.metadata:
            width,height=self.metadata['viewport']['width'],self.metadata['viewport']['height']
        text=self.zoom.currentText()
        if text=='Fit':
            scale=max(.1,min(available_width/width,available_height/height))
        else:scale=float(text.replace('%',''))/100
        for view in [self.source,self.player]:
            view.setFixedSize(round(width*scale),round(height*scale))
            view.setZoomFactor(scale)
        self.dimensions.setText(f'{width} × {height}  ·  {round(scale*100)}%')

    def eventFilter(self, watched, event):
        if watched is getattr(self, 'stack', None) and event.type()==QEvent.Type.Resize:
            QTimer.singleShot(0,self.resize_canvases)
        return super().eventFilter(watched,event)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'zoom'):QTimer.singleShot(0,self.resize_canvases)

    def change_viewport(self,index):
        presets=[(1280,800),(1440,900),(768,1024),(390,844)]
        if index==4:self.show_settings();return
        if self.project:
            self.notice.setText('Viewport changed for the next capture. Current project playback keeps its captured viewport.')
            self.project=None;self.blueprint=None;self.metadata=None;self.export_button.setEnabled(False)
            self.js('stop()');self.tabs.setCurrentIndex(0)
        if index==5:
            self.settings.save({'viewport_mode':'window'})
            self.zoom.setCurrentText('Fit')
        else:
            width,height=presets[index]
            self.settings.save({'width':width,'height':height,'viewport_mode':'fixed'})
        self.viewport.setCurrentIndex(index)
        self.resize_canvases()

    def show_settings(self):
        dialog=SettingsDialog(self.settings.values,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            values=dialog.values()
            if (values['width'],values['height']) != (self.settings.values['width'],self.settings.values['height']):
                values['viewport_mode']='fixed'
                self.viewport.setCurrentIndex(4)
            self.settings.save(values);self.populate_agents();self.tour.setChecked(values['auto_tour']);self.audio.setChecked(values['sound']);self.speed.setCurrentText(f"{values['speed']:g}×")
            self.js('setOptions('+json.dumps(values)+')');self.resize_canvases();self.status('Settings saved. Agent count and capture settings apply on the next reconstruction.')

    def load_recent(self):
        self.recents.clear();self.recents.addItem('Recent projects',None)
        for project_id,name,url in self.store.recent():self.recents.addItem(name,project_id)

    def recent_selected(self,index):
        project_id=self.recents.itemData(index)
        if project_id and not self.busy:self.load_project(project_id)

    def open_project(self):
        if self.busy:return
        dialog=QDialog(self);dialog.setWindowTitle('Open a saved reconstruction');dialog.resize(650,420)
        layout=QVBoxLayout(dialog);listing=QListWidget();layout.addWidget(listing)
        for project_id,name,url in self.store.recent():
            item=QListWidgetItem(name+'\n'+url);item.setData(Qt.ItemDataRole.UserRole,project_id);listing.addItem(item)
        if not listing.count():layout.addWidget(QLabel('No saved projects yet. Capture a page or try the offline demo.'))
        def choose():
            if listing.currentItem():self.load_project(listing.currentItem().data(Qt.ItemDataRole.UserRole));dialog.accept()
        listing.itemDoubleClicked.connect(choose)
        layout.addWidget(button('Open selected project',choose,primary=True));layout.addWidget(button('Close',dialog.reject))
        dialog.exec()

    def load_project(self,project_id):
        try:self.project,self.metadata,self.blueprint=self.store.load(project_id)
        except ValueError as exc:self.fail(str(exc));return
        self.project_id=project_id;self.update_stats();self.export_button.setEnabled(True);self.compare_button.setEnabled(True);self.cancel_button.setEnabled(True)
        self.url.setText(self.metadata['url']);self.notice.setText('Saved project opened without recapture. Original tab retains the last live website; comparison uses the saved baseline.')
        self.pending_load=True;self.load_player()

    def new_project(self):
        if self.busy:return
        self.js('stop()');self.project=None;self.metadata=None;self.blueprint=None;self.feed.clear();self.timeline.reset();self.progress.setValue(0)
        self.record_button.setEnabled(False)
        self.export_button.setEnabled(False);self.compare_button.setEnabled(False);self.tabs.setCurrentIndex(0);self.stack.setCurrentWidget(self.welcome);self.url.clear();self.url.setFocus();self.populate_agents()
        for control in [self.play_button,self.replay_button,self.step_back,self.step_forward]:control.setEnabled(False)
        self.notice.setText('Enter a website URL or try the bundled offline demo. Capture only material you have permission to reproduce.')

    def run_comparison(self):
        if not self.project or self.compare_busy:return
        if not self.engine_ready:
            self.pending_comparison=True
            self.status('Waiting for the reconstructed document before comparison…')
            return
        self.compare_busy=True
        self.comparison_viewport=True
        self.resize_canvases()
        self.compare_button.setEnabled(False)
        self.tabs.setCurrentIndex(2);self.stack.setCurrentWidget(self.player_area)
        self.js('showClone()')
        self.status('Rendering the local clone at the capture viewport…')
        QTimer.singleShot(650,self.take_comparison)

    def take_comparison(self):
        if not self.project:self.compare_busy=False;return
        self.player.grab().save(str(self.project/'screenshots/reconstructed.png'))
        script='''(()=>{const studio=window.Studio,d=studio.frame.contentDocument;let boxes=[],missing=[];for(const e of studio.model.elements){const n=d.querySelector('[data-sw-id="'+e.id+'"]');if(!n){missing.push(e.id);continue;}const r=n.getBoundingClientRect(),o=e.originalBox;const delta=Math.max(Math.abs(r.x-o.x),Math.abs(r.y-o.y),Math.abs(r.width-o.w),Math.abs(r.height-o.h));if(delta>2)boxes.push({id:e.id,maximum_delta_px:Math.round(delta*10)/10});}return JSON.stringify({nodes:d.querySelectorAll('[data-sw-id]').length,selectable_text_characters:d.body.innerText.length,missing_elements:missing,bounding_box_mismatches:boxes.slice(0,100),broken_images:[...d.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.getAttribute('data-sw-id')),viewport:{width:studio.frame.contentWindow.innerWidth,height:studio.frame.contentWindow.innerHeight}});})()'''
        def finished(raw):
            try:
                dom=json.loads(raw) if raw else {'error':'DOM validation did not respond'}
                report=quality_report(self.project,dom)
                self.comparison.load(self.project,report)
                self.quality_label.setText(f"Mean RGB difference: {report['mean_absolute_rgb_difference']:.2f}/255\n{len(dom.get('broken_images',[]))} broken images · {len(dom.get('bounding_box_mismatches',[]))} geometry mismatches")
                self.log('Comparison saved with pixel heatmap and DOM diagnostics.')
                self.tabs.setCurrentIndex(3);self.stack.setCurrentWidget(self.comparison)
                self.notice.setText('Comparison measures the captured viewport. Pixel similarity does not prove functional or backend equivalence.')
            except Exception as exc:self.fail(f'Comparison could not finish: {exc}')
            finally:
                self.compare_busy=False
                self.comparison_viewport=False
                self.compare_button.setEnabled(True)
                self.resize_canvases()
        self.player.page().runJavaScript(script,finished)

    def export_project(self):
        if not self.project or self.busy or self.export_worker and self.export_worker.isRunning():return
        directory=self.settings.values['export_directory'] or str(Path.home()/'Desktop')
        destination,_=QFileDialog.getSaveFileName(self,'Export reconstruction',str(Path(directory)/'swarm-project.zip'),'ZIP archive (*.zip)')
        if destination:self.export_to(destination)

    def show_recording(self):
        if not self.project or self.busy:
            self.status('Build or open a saved project before recording.');return
        if getattr(self,'recording_dialog',None) and self.recording_dialog.isVisible():
            self.recording_dialog.raise_();self.recording_dialog.activateWindow();return
        from app.recording_dialog import RecordingDialog
        self.recording_dialog=RecordingDialog(self)
        self.recording_dialog.show()

    def export_to(self,destination):
        self.export_button.setEnabled(False)
        self.export_worker=ExportWorker(self.project,destination,self.settings.values.copy())
        def done(path):
            self.export_button.setEnabled(True);self.notice.setText('Export saved: '+path);self.log('Export saved: '+path)
            if self.settings.values['open_export']:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
        self.export_worker.ready.connect(done)
        self.export_worker.error.connect(lambda message:(self.export_button.setEnabled(True),self.fail(message)))
        self.export_worker.start()

    def toggle_presentation(self):
        present=not self.isFullScreen()
        if present:self.showFullScreen();self.presentation.setText('Exit presentation')
        else:self.showMaximized();self.presentation.setText('Present')
        QTimer.singleShot(0,self.resize_canvases)

    def closeEvent(self,event):
        self.browser.cancel()
        active=[worker for worker in [self.worker,self.export_worker,self.recording_worker] if worker and worker.isRunning()]
        if active:
            if self.worker:self.worker.cancel_event.set()
            if self.recording_worker:self.recording_worker.cancel_event.set()
            self.closing=True;self.status('Finishing background file operations before closing…');event.ignore();QTimer.singleShot(250,self.close);return
        self.js('stop()')
        self.browser.navigation_timeout.stop()
        self.source.stop();self.player.stop()
        self.server.close();self.store.close()
        event.accept()
