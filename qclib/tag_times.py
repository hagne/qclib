# -*- coding: utf-8 -*-
# from atmPy.aerosols.instruments import POPS
# import icarus
import pathlib

import numpy as np
import xarray as xr
import pandas as pd

from ipywidgets import widgets
from IPython.display import display

import matplotlib.pylab as plt
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

from nsasci import database
import sqlite3



# def read_POPS(path):
#     # print(path.glob('*'))
#     hk = POPS.read_housekeeping(path, pattern = 'hk', skip_histogram= True)
#     hk.get_altitude()
#     return hk

# def read_iMet(path):
#     ds = xr.open_dataset(path)
    
#     # return ds
#     alt_gps = ds['GPS altitude [km]'].to_pandas()
#     alt_bar = ds['altitude (from iMet PTU) [km]'].to_pandas()

#     df = pd.DataFrame({'alt_gps': alt_gps,
#               'alt_bar': alt_bar})
#     df *= 1000
#     return df


def read_nc(path):
    ds = xr.open_dataset(path)
    df = ds.altitude.to_dataframe()
    return df

class Data_container(object):
    def __init__(self, controller):
        self.controller = controller
        self.delta_t = 0
        # path2data1 = pathlib.Path(path2data1)
        read_data = read_nc #icarus.icarus_lab.read_imet
        self.dataset1 = Data(self, self.controller.paths['path2data'], read_data, glob_pattern = '*.nc')

        if not isinstance(self.controller.paths['path2data_alt'], type(None)):
            path2data2 = pathlib.Path(self.controller.paths['path2data_alt'])
            # read_data = read_POPS
            raise ValueError('Work needed ... this is not working yet/anymore')
            self.dataset2 = Data(self, path2data2, read_data, glob_pattern='olitbspops*')
        else:
            self.dataset2 = None

class Data(object):
    def __init__(self, datacontainer, path2data, read_data, load_all = None , glob_pattern = '*'):
        self.controller = datacontainer.controller
        self._datacontainer = datacontainer
        self.read_data = read_data
        self.path2data = path2data
        self._path2active = None

        # paths = dict(path2data = path2data,
        #              path2database = path2database)
        # for k,v in paths.items():
        #     if not isinstance(v, pathlib.PosixPath):
        #         paths[k] = (pathlib.Path(v))
        # self.paths = paths
        
        
        # self.path2data_list = sorted(list(path2data.glob(glob_pattern)))
        if path2data.is_dir():
            path2data_list = sorted(list(path2data.glob(glob_pattern)))
        elif path2data.is_file():
            path2data_list = [path2data]
        else:
            assert(False)
        self.path2data_list = path2data_list
        self._load_all = load_all
        self.path2active = self.path2data_list[0]
        
        if load_all:
            self.load_all(path2data,glob_pattern)
        # else:
        #     df = self.read_data(self.path2active)
        #     self.active = df
        

        

    def load_all(self):
        path2data_list = self.path2data_list
        data_list = []
        data_info_list = []
        for path in path2data_list:
            df = self.read_data(path)
            # add_on = path.name.split('.')[-2][-2:]
            # df.columns = ['_'.join([col, add_on]) for col in df.columns]
            data_list.append(df)

            dffi = dict(t_start=df.index.min(),
                        t_end=df.index.max(),
                        v_max=df.max().max(),
                        v_min=df.min().min())
            data_info_list.append(pd.DataFrame(dffi, index=[path.name]))

        self.active = pd.concat(data_list, sort = True)
        self.active_info = pd.concat(data_info_list, sort = True)

    @property
    def path2active(self):
        return self._path2active

    @path2active.setter
    def path2active(self, value):
        self._datacontainer.delta_t = 0
        self._path2active = value
        if self._load_all:
            return
        else:
            self.controller.send_message('opening {}'.format(self._path2active.name))
            # print(self._path2active.name)
            self.active = self.read_data(self._path2active)

    def previous(self):
        idx = self.path2data_list.index(self.path2active)
        if idx == 0:
            self.controller.send_message('first')
            pass
        elif idx == -1:
            raise ValueError('not possibel')
        else:
            self.path2active = self.path2data_list[idx - 1]

    def next(self):
        idx = self.path2data_list.index(self.path2active)
        if idx == len(self.path2data_list) - 1:
            self.controller.send_message('last')
            pass
        elif idx == -1:
            raise ValueError('not possibel')
        else:
            self.path2active = self.path2data_list[idx + 1]


