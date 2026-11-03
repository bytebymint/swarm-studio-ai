# Windows DLL isolation

The first packaged launch failed at `PySide6.QtCore` despite working from Python.
Inspection of PE imports and `Analysis-00.toc` identified an incompatible
`icuuc.dll` copied from the Codex host's Poppler tool directory. That library
exports version-suffixed ICU 78 symbols; QtCore requests the Windows unversioned
ICU facade. A development Python process correctly loaded System32's facade.

