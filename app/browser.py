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
