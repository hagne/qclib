"""
Todo
-----
- save notes
- the date picker still does not work properly
- save tags
"""


# from atmPy.aerosols.instruments import POPS
# import icarus
import pathlib as pl

import numpy as np
#import xarray as xr
import pandas as pd

from ipywidgets import widgets
from IPython.display import display

import matplotlib.pylab as plt
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

from nsasci import database
import sqlite3

from ipywidgets import Layout
from sys import exc_info

import xarray as _xr

# def read_POPS(path):
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
#     return df

class Data(object):
    def __init__(self, path2datafolder, 
                 plot_function, 
                 gridspec_kwargs = None,
                 dropna = True,
                 file_read_error = 'raise'):
        """
        

        Parameters
        ----------
        path2datafolder : nested list
            [[dataset_name,path2datafolder,read_function, path2date_function],
             ...
            ].
            here:
                dataset_name: 
                path2datafolder: ...
                read_function: function that takes the path2file and returns a xarray ds
                path2date_function: a function that takes the path2file and returns a date 
            example:
            [['aod2','/mnt/telg/data/grad/surfrad/aod1625/0.4/tbl/2021/',read_function_AOD, path2date_function],
             ...
            ].
        plot_function : dict
            {dataset_name: plot_function,
             ...
             }
            here:
                dataset_name: has to match the dataset_name from path2datafolder
                plot_function: function that takes the data_object (e.g. self.active_data) and axis
        gridspec_kwargs : TYPE, optional
            DESCRIPTION. The default is None.
        dropna : TYPE, optional
            DESCRIPTION. The default is True.
        file_read_error: str [raise, ignore]
            What to do if the file fails to open.

        Returns
        -------
        None.

        """
        
        
        # self.axis_name = axis_name
        #### dataset properties
        ### how to read data
        # self.read_function = read_function
        self.gridspec_kwargs = gridspec_kwargs
        
        ### path to files
        if isinstance(path2datafolder, dict):
            assert(False), 'needs programming ... only nested list right now'
            zl = path2datafolder.items()
            dataset_name,path2datafolder = zip(*zl)
            
        elif isinstance(path2datafolder, list):
            dataset_name,path2datafolder, read_function, path2date_function, glob_pattern = list(zip(*path2datafolder))
            # pass
            # path2datafolder_list = path2datafolder
            # path2datafolder_list = [item for sublist in path2datafolder for item in sublist]

        else:
            assert(False), 'needs programming ... only nested list right now'
            path2datafolder = [path2datafolder,]
        
        path2datafolder = [pl.Path(p2fld) for p2fld in path2datafolder]
        self.path2datafolder = path2datafolder
        self.dataset_name = dataset_name
        self.read_function = read_function
        ### dataset names
        # if isinstance(dataset_name, type(None)):
        #     dataset_name = range(len(path2datafolder))
        # elif isinstance(dataset_name, str):
        #     dataset_name = [dataset_name,]
            
        assert(isinstance(dataset_name, (list, tuple))), f'nenenene, should not be possible ({type(dataset_name)})'
        self.dataset_name = dataset_name
        
        ### how to turn file name into datetime
        # if not isinstance(path2date_function, list):
        #     # this assumes the single provided function applies to all datasets
        #     path2date_function = [path2date_function,] * len(path2datafolder)
        
        self.path2date_function = path2date_function
        
        ### on which axis to plot
        # self.axis2ploton = axis2ploton
        
        ### bunch into datafram
        self.dataset_properties =   pd.DataFrame([path2datafolder, 
                                                  read_function, 
                                                  path2date_function,
                                                  glob_pattern
                                                  # self.axis2ploton,
                                                  ], 
                                                 index=['path2data', 'read_func', 'path2date_func','glob_pattern',
                                                        # 'axis2ploton',
                                                        ], 
                                                 columns = dataset_name).transpose()
        
        # return
        
        #### available files
        file_list = []        
        for idx, dprow in self.dataset_properties.iterrows():        
            # p2fld = row.path2data#pl.Path(p2fld)
            files = pd.Series(dprow.path2data.glob(dprow.glob_pattern))#, columns=['path2file'])
            files.index = files.apply(lambda row: dprow.path2date_func(row))
            files.sort_index(inplace=True)
            files.name = dprow.name #dataset_name[e]
            duplicates = files.index.duplicated().sum()
            assert(duplicates == 0), f'Dataset {dprow.name} has {duplicates} duplicates. improve glob string pattern?'
            file_list.append(files)
    
        files = pd.concat(file_list, axis = 1, )
        assert(dropna), 'dropna != True is not implemented yet'
        files.dropna(inplace=True)
        files.columns.name = 'dataset_name'
        files.index.name = 'date'
        
        #### plot properties
        assert(isinstance(plot_function, dict)), f'currently plot_function has to be dict, is {type(plot_function)}'
        zl = plot_function.items()
        axis_name,plot_function = zip(*zl)
        self.plot_function = plot_function
        self.axis_name = axis_name
        self.plot_properties = pd.DataFrame([self.plot_function,], columns= self.axis_name, index = ['plot_func']).transpose()
        # reduce to series if only one dataset
        # if files.shape[1] == 1:
        #     files = files.loc[:,0]
        
        # path2datafolder = pl.Path(path2datafolder)
        # files = pd.DataFrame(path2datafolder.glob('*.nc'), columns=['path2file'])
        # files.index = files.apply(lambda row: path2date_function(row.path2file), axis = 1)
        # files.sort_index(inplace=True)
        self.files = files
        self.valid_dates = files.index
        try:
            self.active_data = self.read_data()
        except:
            if file_read_error == 'ignore':
                print('could not load active dataset')
            elif file_read_error == 'raise':
                raise
                
    
    def read_data(self, date = None):
        if isinstance(date, type(None)):
            files = self.files.iloc[-1]
        else:
            files = self.files.loc[date]
            
        data = {dsn: self.dataset_properties.loc[dsn, 'read_func'](p2f) for dsn, p2f in files.items()}

        return data
    
    def plot(self, date = None, ax = None):
        if isinstance(ax, type(None)):
            f,aa = plt.subplots(self.plot_properties.shape[0], sharex=True, gridspec_kw=self.gridspec_kwargs)
            self.plot_properties['axis'] = aa
        else:
            if isinstance(ax, list):
                for a in ax:
                    a.clear()
            else:
                ax.clear() #to clean up the plo   
        # return a
        # if date is not given plot first file 
    
        
        if not isinstance(date, type(None)):
            path2file = self.files.loc[date]
            self.active_files = path2file
            #### TODO: try if we can fix the dying kernel issue if we close all files first, bettwer would it be if we would keep some in a list or so and only close if list is longer than xy
            for dataset in self.active_data:
                ds = self.active_data[dataset]
                if isinstance(ds, _xr.Dataset):
                    ds.close()
                
            self.active_data = self.read_data(date)
        
        out = {}
        # for axname, grp in self.dataset_properties.groupby('axis2ploton'):
        
        #     plot_func = self.plot_properties.loc[axname, 'plot_func']
        #     at = self.plot_properties.loc[axname, 'axis']
        #     data = {dsname: self.active_data[dsname] for dsname in grp.index}
        #     plot_func(data, at)
        #     at.zobjects = []
        #     out[axname] = {'a': at}
        for axname, row in self.plot_properties.iterrows():
            row.plot_func(self.active_data, row.axis)
            row.axis.zobjects = []
            out[axname] = {'a': row.axis}    
            
            
        # self.plot_function(self.active_data, a)
        
        # out = {'thisone':{'a':a}}
        return out

