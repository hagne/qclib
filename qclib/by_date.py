from atmPy.aerosols.instruments import POPS
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



def read_POPS(path):
    hk = POPS.read_housekeeping(path, pattern = 'hk', skip_histogram= True)
    hk.get_altitude()
    return hk

def read_iMet(path):
    ds = xr.open_dataset(path)
    # return ds
    alt_gps = ds['GPS altitude [km]'].to_pandas()
    alt_bar = ds['altitude (from iMet PTU) [km]'].to_pandas()

    df = pd.DataFrame({'alt_gps': alt_gps,
              'alt_bar': alt_bar})
    return df


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

        self.plot = Plot(self)
        self.controlls = Controlls(self)

# View
class Plot(object):
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
        self.controller.initiation_in_progress = False
        return self.a

    def update_axes(self):
        date = pd.to_datetime(self.controller.view.controlls.date_picker.value)
        self.controller.data.plot(date, ax = self.a)
        self.update_lims_from_db()

    def update_lims_from_db(self):
        tbl_name = self.controller.database.tbl_name_plot_settings #  'vis_nsascience_quicklooks_plot_settings'
        date = self.controller.view.controlls.date_picker.value
        for k in self.plot_content:
            # print(k)
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
                lc.set_clim(vmin, vmax)
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


class Controlls(object):
    def __init__(self, view):
        self.view = view
        self.controller = view.controller

    def _tags(self):
        tags = {'conditions': {'options': ['cloudi', 'clear', 'precip_snow', 'precip_rain']}}
        def on_add_tag(evt, box, options, new_tag, all_checkboxes):
            if new_tag.value in options:
                return
            elif new_tag.value.strip() == '':
                return
            else:
                options.append(new_tag.value)
                newcb = widgets.Checkbox(description=new_tag.value)
                all_checkboxes.append(newcb)
                box.children = box.children + (newcb,)
                return

        radio_button_list = []
        all_checkboxes = []
        for tag_type in tags.keys():
            #     rb = widgets.RadioButtons(options = tags[tag_type]['options'])
            cbs = []
            for opt in tags[tag_type]['options']:
                cb = widgets.Checkbox(description=opt)
                cbs.append(cb)
                all_checkboxes.append(cb)
            cb_box = widgets.VBox(cbs)
            # new tag
            new_tag = widgets.Text(placeholder='Type something')
            add_button = widgets.Button(description='add tag')
            add_button.on_click(lambda x: on_add_tag(x, cb_box, tags[tag_type]['options'], new_tag, all_checkboxes))
            add_box = widgets.HBox([add_button, new_tag])

            # box it
            box = widgets.HBox([cb_box, add_box])

            radio_button_list.append(box)

        acc = widgets.Accordion(radio_button_list)
        for e, tag_type in enumerate(tags.keys()):
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

        xlim_min = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=0.1,
            description='x_min',
            disabled=False
        )

        xlim_max = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=0.1,
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
            step=0.1,
            description='y_min',
            disabled=False
        )
        ylim_max = widgets.FloatText(
            value=7.5,
            # min=vmin,
            # max=vmax,
            step=0.1,
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
            step=0.1,
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
            step=0.1,
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
        dp = widgets.DatePicker()

        def on_statepicker_change(evt):
            print('picker')
            new_value = pd.to_datetime(evt['new'])
            if new_value not in self.controller.data.valid_dates:
                print('find closest')
                new_value = self.controller.data.valid_dates[abs(self.controller.data.valid_dates - new_value).argmin()]
                self.date_picker.value = pd.to_datetime(new_value)
                return
            else:
                if not isinstance(self.controller.view.plot.a, type(None)):
                    self.controller.view.plot.update_axes()

        dp.observe(on_statepicker_change, names= 'value')


        self.date_picker = dp
        button_previous = widgets.Button(description='<',
                                         disabled=False,
                                         button_style='',  # 'success', 'info', 'warning', 'danger' or ''
                                         tooltip='previous date',
                                         #                 icon='>'
                                         )

        button_next = widgets.Button(description='>',
                                     disabled=False,
                                     button_style='',  # 'success', 'info', 'warning', 'danger' or ''
                                     tooltip='next date',
                                     #                 icon='right-arrow'
                                     )

        def on_next(evt):
            idx = (self.controller.data.valid_dates == pd.to_datetime(self.date_picker.value.date())).argmax()
            new_value = self.controller.data.valid_dates[idx + 1]
            self.date_picker.value = pd.to_datetime(new_value)
            # self.controller.view.plot.update_axes()
            # self.controller.view.controlls._plot_settings_accordion_update()

        def on_previous(evt):
            idx = (self.controller.data.valid_dates == pd.to_datetime(self.date_picker.value.date())).argmax()
            if idx == 0:
                self.controller.send_message('first available measurement')
                return
            new_value = self.controller.data.valid_dates[idx - 1]
            self.date_picker.value = pd.to_datetime(new_value)
            # self.controller.view.plot.update_axes()

        button_next.on_click(on_next)
        button_previous.on_click(on_previous)

        hbox = widgets.HBox([dp, button_previous, button_next])
        return hbox

    def initiate(self):
        self.controller.initiation_in_progress = True
        datepicker = self._date_picker()
        self.date_picker.value = pd.to_datetime(self.controller.data.valid_dates[0])

        plot_settings = self._plot_settings()

        accordion = widgets.Accordion(children = (self._tags(),plot_settings,))
        accordion.set_title(0, 'assign tags')
        accordion.set_title(1, 'plot settings')

        self.messages = widgets.Textarea('\n'.join(self.controller._message), layout={'width': '100%'})

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
        self.path2db = path2db
        self.controller = controller
        self.tbl_name_plot_settings ='{}_plot_settings'.format(db_tb_name_base)
        pr = """plot TEXT,
                lim TEXT CHECK (lim IN ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")),
                value FLOAT"""
        self.create_table_if_not_excists(self.tbl_name_plot_settings, pr)
        self.tbl_name_tags = '{}_tags'.format(db_tb_name_base)
        pr = "tag TEXT"
        self.create_table_if_not_excists(self.tbl_name_tags, pr)

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

            self.controller.send_message('value updated')

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

            self.controller.send_message('value inserted')

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
        self.data.send_message = self.send_message

        self.view = View(self)
        if isinstance(path2database, type(None)) or isinstance(database_table_name_base, type(None)):
            raise ValueError('currently neither of path2database or database_table_nme_base can be None')
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