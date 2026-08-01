import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.Qt import QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib import colors
from matplotlib.lines import Line2D
from matplotlib.image import AxesImage


from matplotlib.widgets import Cursor

from widgets.MPLElements import ResizableLine, Markers
from widgets.MPLToolbar import MPLToolbar

from copy import deepcopy

class MPLView(QWidget):
    
    sig_traceAsked = pyqtSignal(float, float) # xy_tuple

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)

        self.figure = Figure(figsize=(5,10))
        self.ax = self.figure.add_subplot(111)
        self.ax.autoscale(enable=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        # resizable line and markers
        self.resizable_line = ResizableLine(self, visible=False)
        self.vmarkers = Markers(self, 'v', visible=False)
        self.hmarkers = Markers(self, 'h', visible=False)
        # init toolbars:
        MPLToolbar(self)

        self.line: Line2D = None # line plot
        self.im: AxesImage = None # image
        self.bar = None # colorbar

        self.plot_dict_fns = {} # reference functions to call for updates. Defined in self.onNewReadFileData
        self.last_plot_dict = {}
        self.current_plotted_dim: 1|2 = None

        # cursor / crosshair
        self.cursor = Cursor(self.ax, useblit=True, color='black', linewidth=1)
        self.setCursor = lambda boo: setattr(self.cursor, 'visible', boo)
        self.setCursor(False)

        self.canvas.mpl_connect('pick_event', self.onPick)
        self.canvas.mpl_connect('button_press_event', self.onMouseClick)


    def onNewReadFileData(self, rfdata):
        self.update_timer.stop()

        if self.bar:
            self.bar.remove()
            del self.bar
            self.bar = None
        if self.im:
            self.im.remove()
            self.im = None
        if self.line:
            self.line.remove()
            self.line = None
        self.ax.clear()
        self.canvas.draw()

        self.ax.add_artist(self.vmarkers.line1); self.ax.add_artist(self.vmarkers.line2)
        self.ax.add_artist(self.hmarkers.line1); self.ax.add_artist(self.hmarkers.line2)
        self.ax.add_artist(self.resizable_line.line)

        if rfdata.data_dict["sweep_dim"] == 1:
            # adding artists
            plotkw = {'marker': 'o', 'linestyle': '-', 'markersize': 3, 'linewidth': 1}
            self.line = self.ax.plot(0, 0, **plotkw)[0]
            ##

            #self.ax.add_artist(self.hmarkers)
            self.plot_dict_fns = {
                "x_title": self.ax.set_xlabel,
                "y_title": self.ax.set_ylabel,
                "x_or_y_data": self.line.set_data,
                "grid": lambda visible: self.ax.grid(visible=visible, color='#DDDDDD', linestyle='-', linewidth=1, alpha=1)
            }

            self.last_plot_dict = {}
            self.figure.tight_layout()
            self.current_plotted_dim = 1

        elif rfdata.data_dict["sweep_dim"] == 2:
            self.im = self.ax.imshow(
                np.full((1, 1), np.nan), origin='lower', 
                aspect='auto', 
                interpolation='nearest',
                cmap="viridis"
            )
            self.bar = self.figure.colorbar(self.im, ax=self.ax)

            self.plot_dict_fns = {
                "x_title": self.ax.set_xlabel,
                "y_title": self.ax.set_ylabel,
                "z_title": self.bar.set_label,
                #"extent": self.im.set_extent,
                "grid": lambda visible: self.ax.grid(visible=visible, color='#DDDDDD', linestyle='--', linewidth=0.8, alpha=0.3),
                #"clims": self.bar.set_
            }

            self.last_plot_dict = {}
            self.figure.tight_layout()
            self.current_plotted_dim = 2

    def plot1D(self, rfdata):
        """ go through plot_dict
        if val is different from self.last_plot_dict:
            update using the function in self.plot_fns
        some special cases are treated first, with a pop.
        """
        d = deepcopy(rfdata.plot_dict)
        last_d = self.last_plot_dict
        self.last_plot_dict = deepcopy(d) # SAVE for the future update

        need_redraw = False
        # SPECIAL CASE
        # set_data if x or y data has changed
        x_data, y_data = d.pop("x_data"), d.pop("y_data")
        if (not np.array_equal(x_data, last_d.pop("x_data", None), equal_nan=True)) or \
            (not np.array_equal(y_data, last_d.pop("y_data", None), equal_nan=True)):
            need_redraw = True
            #print("redraw")
            self.plot_dict_fns["x_or_y_data"](x_data, y_data)
            # markers
            self.hmarkers.setPosition(np.nanmin(y_data), np.nanmax(y_data))
            self.vmarkers.setPosition(np.nanmin(x_data), np.nanmax(x_data))
            self.resizable_line.setPosition(np.nanmin(x_data), np.nanmin(y_data), np.nanmax(x_data), np.nanmax(y_data))

            self.ax.relim()
            self.ax.autoscale_view()
            # For home button:
            self.toolbar._nav_stack.clear()
            self.toolbar.push_current()
            #
            self.toolbar.home()
        

        # OTHER KEYS
        for key, val in d.items():
            # if val is different from before, exec the function
            if val != last_d.get(key, None):
                #print(f"new:{key} {val}")
                fn = self.plot_dict_fns[key]
                fn(val)
        
        if need_redraw:
            self.figure.tight_layout()
            self.canvas.draw_idle()

    def plot2D(self, rfdata):
        """ go through plot_dict
        if val is different from self.last_plot_dict:
            update using the function in self.plot_fns
        some special cases are treated first, with a pop.
        """
        d = deepcopy(rfdata.plot_dict)
        last_d = self.last_plot_dict
        self.last_plot_dict = deepcopy(d) # SAVE for the future update

        # SPECIAL CASES
        ## CBAR
        need_redraw = False
        need_cbar_redraw = False
        
        cmap = d.pop("cmap")
        if cmap != self.bar.mappable.get_cmap().name:
            need_redraw = True
            self.im.set_cmap(cmap)

        ## IMG
        img = d.pop("img")
        last_img = last_d.pop("img", None)
        if not np.array_equal(img, last_img, equal_nan=True):
            need_redraw = True
            self.im.set_data(img)
            self.im.autoscale() # Rescale colors
            # Set scale lims
            vmin, vmax = np.nanmin(img), np.nanmax(img)
            self.im.set_norm(colors.Normalize(vmin, vmax))
            self.bar.update_normal(self.im)
            if vmin == vmax:
                vmin, vmax = vmax*0.9, vmax*1.1
            self.bar.ax.set_ylim(vmin, vmax)
            ## update home
            # save temp image axes view
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            # go to default xlim ylim
            def_extent = self.im.get_extent()
            self.ax.set_xlim(def_extent[0], def_extent[1])
            self.ax.set_ylim(def_extent[2], def_extent[3])
            # save position as home
            self.toolbar._nav_stack.clear()
            self.toolbar.push_current()
            # restore image axes view
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)

        ## EXTENT
        extent = d.pop("extent")
        last_extent = last_d.pop("extent", None)
        if extent != last_extent:
            self.im.set_extent(extent)
            # Sync home button:
            self.ax.set_xlim(extent[0], extent[1])
            self.ax.set_ylim(extent[2], extent[3])
            self.vmarkers.setPosition(extent[0], extent[1])
            self.hmarkers.setPosition(extent[2], extent[3])
            self.resizable_line.setPosition(extent[0], extent[2], extent[1], extent[3])

            self.toolbar._nav_stack.clear()
            self.toolbar.push_current()
            #

        # OTHER KEYS
        for key, val in d.items():
            # if val is different from before, exec the function
            if val != last_d.get(key, None):
                #print(f"new:{key} {val}")
                fn = self.plot_dict_fns.get(key, lambda *args: print("No function defined"))
                fn(val)
        if need_redraw:
            self.figure.tight_layout()
            self.canvas.draw_idle()

    # HANDLING EVENTS

    def onMouseClick(self, event):
        if event.inaxes != self.ax: return
        #print('click', event.xdata, event.ydata)
        if event.button == 1:
            if self.actionTrace.isChecked():
                #self.parent.showTrace(event.xdata, event.ydata)
                self.sig_traceAsked.emit(event.xdata, event.ydata)
    
    def onPick(self, event):
        artist = event.artist
        #print(artist)
        pass
        if artist == self.resizable_line.line and self.resizable_line.visible:
            self.resizable_line.onPick(event)
        if artist in self.vmarkers.lines and self.vmarkers.visible:
            self.vmarkers.onPick(event)
        if artist in self.hmarkers.lines and self.hmarkers.visible:
            self.hmarkers.onPick(event)
        
    def onNewTrace(self, x, y, color='black'):
        # add a cross to the graph
        self.trace_crosses.append(self.ax.plot(x, y, 'x', color=color)[0])
        self.canvas.draw()
    def clearCrosses(self):
        for cross in self.trace_crosses:
            cross.remove()
        self.trace_crosses = []

    def copyCurrentLims(self):
        dim = self.current_plotted_dim
        if dim not in [1,2]:
            return

        cb = QApplication.clipboard()
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()

        if dim == 1:
            text = f"{x0:.6f}, {x1:.6f}"
        elif dim == 2:
            text = f"[{x0:.6f}, {y0:.6f}], [{x1:.6f}, {y1:.6f}]"
        cb.setText(text)
        self.parent.write("Copied: " + text)
    # END OF HANDLING EVENTS
    
    def wait_for_autoupdate(self, ms_time, function):
        try:
            self.update_timer.disconnect()
        except TypeError:
            pass
        self.update_timer.timeout.connect(function)
        self.update_timer.start(ms_time)

def set_1d_ax_lim(ax, x_data, y_data, padding_factor=0.05):
    x_padding = padding_factor*(np.nanmax(x_data)-np.nanmin(x_data))
    y_padding = padding_factor*(np.nanmax(y_data)-np.nanmin(y_data))
    ax.set_xlim(np.nanmin(x_data)-x_padding, np.nanmax(x_data)+x_padding)
    ax.set_ylim(np.nanmin(y_data)-y_padding, np.nanmax(y_data)+y_padding)