# class old_Data_container(object):
#     def __init__(self, controller, path2data):
#         self.controller = controller
#         # self.delta_t = 0
#
#         if not isinstance(path2data1, type(None)):
#             path2data1 = pathlib.Path(path2data1)
#             read_data = read_iMet #icarus.icarus_lab.read_imet
#             self.dataset1 = Data(self, path2data1, read_data, glob_pattern = 'oli*')
#         else:
#             self.dataset1 = None
#
#         if not isinstance(path2data2, type(None)):
#             path2data2 = pathlib.Path(path2data2)
#             read_data = read_POPS
#             self.dataset2 = Data(self, path2data2, read_data, glob_pattern='olitbspops*')
#         else:
#             self.dataset2 = None
#         path2data2 = Path(path2data2)

# class Data(object):
#     def __init__(self, datacontainer, path2data, read_data, glob_pattern = '*'):
#         self.controller = datacontainer.controller
#         self._datacontainer = datacontainer
#         self.read_data = read_data
#         self.path2data = path2data
#         self._path2active = None
#
#
#         self.path2data_list = sorted(list(path2data.glob(glob_pattern)))
#         self.path2active = self.path2data_list[0]
#
#     @property
#     def path2active(self):
#         return self._path2active
#
#     @path2active.setter
#     def path2active(self, value):
#         self._datacontainer.delta_t = 0
#         self._path2active = value
#         self.controller.send_message('opening {}'.format(self._path2active.name))
#         self.active = self.read_data(self._path2active)
#
#     def previous(self):
#         idx = self.path2data_list.index(self.path2active)
#         if idx == 0:
#             pass
#         elif idx == -1:
#             raise ValueError('not possibel')
#         else:
#             self.path2active = self.path2data_list[idx - 1]
#
#     def next(self):
#         idx = self.path2data_list.index(self.path2active)
#         if idx == len(self.path2data_list) - 1:
#             pass
#         elif idx == -1:
#             raise ValueError('not possibel')
#         else:
#             self.path2active = self.path2data_list[idx + 1]


class View(object):
    def __init__(self, controller):
        self.controller = controller

        self.plot = ViewPlot(self)
        self.controlls = ViewControlls(self)

# View
class ViewPlot(object):
    def __init__(self, view):
        self.view = view
        self.controller = view.controller
        self.f = None
        self.a = None
        # self.at = None
        self.plot_content = None

    def initiate(self):
        self.controller.initiation_in_progress = True
        self.plot_content = self.controller.data.plot(self.controller.view.controlls.date_picker.value)
        # self.a = [pc['a'] for pc in self.plot_content]
        self.a = [self.plot_content[k]['a'] for k in self.plot_content]
        self.f = self.a[0].get_figure()
        # for at in self.a:
        #     leg = at.legend()
        #     leg.remove()
        self.controller.view.controlls._plot_settings_accordion_initiate()
        # self.f, self.a = plt.subplots()
        # self.f.autofmt_xdate()
        #
        # self.at = self.a.twinx()
        #
        # self.plot_active_d1()
        # self.plot_active_d2()
        # self.update_xlim()
        self.update_lims_from_db()
        self.controller.view.controlls._tags_assign_update()
        self.controller.initiation_in_progress = False
        return self.a

    def update_axes(self):
        date = pd.to_datetime(self.controller.view.controlls.date_picker.value)
        self.controller.data.plot(date, ax = self.a)
        self.update_lims_from_db()

    def update_lims_from_db(self):
        if not self.controller.database._valid:
            return
        tbl_name = self.controller.database.tbl_name_plot_settings #  'vis_nsascience_quicklooks_plot_settings'
        date = self.controller.view.controlls.date_picker.value
        for k in self.plot_content:
            qu = 'select * from "{}" WHERE plot="{plot}" AND date="{date}"'.format(tbl_name, plot=k, date=date)
            with sqlite3.connect(self.controller.database.path2db) as db:
                out = pd.read_sql(qu, db)
            #     break

            a = self.plot_content[k]['a']

            vmax = None
            vmin = None

            for idx, row in out.iterrows():

                if row.lim == 'z_max':
                    vmax = row.value
                elif row.lim == 'z_min':
                    vmin = row.value
                else:
                    self.controller.send_message('sorry not yet implemented for {}'.format(row.lim))

            for lc in a.zobjects:
                lable = a.cax.get_ylabel()
                lc.set_clim(vmin, vmax)
                a.cax.set_ylabel(lable)
                pass


    # def plot_active_d1(self):
    #     # self.controller.data.dataset1.active.data['altitude (from iMet PTU) [km]'].plot(ax = self.a, label = 'altitude (from iMet PTU) [km]')
    #     # self.controller.data.dataset1.active.data['GPS altitude [km]'].plot(ax = self.a, label = 'GPS altitude [km]')
    #     self.controller.data.dataset1.active.plot(ax = self.a)
    #     self.a.legend(loc = 2)

    def old_plot_active_d1(self):
        if not isinstance(self.controller.data.dataset1, type(None)):
            self.controller.data.dataset1.active.plot(ax=self.a)
            self.a.legend(loc=2)
            # self.at.legend(loc = 1)
            return True
        else:
            return False


    def old_update_1(self):
        self.a.clear()
        self.plot_active_d1()
        self.update_xlim()

    def old_plot_active_d2(self):
        if not isinstance(self.controller.data.dataset2, type(None)):
            self.controller.data.dataset2.active.data.Altitude.plot(ax = self.at, color = colors[2])
            self.at.legend(loc = 1)
            return True
        else:
            return False

    def old_update_2(self, keep_limits = False):
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
        pass
        # xmin = np.min([self.controller.data.dataset1.active.index.min(), self.controller.data.dataset2.active.data.index.min()])
        # xmax = np.max([self.controller.data.dataset1.active.index.max(), self.controller.data.dataset2.active.data.index.max()])
        # self.a.set_xlim(xmin, xmax)


