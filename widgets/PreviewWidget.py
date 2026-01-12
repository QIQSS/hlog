from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QLabel(alignment=Qt.AlignCenter)
        self.label.setMinimumSize(0, 0)
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        self._src_pixmap = None
        self._last_size = None

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def showPng(self, png_bytes):
        pm = QPixmap()
        pm.loadFromData(png_bytes, "PNG")
        self._src_pixmap = pm
        self._last_size = None
        self._updatePixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updatePixmap()

    def _updatePixmap(self):
        if not self._src_pixmap:
            return

        size = self.label.size()
        if size == self._last_size:
            return

        self._last_size = size
        self.label.setPixmap(
            self._src_pixmap.scaled(
                size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def clear(self):
        self._src_pixmap = None
        self.label.clear()
