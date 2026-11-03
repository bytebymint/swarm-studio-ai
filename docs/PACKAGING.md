# Windows DLL isolation

The first packaged launch failed at `PySide6.QtCore` despite working from Python.
Inspection of PE imports and `Analysis-00.toc` identified an incompatible
`icuuc.dll` copied from the Codex host's Poppler tool directory. That library
exports version-suffixed ICU 78 symbols; QtCore requests the Windows unversioned
ICU facade. A development Python process correctly loaded System32's facade.

The specification now replaces the packaging process's PATH with Python, its Qt
packages and Windows system directories, rejects binaries resolved from the Codex
host runtime, and excludes app-local ICU facades. Windows 11 supplies the required
system interface. This changes no machine-wide PATH or installed Windows DLL.