class View(object):
    def __init__(self, controller):
        self.controller = controller

        self.plot = Plot(self)
        self.controlls = Controlls(self)

# View
class Plot(object):
    def __init__(self, view):
        self.view = view
        self.controller = view.controller
        self.f = None
        self.a = None
        self.at = None
        self._tmp_alt_x = 0
        self.keymap = {'a': 'ascent',
                    'w': 'park',
                    'd': 'descent',
                    't': 'top',
                    'v': 'launch',
                    'b': 'landing'}
        self.tag_color_map = {'ascent': colors[1], 
                              'descent': colors[2],
                              'park': colors[3],
                              'top': 'black'}
        self.tag_lw_map = {'top': 1.5}

    def initiate(self):
        self.f, self.a = plt.subplots()
        self.f.autofmt_xdate()
        # self.at = self.a.twinx()

        self.plot_active_d1()
        self.plot_active_d2()
        self.update_xlim()
        self.event_handling()
        self.draw_vlines_from_database()

        # out = self.controller.database.get_all_flights()
        # for idx, flight in out.iterrows():
        #     self.controller.view.plot.plot_flight_duration(flight.start, flight.end, flight.alt, flight.alt_source)

        # custom_lines = [plt.Line2D([0], [0], color=colors[0], alpha = 0.3, lw=5),
        #                 plt.Line2D([0], [0], color=colors[1], alpha = 0.3, lw=5),
        #                 plt.Line2D([0], [0], color='0.5', alpha = 0.3, lw=5),]

        # legend_source = self.a.legend(custom_lines, ['gps', 'baro', 'bad'], loc = 1)
        # self.a.legend(loc = 2)
        # self.a.add_artist(legend_source)
        # self.a.grid(True)
        return self.a, None #self.at

    def draw_vlines_from_database(self):
        out = self.controller.database.get_change_points_from_active()
        for _,row in out.iterrows():
            self.add_tag_visualization(row.datetime, row.type)
        
    def add_tag_visualization(self, datetime, tag_type):
        color_map = self.tag_color_map
        try:
            col = color_map[tag_type]
        except KeyError:
            col = None
            
        try:
            lw = self.tag_lw_map[tag_type]
        except KeyError:
            lw = 1
        g = self.a.axvline(pd.to_datetime(datetime), color = col, lw = lw, ls = '--', gid = f'vline_{datetime}')
        self.controller.tp_hline = g
        self.controller.tp_dt = datetime
        if tag_type == 'landing':
            df = self.controller.database.get_change_points_from_active()
            df.index = df.datetime
            df.sort_index(inplace = True)
            df = df.truncate(after=datetime)
            last_launch = df[df.type == 'launch'].iloc[-1]
            self.a.axvspan(pd.to_datetime(last_launch.datetime), pd.to_datetime(datetime),color = '0.8', zorder = 0, gid = f'vspan_{datetime}' )
    
    def remove_tag_visualization(self, datetime):
        for child in self.a.get_children():
            if not isinstance(child.get_gid(), type(None)):
                if datetime in child.get_gid():
                    child.remove()
        
        
    def event_handling(self):
        # def onclick(event):
        #     self.controller.send_message('{},{}'.format(event.xdata, event.ydata))
        #     # self.controller.event = event

        def on_key(event):
            self.controller.send_message('key: {}'.format(event.key))
            self.controller.tp_event = event
            if event.key == 'z':
                dt = pd.to_datetime(plt.num2date(event.xdata).strftime('%Y-%m-%d %H:%M:%S'))
                self.controller.view.controlls.accordeon_start.value = dt.__str__()
            elif event.key == 'x':
                dt = pd.to_datetime(plt.num2date(event.xdata).strftime('%Y-%m-%d %H:%M:%S'))
                self.controller.view.controlls.accordeon_end.value = dt.__str__()
            # elif event.key == 'a':
            #     self.controller.view.controlls.accordeon_alt.value = str(event.ydata)
            #     self._tmp_alt_x = event.xdata
            
            elif event.key in self.keymap.keys():
                key2type = self.keymap
                cp_type = key2type[event.key]
                # self.controller.send_message('trying 1')
                dt = pd.to_datetime(plt.num2date(event.xdata).strftime('%Y-%m-%d %H:%M:%S')).__str__()
                # self.controller.send_message('trying 2')
                self.view.controlls.add_row2gridbox(dt,cp_type)
                # self.controller.send_message('trying 3')
                self.controller.database.add_change_point(dt,cp_type)
                self.add_tag_visualization(dt, cp_type)

        self.f.canvas.mpl_connect('key_press_event', on_key)

        # self.f.canvas.mpl_connect('button_press_event', onclick)

    def plot_active_d1(self):
        # self.controller.data.dataset1.active.data['altitude (from iMet PTU) [km]'].plot(ax = self.a, label = 'altitude (from iMet PTU) [km]')
        # self.controller.data.dataset1.active.data['GPS altitude [km]'].plot(ax = self.a, label = 'GPS altitude [km]')
        # self.controller.data.dataset1.active.plot(ax = self.a)
        
        active = self.controller.data.dataset1.active
        plt.plot(active.index, active.iloc[:,0].values, zorder = 100)
        # self.a.legend(loc = 2)

    def update_1(self):
        if isinstance(self.controller.data.dataset1._load_all, type(None)):
            self.a.clear()
            self.plot_active_d1()
        else:
            finfo = self.controller.data.dataset1.active_info.loc[self.controller.data.dataset1.path2active.name, :]
            self.a.set_ylim(finfo.v_min, finfo.v_max)
            
        self.draw_vlines_from_database()
        self.update_xlim()
        self.f.autofmt_xdate()

    def plot_active_d2(self):
        if not isinstance(self.controller.data.dataset2, type(None)):
            self.controller.data.dataset2.active.data.Altitude.plot(ax = self.at, color = colors[2])
            # self.at.legend(loc = 1)
            return True
        else:
            return False

    def update_2(self, keep_limits = False):
        if isinstance(self.at, type(None)):
            return

        xlim = self.at.get_xlim()
        ylim = self.at.get_ylim()

        self.at.clear()
        self.plot_active_d2()
        if not keep_limits:
            self.update_xlim()
        else:
            self.at.set_xlim(xlim)
            self.at.set_ylim(ylim)

    def update_xlim(self):
        if isinstance(self.controller.data.dataset1._load_all, type(None)):
            if not isinstance(self.controller.data.dataset2, type(None)):
                xmin = np.min([self.controller.data.dataset1.active.index.min(), self.controller.data.dataset2.active.data.index.min()])
                xmax = np.max([self.controller.data.dataset1.active.index.max(), self.controller.data.dataset2.active.data.index.max()])
            else:
                xmin = self.controller.data.dataset1.active.index.min()
                xmax = self.controller.data.dataset1.active.index.max()
        else:
            finfo = self.controller.data.dataset1.active_info.loc[self.controller.data.dataset1.path2active.name, :]
            xmin, xmax = (finfo.t_start, finfo.t_end)
        # if self.controller.data.dataset1._load_all:

        self.a.set_xlim(xmin, xmax)

    def plot_flight_duration(self, start=None, end=None, alt = None, alt_source = None):
        if isinstance(start, type(None)):
            start = self.controller.view.controlls.accordeon_start.value
        if isinstance(end, type(None)):
            end = self.controller.view.controlls.accordeon_end.value
        if isinstance(alt, type(None)):
            self.controller.send_message('test alt: {}'.format(self.controller.view.controlls.accordeon_alt.value))
            alt = float(self.controller.view.controlls.accordeon_alt.value)
        if isinstance(alt_source, type(None)):
            alt_source = self.controller.view.controlls.dropdown_gps_bar_bad.value

        if alt_source == 'gps':
            col = colors[0]
            label = 'gps'
        elif alt_source == 'baro':
            col = colors[1]
            label = 'baro'
        elif alt_source in ['bad', 'bad_but_usable_gps', 'bad_but_usable_baro']:
            col = '0.5'
            label = 'bad'
        else:
            raise ValueError('{} is not an option'.format(alt_source))

        self.a.axvspan(start, end, alpha=0.3, picker=5, color = col)

        self.controller.send_message('start: {}'.format(start))
        self.controller.send_message('end: {}'.format(end))
        self.controller.send_message('alt: {}'.format(alt))
        self.a.plot([pd.to_datetime(start),pd.to_datetime(end)],[float(alt),float(alt)], color = 'black', ls = '--')


