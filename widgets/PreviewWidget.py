from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

import numpy as np
import h5py

from typing import Callable


class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.dict = DictPreview()
        self.image = ImgPreview()

        layout = QVBoxLayout(self)
        layout.addWidget(self.dict)
        layout.addWidget(self.image)

        self.clear()

    def showPng(self, png_bytes):
        self.image.showPng(png_bytes)

    def showResultGroup(self, results_group, ask_load_fn):
        self.dict.show()
        self.dict.set_result_group_data(results_group, ask_load_fn)

    def showZiGroup(self, zi_h5_file, ask_load_fn):
        self.dict.show()
        self.dict.set_zi_group_data(zi_h5_file, ask_load_fn)

    def clear(self):
        self.image.clear()
        self.dict.clear()
        self.dict.hide()


class ImgPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignCenter)
        # self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self._src_pixmap = None
        self._last_size = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updatePixmap()

    def clear(self):
        self._src_pixmap = None
        self._last_size = None
        super().clear()

    def showPng(self, png_bytes):
        pm = QPixmap()
        if not pm.loadFromData(png_bytes, "PNG"):
            self.clear()
            return

        self._src_pixmap = pm

        size = self.size()
        if size == self._last_size:
            return

        self.setPixmap(
            self._src_pixmap.scaled(
                size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _updatePixmap(self):
        if self._src_pixmap is None or self._src_pixmap.isNull():
            return

        size = self.size()
        if size == self._last_size:
            return

        self._last_size = size

        self.setPixmap(
            self._src_pixmap.scaled(
                size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


class DictPreview(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setColumnCount(2)
        self.setHeaderLabels(["Name", "Info"])
        self.setAlternatingRowColors(True)
        self.itemDoubleClicked.connect(self.onItemDoubleClick)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            item = self.currentItem()
            if item is not None:
                self.onItemDoubleClick(item, 0)
        else:
            super().keyPressEvent(event)
            
    def resize_fit(self):
        # resize fit to height
        rows = self.model().rowCount()
        for i in range(self.topLevelItemCount()):
            rows += self.topLevelItem(i).childCount()
            for j in range(self.topLevelItem(i).childCount()):
                rows += self.topLevelItem(i).child(j).childCount()

        row_h = self.sizeHintForRow(0) if rows else self.fontMetrics().height() + 6
        height = self.header().height() + rows * row_h + 2 * self.frameWidth()
        self.setFixedHeight(height)

    def set_result_group_data(
        self,
        result_group: h5py.Group,
        ask_load_fn: Callable[[str, str], bool]
    ):
        """
        ask_load_fn ignature: ask_load_fn(groupname: str, result_name: str)
        """
        self.clear()

        for group_name, group in result_group.items():
            group_item = QTreeWidgetItem([group_name])
            self.addTopLevelItem(group_item)
            group_item.setExpanded(True)


            axes_item = QTreeWidgetItem(["Axes"])
            results_item = QTreeWidgetItem(["Results"])
            group_item.addChild(axes_item)
            group_item.addChild(results_item)
            axes_item.setExpanded(False)
            results_item.setExpanded(True)

            data_names = group.attrs["result_data_names"]
            ax_names = group.attrs["sweeped_ax_names"]

            for ax_name in ax_names:
                ax = group.get(ax_name)
                info = f"len={len(ax)} dtype={ax.dtype}"
                item = QTreeWidgetItem([ax_name, info])
                item.setData(0, Qt.UserRole, "ax")
                axes_item.addChild(item)
            for data_name in data_names:
                data = group.get(data_name)
                info = f"{data.shape} {data.attrs.get('axes')}, dtype={data.dtype}"
                if (res_type:=data.attrs.get("res_type", None)):
                    info += f" res_type={res_type}"
                item = QTreeWidgetItem([data_name, info])
                item.setData(0, Qt.UserRole, "result")
                item.setData(1, Qt.UserRole, group_name)
                item.setData(2, Qt.UserRole, data_name)
                item.setData(3, Qt.UserRole, ask_load_fn)
                results_item.addChild(item)

        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resize_fit()

    def set_zi_group_data(
        self,
        zi_h5_file: h5py.File,
        ask_load_fn: Callable[[str, str], bool]
    ):
        """
        ask_load_fn ignature: ask_load_fn(groupname: str, result_name: str)
        """
        self.clear()
        for sweep_lbl in zi_h5_file:
            item = QTreeWidgetItem([sweep_lbl])
            self.addTopLevelItem(item)
            
            item.setData(0, Qt.UserRole, "zi_sweep")
            item.setData(1, Qt.UserRole, sweep_lbl)
            item.setData(2, Qt.UserRole, ask_load_fn)
        self.resize_fit()


    def onItemDoubleClick(self, item, column):
        if item.data(0, Qt.UserRole) == "result":
            group_name = item.data(1, Qt.UserRole)
            data_name = item.data(2, Qt.UserRole)
            ask_load_fn = item.data(3, Qt.UserRole)
            ask_load_fn(group_name, data_name)

        elif item.data(0, Qt.UserRole) == "zi_sweep":
            group_name = item.data(1, Qt.UserRole)
            ask_load_fn = item.data(2, Qt.UserRole)
            ask_load_fn(group_name)