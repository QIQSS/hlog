import sys, os
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib import colors

from src.Cursors import ResizableLine, Crosshair

class MPLWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setAcceptDrops(True)


        # Create a Matplotlib FigureCanvas and set up the layout
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.toolbar.addSeparator()
        # slope line copied from TraitementQuantique, 
        # TODO: do better, not redrawing the whole figure, if possible
        self.line1 = ResizableLine(self.ax, 0, 0, 1, 1, name='line1')
        self.line1.label = self.toolbar.addAction('line 1', self.line1.toggleVisible)
        self.line2 = ResizableLine(self.ax, 0, 0, 1, 1, name='line2', color='green')
        self.line2.label = self.toolbar.addAction('line 2', self.line2.toggleVisible)
        self.line3 = ResizableLine(self.ax, 0, 0, 1, 1, name='line3', color='purple')
        self.line3.label = self.toolbar.addAction('line 3', self.line3.toggleVisible)
        
        # crosshair
        self.crosshair = Crosshair(self.ax)
        self.action_crosshair = self.toolbar.addAction('Crosshair', self.crosshair.toggleVisible)


        self.im = None # image
        self.bar = None # colorbar
        
    # DROPPING THINGS:
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
        else: e.ignore()
    
    def dropEvent(self, e):
        file_urls = [url.toLocalFile() for url in e.mimeData().urls()]
        if len(file_urls) > 1:
            self.write('I\'m sorry but one file at a time please...\n Or you can drop your folder!')
            return
        if os.path.isdir(file_urls[0]):
            self.parent.controller.changePath(file_urls[0])
        else:
            self.parent.controller.openFile(file_urls[0])
    # END OF DROPPING THINGS
    

    def beforeDisplay(self, plot_kwargs={}):
        # things in common for both displayImage and displayPlot
        if self.bar:
            self.bar.remove()
            self.bar = None
        self.ax.clear()
        title = plot_kwargs.pop('title', '')
        x_title = plot_kwargs.pop('xlabel', '')
        y_title = plot_kwargs.pop('ylabel', '')
        self.ax.set_title(title)
        self.ax.set_xlabel(x_title)
        self.ax.set_ylabel(y_title)
    
    def afterDisplay(self):
        xlim, dx = self.ax.get_xlim(), 0.1*(self.ax.get_xlim()[1]-self.ax.get_xlim()[0])
        ylim, dy = self.ax.get_ylim(), 0.1*(self.ax.get_ylim()[1]-self.ax.get_ylim()[0])
        self.line1.line.set_data([xlim[0]+dx, xlim[1]-dx], [ylim[0]+dy, ylim[1]-dy])
        self.ax.add_artist(self.line1.line)
        self.line2.line.set_data([xlim[0]+dx, xlim[1]-dx], [np.mean(ylim), np.mean(ylim)])
        self.ax.add_artist(self.line2.line)
        self.line3.line.set_data([xlim[0]+dx, xlim[1]-dx], [ylim[1]-dy, ylim[0]+dy])
        self.ax.add_artist(self.line3.line)
        self.ax.add_artist(self.crosshair.vline)
        self.ax.add_artist(self.crosshair.hline)
        self.canvas.draw()

    def displayImage(self, image_data, extent, plot_kwargs={}, keep_position=False):
        # popping
        zlabel = plot_kwargs.pop('zlabel', '')
        cbar_min, cbar_max = plot_kwargs.pop('cbar_factor_min', 0), plot_kwargs.pop('cbar_factor_max', 1)
        
        def _calcColorbarLimit():
            data_min, data_max = np.nanmin(image_data), np.nanmax(image_data)
            return data_min+(data_max-data_min)*cbar_min, data_min+(data_max-data_min)*cbar_max

        if keep_position:
            self.im.set_data(image_data)
            self.im.set_extent(extent)
            self.im.set_clim(*_calcColorbarLimit())
            self.canvas.draw()
            return

        self.beforeDisplay(plot_kwargs)

        # plotting
        self.im = self.ax.imshow(image_data, origin='lower', aspect='auto', interpolation='nearest',
                                 extent=extent, **plot_kwargs)
        self.bar = self.figure.colorbar(self.im, ax=self.ax, label=zlabel)

        # colorbar limits
        cb_mn, cb_mx = _calcColorbarLimit()
        self.im.set_clim(cb_mn, cb_mx)
        
        self.afterDisplay()

    def displayPlot(self, x_data, y_data, plot_kwargs={}):
        self.beforeDisplay(plot_kwargs)

        self.ax.set_yscale(plot_kwargs.pop('yscale', 'linear'))
        self.ax.set_xscale(plot_kwargs.pop('xscale', 'linear'))
        self.ax.grid(plot_kwargs.pop('grid', True))
        self.ax.plot(x_data, y_data, **plot_kwargs)
        
        self.afterDisplay()
    
    def write(self, text):
        self.beforeDisplay()
        loading_label = self.ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=12, color="gray")
        self.canvas.draw()
