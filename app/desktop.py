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