class ViewControlls(object):
    def __init__(self, view):
        self.view = view
        self.controller = view.controller

# todo: tags
    def _tags_constrain_get_state(self):
        dd_list = self.tags_constrain_dropdownlist
        out = [dd_list[0].value] + [[hb.children[0].value, hb.children[1].value] for hb in dd_list[1:]]
        return out

    def _tags_constrain(self):
        tag_list = [''] + self.controller.database.get_available_tags()

        op_list = ['and', 'or', 'not']
        dd_list = []

        def on_change(evt):
            if evt['name'] == 'value':
                check_unused()
                self.controller.selection_from_tags()
                self.date_picker_dropdown.options = self.controller.valid_dates_selection
            else:
                return

        def on_add(evt):
            op = widgets.Dropdown(
                options=op_list,
                value='and',
                description='',
                disabled=False, )
            op.observe(on_change)
            dd2 = widgets.Dropdown(
                options=tag_list.copy(),
                value='',
                description='',
                disabled=False,
            )
            dd2.observe(on_change)

            hb = widgets.HBox([op, dd2])
            dd_list.append(hb)
            vb.children = vb.children[:-1] + (hb,) + (vb.children[-1],)

        def check_unused():
            dd_list_t = self.tags_constrain_dropdownlist.copy()
            for e, dd in enumerate(dd_list_t):
                if e == 0:
                    continue
                if dd.children[1].value == '':
                    dd_list_t.pop(e)

            if len(self.tags_constrain_dropdownlist) != len(dd_list_t):
                self.tags_constrain_dropdownlist = dd_list_t
                vb.children = self.tags_constrain_dropdownlist


        dd = widgets.Dropdown(
            options=tag_list.copy(),
            value='',
            description='tag:',
            disabled=False,
        )
        dd.observe(on_change)
        dd_list.append(dd)

        bt_add = widgets.Button(
            description='add tag',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Click me',
            icon='plus'
        )
        bt_add.on_click(on_add)

        vb = widgets.VBox([dd, bt_add])
        self.tags_constrain_dropdownlist = dd_list
        return vb

    def _tags_assign_update(self):
        """updates the state of the checkboxes accoring to whats saved in the db for the particular day"""
        if not self.controller.database._valid:
            return
        tags_and_values = self.controller.database.get_tags()
        tags,values = zip(*tags_and_values)
        self.controller.tp_tags = tags
        # tag = out[0]
        # available_tags = [tag.description for tag in self.tags]
        for cb in self.tags:
            tt = cb.description
            text = [tag for tag in self.tag_values if tag.placeholder == tt][0]
            if tt in tags:
                cb.value = True
                vt = [tag for tag in tags_and_values if tag[0] == tt][0][1]
                if isinstance(vt, type(None)):
                    vt = ''
                else:
                    vt = '{}'.format(vt)
                text.value = vt
            else:
                cb.value = False
                text.value = ''

        # for tag in tags:
        #     cb = [cb for cb in self.tags if cb.description == tag][0]
        #     cb.value = True


    def _tags_assign(self):
        tags = self.controller.database.get_available_tags()
        # tag_dict = {'conditions': {'options': ['cloudi', 'clear', 'precip_snow', 'precip_rain']}}
        tag_dict = {'conditions': {'options': tags}}

        def on_add_tag(evt, box, options, new_tag, all_checkboxes):
            if new_tag.value in options:
                return
            elif new_tag.value.strip() == '':
                returnpath2database = path2database
            else:
                options.append(new_tag.value)
                newcb = widgets.Checkbox(description=new_tag.value)
                newcb.observe(on_cb_change, names=['_property_lock'])
                all_checkboxes.append(newcb)
                box_child_list = list(box.children + (newcb,))
                box_child_list.sort(key=lambda x: x.description)
                box.children =box_child_list
                self.controller.tp_box = box
                return

        def on_add_tag_new(evt, box, options, all_checkboxes, all_values):
            if evt.value in options:
                return
            elif evt.value.strip() == '':
                return
            else:
                options.append(evt.value)
                newcb = widgets.Checkbox(description=evt.value, indent = False, value = False)
                newcb.observe(lambda x: on_cb_change(x, all_checkboxes, all_values), names=['_property_lock'])
                newtext = widgets.Text(placeholder = evt.value)
                newtext.on_submit(lambda x: on_cb_change(x, all_checkboxes, all_values))
                newbox = widgets.HBox([newcb, newtext])
                all_checkboxes.append(newcb)
                all_values.append(newtext)
                box_child_list = list(box.children + (newbox,))
                # box_child_list.sort(key=lambda x: x.children[0].description)
                box.children = box_child_list
                self.controller.tp_box = box
                return


        def on_cb_change(evt, cbs, values):
            tp = type(evt).__name__
            if type(evt).__name__ == 'Bunch':
                cb = evt['owner']
                tag = cb.description
                text = [txt for txt in values if txt.placeholder == tag][0]
                new = evt['new']
                # not sure why the following was necessary
                if len(new) != 1:
                    return
                cb_value = new['value']
            elif type(evt).__name__ == 'Text':
                text = evt
                tag = evt.placeholder
                cb = [cb for cb in cbs if cb.description == tag][0]
                cb_value = cb.value

            # print('{}: {} -> {}'.format(tp, cb , text))
            # return
            # print('{}: cb: {}, tx: {}'.format(tag, cb_value, text.value))
            # return
            self.controller.send_message('set tag {}:{} ({})'.format(tag, cb_value, text.value))
            self.controller.database.set_tag(tag, cb_value, text.value)

        radio_button_list = []
        all_checkboxes = []
        all_values = []
        self.tag_values  = all_values
        self.tags = all_checkboxes

        #This loop not really used currently ... only one element
        for tag_type in tag_dict.keys():
            #     rb = widgets.RadioButtons(options = tags[tag_type]['options'])

            cb_box = widgets.VBox() # needs to be defined here since used by new_tag
            # new tag

            new_tag = widgets.Text(placeholder='enter new tag')
            new_tag.on_submit(lambda x: on_add_tag_new(x, cb_box, tag_dict[tag_type]['options'], all_checkboxes, all_values))
            add_box = widgets.HBox([new_tag,])
            cbs = []
            for opt in tag_dict[tag_type]['options']:
                cb = widgets.Checkbox(description=opt, indent = False)
                cb.observe(lambda x: on_cb_change(x, all_checkboxes, all_values), names=['_property_lock'])
                text = widgets.Text(placeholder = opt)
                text.on_submit(lambda x: on_cb_change(x, all_checkboxes, all_values))
                cbs.append(widgets.HBox([cb,text]))
                all_checkboxes.append(cb)
                all_values.append(text)
            # cb_box = widgets.VBox([add_box]+cbs)
            cb_box.children = [add_box] + cbs
            # box it
            # box = widgets.HBox([cb_box, add_box])
            radio_button_list.append(cb_box)

        acc = widgets.Accordion(radio_button_list)
        for e, tag_type in enumerate(tag_dict.keys()):
            acc.set_title(e, tag_type)
        return acc

    def _plot_settings_axes(self, axes_content, key):
        # vmin = -1e100
        # vmax = 1e100
        a = axes_content['a']
        def on_change(change, set_lim, vmin, vmax):
            if self.controller.initiation_in_progress:
                return
            # self.tester = change
            param  = change['owner'].description
            self.controller.database.set_plot_settings(key, param, change['new'])
            set_lim(vmin.value, vmax.value)
        step = 1
        xlim_min = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='x_min',
            disabled=False
        )

        xlim_max = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='x_max',
            disabled=False
        )

        # xlim_min.observe(lambda x: on_change(x, a.set_xlim(), xlim_min, xlim_max), names='value')
        # ylim_max.observe(lambda x: on_change(x, set_lim_z, xlim_min, xlim_max), names='value')

        xhbox = widgets.HBox([xlim_min, xlim_max])
        # display(xhbox)

        ylim_min = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='y_min',
            disabled=False
        )
        ylim_max = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='y_max',
            disabled=False
        )

        ylim_min.observe(lambda x: on_change(x, a.set_ylim, ylim_min, ylim_max), names='value')
        ylim_max.observe(lambda x: on_change(x, a.set_ylim, ylim_min, ylim_max), names='value')
        yhbox = widgets.HBox([ylim_min, ylim_max])
        # display(hbox)

        zlim_min = widgets.FloatText(
            # value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='z_min',
            disabled=False
        )

        def set_lim_z(vmin, vmax):
            # for zo  in axes_content['zobjects']:
            for zo in a.zobjects:
                zo.set_clim(vmin,vmax)

        zlim_max = widgets.FloatText(
            # value=7.5,
            # min=vmin,
            # max=vmax,
            step=step,
            description='z_max',
            disabled=False
        )
        zlim_min.observe(lambda x: on_change(x, set_lim_z, zlim_min, zlim_max), names='value')
        zlim_max.observe(lambda x: on_change(x, set_lim_z, zlim_min, zlim_max), names='value')

        zhbox = widgets.HBox([zlim_min, zlim_max])

        vbox = widgets.VBox([xhbox, yhbox, zhbox])
        return vbox, {'x': (xlim_min, xlim_max), 'y': (ylim_min, ylim_max), 'z': (zlim_min, zlim_max)}

    def _plot_settings(self):
        pc = self.controller.view.plot.plot_content
        self.plot_setting_accordion = widgets.Accordion([])
        if not isinstance(pc, type(None)):
            self._plot_settings_accordion_initiate()
        return self.plot_setting_accordion


    # def _plot_settings_accordion_update(self):

    def _plot_settings_accordion_initiate(self):
        self.controller.initiation_in_progress = True
        pc = self.controller.view.plot.plot_content
        childs = []
        self.plot_settings = {}
        for key in pc:
            axes = pc[key]
            a = axes['a']
            vbox, ps = self._plot_settings_axes(axes, key)
            childs.append(vbox)
            self.plot_settings[key] = ps

            # axes['plot_settings'] = ps
            #
            # clim = axes['clim']
            # ps['z'][0].value, ps['z'][1].value = clim
            # # ps['z'][1].value = clim[1]
            # ps['y'][0].value, ps['y'][1].value = a.get_ylim()


            # zlim =
    # accor = widgets.Accordion(childs)
        self.plot_setting_accordion.children = childs
        for e,ch in enumerate(pc):
            self.plot_setting_accordion.set_title(e,ch)

        self.controller.initiation_in_progress = False

    def _date_picker(self):
        layout_width = [40,40,10,10] # percentages of widths of different subwidgets 
        dp = widgets.DatePicker(layout = widgets.Layout(width=f'{layout_width[0]}%'))

        def on_statepicker_change(evt):
            new_value = pd.to_datetime(evt['new'])
            if new_value not in self.controller.valid_dates_selection:
                new_value = self.controller.valid_dates_selection[abs(self.controller.valid_dates_selection - new_value).argmin()]
                self.date_picker.value = pd.to_datetime(new_value)
                self.date_picker_dropdown.value = pd.to_datetime(new_value)
                return
            else:
                if not isinstance(self.controller.view.plot.a, type(None)):
                    self.controller.send_message('on_statepicker_change - else')
                    # self.controller.send_message(new_value)
                    self.controller.view.plot.update_axes()
                    self._notes_update()
                    self._tags_assign_update()

        dp.observe(on_statepicker_change, names= 'value')
        self.date_picker = dp
        # todo: here
        def on_change_dd(evt):
            new = evt['new']
            self.controller.tp_evt = evt
            if len(new) == 1:
                value = evt['owner'].options[new['index']]
                self.controller.send_message('on_change_dd')
                self.date_picker.value = pd.to_datetime(value)

        dd = widgets.Dropdown(options = self.controller.valid_dates_selection, layout = widgets.Layout(width=f'{layout_width[1]}%'))
        dd.observe(on_change_dd, names=['_property_lock'])
        self.date_picker_dropdown = dd
        button_previous = widgets.Button(description='<',
                                         disabled=False,
                                         button_style='',  # 'success', 'info', 'warning', 'danger' or ''
                                         tooltip='previous date',
                                         #                 icon='>'
                                         layout = widgets.Layout(width=f'{layout_width[2]}%'),
                                         )

        button_next = widgets.Button(description='>',
                                     disabled=False,
                                     button_style='',  # 'success', 'info', 'warning', 'danger' or ''
                                     tooltip='next date',
                                     #                 icon='right-arrow'
                                     layout = widgets.Layout(width=f'{layout_width[3]}%'),
                                     )

        def on_next(evt):
            idx = (self.controller.valid_dates_selection == pd.to_datetime(self.date_picker.value.date())).argmax()
            try:
                new_value = self.controller.valid_dates_selection[idx + 1]
            except IndexError:
                _,_,traceback = exc_info()
                self.controller.send_message('last available value (gclib.by_date.py:{})'.format(traceback.tb_lineno))
                return
            self.date_picker.value = pd.to_datetime(new_value)
            self.date_picker_dropdown.value = pd.to_datetime(new_value)
            self.controller.view.plot.update_axes()
            # self.controller.view.controlls._plot_settings_accordion_update()

        def on_previous(evt):
            idx = (self.controller.valid_dates_selection == pd.to_datetime(self.date_picker.value.date())).argmax()
            if idx == 0:
                self.controller.send_message('first available measurement')
                return
            new_value = self.controller.valid_dates_selection[idx - 1]
            self.date_picker.value = pd.to_datetime(new_value)
            self.date_picker_dropdown.value = pd.to_datetime(new_value)
            self.controller.view.plot.update_axes()

        button_next.on_click(on_next)
        button_previous.on_click(on_previous)

        hbox = widgets.HBox([dp, dd, button_previous, button_next])
        return hbox

    def _notes(self):
        def on_change(evt):
            self.controller.database.set_notes(evt['new'])

        l = Layout(flex = '0 1 auto', height = '340px', min_height = '340px', width = 'auto')
        texarea = widgets.Textarea(value='',
                                   placeholder='Type something',
                                   description='Notes:',
                                   disabled=False,
                                   layout = l
                                   )
        texarea.observe(on_change, names = 'value')
        self.notes = texarea
        return texarea

    def _notes_update(self):
        notes = self.controller.database.get_notes()
        self.notes.value = notes

    def initiate(self, index = -1):
        self.controller.initiation_in_progress = True
        datepicker = self._date_picker()
        self.date_picker.value = pd.to_datetime(self.controller.valid_dates_selection[index])

        plot_settings = self._plot_settings()

        notes = self._notes()
        
        self._notes_update()

        accordion = widgets.Accordion(children = (self._tags_constrain(),self._tags_assign(), plot_settings, notes))

        for e,key in enumerate(['select by tags', 'assign tags', 'plot settings', 'notes']):
            accordion.set_title(e, key)
            # accordion.set_title(1, 'plot settings')
            # accordion.set_title(2, 'notes')

        l = Layout(flex='0 1 auto', height='240px', min_height='240px', width='auto')
        self.messages = widgets.Textarea('\n'.join(self.controller._message),
                                         # layout={'width': '100%'},
                                         layout = l
                                         )

        vbox = widgets.VBox([datepicker, accordion, self.messages])
        display(vbox)
        self.controller.initiation_in_progress = False


    def old_initiate(self):

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

        d1_box_h_1 = widgets.HBox([d1_button_prev, d1_button_next])
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
        d2_vbox_childs = []
        ##
        ###
        d2_button_next = widgets.Button(description='next measurement')
        d2_button_prev = widgets.Button(description='prev measurement')


        self.d2_dropdown_fnames = widgets.Dropdown(options=[1],#[i.name for i in self.controller.data.dataset2.path2data_list],
                                              value=1,#self.controller.data.dataset2.path2active.name,
                                            #     description='N',
                                                disabled=False,
                                            )

        d2_button_next.on_click(self.on_d2_botton_next)
        d2_button_prev.on_click(self.on_d2_botton_prev)
        self.d2_dropdown_fnames.observe(self.on_change_d2_dropdown_fnames)

        d2_box_h_1 = widgets.HBox([d2_button_prev, d2_button_next, self.d2_dropdown_fnames])
        ###
        d2_vbox_childs.append(d2_box_h_1)

        ##
        ###
        # text field showing the path
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

        self.accordeon_assigned = widgets.Valid(value=False,
                                                description='bound?',
                                                )

        self.dropdown_popssn= widgets.Dropdown(options=['00', '14', '18'],
                                                    # value='2',
                                                    description='popssn',
                                                    disabled=False,
                                                    )

        self.inttext_deltat = widgets.IntText(value=0,
                                              description='deltat',
                                              disabled=False
                                              )
        self.inttext_deltat.observe(self.on_inttext_deltat)

        self.dropdown_gps_bar_bad = widgets.Dropdown(
            options=['gps', 'baro', 'bad', 'bad_but_usable_gps', 'bad_but_usable_baro'],
            value='gps',
            description='which alt to use:',
            disabled=False,
            )


        self.button_bind_measurements = widgets.ToggleButton(description = 'bind/unbind measurements')
        # button_bind_measurements.on_click(self.deprecated_on_button_bind_measurements)
        self.button_bind_measurements.observe(self.on_button_bind_measurements)



        accordon_box = widgets.VBox([self.accordeon_assigned, self.dropdown_popssn, self.inttext_deltat, self.dropdown_gps_bar_bad, self.button_bind_measurements])
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

    def on_inttext_deltat(self, evt):
        if evt['name'] == "value":
            self.controller.data.delta_t = int(evt['new'])
            dt = int(evt['new']) - int(evt['old'])
            self.controller.data.dataset2.active.data = self.controller.data.dataset2.active.data.shift(periods=-dt,
                                                                                  freq=pd.to_timedelta(1, 's'))
            self.controller.view.plot.update_2(keep_limits = True)


    def old_update_d1(self):
        pass
        # self.d1_text_path.value = self.controller.data.dataset1.path2active.name
        # self.dropdown_popssn.value = self.controller.data.dataset1.path2active.name.split('.')[-2][-2:]
        # self.inttext_deltat.value = self.controller.data.delta_t

    def old_on_d1_botton_next(self, evt):
        self.controller.data.dataset1.next()
        self.update_d1()
        self.update_accordeon()
        self.controller.view.plot.update_1()

    def old_on_d1_botton_prev(self, evt):
        self.controller.data.dataset1.previous()
        self.update_d1()
        self.update_accordeon()
        self.controller.view.plot.update_1()

    def old_update_d2(self):
        pass
        # self.d2_text_path.value = self.controller.data.dataset2.path2active.name
        # self.d2_dropdown_fnames.value = self.controller.data.dataset2.path2active.name
        # self.inttext_deltat.value = self.controller.data.delta_t

    def old_update_accordeon(self):
        pass
        # active = self.controller.database.active_set()
        # self.button_bind_measurements.unobserve(self.on_button_bind_measurements)
        # if active.shape[0] == 1:
        #     self.dropdown_popssn.value = active.popssn[0]
        #     self.inttext_deltat.value = active.delta_t_s[0]
        #     self.accordeon_assigned.value = True
        #     self.button_bind_measurements.value = True
        # elif active.shape[0] == 0:
        #     self.accordeon_assigned.value = False
        #     self.button_bind_measurements.value = False
        #     pass
        # self.button_bind_measurements.observe(self.on_button_bind_measurements)


    def old_on_change_d2_dropdown_fnames(self, change):

        if change['type'] == 'change' and change['name'] == 'value':
            base = self.controller.data.dataset2.path2data
            self.controller.data.dataset2.path2active = base.joinpath(change['new'])
            self.update_accordeon()
            self.d2_text_path.value = self.controller.data.dataset2.path2active.name
            self.controller.view.plot.update_2()


    def old_on_d2_botton_next(self, evt):
        self.controller.data.dataset2.next()
        self.update_d2()
        self.update_accordeon()
        self.controller.view.plot.update_2()

    def old_on_d2_botton_prev(self, evt):
        self.controller.data.dataset2.previous()
        self.update_d2()
        self.update_accordeon()
        self.controller.view.plot.update_2()

    def old_deprecated_on_button_bind_measurements(self, evt):
        self.controller.database.bind_measurements()

    def old_on_button_bind_measurements(self, evt):
        if evt['name'] == 'value':
            if evt['new'] == True:
                self.controller.database.bind_measurements()
            if evt['new'] == False:
                self.controller.database.unbind_measurements()
            self.update_accordeon()

