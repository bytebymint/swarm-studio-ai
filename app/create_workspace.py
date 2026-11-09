"""Native instruction workspace for live, model-backed website authoring."""
import copy
import base64
import io
import uuid
import json
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget)

from app.browser import make_player
from app.creation import CreationStore, GenerationWorker, KeyVault, MODEL_DEFAULTS, WebsiteDocument, endpoint_url
from app.projects import write_json


def control(text, callback, primary=False):
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(callback)
    if primary:
        button.setObjectName('primary')
    return button


class CreationNetworkPolicy(QWebEngineUrlRequestInterceptor):
    def __init__(self, origin, parent=None):
        super().__init__(parent)
        self.origin = origin

    def interceptRequest(self, info):
        url = info.requestUrl()
        text = url.toString()
        allowed = url.scheme() in {'about', 'data', 'blob'} or text.startswith(self.origin + '/ui/')
        if not allowed:
            info.block(True)


class ModelDialog(QDialog):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.setWindowTitle('Connect Qwen')
        self.resize(590, 350)
        layout = QVBoxLayout(self)
        heading = QLabel('One connection. A whole creation team.')
        heading.setObjectName('createHeading')
        layout.addWidget(heading)
        note = QLabel('Add your Alibaba Cloud Model Studio key when you are ready. Your key stays in the native app and is encrypted for your Windows user.')
        note.setWordWrap(True);note.setObjectName('muted');layout.addWidget(note)
        form = QFormLayout()
        self.endpoint = QLineEdit(workspace.config['endpoint'])
        self.endpoint.setAccessibleName('Qwen API endpoint')
        self.model = QLineEdit(workspace.config['model'])
        self.model.setAccessibleName('Qwen model')
        self.key = QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setAccessibleName('Qwen API key')
        self.key.setPlaceholderText('Key already saved — leave blank to keep it' if workspace.has_key() else 'Paste your API key here later')
        self.review = QCheckBox('Smart review: check the result and make a final repair pass')
        self.review.setChecked(workspace.config.get('review', True))
        form.addRow('API endpoint', self.endpoint);form.addRow('Model', self.model);form.addRow('API key', self.key)
        layout.addLayout(form);layout.addWidget(self.review)
        region = QLabel('Default: Singapore / international. For another region or your own deployment, use its OpenAI-compatible base URL. Inference uses your provider account.')
        region.setWordWrap(True);region.setObjectName('muted');layout.addWidget(region)
        self.error = QLabel();self.error.setWordWrap(True);layout.addWidget(self.error)
        buttons = QHBoxLayout();buttons.addStretch()
        buttons.addWidget(control('Cancel', self.reject))
        def save():
            try:
                config = dict(workspace.config, endpoint=endpoint_url(self.endpoint.text()), model=self.model.text().strip(), review=self.review.isChecked())
                if not config['model'] or len(config['model']) > 120:
                    raise ValueError('Enter a model identifier.')
                if self.key.text().strip():
                    workspace.vault.save(self.key.text())
                write_json(workspace.config_path, config)
                workspace.config = config
                self.key.clear()
                self.accept()
            except (ValueError, OSError) as exc:
                self.error.setText(str(exc))
        buttons.addWidget(control('Save connection', save, True));layout.addLayout(buttons)


