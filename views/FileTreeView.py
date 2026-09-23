from PyQt5.QtWidgets import QWidget, QFileSystemModel, QTreeView, QMenu, QApplication
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import Qt, QEvent, pyqtSignal
import os

from src.ReadfileData import h5_preview_results_group, zi_h5_preview

from enum import Enum, auto

class ItemType(Enum):
    DIR = auto()
    FILE = auto()

class FileType(Enum):
    TXT = auto()
    HDF5 = auto()
    HDF5_WITH_RESULT = auto()
    H5_ZI = auto()


class FileTreeView(QWidget):
    sig_askOpenFile = pyqtSignal(str, dict)

    def __init__(self, main_view):
        super().__init__()
        self.main_view = main_view
        self.clipboard = QApplication.clipboard()

        self.model = QFileSystemModel()
        self.view = QTreeView()
        self.view.setModel(self.model)

        self.new_tab_asked = False

        # arrange columns
        self.view.setColumnHidden(2, True)  # hide type
        self.view.setColumnWidth(0, 300)  # resize name

        # right click menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.showContextMenu)

        # key press
        self.view.keyPressEvent = self.onKeyPress

        self.view.doubleClicked.connect(lambda *args: self.askOpenCurrentIndex())
        # on item changed
        self.view.selectionModel().currentChanged.connect(self.onItemChanged)

        # drag out
        self.view.setDragEnabled(True)

    def makeMenu(self, item_type: ItemType, path):
        """ Build context menu based on item_type """
        menu = QMenu()

        ## special: dir | file
        match item_type:
            case ItemType.FILE:
                actions = [
                    ("Open", lambda: self.sig_askOpenFile.emit(path, {})),
                    ("Open in new tab", lambda: (setattr(self, "new_tab_asked", True), self.askOpenCurrentIndex())),
                    ("Open in notepad", self.openInTE),
                ]

                match self.get_file_type(path):
                    case FileType.HDF5_WITH_RESULT:
                        actions += h5_preview_results_group(
                            path,
                            lambda res_grp: [
                                (f"{group_name}.{res_name}", lambda g=group_name, r=res_name: self.onOpenResultGroup(g, r))
                                for group_name in res_grp
                                for res_name in res_grp[group_name].attrs["result_data_names"]
                            ],
                        )

            case ItemType.DIR:
                actions = [("Open", self.openDir)]

        for name, fn in actions:
            menu.addAction(name, fn)

        ## general
        menu.addAction("Copy path", self.copyPath)
        menu.addSeparator()
        menu.addAction("Go up a dir", self.goUpDir)
        # menu.addAction('Open in file explorer', self.openInFE)
        expand_all_action = [
            ("Expand all", self.view.expandAll),
            ("Collapse all", self.view.collapseAll),
        ]
        for action in expand_all_action:
            menu.addAction(action[0], action[1])
        menu.addAction("Refresh", self.refresh)
        return menu

    def get_type(self, index) -> ItemType:
        if self.model.isDir(index):
            return ItemType.DIR
        else:
            return ItemType.FILE
        
    def get_file_type(self, path) -> FileType:
        if path.endswith(".hdf5"):
            if h5_preview_results_group(path):
                return FileType.HDF5_WITH_RESULT
            return FileType.HDF5

        elif path.endswith(".h5"):
            return FileType.H5_ZI

        elif path.endswith(".txt"):
            return FileType.TXT

        

    def showContextMenu(self, pos):
        index = self.view.indexAt(pos)
        if not index.isValid():
            return
        menu = self.makeMenu(self.get_type(index), self.model.filePath(index))
        menu.exec_(self.view.mapToGlobal(pos))

    def onKeyPress(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # Enter or Space -> open file
        if key in (Qt.Key_Return, Qt.Key_Space):
            self.askOpenCurrentIndex()

        elif key == Qt.Key_H:
            self.view.keyPressEvent(
                QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.NoModifier)
            )
        elif key == Qt.Key_L:
            self.view.keyPressEvent(
                QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier)
            )
        elif key == Qt.Key_J:
            steps = 5 if modifiers & Qt.ShiftModifier else 1
            for _ in range(steps):
                self.view.keyPressEvent(
                    QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier)
                )
        elif key == Qt.Key_K:
            steps = 5 if modifiers & Qt.ShiftModifier else 1
            for _ in range(steps):
                self.view.keyPressEvent(
                    QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier)
                )
        # g / Shift+G navigation
        elif key == Qt.Key_G:
            if modifiers & Qt.ShiftModifier:
                self.view.keyPressEvent(
                    QKeyEvent(QEvent.KeyPress, Qt.Key_End, Qt.NoModifier)
                )
            else:
                self.view.keyPressEvent(
                    QKeyEvent(QEvent.KeyPress, Qt.Key_Home, Qt.NoModifier)
                )
        elif key == Qt.Key_Y:
            self.copyPath()

        elif key == Qt.Key_W:
            if modifiers & Qt.ControlModifier:
                self.main_view.closeTab()

        elif (key == Qt.Key_Tab and modifiers & Qt.ControlModifier) or (
            key == Qt.Key_Backtab and modifiers & Qt.ControlModifier
        ):
            tabs = self.main_view.graphic_tabs
            n = tabs.count()
            if n == 0:
                return

            i = tabs.currentIndex()

            if key == Qt.Key_Backtab:
                tabs.setCurrentIndex((i - 1) % n)
            else:
                tabs.setCurrentIndex((i + 1) % n)
        else:
            QTreeView.keyPressEvent(self.view, event)

    def onItemChanged(self, current, previous):
        """ Update preview based on item type """

        self.main_view.preview_widget.clear()
        match self.get_type(self.view.currentIndex()):
            case ItemType.DIR:
                self.main_view.preview_widget.clear()

            case ItemType.FILE:
                path = self.model.filePath(current)
                file_type = self.get_file_type(path)

                if file_type is FileType.HDF5_WITH_RESULT:
                    h5_preview_results_group(
                        path,
                        handler=lambda results_group: 
                            self.main_view.preview_widget.showResultGroup(results_group,
                            self.onOpenResultGroup)
                    )
                elif file_type is FileType.H5_ZI:
                    zi_h5_preview(
                        path,
                        handler = lambda file: self.main_view.preview_widget.showZiGroup(file, self.onOpenZiGroup),
                    )

                if png := self.main_view.hlog.db.get_fig(path):
                    self.main_view.preview_widget.showPng(png)


    def onOpenResultGroup(self, group_name, result_name):
        self.askOpenCurrentIndex(
            loading_kwargs={
                "hdf5": {"group_name": group_name, "result_name": result_name}
            }
        )

    def onOpenZiGroup(self, group_name):
        self.askOpenCurrentIndex(
            loading_kwargs={
                "zi_h5": {"group_name": group_name}
            }
        )
    ### ACTIONS ###

    def askOpenCurrentIndex(self, loading_kwargs={}):

        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            self.new_tab_asked = True
        
        index = self.view.currentIndex()
        path = self.model.filePath(index)

        match self.get_type(index):
            case ItemType.FILE:
                self.sig_askOpenFile.emit(path, loading_kwargs)
            case ItemType.DIR:
                pass

    def changePath(self, path):
        if not os.path.exists(path):
            self.main_view.write("Path does not exist: " + path)
            return
        self.model.setRootPath(path)
        self.view.setRootIndex(self.model.index(path))
        print("Path changed to:", path)

    def openInTE(self):
        # try to open in text editor
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        index = self.view.currentIndex()
        path = self.model.filePath(index)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.main_view.write(f"Could not open in text editor: {path}")

    def goUpDir(self):
        path = self.model.filePath(self.view.rootIndex())
        path = os.path.dirname(path)
        self.changePath(path)

    def openDir(self):
        index = self.view.currentIndex()
        path = self.model.filePath(index)
        self.changePath(path)

    def copyPath(self):
        index = self.view.currentIndex()
        path = self.model.filePath(index)
        self.clipboard.setText(path)
        self.main_view.write("Copied: " + path)

    def refresh(self):
        path = self.model.filePath(self.view.rootIndex())
        self.model.setRootPath("")
        self.model.setRootPath(path)
