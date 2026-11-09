import json
import logging

from PySide6.QtCore import QFile, QIODevice, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.config import WEB

WORLD = QWebEngineScript.ScriptWorldId.ApplicationWorld


class RestrictedPage(QWebEnginePage):
    blocked = Signal(str)

    def __init__(self, profile, parent, trusted_origin=None, trusted_entry='player.html'):
        super().__init__(profile, parent)
        self.trusted_origin = trusted_origin
        self.trusted_entry = trusted_entry
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, False)
        self.certificateError.connect(lambda error: error.rejectCertificate())
        if hasattr(self, 'permissionRequested'):
            self.permissionRequested.connect(lambda permission: permission.deny())

    def acceptNavigationRequest(self, url, nav_type, is_main):
        if not is_main:
            return True
        if self.trusted_origin and url.toString().split('#')[0].split('?')[0] != self.trusted_origin + '/ui/' + self.trusted_entry:
            self.blocked.emit('Navigation outside the trusted animation page was blocked.')
            return False
        if url.scheme() not in {'http', 'https', 'about'}:
            self.blocked.emit('This URL scheme is not supported in the website viewport.')
            return False
        return True

    def javaScriptConsoleMessage(self, level, message, line, source):
        logging.info('Chromium %s:%s %s', source, line, message)


class Bridge(QObject):
    received = Signal(object)

    @Slot(str)
    def publish(self, raw):
        if len(raw) > 65536:
            return
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get('type'), str):
                self.received.emit(data)
        except (ValueError, TypeError):
            logging.warning('Invalid playback event')


class BrowserController(QObject):
    capture_ready = Signal(object)
    error = Signal(str)
    phase = Signal(str)
    navigated = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile = QWebEngineProfile(self)  # Off-the-record, memory-only profile.
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.downloadRequested.connect(lambda download: download.cancel())
        self.source = QWebEngineView()
        self.page = RestrictedPage(self.profile, self.source)
        self.source.setPage(self.page)
        self.page.blocked.connect(self.error)
        self.page.renderProcessTerminated.connect(lambda *_: self.error.emit('Chromium stopped unexpectedly. Reload the website to recover.'))
        self.source.loadStarted.connect(self._load_started)
        self.source.loadFinished.connect(self._load_finished)
        self.timer = QTimer(self)
        self.timer.setInterval(130)
        self.timer.timeout.connect(self.poll)
        self.navigation_timeout = QTimer(self)
        self.navigation_timeout.setSingleShot(True)
        self.navigation_timeout.timeout.connect(self._timed_out)
        self.ready = False
        self.capturing = False
        self.generation = 0

    def _load_started(self):
        if self.capturing:
            self.cancel()
            self.error.emit('The page navigated during capture. Wait for it to finish, then capture again.')
        self.ready = False
        self.navigation_timeout.start(30000)
        self.phase.emit('Loading website…')

    def _load_finished(self, ok):
        self.navigation_timeout.stop()
        self.ready = ok
        self.navigated.emit(ok)
        if not ok:
            self.error.emit('The website could not load. Check the address, network and certificate, then reload.')
        else:
            self.phase.emit('Website ready. Initialize the swarm when the page looks right.')

    def _timed_out(self):
        self.source.stop()
        self.error.emit('Navigation exceeded 30 seconds. The website may still be loading; reload or try a simpler page.')

    def navigate(self, url):
        self.ready = False
        self.source.setUrl(QUrl(url))

    def capture(self, settings):
        if not self.ready:
            self.error.emit('Load a website successfully before initializing the swarm.')
            return
        self.generation += 1
        self.capturing = True
        self.settings = settings.copy()
        self.elapsed = 0
        script = (WEB / 'capture.js').read_text('utf-8')
        self.page.runJavaScript(script, WORLD)
        self.page.runJavaScript('window.StudioCapture.start(' + json.dumps(settings) + '); void 0;', WORLD)
        self.timer.start()
        self.phase.emit('Discovering page content…')

    def poll(self):
        self.elapsed += self.timer.interval()
        if self.elapsed > (self.settings.get('timeout', 25) + 5) * 1000:
            self.cancel()
            self.error.emit('Capture reached its time limit. Increase the timeout or reduce the element limit.')
            return
        generation = self.generation
        def received(raw):
            if generation != self.generation or not self.capturing:
                return
            if not raw:
                self.timer.stop()
                self.capturing = False
                self.error.emit('Capture script did not respond. Reload the website and retry.')
                return
            try:
                state = json.loads(raw)
            except (ValueError, TypeError):
                return
            if state.get('status') == 'complete':
                self.timer.stop()
                self.capturing = False
                self.capture_ready.emit(state['result'])
            elif state.get('status') in {'error', 'cancelled'}:
                self.timer.stop()
                self.capturing = False
                self.error.emit(state.get('error', 'Capture cancelled.'))
        self.page.runJavaScript('JSON.stringify(window.StudioCapture?.state || null)', WORLD, received)

    def cancel(self):
        self.generation += 1
        self.timer.stop()
        self.capturing = False
        self.page.runJavaScript('window.StudioCapture?.cancel()', WORLD)


def make_player(profile, origin, parent=None, entry='player.html'):
    view = QWebEngineView(parent)
    page = RestrictedPage(profile, view, trusted_origin=origin, trusted_entry=entry)
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
    view.setPage(page)
    channel = QWebChannel(page)
    bridge = Bridge(channel)
    channel.registerObject('bridge', bridge)
    page.setWebChannel(channel)
    # qrc URLs are intentionally not exposed to arbitrary HTTP documents.
    # Inject Qt's bundled bridge library only into this dedicated trusted page.
    source = QFile(':/qtwebchannel/qwebchannel.js')
    if not source.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError('Qt WebChannel JavaScript resource is unavailable.')
    script = QWebEngineScript()
    script.setName('trusted-studio-channel')
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    script.setSourceCode(bytes(source.readAll()).decode('utf-8'))
    source.close()
    page.scripts().insert(script)
    view.channel, view.bridge = channel, bridge
    return view
