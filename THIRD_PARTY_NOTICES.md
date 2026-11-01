# Third-party materials and notices

The [SWARM STUDIO license](LICENSE) covers Byte by Mint's original materials.
It does not replace or restrict licenses granted by third-party authors.

## Runtime and build components

The project uses Python, PySide6/Qt and Qt WebEngine/Chromium, HTTPX and its
dependencies, Beautiful Soup, lxml, Pillow, Playwright, PyAV/FFmpeg, NumPy,
PyInstaller and test/build dependencies. Their copyright notices and license
terms remain applicable. FFmpeg codec libraries may have distinct terms.

`scripts/collect_licenses.py` collects installed package notices into
`dist/SwarmStudio/Notices/` during a Windows build. `PACKAGES.txt` lists the
collected package versions and reported license information. Keep the complete
distribution, including those notices and any bundled dependency licenses,
together. The notice collector is an aid, not a substitute for checking the
obligations of the specific dependencies and codecs you distribute.

Installed Microsoft Edge and Google Chrome are not bundled in the project.
Recording launches a fresh browser session through Playwright and uses local
project files. The installed browser remains governed by its publisher's terms.

## Website content and demonstration footage

Captured websites retain their owners' rights in designs, text, images, fonts,
logos, media and trademarks. Saving a local reconstruction or a recording does
not transfer those rights or establish permission to republish it.

The README animation is a ten-second excerpt of a user-supplied SWARM STUDIO
recording. It depicts a third-party website solely to demonstrate the software's
operation. Third-party branding and content remain the property of their
respective owners; inclusion does not imply sponsorship, affiliation,
endorsement or permission for further reuse. This caption is not a claim of a
copyright exception or a grant of rights. Confirm appropriate permissions before
redistributing or publishing the footage.

The Fieldwork page under `web/demo/` is the independently created offline demo
used for local smoke checks and recordings.

## Isolated reference material

The separately supplied `swarm-cursors-main/` reference has no published license
identified in its supplied materials. It is excluded from Git and from the app
distribution. Its engine, demo, recordings and assets are not licensed under
SWARM STUDIO's license. See [reference provenance](docs/REFERENCE.md).

## Contact

For permission involving Byte by Mint's materials, contact
[info@bytebymint.space](mailto:info@bytebymint.space). For third-party materials,
contact the relevant rights holder.