class Database(database.NsaSciDatabase):
    def __init__(self, controller, path2db, db_tb_name_base):
        # super().__init__(path2db)
        self.controller = controller
        self.path2db = path2db
        
        if isinstance(path2db, type(None)):
            self._valid = False
        else:
            self._valid = True
            self.tbl_name_plot_settings ='{}_plot_settings'.format(db_tb_name_base)
            pr = """plot TEXT,
                    lim TEXT CHECK (lim IN ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")),
                    value FLOAT"""
            self.create_table_if_not_excists(self.tbl_name_plot_settings, pr)
    
            self.tbl_name_tags = '{}_tags'.format(db_tb_name_base)
            pr = "tag TEXT"
            self.create_table_if_not_excists(self.tbl_name_tags, pr)
    
            pr = "note TEXT"
            self.tbl_name_notes = '{}_notes'.format(db_tb_name_base)
            self.create_table_if_not_excists(self.tbl_name_notes, pr)


    def create_table_if_not_excists(self,tbl_name, params):
        with sqlite3.connect(self.path2db) as db:
            qu = "select name from sqlite_master where type = 'table'"
            out = db.execute(qu).fetchall()

        if tbl_name not in [o[0] for o in out]:
            qu = """CREATE TABLE {} (
             id integer PRIMARY KEY autoincrement,
             date TEXT,
             {}
            )""".format(tbl_name,params)
            with sqlite3.connect(self.path2db) as db:
                db.execute(qu)
            self.controller.send_message('createded table: {} '.format(tbl_name))

    def get_notes(self):
        if not self._valid:
            return ''
        date = self.controller.view.controlls.date_picker.value
        qu = 'SELECT * FROM {tb_name} WHERE date="{date}";'.format(
            tb_name=self.tbl_name_notes,
            date=date)
        with sqlite3.connect(self.path2db) as db:
            out = pd.read_sql(qu,db)

        if out.shape[0] == 0:
            note = ''
        elif out.shape[0] == 1:
            note = out.note.iloc[0]
        else:
            raise ValueError('not possible')
        return note

    def set_notes(self, value):
        date = self.controller.view.controlls.date_picker.value
        qu = 'SELECT * FROM {tb_name} WHERE date="{date}";'.format(
            tb_name=self.tbl_name_notes,
            date=date)

        with sqlite3.connect(self.path2db) as db:
            out = db.execute(qu).fetchall()

        if len(out) > 1:
            raise ValueError('more then one entry ... not possible')
        elif len(out) == 1:

            qu = """UPDATE {tb_name}
            SET note = "{value}"
            WHERE date="{date}";
            """.format(tb_name=self.tbl_name_notes, value = value, date=date)
            with sqlite3.connect(self.path2db) as db:
                db.execute(qu)

            # self.controller.send_message('note updated')

        elif len(out) == 0:
            qu = """INSERT
            INTO {tb_name} (date, note)
            VALUES("{date}", "{note}");
            """.format(tb_name = self.tbl_name_notes,
                       date = date,
                       note = value)
            with sqlite3.connect(self.path2db) as db:
                db.execute(qu)

            # self.controller.send_message('note added')

