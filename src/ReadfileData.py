import pyHegel.commands as c
import os, sys, hashlib
import h5py
import numpy as np

DATA_DICT_FORMAT = {
    'x': {
        'range': [-1,1,6,0.2], 
        'title': 'random_x', 
        'data': np.zeros((11,6))},
    'y': {
        'range': [0,2,11,0.1], 
        'title': 'random_y', 
        'data': np.zeros((11,6))
    },
    'out': {
        'titles': ['out1', 'out2'],
        'data': [np.random.rand(11,6), np.random.rand(11,6)]
    },
    'computed_out': {'titles': [], 'data': []}, # for computed data (r, deg, x, y)
    'alternate': False,
    'beforewait': True,
    'sweep_dim': 2,
            #'hl_logs': {'dev1': 0.1, 'dev2': 0.2},
            #'ph_logs': ['#dev1', '#dev2']
    'config': [],
    'comments': [],
    'sweep_time': None # epoch [beginning, end]
    }

class ReadfileData:

    def __init__(self, filepath, metadata, h, data_dict, reload_function):
        self.h = h
        self.metadata = metadata
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.data_dict = data_dict
        self.plot_dict = None # used to store current plotted (filtered) data
        self.reload_function = reload_function
    
    def reload(self):
        self.data_dict = self.reload_function(self.filepath)
        return self
            
    def get_data(self, title, alternate=False, transpose=False):
        # get the data array corresponding to the title
        # search in the out titles and data
        if title in self.data_dict['out']['titles']:
            i = self.data_dict['out']['titles'].index(title)
            data_cp = self.data_dict['out']['data'][i].copy()
        # search in the computed_out titles and data
        #elif title in self.data_dict['computed_out']['titles']:
        #    i = self.data_dict['computed_out']['titles'].index(title)
        #    data_cp = self.data_dict['computed_out']['data'][i].copy()
        else:
            raise KeyError()
        if self.data_dict['sweep_dim'] == 1:
            return data_cp
        if self.data_dict['sweep_dim'] == 2:
            # alternate data if needed
            if alternate:
                # flip odd rows
                data_cp[1::2] = data_cp[1::2, ::-1]
            if transpose:
                data_cp = data_cp.T
            # transpose by default
            return data_cp.T
    
    def get_extent(self, transpose=False):
        x_start, x_stop, x_nbpts, x_step = self.data_dict['x']['range']
        y_start, y_stop, y_nbpts, y_step = self.data_dict['y']['range']
        # extent = (x_start, x_stop, y_start, y_stop)
        extent = (
            min(x_start, x_stop)-abs(x_step)/2, 
            max(x_start, x_stop)+abs(x_step)/2,
            min(y_start, y_stop)-abs(y_step)/2, 
            max(y_start, y_stop)+abs(y_step)/2)
        if transpose: extent = (extent[2], extent[3], extent[0], extent[1])
        if any([np.isnan(e) for e in extent]):
                extent = None
        return extent
    
    def get_time_taken(self) -> str:
        sweep_time = self.data_dict["sweep_time"]
        if sweep_time is None:
            return ""
        if np.isnan(sweep_time).any():
            return ""
        return c.util.format_time(sweep_time[1] - sweep_time[0])

    # -- POLAR/CARTESIAN CONVERSION --
    def clearComputedData(self):
        self.data_dict['computed_out']['titles'] = []
        self.data_dict['computed_out']['data'] = []
    
    def genXYData(self, r_title, deg_title, alternate=False):
        # from the r aneg titles, gen new out titles and data arrays for x and y
        r_data = self.getData(r_title, alternate=alternate)
        deg_data = self.getData(deg_title, alternate=alternate)
        x_data = r_data * np.cos(np.radians(deg_data))
        y_data = r_data * np.sin(np.radians(deg_data))
        x_data, y_data = x_data.T, y_data.T

        self.clearComputedData()
        self.data_dict['computed_out']['titles'].append(r_title + '_X')
        self.data_dict['computed_out']['titles'].append(deg_title + '_Y')
        self.data_dict['computed_out']['data'].append(x_data)
        self.data_dict['computed_out']['data'].append(y_data)

    def genPolarData(self, x_title, y_title, alternate=False):
        # from the x and y titles, gen new out titles and data arrays for r and deg
        x_data = self.getData(x_title, alternate=alternate)
        y_data = self.getData(y_title, alternate=alternate)
        r_data = np.sqrt(x_data**2 + y_data**2)
        deg_data = np.arctan2(y_data, x_data)
        deg_data = np.degrees(deg_data)
        
        self.clearComputedData()
        self.data_dict['computed_out']['titles'].append(x_title + '_R')
        self.data_dict['computed_out']['titles'].append(y_title + '_DEG')
        self.data_dict['computed_out']['data'].append(r_data)
        self.data_dict['computed_out']['data'].append(deg_data)


    @staticmethod
    def from_filepath(filepath):
        h =  hash_file(filepath)
        metadata = os.stat(filepath)

        ext = filepath.split('.')[-1]
        # Get load_function, fallback to pyHegel
        load_function = {"txt": ph_load, "hdf5": h5_load}.get(ext, ph_load)
        data_dict = load_function(filepath)
        
        return ReadfileData(
            filepath,
            metadata=metadata,
            h=h,
            data_dict=data_dict,
            reload_function = load_function
        )

