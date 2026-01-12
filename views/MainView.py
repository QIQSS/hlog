from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QSplitter, QWidget, QTabWidget, QTabBar
from PyQt5.QtWidgets import QToolBar, QAction, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import pyqtgraph as pg

from views.MPLView import MPLView
from widgets.MPLTraceWidget import MPLTraceWidget
from views.FilterTreeView import FilterTreeView
from views.SettingTreeView import SettingTreeView
from views.SweepTreeView import SweepTreeView
from views.FileTreeView import FileTreeView

from widgets.CustomQWidgets import CustomTabWidget
from widgets.PreviewWidget import PreviewWidget

from src.ReadfileData import ReadfileData

import numpy as np
import os


class MainView(QMainWindow):
    """
    Gère les différentes vues
    """

    def __init__(self, hlog="to_remove"):
        super().__init__()
        self.hlog = hlog
        self.setWindowTitle('hlog')
        self.resize(1000, 600)
        icon = pg.QtGui.QIcon('./resources/icon.png')
        self.setWindowIcon(icon)
        
        self.block_update = False

        ## extra windows
        # TODO: remove `self` dependence
        self.trace_window = MPLTraceWidget(self)
        
        ## MAIN LAYOUT
        self.file_tree = FileTreeView(self)
        self.graphic_tabs = CustomTabWidget(self)
        self.graphic_tabs.tabCloseRequested.connect(self.closeTab)

        self.file_preview_splitter = QSplitter(2)
        self.preview_widget = PreviewWidget(parent=self.file_preview_splitter)
        self.file_preview_splitter.addWidget(self.file_tree.view)
        self.file_preview_splitter.addWidget(self.preview_widget)

        # Splitter: (FILES, TABS)
        self.v_splitter = QSplitter()
        self.v_splitter.addWidget(self.file_preview_splitter)
        self.v_splitter.addWidget(self.graphic_tabs)
        self.setCentralWidget(self.v_splitter)
        self.v_splitter.setSizes([300, 500])
        ##

    def newTab(self, name:str):
        """ Build tab layout
        return: sweep_tree, filter_tree, setting_tree, graph
        
        """
        # LAYOUT
        graph = MPLView(self)
        # --
        sweep_tree = SweepTreeView()
        filter_tree = FilterTreeView()
        setting_tree = SettingTreeView()
        # bottom (sweep, [analyse, graph settings])
        setting_tabs = QTabWidget()
        setting_tabs.addTab(filter_tree.tree, 'Analyse')
        #setting_tabs.addTab(setting_tree.tree, 'Graph')

        bottom_splitter = QSplitter()
        bottom_splitter.addWidget(sweep_tree.tree)
        bottom_splitter.addWidget(setting_tabs)
        bottom_splitter.setSizes([200, 1])

        # main splitter
        layout = QSplitter(2)
        layout.addWidget(graph)
        layout.addWidget(bottom_splitter)
        layout.setSizes([250, 100])

        # saving trees for easy retrieve
        layout.sweep_tree = sweep_tree
        layout.filter_tree = filter_tree
        layout.setting_tree = setting_tree
        layout.graph = graph

        # add the tab
        self.graphic_tabs.addTab(layout, name)
        self.graphic_tabs.setCurrentWidget(layout)

        return sweep_tree, filter_tree, setting_tree, graph

    def currentTab(self, name):
        layout = self.graphic_tabs.currentWidget()
        if not layout:
            return self.newTab(name)

        sweep_tree  = layout.sweep_tree
        filter_tree = layout.filter_tree
        setting_tree = layout.setting_tree
        graph = layout.graph

        index = self.graphic_tabs.currentIndex()
        self.graphic_tabs.setTabText(index, name)

        return sweep_tree, filter_tree, setting_tree, graph

    def closeTab(self, index=None):
        if not index:
            index = self.graphic_tabs.currentIndex()
        self.graphic_tabs.removeTab(index)

    def write(self, text):
        print(text)
        self.statusBar().showMessage(text)

    def onFileOpened(self, rfdata, new_tab_asked:bool):

        fn = {True:self.newTab, False:self.currentTab}[new_tab_asked]
        sweep_tree, filter_tree, setting_tree, graph = fn(name=rfdata.filename)

        self.block_update = True
        # Tell the views about the new rfdata:
        sweep_tree.onNewReadFileData(rfdata)
        filter_tree.onNewReadFileData(rfdata)
        graph.onNewReadFileData(rfdata)
        #setting_tree.onNewReadFileData(rfdata)
        
        # Connect signals
        update_this_graph = lambda **kwargs: self.prepare_and_send_plot_dict(rfdata, filter_tree, sweep_tree, graph, **kwargs)

        filter_tree.parameters.sigTreeStateChanged.disconnect()
        sweep_tree.parameters.sigTreeStateChanged.disconnect()
        try:
            graph.sig_traceAsked.disconnect()
        except:
            pass
        # great code. no time.

        filter_tree.parameters.sigTreeStateChanged.connect(update_this_graph)
        sweep_tree.parameters.sigTreeStateChanged.connect(update_this_graph)
        plotTrace = lambda x, y: self.plotTrace(rfdata, x, y)
        graph.sig_traceAsked.connect(plotTrace)

        
        self.block_update = False
        update_this_graph()

    def prepare_and_send_plot_dict(self,
        rfdata:ReadfileData, 
        filter_tree:FilterTreeView, 
        sweep_tree:SweepTreeView, 
        graph:MPLView,
    ):
        """ Prepare a new `plot_dict` and send to MPLView """
        if self.block_update: return
        self.block_update = True

        d = rfdata.data_dict
        transpose_checked = filter_tree.transposeChecked()
        x_title, y_title = sweep_tree.get_xy_titles(transpose=transpose_checked)

        if d["sweep_dim"] == 1:

            x_data = rfdata.get_data(x_title)
            y_data = rfdata.get_data(y_title)
            y_data, y_mod_title = filter_tree.applyOnData(y_data, y_title)

            plot_dict = {
                "x_title": x_title,
                "y_title": y_mod_title,
                "x_data": rfdata.get_data(x_title),
                "y_data": y_data,
                "grid": True
            }
            rfdata.plot_dict = plot_dict # saved for Traces
            graph.plot1D(rfdata)

        elif d["sweep_dim"] == 2:
            out_title = sweep_tree.get_z_title()
            alternate = sweep_tree.alternate_checked()
            
            img = rfdata.get_data(out_title, alternate=alternate,
            transpose=transpose_checked)
            img, out_mod_title = filter_tree.applyOnData(img, out_title)

            plot_dict = {
                "img": img,
                "x_title": x_title,
                "y_title": y_title,
                "z_title": out_mod_title,
                "cmap": filter_tree.getCmap(),
                "extent": rfdata.get_extent(transpose=transpose_checked),
                "grid": True,
                #"z_scale": {False:"linear", True:"log"}[filter_tree.zLogChecked()]
            }
            rfdata.plot_dict = plot_dict # saved for Traces
            graph.plot2D(rfdata)

        self.block_update = False

        if filter_tree.autoUpdateChecked() and not graph.waiting_for_update:
            graph.waiting_for_update = True
            QTimer.singleShot(
                2000,
                lambda: self._delayed_update(
                    rfdata, filter_tree, sweep_tree, graph
                )
            )
        
        self.hlog.db.add_fig(rfdata, graph.figure)

    def _delayed_update(self, rfdata, filter_tree, sweep_tree, graph):
        graph.waiting_for_update = False
        self.prepare_and_send_plot_dict(
            rfdata.reload(), filter_tree, sweep_tree, graph
        )

    ### TRACE WINDOW
    def showTraceWindow(self):
        self.trace_window.show()
        self.trace_window.raise_()
        self.trace_window.activateWindow()
    
    ####
    def plotTrace(self, rfdata:ReadfileData, click_x, click_y):
        # if click_x and click_y are not None, also display the trace for the clicked position
        self.trace_window.show()
        color = self.trace_window.getColor()

        if rfdata.data_dict['sweep_dim'] == 1:
            x_ax = rfdata.plot_dict["x_data"]
            y_ax = rfdata.plot_dict["y_data"]
            self.trace_window.plotHorizontalTrace(x_ax, y_ax, color)
        
        elif rfdata.data_dict['sweep_dim'] == 2:
            extent = rfdata.plot_dict["extent"]
            img = rfdata.plot_dict["img"]
            # gen linspace for x axis from the extent
            x_start, x_stop, y_start, y_stop = extent
            x_start, x_stop, y_start, y_stop = min(x_start, x_stop), max(x_start, x_stop), min(y_start, y_stop), max(y_start, y_stop)
            x_ax = np.linspace(x_start, x_stop, img.shape[1])
            y_ax = np.linspace(y_start, y_stop, img.shape[0])
            # get closest point
            x_index_clicked = indexOfClosestToTarget(click_x, x_ax)
            y_index_clicked = indexOfClosestToTarget(click_y, y_ax)
            
            x_title = rfdata.plot_dict['x_title']
            y_title = rfdata.plot_dict['y_title']
            z_title = rfdata.plot_dict['z_title']

            hor_trace = img[y_index_clicked]
            hor_label = f"{z_title}({x_title}), {y_title}={y_ax[y_index_clicked]:.3g}"
            vert_trace = img[:, x_index_clicked]
            vert_label = f"{z_title}({y_title}), {x_title}={x_ax[x_index_clicked]:.3g}"

            self.trace_window.plotVerticalTrace(y_ax, vert_trace, color=color, label=vert_label)
            self.trace_window.plotHorizontalTrace(x_ax, hor_trace, color=color, label=hor_label)
            
    def clearTraces(self):
        self.trace_window.clear()

    ### DROP

    def onDrop(self, event, shift):
        file_urls = [url.toLocalFile() for url in event.mimeData().urls()]
        if len(file_urls) > 1:
            self.write('I\'m sorry but one file at a time please...\n Or you can drop your folder to open it.')
            return
        if os.path.isdir(file_urls[0]):
            self.file_tree.changePath(file_urls[0])
        else:
            self.file_tree.new_tab_asked = shift
            self.file_tree.sig_askOpenFile.emit(file_urls[0])


def indexOfClosestToTarget(target, array):
    # find the closest point in the array to the target
    index = np.argmin(np.abs(array - target))
    return index