# todo: tags
    def set_tag(self, tag, cb_value, tx_value):
        """here value == False means deleting the tag"""
        date = self.controller.view.controlls.date_picker.value
        qu = 'SELECT * FROM {tb_name} WHERE date="{date}" AND tag="{tag}";'.format(tb_name=self.tbl_name_tags,
                                                                                   date=date, tag=tag)
        with sqlite3.connect(self.path2db) as db:
            out = db.execute(qu).fetchall()

        # no entry ... add row
        if len(out) == 0 and cb_value == True:
            qu = """INSERT
            INTO {tb_name} (date, tag, value)
            VALUES ("{date}", "{tag}", "{value}");""".format(tb_name=self.tbl_name_tags,
                                                             date=date,
                                                             tag=tag,
                                                             value = tx_value)
        # entry exists and need to deleted
        elif len(out) == 1 and cb_value == False:
            qu = """DELETE FROM {tb_name}
            WHERE tag="{tag}" AND date="{date}";""".format(tb_name = self.tbl_name_tags, tag = tag, date = date)

        # entry exists ... only value changed
        elif len(out) == 1 and cb_value == True:
            qu = """UPDATE {tb_name}
                    SET value = "{value}"
                    WHERE tag="{tag}" AND date="{date}";""".format(tb_name=self.tbl_name_tags,
                                                                   value=tx_value,
                                                                   tag=tag,
                                                                   date=date)

        else:
            raise ValueError('nonono! this should not be happening')

        with sqlite3.connect(self.path2db) as db:
            self.controller.tp_qu = qu
            db.execute(qu)

    def get_available_tags(self):
        if not self._valid:
            return []
        tbl_name = self.tbl_name_tags
        qu = 'SELECT tag from "{}"'.format(tbl_name)
        with sqlite3.connect(self.path2db) as db:
            out = db.execute(qu).fetchall()

        out = list(np.unique([tag[0] for tag in out]))
        out.sort()
        return out

    def get_tags(self):
        date = self.controller.view.controlls.date_picker.value
        qu = 'SELECT tag,value FROM {tb_name} WHERE date="{date}";'.format(tb_name=self.tbl_name_tags,
                                                                                   date=date)
        with sqlite3.connect(self.path2db) as db:
            # out = pd.read_sql(qu,db)
            out = db.execute(qu).fetchall()
        out = [i for i in out]
        return out

    def get_tag_table(self):
        qu = 'SELECT * from "{}"'.format(self.tbl_name_tags)
        with sqlite3.connect(self.path2db) as db:
            #     out = db.execute(qu).fetchall()
            out = pd.read_sql(qu, db)
        return out

    def set_plot_settings(self,key, param, value):
        date = self.controller.view.controlls.date_picker.value
        qu = 'SELECT * FROM {tb_name} WHERE plot="{key}" AND date="{date}" AND lim="{lim}";'.format(tb_name=self.tbl_name_plot_settings,
                                                                                                    key = key,
                                                                                                    date=date, lim=param)
        with sqlite3.connect(self.path2db) as db:
            out = db.execute(qu).fetchall()
        if len(out) > 1:
            raise ValueError('more then one entry ... not possible')

        elif len(out) == 1:
            qu = """UPDATE {tb_name} 
            SET value = {value}
            WHERE plot="{key}" AND date="{date}" AND lim="{lim}";""".format(tb_name=self.tbl_name_plot_settings,
                                                                            key = key,
                                                           value=value, date=date,
                                                           lim=param)
            with sqlite3.connect(self.path2db) as db:
                db.execute(qu)

            # self.controller.send_message('value updated')

        elif len(out) == 0:
            qu = """INSERT 
            INTO {tb_name} (date, plot, lim, value)
            VALUES("{date}", "{key}", "{lim}", {value});""".format(tb_name=self.tbl_name_plot_settings,
                                                                key = key,
                                                                date=date,
                                                                lim=param,
                                                                value=value)
            with sqlite3.connect(self.path2db) as db:
                db.execute(qu)

            # self.controller.send_message('value inserted')

    # def add_active_set(self):
    #     imet_active_name = self.controller.data.dataset1.path2active.name
    #     pops_active_name = self.controller.data.dataset2.path2active.name
    #
    #     # # test if exists
    #     # qu = 'select * from match_datasets_imet_pops WHERE fn_imet="{}"'.format(imet_active_name)
    #     # imet_exists = pd.read_sql(qu, self.db).shape[0]
    #     # qu = 'select * from match_datasets_imet_pops WHERE fn_pops="{}"'.format(pops_active_name)
    #     # pops_exists = pd.read_sql(qu, self.db).shape[0]
    #     # if imet_exists:
    #     #     self.controller.send_message('ERROR: iMet file was assigned before')
    #     #     return
    #     # elif pops_exists:
    #     #     self.controller.send_message('ERROR: POPS file was assigned before')
    #     #     return
    #     #
    #     # # get next index
    #     # qu = 'select Max(idx) from match_datasets_imet_pops'
    #     # next_idx = pd.read_sql(qu, self.db).iloc[0, 0]
    #     # if not next_idx:
    #     #     next_idx = 1
    #     # else:
    #     #     next_idx = int(next_idx) + 1
    #     #
    #     # #bind
    #     dic = dict(fn_imet=imet_active_name,
    #                fn_pops=pops_active_name,
    #                popssn=self.controller.view.controlls.dropdown_popssn.value,
    #                delta_t_s= self.controller.data.delta_t,
    #                which_alt = self.controller.view.controlls.dropdown_gps_bar_bad.value
    #                )
    #     with sqlite3.connect(self.path2db) as db:
    #         # get next index
    #         # qu = 'select Max(idx) from match_datasets_imet_pops'
    #         # next_idx = pd.read_sql(qu, db).iloc[0, 0]
    #         # if not next_idx:
    #         #     next_idx = 1
    #         # else:
    #         #     next_idx = int(next_idx) + 1
    #         qu = 'select id from match_datasets_imet_pops'
    #         next_idx = pd.read_sql(qu, db)  # .iloc[0, 0]
    #         next_idx = next_idx.astype(int).max().iloc[0]
    #         if not next_idx:
    #             next_idx = 1
    #         elif np.isnan(next_idx):
    #             next_idx = 1
    #         else:
    #             next_idx = int(next_idx) + 1
    #
    #
    #         df = pd.DataFrame(dic, index=[next_idx])
    #         df.index.name = 'id'
    #
    #         # self.add_line2db(df, 'match_datasets_imet_pops')
    #         table_name = 'match_datasets_imet_pops'
    #
    #         df.to_sql(table_name, db,
    #                 #                  if_exists='replace'
    #                 if_exists='append'
    #                 )

    # def update_values(self):
    #     qu = """UPDATE match_datasets_imet_pops
    #             SET
    #             popssn={popssn},
    #             delta_t_s={delta_t_s}
    #             WHERE
    #             fn_imet="{fn_imet}"
    #             AND
    #             fn_pops="{fn_pops}"
    #             """.format(popssn=self.controller.view.controlls.dropdown_popssn.value,
    #                        delta_t_s = self.controller.view.controlls.inttext_deltat.value,
    #                        fn_imet = self.controller.data.dataset1.path2active.name,
    #                        fn_pops = self.controller.data.dataset2.path2active.name)
    #     with sqlite3.connect(self.path2db) as db:
    #         db.execute(qu)

    # def active_set(self):
    #     with sqlite3.connect(self.path2db) as db:
    #         qu = '''select * from match_datasets_imet_pops
    #         where
    #         fn_imet="{}"
    #         and
    #         fn_pops="{}"
    #         '''.format(self.controller.data.dataset1.path2active.name, self.controller.data.dataset2.path2active.name)
    #         out = pd.read_sql(qu, db)
    #         # out = db.execute(qu).fetchall()
    #     return out

    # def bind_measurements(self):
    #     if self.active_set().shape[0] == 0:
    #         self.add_active_set()
    #     elif self.active_set().shape[0] == 1:
    #         self.update_values()
    #
    # def unbind_measurements(self):
    #     with sqlite3.connect(self.path2db) as db:
    #         qu = 'DELETE from {} WHERE id = {}'.format(self.tbl_name, self.active_set().id[0])
    #         db.execute(qu)