def ph_load(filepath) -> dict:
    data_dict = DATA_DICT_FORMAT.copy()
    try:
        data, titles, headers = c.readfile(filepath, getheaders=True, multi_sweep='force')
    except:
        try:
            data, titles, headers = c.readfile(filepath, getheaders=True, multi_sweep=False)
        except Exception as e:
            raise e

    if data[0].ndim == 1:
        data_dict['sweep_dim'] = 1
        ph_build1DDataDict(data, titles, headers, data_dict)
    elif data[0].ndim == 2:
        data_dict['sweep_dim'] = 2
        ph_build2DDataDict(data, titles, headers, data_dict)

    data_dict['beforewait'] = ph_findBeforeWait(headers)
    config, comment = ph_findConfigAndComments(headers)
    data_dict['config'] = config
    data_dict['comments'] = comment
    
    return data_dict

def ph_build1DDataDict(data, titles, header, data_dict):
    # in one dimension, we use the x and out keys
    x_data = data[0]
    data_dict['x']['data'] = x_data
    data_dict['x']['title'] = titles[0]
    data_dict['x']['range'] = findSweepRange1D(x_data)

    data_dict['out']['titles'] = []
    data_dict['out']['data'] = []
    rev_data = True if data_dict['x']['range'][3] < 0 else False
    for i, title in enumerate(titles):
        data_dict['out']['titles'].append(title)
        out_data = data[i][::-1] if rev_data else data[i]
        data_dict['out']['data'].append(out_data)
    
    time_data = data_dict['out']['data'][-1]
    data_dict['sweep_time'] = [np.nanmin(time_data), np.nanmax(time_data)]

def ph_detectXYIndex(titles):
    # manually detect if the first two columns are actually the same value:
    # ex: field_scale, field_raw 
    if titles[0].endswith('scale') and titles[1].endswith('raw'):
        return 0, 2
    return 0, 1

def ph_build2DDataDict(data, titles, headers, data_dict):
    x_index, y_index = ph_detectXYIndex(titles)
    data_x, data_y = data[x_index], data[y_index]
    data_dict['x']['data'] = data_x
    data_dict['y']['data'] = data_y
    # check if titles are the same:
    if titles[x_index] == titles[y_index]:
        titles[x_index] = titles[y_index] + '_'
    data_dict['x']['title'] = titles[x_index]
    data_dict['y']['title'] = titles[y_index]
    ph_findSweepRange2D(data, headers, data_dict)
    data_dict['alternate'] = False if np.array_equal(data_y[0], data_y[1]) else True

    data_dict['out']['titles'] = []
    data_dict['out']['data'] = []
    rev_x = True if data_dict['x']['range'][3] < 0 else False
    rev_y = True if data_dict['y']['range'][3] < 0 else False
    for i, title in enumerate(titles[y_index+1:]):
        data_dict['out']['titles'].append(title)
        out_data = data[i+1+y_index] # we start at index y+1
        # reverse if needed
        out_data = out_data[::-1] if rev_x else out_data
        out_data = out_data[:,::-1] if rev_y else out_data
        #print(rev_x, rev_y)
        data_dict['out']['data'].append(out_data)

    time_data = data_dict['out']['data'][-1]
    data_dict['sweep_time'] = [np.nanmin(time_data), np.nanmax(time_data)]

