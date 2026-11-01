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

    def __init__(self, profile, parent, trusted_origin=None):
        super().__init__(profile, parent)
        self.trusted_origin = trusted_origin
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
        if self.trusted_origin and not url.toString().startswith(self.trusted_origin + '/ui/player.html'):
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