class Controlls(object):
    def __init__(self, view):
        self.view = view
        self.controller = view.controller

    def initiate(self):

        tab_children = []
    ###########################
    # data 1 box
        d1_vbox_childs = []
        ##
        ###
        d1_button_next = widgets.Button(description='next measurement')
        d1_button_prev = widgets.Button(description='prev measurement')

        d1_button_next.on_click(self.on_d1_botton_next)
        d1_button_prev.on_click(self.on_d1_botton_prev)

        d1_dropdown_fnames_options = [i.name for i in self.controller.data.dataset1.path2data_list]
        d1_dropdown_fnames_value = self.controller.data.dataset1.path2active.name
        self.d1_dropdown_fnames = widgets.Dropdown(options=d1_dropdown_fnames_options,
                                                   value=d1_dropdown_fnames_value,
                                                   #     description='N',
                                                   # disabled=disable_data_2,
                                                   )

        self.d1_dropdown_fnames.observe(self.on_change_d1_dropdown_fnames)


        d1_box_h_1 = widgets.HBox([d1_button_prev, d1_button_next, self.d1_dropdown_fnames])
        ###
        d1_vbox_childs.append(d1_box_h_1)

        ##
        ###
        d1_text_path = widgets.Text(placeholder='path name', disabled = False)
        self.d1_text_path = d1_text_path
        d1_vbox_childs.append(d1_text_path)

        ##
        d1_vbox = widgets.VBox(d1_vbox_childs)
        tab_children.append({'element': d1_vbox, 'title': 'iMet'})

    ############################
    # data 2 box
        if isinstance(self.controller.data.dataset2, type(None)):
            disable_data_2 = True
            d2_dropdown_fnames_options = []
            d2_dropdown_fnames_value = None
        else:
            disable_data_2 = False
            d2_dropdown_fnames_options = [i.name for i in self.controller.data.dataset2.path2data_list]
            d2_dropdown_fnames_value = self.controller.data.dataset2.path2active.name

        d2_vbox_childs = []
        ##
        ###
        d2_button_next = widgets.Button(description='next measurement', disabled = disable_data_2)
        d2_button_prev = widgets.Button(description='prev measurement', disabled = disable_data_2)
        self.d2_dropdown_fnames = widgets.Dropdown(options=d2_dropdown_fnames_options,
                                              value=d2_dropdown_fnames_value,
                                            #     description='N',
                                                disabled = disable_data_2,
                                            )

        d2_button_next.on_click(self.on_d2_botton_next)
        d2_button_prev.on_click(self.on_d2_botton_prev)
        self.d2_dropdown_fnames.observe(self.on_change_d2_dropdown_fnames)

        d2_box_h_1 = widgets.HBox([d2_button_prev, d2_button_next, self.d2_dropdown_fnames])
        ###
        d2_vbox_childs.append(d2_box_h_1)

        ##
        ###
        ## text field showing the path
        d2_text_path = widgets.Text(placeholder='path name', disabled = False)
        self.d2_text_path = d2_text_path

        d2_vbox_childs.append(d2_text_path)

        ##
        d2_vbox = widgets.VBox(d2_vbox_childs)
        tab_children.append({'element': d2_vbox, 'title': 'POPS'})

        # others box



    # Tab
        tab = widgets.Tab([child['element'] for child in tab_children])
        for e ,child in enumerate(tab_children):
            tab.set_title(e ,child['title'])

    # accordeon
        txt = 'keymap:\t'
        txt += ' - '.join(['{}:{}'.format(i[0], i[1]) for i in self.controller.view.plot.keymap.items()])
        box_layout = widgets.Layout(border='solid 1px')
        description = widgets.Box((widgets.Label(txt),), layout = box_layout)
        # items = [widgets.Label('change point'), widgets.Label('followed by'), widgets.Label('')]
        self.gridbox = widgets.GridBox([], layout=widgets.Layout(grid_template_columns="repeat(3, 200px)"))
        self.populate_gridbox_from_database()
        self.controller.tp_gb = self.gridbox
        
        self.button_gridbox_reinitiate = widgets.Button(description = 'sort by datetime')
        self.button_gridbox_reinitiate.on_click(self.populate_gridbox_from_database)
    # the old one
    
        # self.accordeon_start = widgets.Text(value='',
        #                                     placeholder='hit z key',
        #                                     description='start:',
        #                                     disabled=False
        #                                     )
        # self.accordeon_end = widgets.Text(value='',
        #                                     placeholder='hit x key',
        #                                     description='end:',
        #                                     disabled=False
        #                                     )
        # self.accordeon_alt = widgets.Text(value='',
        #                                   placeholder='hit a key',
        #                                   description='altitude:',
        #                                   disabled=False
        #                                   )
        # hbox_accordeon_start_stop = widgets.HBox([self.accordeon_start, self.accordeon_end])


        # self.dropdown_gps_bar_bad= widgets.Dropdown(options=['gps', 'baro', 'bad', 'bad_but_usable_gps', 'bad_but_usable_baro'],
        #                                             value='gps',
        #                                             description='which alt to use:',
        #                                             disabled=False,
        #                                             )

        # self.button_save_unsave_flight = widgets.Button(description = 'save/unsave flight')
        # self.button_save_unsave_flight.on_click(self.on_button_save_flight)

        # hbox_accordeon_alt_source = widgets.HBox([self.dropdown_gps_bar_bad, self.accordeon_alt])

        accordon_box = widgets.VBox([description, self.button_gridbox_reinitiate, self.gridbox])#,hbox_accordeon_start_stop, hbox_accordeon_alt_source, self.button_save_unsave_flight])
        accordion_children = [accordon_box]
        accordion = widgets.Accordion(children=accordion_children)
        accordion.set_title(0,'do_stuff')

    # messages
        self.messages = widgets.Textarea('\n'.join(self.controller._message), layout={'width': '100%'})
        # message_box = widgets.HBox([self.messages])
        # OverVbox

        overVbox = widgets.VBox([tab, accordion, self.messages])
        display(overVbox)
        ####################
        self.update_d1()
        self.update_d2()
        self.update_accordeon()

    # def on_inttext_deltat(self, evt):
    #     if evt['name'] == "value":
    #         self.controller.data.delta_t = int(evt['new'])
    #         dt = int(evt['new']) - int(evt['old'])
    #         self.controller.data.dataset2.active.data = self.controller.data.dataset2.active.data.shift(periods=-dt,
    #                                                                               freq=pd.to_timedelta(1, 's'))
    #         self.controller.view.plot.update_2(keep_limits = True)

    def populate_gridbox_from_database(self, *args):
        items = [widgets.Label('change point'), widgets.Label('followed by'), widgets.Label('')]
        self.gridbox.children = items
        out = self.controller.database.get_change_points_from_active()
        out.sort_values('datetime', inplace=True)
        for _,row in out.iterrows():
            self.add_row2gridbox(row.datetime, row.type)

    def add_row2gridbox(self,dt,cp_type, initialization = False):
        layout={'width': '90%'}
        
        # row_id = int(len(self.gridbox.children) / 3) + 1
        # wdg_text_dt = widgets.Text(dt,layout = layout, model_id = f'gbtxtdt_{row_id:04d}')
        # wdg_text_type = widgets.Text(cp_type,layout = layout, model_id = f'gbtxtstyle_{row_id:04d}')
        # wdg_button = widgets.Button(description = 'delete', model_id = f'gbbtndel_{row_id:04d}')
        
        row_id = dt
        wdg_text_dt = widgets.Text(dt,layout = layout, model_id = f'gbtxtdt_{row_id}')
        wdg_text_type = widgets.Text(cp_type,layout = layout, model_id = f'gbtxtstyle_{row_id}')
        wdg_button = widgets.Button(description = 'delete', model_id = f'gbbtndel_{row_id}')
        
        wdg_button.on_click(self.on_delet_gridbox_row)
        self.gridbox.children += (wdg_text_dt, wdg_text_type, wdg_button)
        
        self.controller.send_message('add row 2 gridbox')
        
        # if not initialization:
        # self.controller.database.add_change_point(dt,cp_type)
        
    
    def on_delet_gridbox_row(self,button):
        self.controller.tp_del = button
        gbrowid = button.model_id.split('_')[-1]
        datetime =  [ch.value for ch in self.gridbox.children if ch.model_id == f'gbtxtdt_{gbrowid}'][0]
        self.gridbox.children = [ch for ch in self.gridbox.children if ch.model_id.split('_')[-1] != gbrowid]
        self.controller.send_message(f'Deleted changepoint with index {gbrowid} from gridbox row')
        self.controller.database.remove_change_point(datetime)
        self.view.plot.remove_tag_visualization(datetime)
    
    def on_button_save_flight(self, event):

        start = self.controller.view.controlls.accordeon_start.value
        if isinstance(pd.to_datetime(start), pd._libs.tslibs.nattype.NaTType):
            self.controller.send_message('error concerning start. Value provided: "{}"'.format(start))
            return

        end = self.controller.view.controlls.accordeon_end.value
        if isinstance(pd.to_datetime(end), pd._libs.tslibs.nattype.NaTType):
            self.controller.send_message('error concerning end. Value provided: "{}"'.format(end))
            return

        alt = self.controller.view.controlls.accordeon_alt.value
        try:
            float(alt)
        except ValueError:
            self.controller.send_message('error concerning altitude. Value provided: "{}"'.format(alt))
            return



        self.controller.event = event
        self.controller.view.plot.plot_flight_duration()
        self.controller.database.add_flight()
        self.accordeon_end.value = ''
        self.accordeon_start.value = ''
        self.accordeon_alt.value = ''
        self.dropdown_gps_bar_bad.value = 'gps'

    def update_d1(self):
        self.d1_text_path.value = self.controller.data.dataset1.path2active.name
        # self.dropdown_popssn.value = self.controller.data.dataset1.path2active.name.split('.')[-2][-2:]
        # self.inttext_deltat.value = self.controller.data.delta_t

    def on_d1_botton_next(self, evt):
        self.controller.data.dataset1.next()
        self.update_d1()
        self.update_accordeon()
        self.controller.view.plot.update_1()
        self.populate_gridbox_from_database()

    def on_d1_botton_prev(self, evt):
        self.controller.data.dataset1.previous()
        self.update_d1()
        self.update_accordeon()
        self.controller.view.plot.update_1()
        self.populate_gridbox_from_database()

    def update_d2(self):
        if isinstance(self.controller.data.dataset2, type(None)):
            return
        else:
            self.d2_text_path.value = self.controller.data.dataset2.path2active.name
            self.d2_dropdown_fnames.value = self.controller.data.dataset2.path2active.name
            self.inttext_deltat.value = self.controller.data.delta_t

    def update_accordeon(self):
        return
        # active = self.controller.database.active_set()
        # self.button_bind_measurements.unobserve(self.on_button_bind_measurements)
        # if active.shape[0] == 1:
        #     # print('blabla')
        #     # print(active)
        #     # print(active.popssn[0])
        #     self.dropdown_popssn.value = active.popssn[0]
        #     self.inttext_deltat.value = active.delta_t_s[0]
        #     self.accordeon_assigned.value = True
        #     self.button_bind_measurements.value = True
        # elif active.shape[0] == 0:
        #     self.accordeon_assigned.value = False
        #     self.button_bind_measurements.value = False
        #     pass
        # self.button_bind_measurements.observe(self.on_button_bind_measurements)


    def on_change_d2_dropdown_fnames(self, change):
        # self.controller.test = change
        # print(change)
        if change['type'] == 'change' and change['name'] == 'value':
            # print("changed to %s" % change['new'])
            base = self.controller.data.dataset2.path2data
            # self.controller.data.dataset2.active = base.joinpath(change['new'])
            self.controller.data.dataset2.path2active = base.joinpath(change['new'])
            # self.update_d2()
            self.update_accordeon()
            self.d2_text_path.value = self.controller.data.dataset2.path2active.name
            self.controller.view.plot.update_2()


    def on_change_d1_dropdown_fnames(self, change):
        # self.controller.test = change
        # print(change)
        if change['type'] == 'change' and change['name'] == 'value':
            # print("changed to %s" % change['new'])
            base = self.controller.data.dataset1.path2data
            # self.controller.data.dataset2.active = base.joinpath(change['new'])
            self.controller.data.dataset1.path2active = base.joinpath(change['new'])
            # self.update_d2()
            self.update_accordeon()
            self.d1_text_path.value = self.controller.data.dataset1.path2active.name
            self.controller.view.plot.update_1()

    def on_d2_botton_next(self, evt):
        self.controller.data.dataset2.next()
        self.update_d2()
        self.update_accordeon()
        self.controller.view.plot.update_2()

    def on_d2_botton_prev(self, evt):
        self.controller.data.dataset2.previous()
        self.update_d2()
        self.update_accordeon()
        self.controller.view.plot.update_2()

    # def on_button_bind_measurements(self, evt):
    #     if evt['name'] == 'value':
    #         if evt['new'] == True:
    #             self.controller.database.bind_measurements()
    #         if evt['new'] == False:
    #             self.controller.database.unbind_measurements()
    #         self.update_accordeon()
    #     # print('baustelle')