class CreateWorkspace(QWidget):
    home_requested = Signal()

    def __init__(self, root, server, parent=None):
        super().__init__(parent)
        self.root, self.server = Path(root), server
        self.store, self.vault = CreationStore(root), KeyVault(root)
        self.config_path = self.root / 'creation-settings.json'
        self.config = MODEL_DEFAULTS.copy()
        try:
            config = json.loads(self.config_path.read_text('utf-8'))
            self.config.update({key: config[key] for key in MODEL_DEFAULTS if key in config and type(config[key]) is type(MODEL_DEFAULTS[key])})
        except (OSError, ValueError):
            pass
        self.project = self.store.new()
        self.working = WebsiteDocument(self.project['document'])
        self.worker = None;self.visual_busy = False;self.browser_ready = False;self.target = None;self.queue = [];self.stopping = False
        self.runtime_errors = [];self.pending_document = None;self.last_problem = '';self.current_instruction_id = None;self.shutting_down = False
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.downloadRequested.connect(lambda item: item.cancel())
        self.policy = CreationNetworkPolicy(server.origin, self.profile)
        self.profile.setUrlRequestInterceptor(self.policy)
        self.view = make_player(self.profile, server.origin, entry='create.html')
        self.view.bridge.received.connect(self.engine_event)
        self.view.page().renderProcessTerminated.connect(lambda *_: self.preview_failed())
        self.build_ui()
        self.refresh()
        self.view.setUrl(QUrl(server.url('ui/create.html')))

    def has_key(self):
        try:
            return bool(self.vault.get())
        except ValueError:
            return False

    def focus_prompt(self):
        self.prompt.setFocus()

    def build_ui(self):
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0);outer.setSpacing(0)
        header = QFrame();header.setObjectName('createHeader')
        row = QHBoxLayout(header);row.setContentsMargins(16, 10, 16, 10);row.setSpacing(8)
        row.addWidget(control('‹ Workspaces', self.home_requested.emit))
        self.title = QLabel('Untitled website');self.title.setObjectName('createTitle');row.addWidget(self.title, 1)
        row.addWidget(control('New', self.new_project));row.addWidget(control('Open', self.open_project))
        self.undo = control('Undo', lambda: self.restore(-1));self.redo = control('Redo', lambda: self.restore(1))
        row.addWidget(self.undo);row.addWidget(self.redo)
        self.connection = control('Model', self.show_model);row.addWidget(self.connection)
        self.export = control('Export ZIP', self.export_project, True);row.addWidget(self.export)
        outer.addWidget(header)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self.splitter, 1)
        self.chat_panel = QFrame();self.chat_panel.setObjectName('creationChat');self.chat_panel.setMinimumWidth(290);self.chat_panel.setMaximumWidth(420)
        chat = QVBoxLayout(self.chat_panel);chat.setContentsMargins(18, 20, 18, 16);chat.setSpacing(12)
        eyebrow = QLabel('CREATE WITH YOUR SWARM');eyebrow.setObjectName('section');chat.addWidget(eyebrow)
        heading = QLabel('Tell it what to make.');heading.setObjectName('createHeading');chat.addWidget(heading)
        self.chat_scroll = QScrollArea();self.chat_scroll.setWidgetResizable(True)
        self.messages = QWidget();self.message_layout = QVBoxLayout(self.messages);self.message_layout.setContentsMargins(0, 8, 5, 4);self.message_layout.setSpacing(16);self.message_layout.addStretch()
        self.chat_scroll.setWidget(self.messages);chat.addWidget(self.chat_scroll, 1)
        self.activity = QLabel('Describe a website to begin.');self.activity.setObjectName('createActivity');self.activity.setWordWrap(True);chat.addWidget(self.activity)
        self.target_row = QFrame();target = QHBoxLayout(self.target_row);target.setContentsMargins(8, 4, 4, 4)
        self.target_label = QLabel();self.target_label.setWordWrap(True);target.addWidget(self.target_label, 1)
        target.addWidget(control('×', self.clear_target));chat.addWidget(self.target_row);self.target_row.hide()
        self.prompt = QPlainTextEdit();self.prompt.setObjectName('createPrompt');self.prompt.setFixedHeight(105)
        self.prompt.setPlaceholderText('A website for…\nOr describe what to add, change or remove.')
        self.prompt.setAccessibleName('Website creation instruction');chat.addWidget(self.prompt)
        self.draft_timer = QTimer(self);self.draft_timer.setSingleShot(True);self.draft_timer.setInterval(500)
        self.draft_timer.timeout.connect(self.save_prompt_draft);self.prompt.textChanged.connect(self.draft_timer.start)
        self.source_draft_timer = QTimer(self);self.source_draft_timer.setSingleShot(True);self.source_draft_timer.setInterval(180)
        self.source_draft_timer.timeout.connect(self.save_source_draft)
        composer = QHBoxLayout()
        self.image_button = control('Add image', self.add_image);self.image_button.setToolTip('Add an image for the website. It is sent to Qwen with your next brief.');composer.addWidget(self.image_button)
        self.stop = control('Stop', self.stop_work);composer.addWidget(self.stop)
        composer.addStretch();self.send = control('Build website', self.submit, True);composer.addWidget(self.send);chat.addLayout(composer)
        hint = QLabel('Ctrl + Enter to send · Changes save automatically');hint.setObjectName('muted');chat.addWidget(hint)
        self.splitter.addWidget(self.chat_panel)
        canvas = QWidget();right = QVBoxLayout(canvas);right.setContentsMargins(0, 0, 0, 0);right.setSpacing(0)
        toolbar = QFrame();toolbar.setObjectName('createToolbar');tools = QHBoxLayout(toolbar);tools.setContentsMargins(12, 8, 12, 8)
        tools.addWidget(control('Chat', lambda: self.chat_panel.setVisible(not self.chat_panel.isVisible())))
        self.preview_mode = QComboBox();self.preview_mode.addItems(['Swarm canvas', 'Interactive preview']);self.preview_mode.setAccessibleName('Creation preview mode')
        self.preview_mode.currentIndexChanged.connect(self.change_preview);tools.addWidget(self.preview_mode)
        self.devices = QComboBox();self.devices.addItems(['Desktop', 'Tablet · 768', 'Mobile · 390']);self.devices.currentIndexChanged.connect(self.resize_preview);self.devices.setAccessibleName('Creation viewport');tools.addWidget(self.devices)
        self.select_button = QPushButton('Select element');self.select_button.setCheckable(True);self.select_button.toggled.connect(lambda value: self.js('select', value));tools.addWidget(self.select_button)
        self.pause_button = control('Pause', self.toggle_pause);tools.addWidget(self.pause_button)
        self.speed = QComboBox();self.speed.addItems(['1×', '2×', '3×', '5×']);self.speed.setCurrentIndex(1);self.speed.setFixedWidth(58)
        self.speed.setAccessibleName('Swarm creation speed');self.speed.currentIndexChanged.connect(lambda: self.js('speed', float(self.speed.currentText().replace('×', ''))));tools.addWidget(self.speed)
        tools.addStretch();self.canvas_status = QLabel('Ready when you are');self.canvas_status.setObjectName('muted');self.canvas_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred);tools.addWidget(self.canvas_status)
        right.addWidget(toolbar)
        self.preview_host = QWidget();self.preview_host.setObjectName('createCanvas');self.preview_layout = QHBoxLayout(self.preview_host);self.preview_layout.setContentsMargins(0, 0, 0, 0);self.preview_layout.setSpacing(0)
        self.preview_layout.addStretch();self.preview_layout.addWidget(self.view);self.preview_layout.addStretch();right.addWidget(self.preview_host, 1)
        self.splitter.addWidget(canvas);self.splitter.setStretchFactor(1, 1);self.splitter.setSizes([340, 1200])
        shortcut = QShortcut(QKeySequence('Ctrl+Return'), self.prompt);shortcut.activated.connect(self.submit)
        self.scroll_animation = QPropertyAnimation(self.chat_scroll.verticalScrollBar(), b'value', self)
        self.scroll_animation.setDuration(180);self.scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.add_message('swarm', 'Describe the website you want. Then ask for changes naturally—add a section, refine a headline, change the style or remove a part. Select an element on the canvas when you want to be precise.', persist=False)

    def resizeEvent(self, event):
        super().resizeEvent(event);QTimer.singleShot(0, self.resize_preview)

    def resize_preview(self, *_):
        if self.shutting_down:return
        if not hasattr(self, 'preview_host'):
            return
        width = self.preview_host.width()
        desired = [width, min(width, 768), min(width, 390)][self.devices.currentIndex()]
        self.view.setFixedWidth(max(1, desired))

    def js(self, method, value=None):
        if self.shutting_down:return
        if not self.browser_ready:
            return
        argument = '' if value is None else json.dumps(value, ensure_ascii=False)
        self.view.page().runJavaScript('window.Creator?.' + method + '(' + argument + ');')
        if method == 'load':
            self.browser_ready = False;self.refresh()

    def show_model(self):
        if self.worker and self.worker.isRunning():
            self.activity.setText('Stop the current request before changing the model connection.');return
        ModelDialog(self).exec();self.refresh()

    def add_message(self, role, text, persist=True):
        bar = self.chat_scroll.verticalScrollBar();follow = bar.maximum() - bar.value() < 60
        bubble = QWidget();layout = QVBoxLayout(bubble);layout.setContentsMargins(0, 0, 0, 0);layout.setSpacing(6)
        label = QLabel('YOU' if role == 'user' else 'SWARM');label.setObjectName('section');layout.addWidget(label)
        content = QLabel(str(text)[:4000]);content.setTextFormat(Qt.TextFormat.PlainText);content.setWordWrap(True);content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content);self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        if persist:
            entry = {'id': uuid.uuid4().hex, 'role': role, 'text': str(text)[:8000], 'status': 'queued' if role == 'user' else 'done'}
            self.project['chat'].append(entry);self.project['chat'] = self.project['chat'][-120:];self.store.save(self.project)
        if follow:
            def scroll():
                self.scroll_animation.stop();self.scroll_animation.setStartValue(bar.value());self.scroll_animation.setEndValue(bar.maximum());self.scroll_animation.start()
            QTimer.singleShot(30, scroll)
        return entry if persist else None

    def refresh(self):
        if self.shutting_down:return
        busy = bool(self.worker and self.worker.isRunning()) or self.visual_busy
        self.title.setText(self.working.data['title'] if self.visual_busy else self.project['document']['title'])
        self.connection.setText('Model · key saved' if self.has_key() else 'Add API key')
        self.undo.setEnabled(not busy and self.project['cursor'] >= 0)
        self.redo.setEnabled(not busy and self.project['cursor'] + 1 < len(self.project['history']))
        self.export.setEnabled(bool(self.project['document']['blocks']) and not busy)
        self.stop.setVisible(busy)
        self.image_button.setEnabled(not busy)
        self.send.setEnabled(self.browser_ready and len(self.queue) < 3)
        self.send.setText('Queue change' if busy else 'Send change' if self.project['document']['blocks'] else 'Build website')
        self.preview_mode.setEnabled(not busy);self.select_button.setEnabled(not busy and bool(self.project['document']['blocks']))

    def submit(self):
        instruction = self.prompt.toPlainText().strip()
        if not instruction:
            self.prompt.setFocus();return
        if len(instruction) > 8000:
            self.activity.setText('Keep each instruction under 8,000 characters.');return
        if not self.has_key():
            self.show_model()
            if not self.has_key():
                self.activity.setText('Your brief is kept here. Add your API key when you are ready.');return
        if len(self.queue) >= 3:
            return
        self.prompt.clear();entry = self.add_message('user', instruction)
        self.queue.append((instruction, copy.deepcopy(self.target), entry['id']));self.clear_target()
        self.next_instruction();self.refresh()

    def next_instruction(self):
        if self.shutting_down:return
        if getattr(self.window(), 'closing', False):
            return
        if not self.queue or self.visual_busy or self.worker and self.worker.isRunning():
            return
        instruction, target, message_id = self.queue.pop(0);self.stopping = False;self.last_problem = '';self.current_instruction_id = message_id
        for message in self.project['chat']:
            if message.get('id') == message_id:message['status'] = 'running'
        try:
            key = self.vault.get()
        except ValueError as exc:
            self.add_message('swarm', str(exc));return
        if self.runtime_errors:
            target = dict(target or {}, preview_errors=self.runtime_errors[-6:])
        self.working = WebsiteDocument(self.project['document']);self.visual_busy = True;self.runtime_errors = []
        self.preview_mode.setCurrentIndex(0);self.js('begin')
        history = [item['text'] for item in self.project['chat'] if item['role'] == 'user' and item.get('status') not in {'queued', 'cancelled'}][-8:]
        if self.worker:self.worker.deleteLater()
        worker = GenerationWorker(self.working.data, instruction, dict(self.config), key, history, target, self)
        self.worker = worker
        worker.changed.connect(self.apply_change);worker.activity.connect(self.activity.setText)
        worker.audit_requested.connect(self.audit);worker.ready.connect(lambda document, summary: self.complete(document, summary, instruction))
        worker.problem.connect(lambda message, document: self.complete(document, message, instruction, failed=True))
        worker.finished.connect(self.worker_finished);worker.start();self.refresh()

    def apply_change(self, command):
        if self.shutting_down:return
        try:
            normalized = self.working.apply(command, validated=True)
            self.js('patch', normalized)
            self.title.setText(self.working.data['title'])
            if normalized['action'] == 'plan':
                self.activity.setText('Plan · ' + ' → '.join(normalized['steps'][:3]))
            else:
                ident = normalized.get('id', '')
                self.activity.setText({'upsert_block': 'Building ' + ident.replace('-', ' ') + '…', 'remove_block': 'Removing ' + ident.replace('-', ' ') + '…', 'set_theme': 'Setting the visual direction…', 'set_script': 'Wiring interactions…', 'set_title': 'Naming your website…'}.get(normalized['action'], 'Working…'))
                if not self.project.get('draft_active'):
                    self.project['draft_active'] = True;self.store.save(self.project)
                self.source_draft_timer.start()
        except (ValueError, OSError) as exc:
            self.stop_work();self.add_message('swarm', 'Could not apply a change: ' + str(exc))

    def audit(self):
        if self.shutting_down:return
        worker = self.worker
        if not worker:
            return
        self.js('requestAudit', worker.audit_token)

    def complete(self, document, summary, instruction, failed=False):
        if self.shutting_down:
            self.store.commit(self.project, document, ('Partial · ' if failed else '') + instruction)
            self.project['chat'].append({'role':'swarm','text':summary[:4000],'status':'done'})
            self.project['chat']=self.project['chat'][-120:];self.store.save(self.project)
            return
        self.source_draft_timer.stop()
        self.last_problem = summary if failed else ''
        for message in self.project['chat']:
            if message.get('id') == self.current_instruction_id:message['status'] = 'partial' if failed else 'done'
        if document != self.project['document']:
            self.store.commit(self.project, document, ('Partial · ' if failed else '') + instruction)
        self.add_message('swarm', summary)
        if self.stopping:
            self.visual_busy = False;self.js('load', document)
        else:self.js('end')
        self.activity.setText('Finishing the visible edits…' if self.visual_busy else 'Saved on this computer.')
        self.refresh()

    def worker_finished(self):
        if self.shutting_down:return
        self.refresh();self.next_instruction()

    def stop_work(self):
        self.stopping = True
        if self.queue:self.add_message('swarm', 'Queued instructions cancelled.')
        self.cancel_queued()
        if self.worker and self.worker.isRunning():
            self.worker.cancel();self.activity.setText('Stopping after the current change…')
        else:
            self.visual_busy = False;self.js('load', self.project['document']);self.activity.setText('Stopped. Your saved changes are kept.');self.refresh()

    def cancel_queued(self):
        cancelled = {item[2] for item in self.queue}
        for message in self.project['chat']:
            if message.get('id') in cancelled:message['status'] = 'cancelled'
        self.queue.clear()

    def engine_event(self, event):
        if self.shutting_down:return
        kind = event['type']
        if kind == 'creator-ready':
            self.browser_ready = True
            self.js('speed', float(self.speed.currentText().replace('×', '')))
            if self.pending_document is not None:
                document = self.pending_document;self.pending_document = None;self.js('load', document)
            self.refresh()
        elif kind == 'finished':
            self.visual_busy = False;self.canvas_status.setText('Partial changes saved' if self.last_problem else 'All changes saved')
            self.activity.setText('Ready to continue from the last completed change.' if self.last_problem else 'Saved on this computer. Tell the swarm what to change next.')
            self.refresh();QTimer.singleShot(0, self.next_instruction)
        elif kind == 'progress' and self.visual_busy:
            self.canvas_status.setText(f"{event.get('completed', 0)} / {event.get('total', 0)} visual tasks")
            self.pause_button.setText('Resume' if event.get('paused') else 'Pause')
        elif kind == 'creator-audit' and self.worker and event.get('token') == self.worker.audit_token:
            self.worker.audit = event.get('report', {}) if isinstance(event.get('report'), dict) else {}
            self.worker.audit['runtime_errors'] = self.runtime_errors[-6:]
            self.worker.audit_event.set()
        elif kind == 'creator-selection':
            block = str(event.get('block', ''))[:64]
            if block not in [b['id'] for b in self.project['document']['blocks']]:
                return
            self.target = {key: str(event.get(key, ''))[:200] for key in ('block', 'tag', 'text', 'id')}
            self.target_label.setText('Editing ' + block + ' · ' + self.target['tag'])
            self.target_row.show();self.select_button.setChecked(False);self.prompt.setFocus()
        elif kind == 'creator-runtime-error':
            self.runtime_errors.append(str(event.get('message', 'Script error'))[:240])
            self.canvas_status.setText('Preview script needs attention — ask the swarm to fix it')
        elif kind == 'creator-preview-ready':
            self.canvas_status.setText('Interactive preview')
        elif kind == 'error':
            self.add_message('swarm', 'Preview: ' + str(event.get('message', 'The preview could not load.'))[:300])

    def clear_target(self):
        self.target = None;self.target_row.hide();self.select_button.setChecked(False)

    def change_preview(self, index):
        self.js('preview', index == 1)
        self.pause_button.setEnabled(index == 0);self.speed.setEnabled(index == 0)

    def toggle_pause(self):
        self.js('pause')

    def restore(self, direction):
        if self.visual_busy or self.worker and self.worker.isRunning():
            return
        self.store.restore(self.project, self.project['cursor'] + direction)
        self.working = WebsiteDocument(self.project['document']);self.preview_mode.setCurrentIndex(0);self.js('load', self.project['document']);self.refresh()
        self.activity.setText('Previous version restored.' if direction < 0 else 'Next version restored.')

    def new_project(self):
        if self.visual_busy or self.worker and self.worker.isRunning():
            self.activity.setText('Finish or stop the current edits before opening another project.');return
        self.save_prompt_draft();self.project = self.store.new();self.render_project()

    def render_project(self):
        self.last_problem = '';self.working = WebsiteDocument(self.project['document']);self.clear_target();self.queue.clear()
        self.prompt.setPlainText(self.project.get('draft_prompt', ''))
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        for message in self.project['chat']:
            self.add_message(message['role'], message['text'], persist=False)
        if not self.project['chat']:
            self.add_message('swarm', 'What would you like to create?', persist=False)
        self.preview_mode.setCurrentIndex(0)
        if self.browser_ready:self.js('load', self.project['document'])
        else:self.pending_document = copy.deepcopy(self.project['document'])
        self.refresh()
        self.activity.setText('Recovered unfinished changes. Undo returns to the previous saved version.' if self.project.pop('_recovered', False) else 'Saved on this computer.' if self.project['document']['blocks'] else 'Describe a website to begin.')

    def open_project(self):
        if self.visual_busy or self.worker and self.worker.isRunning():
            self.activity.setText('Finish or stop the current edits first.');return
        dialog = QDialog(self);dialog.setWindowTitle('Open a created website');dialog.resize(560, 400)
        layout = QVBoxLayout(dialog);listing = QListWidget();layout.addWidget(listing)
        for ident, name in self.store.recent():
            item = QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole, ident);listing.addItem(item)
        def choose():
            if listing.currentItem():
                try:
                    self.save_prompt_draft();self.project = self.store.load(listing.currentItem().data(Qt.ItemDataRole.UserRole));self.render_project();dialog.accept()
                except (OSError, ValueError, KeyError):
                    QMessageBox.warning(dialog, 'Could not open', 'This project is missing files or has invalid metadata.')
        listing.itemDoubleClicked.connect(choose);layout.addWidget(control('Open website', choose, True));layout.addWidget(control('Close', dialog.reject));dialog.exec()

    def export_project(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export website', self.project['document']['title'] + '.zip', 'Website ZIP (*.zip)')
        if not path:
            return
        try:
            self.store.export(self.project, path);self.activity.setText('Website ZIP exported. It runs without the model API.')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))

    def add_image(self):
        if self.visual_busy or self.worker and self.worker.isRunning():
            return
        assets = self.project['document'].setdefault('assets', {})
        if len(assets) >= 6:
            self.activity.setText('Use up to six uploaded images per website.');return
        name, _ = QFileDialog.getOpenFileName(self, 'Add a website image', '', 'Images (*.png *.jpg *.jpeg *.webp)')
        if not name:
            return
        try:
            from PIL import Image, ImageOps
            path = Path(name)
            if path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('Choose an image smaller than 20 MB.')
            with Image.open(path) as image:
                if image.width * image.height > 24000000:
                    raise ValueError('Choose an image under 24 megapixels.')
                alpha = image.mode in {'RGBA', 'LA'} or 'transparency' in image.info
                image = ImageOps.exif_transpose(image).convert('RGBA' if alpha else 'RGB');image.thumbnail((1200, 1200))
                fmt = 'PNG' if alpha else 'JPEG'
                output = io.BytesIO();image.save(output, fmt, quality=78, optimize=True)
                if output.tell() > 120000:
                    image.thumbnail((850, 850));output = io.BytesIO();image.save(output, fmt, quality=65, optimize=True)
                if output.tell() > 120000:
                    raise ValueError('This image is too detailed for the embedded image budget. Use a smaller image.')
                ident = 'image-' + uuid.uuid4().hex[:10]
                assets[ident] = {'name': path.name[:100], 'width': image.width, 'height': image.height,
                                 'data': ('data:image/png;base64,' if alpha else 'data:image/jpeg;base64,') + base64.b64encode(output.getvalue()).decode('ascii')}
            self.store.save(self.project)
            self.add_message('swarm', 'Image added: ' + path.name + '. Tell the swarm where to use it.')
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            self.activity.setText('Could not add image: ' + str(exc)[:180])

    def save_prompt_draft(self):
        if self.shutting_down:return
        self.draft_timer.stop();self.project['draft_prompt'] = self.prompt.toPlainText()[:8000];self.store.save(self.project)

    def save_source_draft(self):
        if self.shutting_down:return
        try:write_json(self.store.path(self.project['id']) / 'draft.json', self.working.data)
        except OSError:self.activity.setText('Could not autosave the draft. Check available disk space.')

    def preview_failed(self):
        if self.shutting_down:return
        self.browser_ready = False;self.visual_busy = False
        if self.worker and self.worker.isRunning():self.worker.cancel()
        self.activity.setText('The preview renderer stopped. Your saved changes are safe. Reopen this workspace to reload it.')
        self.refresh()

    def begin_shutdown(self):
        if self.shutting_down:return
        self.setEnabled(False)
        self.cancel_queued();self.stopping=True
        self.save_prompt_draft();self.source_draft_timer.stop()
        if self.project.get('draft_active'):self.save_source_draft()
        self.shutting_down=True
