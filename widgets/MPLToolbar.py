from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QToolBar
from src.ReadfileData import ReadfileData

class MPLToolbar:
    """
    Helper to setup MPLView toolbars:
      - main_toolbar: Zoom, Pan, Trace, Trace Window
      - secondary_toolbar: Resizable line, vertical & horizontal markers
    """

    def __init__(self, mpl_view):
        self.view = mpl_view
        self._changing_mode = False

        self.initMainToolbar()
        self.initSecondaryToolbar()
        self.connectSignals()

    def initMainToolbar(self):
        """ add Trace button, add Trace Window button """
        tb = self.view.toolbar  # NavigationToolbar
        self.view.actionTrace = QAction('Traces', self.view)
        self.view.actionTrace.setCheckable(True)

        self.view.actionPan = tb.actions()[4]
        self.view.actionZoom = tb.actions()[5]
        
        tb.insertAction(tb.actions()[6], self.view.actionTrace)
        tb.addSeparator()

        self.view.copy_lims = tb.addAction('Copy lims', self.view.copyCurrentLims)

        self.view.trace_action = tb.addAction('Trace window', self.view.parent.showTraceWindow)
        self.view.trace_crosses = []

    def initSecondaryToolbar(self):
        self.secondary_toolbar = QToolBar("Markers & Lines", self.view)

        # Resizable line
        rl = self.view.resizable_line
        self.view.line1_action = self.secondary_toolbar.addAction(
            rl.makeText(0,0,0,0),
            rl.toggleActive
        )
        self.view.line1_action.setCheckable(True)
        rl.action_button = self.view.line1_action

        # Vertical markers
        v = self.view.vmarkers
        self.view.vmarkers_action = self.secondary_toolbar.addAction(
            v.makeText(0,0),
            v.toggleActive
        )
        self.view.vmarkers_action.setCheckable(True)
        v.action_button = self.view.vmarkers_action

        # Horizontal markers
        h = self.view.hmarkers
        self.view.hmarkers_action = self.secondary_toolbar.addAction(
            h.makeText(0,0),
            h.toggleActive
        )
        self.view.hmarkers_action.setCheckable(True)
        h.action_button = self.view.hmarkers_action

        # Add the secondary toolbar to the layout
        self.view.layout().insertWidget(1, self.secondary_toolbar)  # after main toolbar

    def connectSignals(self):
        self.view.actionZoom.toggled.connect(lambda boo: self.actionModeChanged(boo, 'ZOOM'))
        self.view.actionPan.toggled.connect(lambda boo: self.actionModeChanged(boo, 'PAN'))
        self.view.actionTrace.toggled.connect(lambda boo: self.actionModeChanged(boo, 'TRACE'))

    def actionModeChanged(self, checked, clicked=''):
        if self._changing_mode: return
        self._changing_mode = True
        #print(clicked, checked)
        v = self.view
        if clicked in ('ZOOM', 'PAN'):
            v.actionTrace.setChecked(False)
            v.setCursor(False)
        elif clicked == 'TRACE':
            if v.actionPan.isChecked(): v.toolbar.pan()
            if v.actionZoom.isChecked(): v.toolbar.zoom()
            v.setCursor(checked)
        self._changing_mode = False


    ####
    def addResizableLine(self):
        self.toolbar.addSeparator()
        rl = self.view.resizable_line
        self.view.line1_action = self.toolbar.addAction(
            rl.makeText(0,0,0,0),
            rl.toggleActive
        )
        self.view.line1_action.setCheckable(True)
        rl.action_button = self.view.line1_action

    def addMarkers(self):
        v, h = self.view.vmarkers, self.view.hmarkers
        self.view.vmarkers_action = self.toolbar.addAction(v.makeText(0,0), v.toggleActive)
        self.view.hmarkers_action = self.toolbar.addAction(h.makeText(0,0), h.toggleActive)
        self.view.vmarkers_action.setCheckable(True)
        self.view.hmarkers_action.setCheckable(True)
        v.action_button = self.view.vmarkers_action
        h.action_button = self.view.hmarkers_action