class Controller(object):
    def __init__(self,
                 data = None,
                 # path2data = None,
                 path2database = None,
                  database_table_name_base = None,):
        self.initiation_in_progress = False
        self._message = []
        self.data = data #Data_container(self, path2data)
        self.valid_dates_all = self.data.valid_dates
        self.valid_dates_selection = self.valid_dates_all
        self.data.send_message = self.send_message

        self.view = View(self)
        if isinstance(path2database, type(None)) or isinstance(database_table_name_base, type(None)):
            # raise ValueError('currently neither of path2database or database_table_nme_base can be None')
            # self.database = None
            pass
        # else:
        self.database = Database(self, path2database, database_table_name_base)


    def send_message(self, txt):
        # self._message +=self._message + '\n' + txt
        self._message.append(txt)
        if len(self._message) > 10:
            self._message = self._message[-20:]
        try:
            mt = list(reversed(self._message))
            self.view.controlls.messages.value = '\n +++++++++++++++\n'.join(mt)
        except AttributeError:
            pass

    def selection_from_tags(self):
        tag_state = self.view.controlls._tags_constrain_get_state()
        if tag_state[0] == '':
            self.valid_dates_selection = self.valid_dates_all
            return
        tags = self.database.get_available_tags()
        tag_table = self.database.get_tag_table()
        df = pd.DataFrame(columns=tags, index=self.valid_dates_all, dtype=bool)
        df[:] = False
        # df

        for e, row in tag_table.iterrows():
            df.loc[row.date, row.tag] = True

        where = df[tag_state[0]]
        for tag in tag_state[1:]:
            if tag[0] == 'and':
                where = where & df[tag[1]]

        self.valid_dates_selection = df[where].index
        return self.valid_dates_selection