def ph_findSweepRange2D(data, headers, data_dict):
    # try to find the ranges of the 2d sweep
    # for multi sweep, it is not well written in the headers
    # so we have to estimate it from the data
    # 1.1 for Y: try to find start/stop in the header
    array_y = data[1][0]
    start_y, stop_y, nbpts_y, step_y = np.nan, np.nan, len(array_y), np.nan
    line_options = headers[-3]
    if 'sweep' in line_options:
        options = line_options.split(',')
        for option in options:
            if 'start' in option:
                try: start_y = float(option.split(' ')[-1])
                except: pass
            elif 'stop' in option:
                try: stop_y = float(option.split(' ')[-1])
                except: pass
    else:
        start_y = array_y[0]
        stop_y = array_y[-1]
    if not np.isnan(start_y) or not np.isnan(stop_y):
        step_y = (stop_y - start_y) / (nbpts_y - 1)

    # 1.2 for X try to deduce start/stop from the data
    array_x = data[0][:,0]
    range_x = findSweepRange1D(array_x)
        
    data_dict['x']['range'] = range_x
    data_dict['y']['range'] = [start_y, stop_y, nbpts_y, step_y]

def ph_findConfigAndComments(headers):
    comments = []
    config = []
    for line in headers:
        if line.startswith('#comment:=') or line.startswith('#com ...:='):
            comments.append(line[10:])
        else:
            config.append(line)
    return config, comments

def ph_findBeforeWait(headers):
    sweep_multi_option = headers[-3]
    # "#sweep_multi_options:= {..., 'beforewait': [0.02, 0.02], ... };\n"
    # or "#sweep_multi_options:= {..., 'beforewait': [0.02], ... };\n"
    beforewait = []
    try:
        beforewait = sweep_multi_option.split('beforewait\': [')[1].split(']')[0]
        beforewait = beforewait.split(',')
        for i, bw in enumerate(beforewait):
            beforewait[i] = float(bw)
    except:
        beforewait = np.nan
    return beforewait

def h5_load(filepath) -> dict:
    data_dict = DATA_DICT_FORMAT.copy()
    with h5py.File(filepath, "r") as file:
        data, meta = file.get("data"), file.get("meta")
        if meta.attrs.get("VERSION") != 0.1: 
            raise NotImplementedError(f"VERSION not supported :)")

        sweep_names = data.attrs.get("sweeped_ax_names")
        out_names = data.attrs.get("result_data_names")

        if len(sweep_names) == 1:
            data_dict['sweep_dim'] = 1
            h5_build1DDataDict(data, sweep_names[0], out_names, data_dict)
        elif len(sweep_names) == 2:
            data_dict['sweep_dim'] = 2
            h5_build2DDataDict(data, sweep_names, out_names, data_dict)
        else:
            raise NotImplementedError(f"Sweep dimension not 1 or 2")
    
        data_dict['config'] = meta.attrs.get("config")
        data_dict['comments'] = meta.attrs.get("cell")

    return data_dict

def h5_build1DDataDict(data, x_name, out_names, data_dict):
    # in one dimension, we use the x and out keys
    x_data = data.get(x_name)[:]
    data_dict['x']['data'] = x_data
    data_dict['x']['title'] = x_name
    data_dict['x']['range'] = findSweepRange1D(x_data)

    data_dict['out']['titles'] = [x_name]
    data_dict['out']['data'] = [x_data]
    for i, title in enumerate(out_names):
        data_dict['out']['titles'].append(title)
        data_dict['out']['data'].append(data.get(title)[:])

def h5_build2DDataDict(data, sweeped_names, out_names, data_dict):
    data_dict['x']['title'] = x_lbl = sweeped_names[0]
    data_dict['y']['title'] = y_lbl = sweeped_names[1]
    data_x, data_y = data[x_lbl][:], data[y_lbl][:]
    data_dict['x']['data'] = data_x
    data_dict['y']['data'] = data_y

    data_dict['x']['range'] = findSweepRange1D(data_x)
    data_dict['y']['range'] = findSweepRange1D(data_y)

    data_dict['out']['titles'] = []
    data_dict['out']['data'] = []
    for i, title in enumerate(out_names):
        data_dict['out']['titles'].append(title)
        out_data = data[title][:]
        data_dict['out']['data'].append(out_data)

    return data_dict

def findSweepRange1D(array):
    # try to find the ranges the sweep array
    start, stop, nbpts, step = np.nan, np.nan, len(array), np.nan
    if array[0] != np.nan:
        start = array[0]
        if not np.isnan(array[-1]):
            stop = array[-1]
            step = (stop - start) / (nbpts - 1)
        elif not np.isnan(array[1]):
            step = array[1] - array[0]
            stop = start + step * (nbpts - 1)
    return [start, stop, nbpts, step]
    

def hash_file(filepath: str) -> str:
    if not os.path.isfile(filepath):
        raise FileNotFoundError(filepath)

    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def last_not_nan(arr):
    arr = np.asarray(arr)
    valid = arr[~np.isnan(arr)]
    return valid[-1] if valid.size else None