class Database(database.NsaSciDatabase):
    def __init__(self, controller):
        # super().__init__(path2db)
        self.controller = controller
        self.path2db = self.controller.paths['path2database']
        # self.tbl_name = 'flights'
        self.connection = self.create_connection()
        sql = """ CREATE TABLE IF NOT EXISTS change_points (
                    file_name text,
                    datetime text,
                    type text,
                    comment text
                ); """
            # sql = """ CREATE TABLE IF NOT EXISTS change_points (
            #         id integer PRIMARY KEY,
            #         file_name text,
            #         datetime text,
            #         type text,
            #         comment text
            #     ); """
        self.create_table(sql)
    
    def create_connection(self):
        """ create a database connection to the SQLite database
            specified by db_file
        :param db_file: database file
        :return: Connection object or None
        """
        conn = None
        # try:
        conn = sqlite3.connect(self.path2db)
            # return conn
        # except Error as e:
            # self.controller.send_message(e)
     
        return conn
    
    def create_table(self, create_table_sql):
        """ create a table from the create_table_sql statement
        :param conn: Connection object
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        # try:
        c = self.connection.cursor()
        c.execute(create_table_sql)
        # except Error as e:
        #     self.controller.send_message(e)
            
    def get_all_change_points(self):
        # try:
        out = pd.read_sql('SELECT * FROM change_points', self.connection)
        # except Error as e:
        #     self.controller.send_message(e)
        return out
    
    def get_change_points_from_active(self):
        fname = self.controller.data.dataset1.path2active.name
        sql = f"""SELECT * FROM change_points
                    WHERE file_name='{fname}'"""
        out = pd.read_sql(sql,self.connection)
        return out
    # def get_all_flights(self):
    #     qu = """Select * from flights"""
    #     with sqlite3.connect(self.path2db)  as db:
    #         out = pd.read_sql(qu, db)
    #     return out

    def add_change_point(self, datetime, cp_type, fname = None, comment = ''):
        # self.controller.send_message('going this way')
        if isinstance(fname, type(None)):
            fname = self.controller.data.dataset1.path2active.name
        sql = f"""INSERT INTO change_points
             VALUES('{fname}', '{datetime}', '{cp_type}', '{comment}')"""
        # self.controller.tp_sql = sql
        c = self.connection.cursor()
        c.execute(sql)
        self.connection.commit()
        self.controller.send_message('added entry to database')
        return
    
    def remove_change_point(self, datetime, fname = None):
        if isinstance(fname, type(None)):
            fname = self.controller.data.dataset1.path2active.name
        sql = f"""DELETE FROM change_points 
            WHERE file_name='{fname}'
            AND datetime='{datetime}'"""
  
        self.controller.tp_sql = sql
        c = self.connection.cursor()
        # try:
        c.execute(sql)
        
        self.connection.commit()
        self.controller.send_message(f'deleted database entry at {datetime}')
        # except Error as e:
            # self.controller.send_message(e)
        
        return
        
        
        # rdict = dict(flight_id='',
        #              start=self.controller.view.controlls.accordeon_start.value,
        #              end=self.controller.view.controlls.accordeon_end.value,
        #              alt = float(self.controller.view.controlls.accordeon_alt.value),
        #              alt_source=self.controller.view.controlls.dropdown_gps_bar_bad.value,
        #               iMet_fname=self.controller.data.dataset1.path2active.name)


        
        # with sqlite3.connect(self.path2db) as db:
        #     # get next index
        #     # qu = 'select Max(idx) from match_datasets_imet_pops'
        #     # next_idx = pd.read_sql(qu, db).iloc[0, 0]
        #     # if not next_idx:
        #     #     next_idx = 1
        #     # else:
        #     #     next_idx = int(next_idx) + 1
        #     qu = 'select id from {}'.format(self.tbl_name)
        #     next_idx = pd.read_sql(qu, db)  # .iloc[0, 0]
        #     next_idx = next_idx.astype(int).max().iloc[0]
        #     if np.isnan(next_idx):
        #         next_idx = 1
        #     else:
        #         next_idx = int(next_idx) + 1


        #     df = pd.DataFrame(rdict, index=[next_idx])
        #     df.index.name = 'id'

        #     df.to_sql(self.tbl_name, db,
        #             #                  if_exists='replace'
        #             if_exists='append'
        #             )




class Controller(object):
    def __init__(self,
                 path2data,
                 path2data_alt = None,
                 path2database = None):      
        
        paths = dict(path2data = path2data,
                     path2data_alt = path2data_alt,
                     path2database = path2database)
        for k,v in paths.items():
            if isinstance(v, type(None)):
                pass
            elif not isinstance(v, pathlib.PosixPath):
                paths[k] = (pathlib.Path(v))
                
        self.paths = paths

        self._message = []
        self.data = Data_container(self)
        self.view = View(self)
        self.database = Database(self)


    def send_message(self, txt):
        # print(txt)
        # self._message +=self._message + '\n' + txt
        self._message.append(txt)
        if len(self._message) > 10:
            self._message = self._message[-10:]
        try:
            mt = list(reversed(self._message))
            self.view.controlls.messages.value = '\n'.join(mt)
        except AttributeError:
            pass
