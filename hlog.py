from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QIcon

import os
import sys
import traceback
from typing import Optional

from views.MainView import MainView
from src.ReadfileData import ReadfileData
from src.QuickThread import QuickThread
from src.Popup import Popup
from src.Database import DBPlots


class hlog(QObject):
    sig_fileOpened = pyqtSignal(ReadfileData, object) #ReadfileData, bool

    def __init__(self, path: str, app: Optional[QApplication] = None, file=None):
        super().__init__()
        self.app = app

        project_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_dir, "plots.db")
        self.db = DBPlots(db_path)

        self.main_view = mv = MainView(self)
        self.pop = Popup()

        self.loading_thread = None
        self.current_data = None # for debug

        # SIGNALS ingoing from views
        mv.file_tree.sig_askOpenFile.connect(self.openFile)

        # SIGNALS outgoing
        self.sig_fileOpened.connect(mv.onFileOpened)

        # First exec:
        self.main_view.file_tree.changePath(path)
        # self.write(':)')
        if file:
            self.openFile(file)

    def openFile(self, path, loading_kwargs={}):
        self.main_view.write("Opening file: " + path)

        # ReadfileData in a thread
        # ReadfileData.from_filepath(path)
        self.loading_thread = QuickThread(ReadfileData.from_filepath, filepath=path, loading_kwargs=loading_kwargs)
        self.loading_thread.sig_finished.connect(self.onFileOpened)
        self.loading_thread.sig_error.connect(self.onFileOpenError)
        self.loading_thread.start()

        # else:
        #    self.main_view.write('File type not supported :(\n'+path)

    def onFileOpened(self, rfdata_list, fn_args, fn_kwargs):
        # called on thread success
        filepath = fn_kwargs.get("filepath")
        self.main_view.write("Opened: " + filepath)
        self.current_data = rfdata_list
        for rfdata in rfdata_list:
            self.sig_fileOpened.emit(rfdata, self.main_view.file_tree.new_tab_asked)
        self.main_view.file_tree.new_tab_asked = False

    def onFileOpenError(self, exception, fn_args, fn_kwargs):
        filepath = fn_kwargs.get("filepath")
        self.main_view.write("Could not open file: " + filepath)
        print(exception)
        traceback.print_exception(
            type(exception),
            exception,
            exception.__traceback__
        )

    def close(self):
        pass


if __name__ == "__main__":
    # Start with no arguments => current directory
    # Start with a directory => load in that directory
    # Start with a file => load that file, and set the directory to the directory above
    # arg --with-app => start with a QApplication (for standalone use)

    app = None
    path, file = os.getcwd(), None

    if "--with-app" in sys.argv:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication([])
        app.setWindowIcon(QIcon("resources/hlog.png"))
        sys.argv.remove("--with-app")

    if len(sys.argv) > 1:
        if os.path.isdir(sys.argv[1]):
            path = sys.argv[1]
        elif os.path.isfile(sys.argv[1]):
            file = sys.argv[1]
            path = os.path.dirname(file)

    hl = hlog(path, app, file=file)
    hl.main_view.show()
    hl.main_view.write("hi")

    if app is not None:
        sys.exit(app.exec_())
