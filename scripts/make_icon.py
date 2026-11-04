from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PIL import Image

root=Path(__file__).resolve().parent.parent
(root/'assets').mkdir(exist_ok=True)
image=QImage(256,256,QImage.Format.Format_ARGB32)
