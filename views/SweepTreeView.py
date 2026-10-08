from PyQt5.QtWidgets import QWidget, QDialog, QTextEdit, QVBoxLayout, QPushButton
import os
import pyqtgraph as pg

children = [
    {'name': 'Sweep', 'type': 'group', 'children': [
        {'name': 'time', 'type': 'str', 'value': ''},
        {'name': 'dev1', 'type': 'group', 'children': []},
        {'name': 'dev2', 'type': 'group', 'children': []},
        {'name': 'is_alternate', 'type': 'bool', 'value': False},
        #{'name': 'Transpose', 'type': 'bool', 'value': False},
        {'name': 'wait_before (s)', 'type': 'str', 'value': '[0.02, 0.02]', 'readonly': True},
        ]},
    {'name': 'Out', 'type': 'group', 'children': [
        {'name': 'x', 'type': 'list', 'values': []},
        {'name': 'y', 'type': 'list', 'values': []},
        {'name': 'z', 'type': 'list', 'values': []}
    ]},
    {'name': 'Header', 'type': 'group', 'children': [
        {'name': 'Open in text editor', 'type': 'action'},
        {'name': 'config', 'type': 'text', 'value': '', 'readonly': True},
        {'name': 'meta', 'type': 'text', 'value': '', 'readonly': True},
        ], 'expanded': False},
] # these are just placeholders, they are filled/rewritten in onNewReadFileData


class SweepTreeView:
    """
    Static view of an rfdata item.
    x/y can be selected.
    """
    def __init__(self):
        super().__init__()
    
        self.parameters = pg.parametertree.Parameter.create(name='params', type='group', children=children)
        self.tree = pg.parametertree.ParameterTree(showHeader=False)
        self.tree.setParameters(self.parameters, showTop=False)
        self.tree.verticalScrollBar().setSingleStep(5)

        self.need_set_data = True
        
        def onParamChange(param, changes):
            #print('a param has changed')
            pass
            #self.updatePlot()
        self.parameters.sigTreeStateChanged.connect(onParamChange)

        p = self.parameters
        p.param('Header', 'Open in text editor').sigActivated.connect(self.show_header_popup)
        
        self.tree.header().setSectionResizeMode(0)
        self.tree.setColumnWidth(0, 130)

    
    def onNewReadFileData(self, rfdata):
        p = self.parameters
        p.param('Out').clearChildren()
        p.param('Sweep').clearChildren()
        
        time_taken:str = rfdata.get_time_taken()
        if time_taken != '':
            p.param('Sweep').addChild({'name': 'time', 'type': 'str', 'value': time_taken})

        data_dict = rfdata.data_dict
        out_titles = data_dict['out']['titles']
        
        if data_dict['sweep_dim'] == 1:
            x_title, y_title = out_titles[:2]
            x_ax = {'name': 'x', 'type': 'list', 'values': out_titles, 'default': x_title}
            y_ax = {'name': 'y', 'type': 'list', 'values': out_titles, 'default': y_title}
            p.param('Out').addChildren([x_ax, y_ax])
            p.param('Out', 'x').setValue(out_titles[0])
            p.param('Out', 'y').setValue(out_titles[1])
            
            x_range = data_dict['x']['range']
            x_sweep = {'name': x_title, 'type': 'group', 'children': [
                {'name': 'range', 'type': 'str', 'value': range_to_string(x_range), 'readonly': True}]}
            p.param('Sweep').addChildren([x_sweep])

        elif data_dict['sweep_dim'] == 2:
            x_title, y_title = rfdata.data_dict['x']['title'], rfdata.data_dict['y']['title']
            x = {'name': 'x', 'type': 'str', 'value': x_title, 'readonly': True, 'visible': False}
            y = {'name': 'y', 'type': 'str', 'value': y_title, 'readonly': True, 'visible': False}
            z = {'name': 'z', 'type': 'list', 'values': out_titles, 'default': out_titles[0]}
            p.param('Out').addChildren([x, y, z])
            p.param('Out', 'z').setValue(out_titles[0])

            x_range, y_range = rfdata.data_dict['x']['range'], rfdata.data_dict['y']['range']
            x_sweep = {'name': x_title, 'type': 'group', 'children': [
                {'name': 'range', 'type': 'str', 'value': range_to_string(x_range), 'readonly': True}]}
            y_sweep = {'name': y_title, 'type': 'group', 'children': [
                {'name': 'range', 'type': 'str', 'value': range_to_string(y_range), 'readonly': True}]}
            p.param('Sweep').addChildren([x_sweep, y_sweep])

            is_alternate = {'name': 'is_alternate', 'type': 'bool', 'value': data_dict['alternate']}
            p.param('Sweep').addChildren([is_alternate])

        # logs
        p.param('Header', 'config').setValue(str(data_dict['config']))
        p.param('Header', 'meta').setValue(str(data_dict['meta']))
        
        #wait_before = {'name': 'wait_before', 'type': 'str', 'value': str(rfdata.data_dict['beforewait']), 'readonly': True},
        #self.params.param('Sweep').addChildren([is_alternate, wait_before])
        
        #transpose = {'name': 'Transpose', 'type': 'bool', 'value': False}
        #p.param('Sweep').addChildren([transpose])

    def get_xy_titles(self, transpose=False):
        p = self.parameters
        x_title = p.param('Out', 'x').value()
        y_title = p.param('Out', 'y').value()
        if transpose:
            x_title, y_title = y_title, x_title
        return x_title, y_title
    
    def get_z_title(self):
        return self.parameters.param('Out', 'z').value()

    def alternate_checked(self):
        return self.parameters.param('Sweep', 'is_alternate').value()

    # def show_header_popup(self):
    #     header_text = f"Config:\n{self.parameters.param('Header', 'config').value()}\n\n" \
    #                   f"Meta:\n{self.parameters.param('Header', 'meta').value()}"
    #     dlg = QDialog()
    #     dlg.setWindowTitle("Header Full Text")
    #     layout = QVBoxLayout()
    #     text_edit = QTextEdit()
    #     text_edit.setReadOnly(True)
    #     text_edit.setText(header_text)
    #     layout.addWidget(text_edit)
    #     close_btn = QPushButton("Close")
    #     close_btn.clicked.connect(dlg.accept)
    #     layout.addWidget(close_btn)
    #     dlg.setLayout(layout)
    #     dlg.resize(600, 400)
    #     dlg.exec_()



    def show_header_popup(self):
        header_text = (
            f"Config:\n{self.parameters.param('Header', 'config').value()}\n\n"
            f"Meta:\n{self.parameters.param('Header', 'meta').value()}"
        )

        import tempfile
        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(header_text)
        open_text_file(path)

def range_to_string(ranges):
    return '[{:.3g}, {:.3g}], npts: {}, step: {:.3g}'.format(*ranges)


def open_text_file(path):
    import platform
    import subprocess
    system = platform.system()

    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":
        subprocess.Popen(["open", "-t", path])
    else:
        subprocess.Popen(["xdg-open", path])