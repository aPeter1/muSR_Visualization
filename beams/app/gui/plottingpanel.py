import threading
import warnings
import logging

from PyQt5 import QtGui, QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np

from app.gui.dialogs.dialog_misc import WarningMessageDialog
from app.gui.dialogs.dialog_plot_file import PlotFileDialog
from app.gui.gui import Panel, PanelPresenter
from app.model import files, domain, services
from app.util import qt_widgets, qt_constants


class PlottingPanel(Panel, QtWidgets.QWidget):
    class SupportPanel(QtWidgets.QDockWidget):
        class PlotStyleBox(qt_widgets.CollapsibleBox):
            def __init__(self) -> None:
                self.title = 'Plot Style'
                super().__init__(self.title)

                self.all_color_options = QtWidgets.QComboBox()
                self.linestyle_options = QtWidgets.QComboBox()
                self.fit_linestyle_options = QtWidgets.QComboBox()
                self.line_color_options = QtWidgets.QComboBox()
                self.fit_color_options = QtWidgets.QComboBox()
                self.line_width_options = QtWidgets.QComboBox()
                self.marker_options = QtWidgets.QComboBox()
                self.marker_color_options = QtWidgets.QComboBox()
                self.marker_size_options = QtWidgets.QComboBox()
                self.fillstyle_options = QtWidgets.QComboBox()
                self.errorbar_style_options = QtWidgets.QComboBox()
                self.errorbar_color_options = QtWidgets.QComboBox()
                self.errorbar_width_options = QtWidgets.QComboBox()

                self.all_color_options.addItems(services.StyleService.color_options_values.keys())
                self.fit_color_options.addItems(services.StyleService.color_options_extra_values.keys())
                self.linestyle_options.addItems(services.StyleService.linestyle_options_values.keys())
                self.fit_linestyle_options.addItems(services.StyleService.linestyle_options_values.keys())
                self.line_color_options.addItems(services.StyleService.color_options_extra_values.keys())
                self.line_width_options.addItems(services.StyleService.line_width_options_values.keys())
                self.marker_options.addItems(services.StyleService.marker_options_values.keys())
                self.marker_color_options.addItems(services.StyleService.color_options_extra_values.keys())
                self.marker_size_options.addItems(services.StyleService.marker_size_options_values.keys())
                self.fillstyle_options.addItems(services.StyleService.fillstyle_options_values.keys())
                self.errorbar_style_options.addItems(services.StyleService.errorbar_styles_values.keys())
                self.errorbar_color_options.addItems(services.StyleService.color_options_extra_values.keys())
                self.errorbar_width_options.addItems(services.StyleService.errorbar_width_values.keys())

                layout = QtWidgets.QGridLayout()
                layout.addWidget(QtWidgets.QLabel("Default Color"), 0, 0)
                layout.addWidget(self.all_color_options, 0, 1)
                layout.addWidget(QtWidgets.QLabel("Linestyle"), 1, 0)
                layout.addWidget(self.linestyle_options, 1, 1)
                layout.addWidget(QtWidgets.QLabel("Line Width"), 3, 0)
                layout.addWidget(self.line_width_options, 3, 1)
                layout.addWidget(QtWidgets.QLabel("Marker Style"), 4, 0)
                layout.addWidget(self.marker_options, 4, 1)
                layout.addWidget(QtWidgets.QLabel("Marker Color"), 5, 0)
                layout.addWidget(self.marker_color_options, 5, 1)
                layout.addWidget(QtWidgets.QLabel("Marker Size"), 6, 0)
                layout.addWidget(self.marker_size_options, 6, 1)
                layout.addWidget(QtWidgets.QLabel("Fillstyle"), 7, 0)
                layout.addWidget(self.fillstyle_options, 7, 1)
                layout.addWidget(QtWidgets.QLabel("Errorbar Style"), 8, 0)
                layout.addWidget(self.errorbar_style_options, 8, 1)
                layout.addWidget(QtWidgets.QLabel("Errorbar Color"), 9, 0)
                layout.addWidget(self.errorbar_color_options, 9, 1)
                layout.addWidget(QtWidgets.QLabel("Errorbar Width"), 10, 0)
                layout.addWidget(self.errorbar_width_options, 10, 1)
                layout.addWidget(QtWidgets.QLabel("Fit Line Color"), 11, 0)
                layout.addWidget(self.fit_color_options, 11, 1)
                layout.addWidget(QtWidgets.QLabel("Fit Linestyle"), 12, 0)
                layout.addWidget(self.fit_linestyle_options, 12, 1)

                box_layout = QtWidgets.QHBoxLayout()
                box_layout.addLayout(layout)
                self.setContentLayout(box_layout)

        class AsymmetryParametersBox(qt_widgets.CollapsibleBox):
            def __init__(self) -> None:
                self.title = 'Asymmetry Parameters'
                super().__init__(self.title)

                self.alpha_input = QtWidgets.QLineEdit()

                layout = QtWidgets.QGridLayout()
                layout.addWidget(QtWidgets.QLabel("Alpha"), 0, 0)
                layout.addWidget(self.alpha_input, 0, 1)
                self.setContentLayout(layout)

        class LegendBox(qt_widgets.CollapsibleBox):
            def __init__(self) -> None:
                self.title = 'Legend'
                super().__init__(self.title)

                self.legend_list = QtWidgets.QListWidget()
                self.__values = {}

                box_layout = QtWidgets.QHBoxLayout()
                box_layout.addWidget(self.legend_list)
                self.setContentLayout(box_layout)

            def set_legend(self, values: dict):
                if self.__values == values:
                    return

                self.__values = values
                self.legend_list.clear()

                for run_id, (label, color) in values.items():
                    qlabel = QtWidgets.QLineEdit()
                    qlabel.setText(label)

                    pixmap = QtGui.QPixmap(100, 100)
                    pixmap.fill(QtGui.QColor(color))
                    qicon = QtGui.QIcon(pixmap)
                    qcolor = QtWidgets.QToolButton()
                    qcolor.setIcon(qicon)

                    file_item = qt_widgets.IdentifiableListWidgetItem(run_id, label, self.legend_list)
                    file_item.setIcon(qicon)

                    # TODO Since we have to set the color as a toolbutton anyways, it would be pretty cool if the user could press it and have
                    #   a color picker pop up to change the color for that particular run.

                    # TODO We need to make it so we can edit the title, this will involve changing the logic quite a bit though in a few places.
                    #   maybe we can go back to our old idea of attaching references to model objects to things like this... OR we just keep a dict
                    #   in this class that references the actual titles to the ones the user has selected. It would have to be persistent for when
                    #   they clear and plot again. I don't imagine we would want to save these values. OR we could have them choose what they want in
                    #   the legend (like select temp or field or material or title). I like that idea, maybe put the options up at the top of the
                    #   collapsible box.

                    # file_item.setFlags(file_item.flags() | QtCore.Qt.ItemIsEditable)

            def set_blank(self):
                self.__values = {}
                self.legend_list.clear()

        class Tree(QtWidgets.QTreeWidget):
            def __init__(self):
                super().__init__()
                self.__manager = PlottingPanel.SupportPanel.TreeManager(self)
                self.setHeaderHidden(True)
                self.setContextMenuPolicy(qt_constants.CustomContextMenu)
                self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
                self.setHorizontalScrollBarPolicy(qt_constants.ScrollBarAsNeeded)
                self.header().setMinimumSectionSize(600)
                self.header().setDefaultSectionSize(900)
                self.header().setStretchLastSection(False)
                self._set_callbacks()

            def _set_callbacks(self):
                self.customContextMenuRequested.connect(self._launch_menu)

            def _launch_menu(self, point):
                index = self.indexAt(point)

                if not index.isValid():
                    return

                item = self.itemAt(point)
                menu = item.menu(self.selectedItems())
                menu.exec_(self.mapToGlobal(point))

            def set_tree(self, tree):
                self.clear()
                self.addTopLevelItems(tree)

            def get_run_ids(self):
                # noinspection PyTypeChecker
                iterator = QtWidgets.QTreeWidgetItemIterator(self, QtWidgets.QTreeWidgetItemIterator.Checked)

                ids = []
                while iterator.value():
                    if isinstance(iterator.value().model, domain.RunDataset):
                        ids.append(iterator.value().model.id)

                    iterator += 1

                return ids

            def get_checked(self):
                # noinspection PyTypeChecker
                iterator = QtWidgets.QTreeWidgetItemIterator(self, QtWidgets.QTreeWidgetItemIterator.Checked)

                ids = []
                while iterator.value():
                    if isinstance(iterator.value().model, domain.RunDataset):
                        ids.append(iterator.value().model.id)

                    iterator += 1

                return ids

            def get_selected(self):
                # noinspection PyTypeChecker
                iterator = QtWidgets.QTreeWidgetItemIterator(self, QtWidgets.QTreeWidgetItemIterator.Selected)

                ids = []
                while iterator.value():
                    if isinstance(iterator.value().model, domain.RunDataset):
                        ids.append(iterator.value().model.id)

                    iterator += 1

                return ids

            def get_selected_names(self):
                # noinspection PyTypeChecker
                iterator = QtWidgets.QTreeWidgetItemIterator(self, QtWidgets.QTreeWidgetItemIterator.Checked)

                ids = []
                while iterator.value():
                    if isinstance(iterator.value().model, domain.RunDataset):
                        ids.append(iterator.value().model.meta[files.TITLE_KEY])

                    iterator += 1

                return ids

            def get_names(self):
                # noinspection PyTypeChecker
                iterator = QtWidgets.QTreeWidgetItemIterator(self)

                ids = []
                while iterator.value():
                    if isinstance(iterator.value().model, domain.RunDataset):
                        ids.append(iterator.value().model.meta[files.TITLE_KEY])

                    iterator += 1

                return ids

            def set_all_checked(self, checked):
                for i in range(self.topLevelItemCount()):
                    self.topLevelItem(i).setCheckState(0, checked)

            def set_checked_by_ids(self, ids):
                # noinspection PyTypeChecker
                for i in range(self.topLevelItemCount()):
                    if self.topLevelItem(i).model.id in ids:
                        self.topLevelItem(i).setCheckState(0, qt_constants.Checked)

        class TreeManager(PanelPresenter):
            def __init__(self, view):
                super().__init__(view)
                self.__view = view
                self.__logger = logging.getLogger("PlottingPanelTreeManager")
                self.__run_service = services.RunService()
                self.__fit_service = services.FitService()
                self.__file_service = services.FileService()
                self.__run_service.signals.added.connect(self.update)
                self.__run_service.signals.loaded.connect(self.update)
                self.__run_service.signals.changed.connect(self.update)

            def _create_tree_model(self, run_datasets):
                run_nodes = []
                for dataset in run_datasets:
                    run_nodes.append(PlottingPanel.SupportPanel.RunNode(dataset))
                return run_nodes

            @QtCore.pyqtSlot()
            def update(self):
                self.__logger.debug("Accepted Signal")
                ids = self.__view.get_run_ids()
                run_datasets = self.__run_service.get_loaded_runs()
                tree = self._create_tree_model(run_datasets)
                self.__view.set_tree(tree)
                self.__view.set_checked_by_ids(ids)

        class RunNode(QtWidgets.QTreeWidgetItem):
            def __init__(self, run_data):
                super(PlottingPanel.SupportPanel.RunNode, self).__init__([run_data.meta[files.TITLE_KEY]])
                self.model = run_data
                self.__selected_items = None
                self.setFlags(self.flags()
                              | qt_constants.ItemIsUserCheckable)
                self.setCheckState(0, qt_constants.Unchecked)

            def menu(self, items):
                self.__selected_items = items
                menu = QtWidgets.QMenu()
                menu.addAction("Plot", self._action_plot)
                menu.addAction("Save", self._action_save)
                return menu

            def _action_save(self):
                pass

            def _action_plot(self):
                pass

        def __init__(self):
            super().__init__()
            self.setTitleBarWidget(QtWidgets.QWidget())
            self.setWindowTitle("Plotting")

            self.plot_button = qt_widgets.StyleOneButton("Plot")
            self.plot_all_button = qt_widgets.StyleOneButton("Plot All")
            self.clear_all_button = qt_widgets.StyleTwoButton("Clear All")

            self.item_tree = self.Tree()
            self.legend_box = self.LegendBox()
            self.plot_style_box = self.PlotStyleBox()
            self.asymmetry_param_box = self.AsymmetryParametersBox()

            self._set_widget_dimensions()
            self._set_widget_attributes()
            self._set_widget_layout()

        def _set_widget_dimensions(self):
            pass

        def _set_widget_attributes(self):
            self.legend_box.toggle_button.pressed.connect(lambda: self._toggle_boxes(self.legend_box.title))
            self.plot_style_box.toggle_button.pressed.connect(lambda: self._toggle_boxes(self.plot_style_box.title))
            self.asymmetry_param_box.toggle_button.pressed.connect(
                lambda: self._toggle_boxes(self.asymmetry_param_box.title))

            self.legend_box.on_pressed()

        def _set_widget_layout(self):
            hbox = QtWidgets.QHBoxLayout()
            hbox.addWidget(self.plot_button)
            hbox.addWidget(self.plot_all_button)
            hbox.addWidget(self.clear_all_button)

            vbox = QtWidgets.QVBoxLayout()
            vbox.addLayout(hbox)
            vbox.addWidget(self.item_tree)
            vbox.addWidget(self.legend_box)
            vbox.addWidget(self.plot_style_box)
            vbox.addWidget(self.asymmetry_param_box)
            vbox.addStretch()

            temp = QtWidgets.QWidget()
            temp.setLayout(vbox)
            self.setWidget(temp)

        def _toggle_boxes(self, box_id):
            if box_id != self.legend_box.title and self.legend_box.is_open():
                self.legend_box.on_pressed()
            elif box_id != self.plot_style_box.title and self.plot_style_box.is_open():
                self.plot_style_box.on_pressed()
            elif box_id != self.asymmetry_param_box.title and self.asymmetry_param_box.is_open():
                self.asymmetry_param_box.on_pressed()

            if box_id == self.legend_box.title:
                self.legend_box.on_pressed()
            elif box_id == self.plot_style_box.title:
                self.plot_style_box.on_pressed()
            elif box_id == self.asymmetry_param_box.title:
                self.asymmetry_param_box.on_pressed()

        def set_first_selected(self):
            if self.item_tree.topLevelItemCount() > 0:
                self.item_tree.setCurrentItem(self.item_tree.topLevelItem(0))

        def _check_add_star(self, box, remove=False):
            for i in range(box.count()):
                if box.itemText(i) == "*":
                    if remove:
                        box.removeItem(i)
                    return
            else:
                if not remove:
                    box.addItem("*")

        def set_alpha(self, alpha):
            self.asymmetry_param_box.alpha_input.setText(alpha)

        def set_default_color(self, color):
            if color == "*":
                self._check_add_star(self.plot_style_box.all_color_options, False)
            else:
                self._check_add_star(self.plot_style_box.all_color_options, True)

            self.plot_style_box.all_color_options.setCurrentText(color)

        def set_linestyle(self, linestyle):
            if linestyle == "*":
                self._check_add_star(self.plot_style_box.linestyle_options, False)
            else:
                self._check_add_star(self.plot_style_box.linestyle_options, True)

            self.plot_style_box.linestyle_options.setCurrentText(linestyle)

        def set_line_color(self, line_color):
            if line_color == "*":
                self._check_add_star(self.plot_style_box.line_color_options, False)
            else:
                self._check_add_star(self.plot_style_box.line_color_options, True)

            self.plot_style_box.line_color_options.setCurrentText(line_color)

        def set_line_width(self, line_width):
            if line_width == "*":
                self._check_add_star(self.plot_style_box.line_width_options, False)
            else:
                self._check_add_star(self.plot_style_box.line_width_options, True)

            self.plot_style_box.line_width_options.setCurrentText(line_width)

        def set_marker(self, marker):
            if marker == "*":
                self._check_add_star(self.plot_style_box.marker_options, False)
            else:
                self._check_add_star(self.plot_style_box.marker_options, True)

            self.plot_style_box.marker_options.setCurrentText(marker)

        def set_marker_color(self, color):
            if color == "*":
                self._check_add_star(self.plot_style_box.marker_color_options, False)
            else:
                self._check_add_star(self.plot_style_box.marker_color_options, True)

            self.plot_style_box.marker_color_options.setCurrentText(color)

        def set_fit_color(self, color):
            if color == "*":
                self._check_add_star(self.plot_style_box.fit_color_options, False)
            else:
                self._check_add_star(self.plot_style_box.fit_color_options, True)

            self.plot_style_box.fit_color_options.setCurrentText(color)

        def set_marker_size(self, size):
            if size == "*":
                self._check_add_star(self.plot_style_box.marker_size_options, False)
            else:
                self._check_add_star(self.plot_style_box.marker_size_options, True)

            self.plot_style_box.marker_size_options.setCurrentText(size)

        def set_fillstyle(self, fillstyle):
            if fillstyle == "*":
                self._check_add_star(self.plot_style_box.fillstyle_options, False)
            else:
                self._check_add_star(self.plot_style_box.fillstyle_options, True)

            self.plot_style_box.fillstyle_options.setCurrentText(fillstyle)

        def set_errorbar_style(self, style):
            if style == "*":
                self._check_add_star(self.plot_style_box.errorbar_style_options, False)
            else:
                self._check_add_star(self.plot_style_box.errorbar_style_options, True)

            self.plot_style_box.errorbar_style_options.setCurrentText(style)

        def set_errorbar_color(self, color):
            if color == "*":
                self._check_add_star(self.plot_style_box.errorbar_color_options, False)
            else:
                self._check_add_star(self.plot_style_box.errorbar_color_options, True)

            self.plot_style_box.errorbar_color_options.setCurrentText(color)

        def set_errorbar_width(self, width):
            if width == "*":
                self._check_add_star(self.plot_style_box.errorbar_width_options, False)
            else:
                self._check_add_star(self.plot_style_box.errorbar_width_options, True)

            self.plot_style_box.errorbar_width_options.setCurrentText(width)

    class PlotToolbar(NavigationToolbar2QT):
        def _init_toolbar(self):
            # fixme, if there are no errors then this is fine
            pass

        NavigationToolbar2QT.toolitems = (
            ('Home', 'Reset original view', 'home', 'home'),
            ('Back', 'Back to previous view', 'back', 'back'),
            ('Forward', 'Forward to next view', 'forward', 'forward'),
            # (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
            # ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
            # (None, None, None, None),
            ('Save', 'Save the figure', 'filesave', 'save_figure'),
        )

    class PlotDisplay(FigureCanvas):
        def __init__(self, settings):
            self._draw_pending = True
            self._is_drawing = True
            self._settings = settings

            FigureCanvas.__init__(self, Figure())
            axes = self.figure.subplots(2, 1, gridspec_kw={'height_ratios': [2, 1]})
            self.figure.set_facecolor("#ffffff")
            self.axes_time = axes[0]
            self.axes_freq = axes[1]

            self.set_blank()

        def set_blank(self):
            title_font_size = 12
            self.axes_time.spines['right'].set_visible(False)
            self.axes_time.spines['top'].set_visible(False)
            self.axes_time.spines['left'].set_visible(False)
            self.axes_time.spines['bottom'].set_visible(False)
            self.axes_time.set_xlabel("Load '.msr', '.dat' or '.asy' files and press 'Plot' to see data.",
                                      fontsize=title_font_size)
            self.axes_time.xaxis.label.set_color("#c0c0c0")
            self.axes_time.tick_params(axis='x', colors='white')
            self.axes_time.tick_params(axis='y', colors='white')
            self.axes_time.set_facecolor("#ffffff")

            self.axes_freq.spines['right'].set_visible(False)
            self.axes_freq.spines['top'].set_visible(False)
            self.axes_freq.spines['left'].set_visible(False)
            self.axes_freq.spines['bottom'].set_visible(False)
            self.axes_freq.tick_params(axis='x', colors='white')
            self.axes_freq.tick_params(axis='y', colors='white')
            self.axes_freq.set_facecolor("#ffffff")

        def set_style(self, remove_legend):
            self.axes_time.tick_params(axis='x', colors='black')
            self.axes_time.tick_params(axis='y', colors='black')
            self.axes_freq.tick_params(axis='x', colors='black')
            self.axes_freq.tick_params(axis='y', colors='black')

            title_font_size = 12
            self.axes_time.spines['right'].set_visible(False)
            self.axes_time.spines['top'].set_visible(False)
            self.axes_time.spines['left'].set_visible(True)
            self.axes_time.spines['bottom'].set_visible(True)
            self.axes_time.set_xlabel("Time (" + chr(956) + "s)", fontsize=title_font_size)
            self.axes_time.set_ylabel("Asymmetry", fontsize=title_font_size)
            self.axes_time.xaxis.label.set_color("#000000")
            self.axes_time.set_facecolor("#ffffff")

            self.axes_freq.spines['right'].set_visible(False)
            self.axes_freq.spines['top'].set_visible(False)
            self.axes_freq.spines['left'].set_visible(True)
            self.axes_freq.spines['bottom'].set_visible(True)
            self.axes_freq.set_xlabel(r'Frequency (MHz)', fontsize=title_font_size)
            self.axes_freq.set_ylabel(r'FFT$^2$', fontsize=title_font_size)
            self.axes_freq.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
            self.axes_freq.set_facecolor("#ffffff")

            self.figure.tight_layout()

        def plot_asymmetry(self, time, asymmetry, uncertainty, fit, color, marker_color, line_color, errorbar_color,
                           fit_color, linestyle, marker, errorbar_style, fillstyle, line_width, marker_size,
                           errorbar_width,
                           fit_linestyle):
            marker_color = color if marker_color == 'Default' else marker_color
            line_color = color if line_color == 'Default' else line_color
            errorbar_color = color if errorbar_color == 'Default' else errorbar_color
            marker_face_color = marker_color if fillstyle != 'none' else 'none'
            fit_color = color if fit_color == 'Default' else fit_color

            if uncertainty is not None and errorbar_style != 'none':
                self.axes_time.errorbar(time, asymmetry, uncertainty, mfc=marker_face_color, mec=marker_color,
                                        color=color, linestyle=linestyle, marker=marker, fillstyle=fillstyle,
                                        linewidth=line_width, markersize=marker_size,
                                        elinewidth=errorbar_width,
                                        ecolor=errorbar_color, capsize=errorbar_style)

            else:
                self.axes_time.plot(time, asymmetry, mfc=marker_face_color, mec=marker_color, color=color,
                                    linestyle=linestyle, marker=marker, fillstyle=fillstyle,
                                    linewidth=line_width,
                                    markersize=marker_size)

            if fit is not None:
                self.axes_time.plot(time, fit, color=fit_color, linestyle=fit_linestyle,
                                    marker='None')

        def plot_fft(self, frequencies, fft, color, label):
            self.axes_freq.plot(frequencies, fft, color=color, label=label)

        def set_asymmetry_plot_limits(self, max_asymmetry, min_asymmetry):
            if not self._settings.is_asymmetry_auto():
                try:
                    y_min = self._settings.get_min_asymmetry()
                    y_max = self._settings.get_max_asymmetry()
                except ValueError:
                    WarningMessageDialog.launch(["Invalid asymmetry limits."])
                    return
                self.axes_time.set_ylim(y_min, y_max)
            else:
                y_min = min_asymmetry - abs(min_asymmetry * 0.1)
                y_max = max_asymmetry + abs(max_asymmetry * 0.1)
                self.axes_time.set_ylim(y_min, y_max)
                self._settings.set_min_asymmetry(y_min)
                self._settings.set_max_asymmetry(y_max)

            try:
                x_min = self._settings.get_min_time()
                x_max = self._settings.get_max_time()
            except ValueError:
                WarningMessageDialog.launch(["Invalid asymmetry limits."])
                return
            self.axes_time.set_xlim(x_min, x_max)

        def set_fft_plot_limits(self, max_fft):
            if not self._settings.is_fft_auto():
                try:
                    y_min = self._settings.get_min_fft()
                    y_max = self._settings.get_max_fft()
                except ValueError:
                    WarningMessageDialog.launch(["Invalid frequency limits."])
                    return
                self.axes_freq.set_ylim(y_min, y_max)
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.axes_freq.set_ylim(0, max_fft * 1.1)
                self._settings.set_min_fft(0)
                self._settings.set_max_fft(max_fft * 1.1)

            if not self._settings.is_freq_auto():
                try:
                    x_min = self._settings.get_min_freq()
                    x_max = self._settings.get_max_freq()
                except ValueError:
                    WarningMessageDialog.launch(["Invalid frequency limits."])
                    return
                self.axes_freq.set_xlim(x_min, x_max)
            else:
                x_min, x_max = self.axes_freq.get_xlim()
                self._settings.set_min_freq(x_min)
                self._settings.set_max_freq(x_max)

        def finish_plotting(self, remove_legend=False):
            self.set_style(remove_legend)
            self.axes_time.figure.canvas.draw()

        def start_plotting(self):
            self.axes_time.clear()
            self.axes_freq.clear()

        def set_full_blank(self):
            self.setEnabled(False)
            self.set_blank()
            self.axes_time.figure.canvas.draw()

    class PlotControl(QtWidgets.QWidget):
        def __init__(self):
            QtWidgets.QWidget.__init__(self)
            # self.setTitleBarWidget(QtWidgets.QWidget())

            self._label_slider_bin = QtWidgets.QLabel('')
            self._label_input_bin = QtWidgets.QLabel('Time Bins (ns)')

            self.slider_bin = QtWidgets.QSlider(qt_constants.Horizontal)
            self.input_bin = QtWidgets.QLineEdit()

            self._label_time = QtWidgets.QLabel('Time')
            self._label_time_xmin = QtWidgets.QLabel('XMin')
            self._label_time_xmax = QtWidgets.QLabel('XMax')
            self._label_time_ymin = QtWidgets.QLabel('YMin')
            self._label_time_ymax = QtWidgets.QLabel('YMax')
            self._label_time_yauto = QtWidgets.QLabel('Auto Y')

            self.input_time_xmin = QtWidgets.QLineEdit()
            self.input_time_xmax = QtWidgets.QLineEdit()

            self.input_time_ymin = QtWidgets.QLineEdit()
            self.input_time_ymax = QtWidgets.QLineEdit()
            self.check_time_yauto = QtWidgets.QCheckBox()

            self._label_freq = QtWidgets.QLabel('Frequency')
            self._label_freq_xmin = QtWidgets.QLabel('XMin')
            self._label_freq_xmax = QtWidgets.QLabel('XMax')
            self._label_freq_ymin = QtWidgets.QLabel('YMin')
            self._label_freq_ymax = QtWidgets.QLabel('YMax')
            self._label_freq_yauto = QtWidgets.QLabel('Auto Y')
            self._label_freq_xauto = QtWidgets.QLabel('Auto X')

            self.input_freq_xmin = QtWidgets.QLineEdit()
            self.input_freq_xmax = QtWidgets.QLineEdit()
            self.input_freq_ymin = QtWidgets.QLineEdit()
            self.input_freq_ymax = QtWidgets.QLineEdit()
            self.check_freq_yauto = QtWidgets.QCheckBox()
            self.check_freq_xauto = QtWidgets.QCheckBox()

            self._set_widget_attributes()
            self._set_widget_tooltips()
            self._set_widget_dimensions()
            self._set_widget_layout()

            # self.setWidget(self._full_widget)

        def _set_widget_attributes(self):
            self.check_freq_xauto.setChecked(True)
            self.check_freq_yauto.setChecked(True)
            self.check_time_yauto.setChecked(True)

            self.input_time_xmin.setText("0")
            self.input_time_xmax.setText("8")
            self.input_time_ymin.setText("-0.3")
            self.input_time_ymax.setText("-0.5")

            self.input_time_ymin.setEnabled(False)
            self.input_time_ymax.setEnabled(False)

            self.input_freq_xmin.setEnabled(False)
            self.input_freq_xmax.setEnabled(False)

            self.input_freq_ymin.setEnabled(False)
            self.input_freq_ymax.setEnabled(False)

            self.slider_bin.setMinimum(0)
            self.slider_bin.setMaximum(500)
            self.slider_bin.setValue(150)
            self.slider_bin.setTickPosition(QtWidgets.QSlider.TicksBothSides)
            self.slider_bin.setTickInterval(20)

            self.input_bin.setText(str(self.slider_bin.value()))

        def _set_widget_tooltips(self):
            pass

        def _set_widget_dimensions(self):
            box_size = 40
            self.input_time_xmin.setMinimumWidth(box_size)
            self.input_time_xmax.setMinimumWidth(box_size)
            self.input_time_ymin.setMinimumWidth(box_size)
            self.input_time_ymax.setMinimumWidth(box_size)
            self.input_freq_xmin.setMinimumWidth(box_size)
            self.input_freq_xmax.setMinimumWidth(box_size)
            self.input_freq_ymin.setMinimumWidth(box_size)
            self.input_freq_ymax.setMinimumWidth(box_size)
            self.input_bin.setFixedWidth(50)

        def _set_widget_layout(self):
            main_layout = QtWidgets.QVBoxLayout()

            row_1 = QtWidgets.QHBoxLayout()
            row_1.addWidget(self._label_input_bin)
            row_1.addWidget(self.input_bin)
            row_1.addWidget(self.slider_bin)

            main_layout.addLayout(row_1)

            time_form = QtWidgets.QGroupBox('Time')
            time_form.setMaximumHeight(110)
            time_layout = QtWidgets.QFormLayout()
            time_grid = QtWidgets.QGridLayout()

            time_grid.addWidget(self._label_time_xmin, 0, 2)
            time_grid.addWidget(self.input_time_xmin, 0, 3)
            time_grid.addWidget(self._label_time_xmax, 0, 4)
            time_grid.addWidget(self.input_time_xmax, 0, 5)
            time_grid.addWidget(self._label_time_yauto, 1, 0)
            time_grid.addWidget(self.check_time_yauto, 1, 1)
            time_grid.addWidget(self._label_time_ymin, 1, 2)
            time_grid.addWidget(self.input_time_ymin, 1, 3)
            time_grid.addWidget(self._label_time_ymax, 1, 4)
            time_grid.addWidget(self.input_time_ymax, 1, 5)

            temp_row = QtWidgets.QHBoxLayout()
            temp_row.addLayout(time_grid)
            time_layout.addRow(temp_row)

            time_form.setLayout(time_layout)

            freq_form = QtWidgets.QGroupBox('Frequency')
            freq_form.setMaximumHeight(110)
            freq_layout = QtWidgets.QFormLayout()
            freq_grid = QtWidgets.QGridLayout()

            freq_grid.addWidget(self._label_freq_xauto, 0, 0)
            freq_grid.addWidget(self.check_freq_xauto, 0, 1)
            freq_grid.addWidget(self._label_freq_xmin, 0, 2)
            freq_grid.addWidget(self.input_freq_xmin, 0, 3)
            freq_grid.addWidget(self._label_freq_xmax, 0, 4)
            freq_grid.addWidget(self.input_freq_xmax, 0, 5)
            freq_grid.addWidget(self._label_freq_yauto, 1, 0)
            freq_grid.addWidget(self.check_freq_yauto, 1, 1)
            freq_grid.addWidget(self._label_freq_ymin, 1, 2)
            freq_grid.addWidget(self.input_freq_ymin, 1, 3)
            freq_grid.addWidget(self._label_freq_ymax, 1, 4)
            freq_grid.addWidget(self.input_freq_ymax, 1, 5)

            temp_row = QtWidgets.QHBoxLayout()
            temp_row.addLayout(freq_grid)
            freq_layout.addRow(temp_row)

            freq_form.setLayout(freq_layout)

            editor_layout = QtWidgets.QHBoxLayout()
            editor_layout.addWidget(time_form)
            editor_layout.addWidget(freq_form)

            main_layout.addLayout(editor_layout)
            self.setLayout(main_layout)

        def get_max_time(self):
            return float(self.input_time_xmax.text())

        def get_min_time(self):
            return float(self.input_time_xmin.text())

        def get_max_freq(self):
            return float(self.input_freq_xmax.text())

        def get_min_freq(self):
            return float(self.input_freq_xmin.text())

        def get_max_asymmetry(self):
            return float(self.input_time_ymax.text())

        def get_min_asymmetry(self):
            return float(self.input_time_ymin.text())

        def get_max_fft(self):
            return float(self.input_freq_ymax.text())

        def get_min_fft(self):
            return float(self.input_freq_ymin.text())

        def get_bin_from_input(self):
            return float(self.input_bin.text())

        def get_bin_from_slider(self):
            return float(self.slider_bin.value())

        def is_asymmetry_auto(self):
            return self.check_time_yauto.isChecked()

        def is_fft_auto(self):
            return self.check_freq_yauto.isChecked()

        def is_freq_auto(self):
            return self.check_freq_xauto.isChecked()

        def set_enabled_asymmetry_auto(self, enabled):
            self.input_time_ymin.setEnabled(enabled)
            self.input_time_ymax.setEnabled(enabled)

        def set_enabled_frequency_auto(self, enabled):
            self.input_freq_xmin.setEnabled(enabled)
            self.input_freq_xmax.setEnabled(enabled)

        def set_enabled_fft_auto(self, enabled):
            self.input_freq_ymin.setEnabled(enabled)
            self.input_freq_ymax.setEnabled(enabled)

        def set_max_time(self, value):
            self.input_time_xmax.setText('{0:.3f}'.format(value))

        def set_min_time(self, value):
            self.input_time_xmin.setText('{0:.3f}'.format(value))

        def set_max_freq(self, value):
            self.input_freq_xmax.setText('{0:.3f}'.format(value))

        def set_min_freq(self, value):
            self.input_freq_xmin.setText('{0:.3f}'.format(value))

        def set_max_asymmetry(self, value):
            self.input_time_ymax.setText('{0:.3f}'.format(value))

        def set_min_asymmetry(self, value):
            self.input_time_ymin.setText('{0:.3f}'.format(value))

        def set_max_fft(self, value):
            self.input_freq_ymax.setText('{0:.1f}'.format(value))

        def set_min_fft(self, value):
            self.input_freq_ymin.setText('{0:.1f}'.format(value))

        def set_bin_input(self, value):
            self.input_bin.setText(str(value))

        def set_bin_slider(self, value):
            self.slider_bin.setValue(int(value))

    def __init__(self):
        super(Panel, self).__init__()
        super(QtWidgets.QWidget, self).__init__()
        self.support_panel = PlottingPanel.SupportPanel()

        self.left_settings = self.PlotControl()
        self.left_display = self.PlotDisplay(self.left_settings)

        self.right_settings = self.PlotControl()
        self.right_display = self.PlotDisplay(self.right_settings)

        self._set_logging()
        self.legend_display = self.support_panel.legend_box

        self._set_widget_layout()
        self._presenter = PlottingPanelPresenter(self)

        self.right_settings.input_bin.setText('5')
        self.right_settings.slider_bin.setValue(5)
        self.right_settings.input_time_xmax.setText('0.5')

    def createSupportPanel(self) -> QtWidgets.QDockWidget:
        return self.support_panel

    def _set_logging(self):
        logger = logging.getLogger('qt_plotting')

        self.left_settings.input_bin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_bin.returnPressed ({})".format(self.left_settings.input_bin.text())))
        self.left_settings.input_time_xmin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_time_xmin.returnPressed ({})".format(self.left_settings.input_time_xmin.text())))
        self.left_settings.input_time_xmax.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_time_xmax.returnPressed ({})".format(self.left_settings.input_time_xmax.text())))
        self.left_settings.input_time_ymin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_time_ymin.returnPressed ({})".format(self.left_settings.input_time_ymin.text())))
        self.left_settings.input_time_ymax.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_time_ymax.returnPressed ({})".format(self.left_settings.input_time_ymax.text())))
        self.left_settings.check_time_yauto.stateChanged.connect(lambda: logger.debug(
            "left_settings.check_time_yauto.stateChanged ({})".format(self.left_settings.check_time_yauto.isChecked())))
        self.left_settings.input_freq_xmin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_freq_xmin.returnPressed ({})".format(self.left_settings.input_freq_xmin.text())))
        self.left_settings.input_freq_xmax.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_freq_xmax.returnPressed ({})".format(self.left_settings.input_freq_xmax.text())))
        self.left_settings.input_freq_ymin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_freq_ymin.returnPressed ({})".format(self.left_settings.input_freq_ymin.text())))
        self.left_settings.input_freq_ymax.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_freq_ymax.returnPressed ({})".format(self.left_settings.input_freq_ymax.text())))
        self.left_settings.check_freq_yauto.stateChanged.connect(lambda: logger.debug(
            "left_settings.check_freq_yauto.stateChanged ({})".format(self.left_settings.check_freq_yauto.isChecked())))
        self.left_settings.check_freq_xauto.stateChanged.connect(lambda: logger.debug(
            "left_settings.check_freq_xauto.stateChanged ({})".format(self.left_settings.check_freq_xauto.isChecked())))
        self.left_settings.input_freq_xmin.returnPressed.connect(lambda: logger.debug(
            "left_settings.input_freq_xmin.returnPressed ({})".format(self.left_settings.input_freq_xmin.text())))
        self.right_settings.slider_bin.sliderMoved.connect(lambda: logger.debug(
            "left_settings.slider_bin.sliderMoved ({})".format(self.left_settings.slider_bin.value())))
        self.left_settings.slider_bin.sliderReleased.connect(lambda: logger.debug(
            "left_settings.slider_bin.sliderReleased ({})".format(self.left_settings.slider_bin.value())))

        self.right_settings.input_bin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_bin.returnPressed ({})".format(self.right_settings.input_bin.text())))
        self.right_settings.input_time_xmin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_time_xmin.returnPressed ({})".format(self.right_settings.input_time_xmin.text())))
        self.right_settings.input_time_xmax.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_time_xmax.returnPressed ({})".format(self.right_settings.input_time_xmax.text())))
        self.right_settings.input_time_ymin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_time_ymin.returnPressed ({})".format(self.right_settings.input_time_ymin.text())))
        self.right_settings.input_time_ymax.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_time_ymax.returnPressed ({})".format(self.right_settings.input_time_ymax.text())))
        self.right_settings.check_time_yauto.stateChanged.connect(lambda: logger.debug(
            "right_settings.check_time_yauto.stateChanged ({})".format(
                self.right_settings.check_time_yauto.isChecked())))
        self.right_settings.input_freq_xmin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_freq_xmin.returnPressed ({})".format(self.right_settings.input_freq_xmin.text())))
        self.right_settings.input_freq_xmax.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_freq_xmax.returnPressed ({})".format(self.right_settings.input_freq_xmax.text())))
        self.right_settings.input_freq_ymin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_freq_ymin.returnPressed ({})".format(self.right_settings.input_freq_ymin.text())))
        self.right_settings.input_freq_ymax.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_freq_ymax.returnPressed ({})".format(self.right_settings.input_freq_ymax.text())))
        self.right_settings.check_freq_yauto.stateChanged.connect(lambda: logger.debug(
            "right_settings.check_freq_yauto.stateChanged ({})".format(
                self.right_settings.check_freq_yauto.isChecked())))
        self.right_settings.check_freq_xauto.stateChanged.connect(lambda: logger.debug(
            "right_settings.check_freq_xauto.stateChanged ({})".format(
                self.right_settings.check_freq_xauto.isChecked())))
        self.right_settings.input_freq_xmin.returnPressed.connect(lambda: logger.debug(
            "right_settings.input_freq_xmin.returnPressed ({})".format(self.right_settings.input_freq_xmin.text())))
        self.right_settings.slider_bin.sliderMoved.connect(lambda: logger.debug(
            "right_settings.input_bin.returnPressed ({})".format(self.right_settings.slider_bin.value())))
        self.right_settings.slider_bin.sliderReleased.connect(lambda: logger.debug(
            "right_settings.input_bin.returnPressed ({})".format(self.right_settings.slider_bin.value())))

        # self.support_panel.all_color_options.currentTextChanged.connect(lambda: logger.debug("support_panel.all_color_options.currentTextChanged ({})".format(self.support_panel.all_color_options.currentText())))
        # self.support_panel.linestyle_options.currentTextChanged.connect(lambda: logger.debug("support_panel.linestyle_options.currentTextChanged ({})".format(self.support_panel.linestyle_options.currentText())))
        # self.support_panel.line_color_options.currentTextChanged.connect(lambda: logger.debug("support_panel.line_color_options.currentTextChanged ({})".format(self.support_panel.line_color_options.currentText())))
        # self.support_panel.line_width_options.currentTextChanged.connect(lambda: logger.debug("support_panel.line_width_options.currentTextChanged ({})".format(self.support_panel.line_width_options.currentText())))
        # self.support_panel.marker_options.currentTextChanged.connect(lambda: logger.debug("support_panel.marker_options.currentTextChanged ({})".format(self.support_panel.marker_options.currentText())))
        # self.support_panel.marker_color_options.currentTextChanged.connect(lambda: logger.debug("support_panel.marker_color_options.currentTextChanged ({})".format(self.support_panel.marker_color_options.currentText())))
        # self.support_panel.marker_size_options.currentTextChanged.connect(lambda: logger.debug("support_panel.marker_size_options.currentTextChanged ({})".format(self.support_panel.marker_size_options.currentText())))
        # self.support_panel.fillstyle_options.currentTextChanged.connect(lambda: logger.debug("support_panel.fillstyle_options.currentTextChanged ({})".format(self.support_panel.fillstyle_options.currentText())))
        # self.support_panel.errorbar_style_options.currentTextChanged.connect(lambda: logger.debug("support_panel.errorbar_style_options.currentTextChanged ({})".format(self.support_panel.errorbar_style_options.currentText())))
        # self.support_panel.errorbar_color_options.currentTextChanged.connect(lambda: logger.debug("support_panel.errorbar_color_options.currentTextChanged ({})".format(self.support_panel.errorbar_color_options.currentText())))
        # self.support_panel.errorbar_width_options.currentTextChanged.connect(lambda: logger.debug("support_panel.errorbar_width_options.currentTextChanged ({})".format(self.support_panel.errorbar_width_options.currentText())))
        # self.support_panel.fit_color_options.currentTextChanged.connect(lambda: logger.debug("support_panel.fit_color_options.currentTextChanged ({})".format(self.support_panel.fit_color_options.currentText())))
        # self.support_panel.fit_linestyle_options.currentTextChanged.connect(lambda: logger.debug("support_panel.fit_linestyle_options.currentTextChanged ({})".format(self.support_panel.fit_linestyle_options.currentText())))

        self.support_panel.item_tree.itemSelectionChanged.connect(lambda: logger.debug(
            "support_panel.item_tree.itemSelectionChanged ({})".format(
                self.support_panel.item_tree.get_selected_names())))

        self.support_panel.plot_button.pressed.connect(lambda: logger.debug(
            "support_panel.plot_button.pressed ({})".format(self.support_panel.item_tree.get_selected_names())))
        self.support_panel.plot_all_button.pressed.connect(lambda: logger.debug(
            "support_panel.plot_all_button.pressed ({})".format(self.support_panel.item_tree.get_names())))
        self.support_panel.clear_all_button.pressed.connect(lambda: logger.debug(
            "support_panel.clear_all_button.pressed ({})".format(self.support_panel.item_tree.get_selected_names())))
        self.support_panel.asymmetry_param_box.alpha_input.returnPressed.connect(lambda: logger.debug(
            "support_panel.alpha_input.returnPressed ({})".format(
                self.support_panel.asymmetry_param_box.alpha_input.text())))

    def _set_widget_attributes(self):
        pass

    def _set_widget_dimensions(self):
        pass

    def _set_widget_layout(self):
        hbox = QtWidgets.QHBoxLayout()

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.left_display, 2)
        vbox.addWidget(self.left_settings)
        hbox.addLayout(vbox)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.right_display, 2)
        vbox.addWidget(self.right_settings)
        hbox.addLayout(vbox)

        self.setLayout(hbox)


class PlottingPanelPresenter(PanelPresenter):
    def __init__(self, view: PlottingPanel):
        super().__init__(view)
        self.__run_service = services.RunService()
        self.__style_service = services.StyleService()
        self.__run_service.signals.added.connect(self.update)
        self.__run_service.signals.changed.connect(self.update_after_change)
        self.__populating_settings = False
        self.__update_alpha = True
        self.__logger = logging.getLogger("PlottingPanelPresenter")
        self._set_callbacks()

    def _set_callbacks(self):
        self._view.left_settings.input_time_xmin.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_time_xmax.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_time_ymin.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_time_ymax.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.check_time_yauto.stateChanged.connect(lambda: self._check_parameter_changed('left'))
        self._view.left_settings.input_freq_xmin.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_freq_xmax.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_freq_ymin.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.input_freq_ymax.returnPressed.connect(lambda: self._start_update('left'))
        self._view.left_settings.check_freq_yauto.stateChanged.connect(lambda: self._check_parameter_changed('left'))
        self._view.left_settings.check_freq_xauto.stateChanged.connect(lambda: self._check_parameter_changed('left'))
        self._view.left_settings.slider_bin.sliderMoved.connect(lambda: self._bin_parameter_changed('left', True))
        self._view.left_settings.slider_bin.sliderReleased.connect(lambda: self._bin_parameter_changed('left', False))
        self._view.left_settings.input_bin.returnPressed.connect(lambda: self._bin_parameter_changed('left', False))
        self._view.right_settings.input_time_xmin.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_time_xmax.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_time_ymin.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_time_ymax.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.check_time_yauto.stateChanged.connect(lambda: self._check_parameter_changed('right'))
        self._view.right_settings.input_freq_xmin.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_freq_xmax.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_freq_ymin.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.input_freq_ymax.returnPressed.connect(lambda: self._start_update('right'))
        self._view.right_settings.check_freq_yauto.stateChanged.connect(lambda: self._check_parameter_changed('right'))
        self._view.right_settings.check_freq_xauto.stateChanged.connect(lambda: self._check_parameter_changed('left'))
        self._view.right_settings.slider_bin.sliderMoved.connect(lambda: self._bin_parameter_changed('right', True))
        self._view.right_settings.slider_bin.sliderReleased.connect(lambda: self._bin_parameter_changed('right', False))
        self._view.right_settings.input_bin.returnPressed.connect(lambda: self._bin_parameter_changed('right', False))
        self._view.support_panel.plot_button.pressed.connect(self._plot)
        self._view.support_panel.plot_all_button.pressed.connect(self._plot_all)
        self._view.support_panel.clear_all_button.pressed.connect(self._clear_all)
        self._view.support_panel.asymmetry_param_box.alpha_input.returnPressed.connect(self.update_alpha)

        self._view.support_panel.plot_style_box.all_color_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.DEFAULT_COLOR,
                                                  self._view.support_panel.plot_style_box.all_color_options.currentText()))
        self._view.support_panel.plot_style_box.linestyle_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.LINESTYLE,
                                                  self._view.support_panel.plot_style_box.linestyle_options.currentText()))
        self._view.support_panel.plot_style_box.line_color_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.LINE_COLOR,
                                                  self._view.support_panel.plot_style_box.line_color_options.currentText()))
        self._view.support_panel.plot_style_box.line_width_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.LINE_WIDTH,
                                                  self._view.support_panel.plot_style_box.line_width_options.currentText()))
        self._view.support_panel.plot_style_box.marker_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.MARKER,
                                                  self._view.support_panel.plot_style_box.marker_options.currentText()))
        self._view.support_panel.plot_style_box.marker_color_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.MARKER_COLOR,
                                                  self._view.support_panel.plot_style_box.marker_color_options.currentText()))
        self._view.support_panel.plot_style_box.marker_size_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.MARKER_SIZE,
                                                  self._view.support_panel.plot_style_box.marker_size_options.currentText()))
        self._view.support_panel.plot_style_box.fillstyle_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.FILLSTYLE,
                                                  self._view.support_panel.plot_style_box.fillstyle_options.currentText()))
        self._view.support_panel.plot_style_box.errorbar_style_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.ERRORBAR_STYLE,
                                                  self._view.support_panel.plot_style_box.errorbar_style_options.currentText()))
        self._view.support_panel.plot_style_box.errorbar_color_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.ERRORBAR_COLOR,
                                                  self._view.support_panel.plot_style_box.errorbar_color_options.currentText()))
        self._view.support_panel.plot_style_box.errorbar_width_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.ERRORBAR_WIDTH,
                                                  self._view.support_panel.plot_style_box.errorbar_width_options.currentText()))
        self._view.support_panel.plot_style_box.fit_color_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.FIT_COLOR,
                                                  self._view.support_panel.plot_style_box.fit_color_options.currentText()))
        self._view.support_panel.plot_style_box.fit_linestyle_options.currentTextChanged.connect(
            lambda: self._style_parameter_changed(self.__style_service.Keys.FIT_LINESTYLE,
                                                  self._view.support_panel.plot_style_box.fit_linestyle_options.currentText()))
        self._view.support_panel.item_tree.itemSelectionChanged.connect(self._populate_settings)

    def _start_update(self, side):
        if side == 'left' or side == 'both':
            threading.Thread(
                target=self._update_canvas(self._view.left_settings, self._view.left_display, 'left', fast=False),
                daemon=True).start()

        if side == 'right' or side == 'both':
            threading.Thread(
                target=self._update_canvas(self._view.right_settings, self._view.right_display, 'right', fast=False),
                daemon=True).start()

    def _plot_all(self):
        self._view.support_panel.item_tree.set_all_checked(True)
        self._plot()

    def _plot(self):
        def _verify_asymmetries_are_calculated():
            runs_without_asymmetries = []
            for run in runs:
                if run.asymmetries[domain.RunDataset.FULL_ASYMMETRY] is None:
                    runs_without_asymmetries.append(run)

            if len(runs_without_asymmetries) > 0:
                code = PlotFileDialog.launch([runs_without_asymmetries])
                if code == PlotFileDialog.Codes.NO_FILES_PLOTTED:
                    return False
            return True

        ids = self._view.support_panel.item_tree.get_run_ids()
        runs = self.__run_service.get_runs_by_ids(ids)
        verified = _verify_asymmetries_are_calculated()

        if not verified:
            return

        self._start_update(side='both')

    def _clear_all(self):
        self._view.support_panel.item_tree.set_all_checked(False)
        self._view.legend_display.set_blank()

        self._start_update(side='both')

    def _bin_parameter_changed(self, side, moving):
        if side == 'left':
            settings = self._view.left_settings
        else:
            settings = self._view.right_settings

        if moving:
            value = settings.get_bin_from_slider()
            settings.set_bin_input(value)

            if value % 5 != 0:
                return
        else:
            settings.set_bin_slider(settings.get_bin_from_input())

        self._start_update(side)

    def _check_parameter_changed(self, side):
        if side == 'left':
            settings = self._view.left_settings
        else:
            settings = self._view.right_settings

        settings.set_enabled_asymmetry_auto(not settings.is_asymmetry_auto())
        settings.set_enabled_frequency_auto(not settings.is_freq_auto())
        settings.set_enabled_fft_auto(not settings.is_fft_auto())

    def _update_canvas(self, settings, display, side, fast=False):
        ids = self._view.support_panel.item_tree.get_run_ids()
        runs = self.__run_service.get_runs_by_ids(ids)
        display.start_plotting()

        if len(runs) == 0:
            display.set_full_blank()
            self._view.legend_display.set_blank()
            return
        else:
            self._view.setEnabled(True)

        max_asymmetry = -1
        min_asymmetry = 1
        max_fft = 0
        min_time = settings.get_min_time()
        max_time = settings.get_max_time()
        bin_size = settings.get_bin_from_input()

        legend_values = {}
        for run in runs:
            if run.asymmetries[domain.RunDataset.FULL_ASYMMETRY] is None:
                continue

            if side == 'left':
                asymmetry = run.asymmetries[domain.RunDataset.LEFT_BINNED_ASYMMETRY]
                if asymmetry is None or asymmetry.bin_size != bin_size or True:
                    asymmetry = run.asymmetries[domain.RunDataset.FULL_ASYMMETRY].bin(bin_size)
                    run.asymmetries[domain.RunDataset.LEFT_BINNED_ASYMMETRY] = asymmetry
            else:
                asymmetry = run.asymmetries[domain.RunDataset.RIGHT_BINNED_ASYMMETRY]
                if asymmetry is None or asymmetry.bin_size != bin_size or True:
                    asymmetry = run.asymmetries[domain.RunDataset.FULL_ASYMMETRY].bin(bin_size)
                    run.asymmetries[domain.RunDataset.RIGHT_BINNED_ASYMMETRY] = asymmetry

            time = asymmetry.time
            uncertainty = asymmetry.uncertainty
            fit = None
            style = self.__style_service.get_style_by_run_id(run.id)
            legend_values[run.id] = (style[self.__style_service.Keys.LABEL], self.__style_service.color_options_extra[
                style[self.__style_service.Keys.DEFAULT_COLOR] if style[self.__style_service.Keys.MARKER_COLOR] == 'Default' else
                style[self.__style_service.Keys.MARKER_COLOR]])

            # We have to do this logic because Matplotlib is not good at setting good default plot limits
            frac_start = float(min_time) / (time[len(time) - 1] - time[0])
            frac_end = float(max_time) / (time[len(time) - 1] - time[0])
            start_index = int(np.floor(len(asymmetry) * frac_start))
            end_index = int(np.floor(len(asymmetry) * frac_end))
            local_max = np.max(asymmetry[start_index:end_index])
            max_asymmetry = local_max if local_max > max_asymmetry else max_asymmetry
            local_min = np.min(asymmetry[start_index:end_index])
            min_asymmetry = local_min if local_min < min_asymmetry else min_asymmetry

            if not fast:
                pass

            display.plot_asymmetry(time, asymmetry, uncertainty, fit,
                                   color=style[self.__style_service.Keys.DEFAULT_COLOR],
                                   marker=style[self.__style_service.Keys.MARKER],
                                   linestyle=style[self.__style_service.Keys.LINESTYLE],
                                   fillstyle=style[self.__style_service.Keys.FILLSTYLE],
                                   marker_color=style[self.__style_service.Keys.MARKER_COLOR],
                                   marker_size=style[self.__style_service.Keys.MARKER_SIZE],
                                   line_color=style[self.__style_service.Keys.LINE_COLOR],
                                   line_width=style[self.__style_service.Keys.LINE_WIDTH],
                                   errorbar_color=style[self.__style_service.Keys.ERRORBAR_COLOR],
                                   errorbar_style=style[self.__style_service.Keys.ERRORBAR_STYLE],
                                   errorbar_width=style[self.__style_service.Keys.ERRORBAR_WIDTH],
                                   fit_color=style[self.__style_service.Keys.FIT_COLOR],
                                   fit_linestyle=style[self.__style_service.Keys.FIT_LINESTYLE])

            if not fast:
                frequencies, fft = self.get_fft_data(time, asymmetry, min_time, max_time, bin_size)
                local_max = np.max(fft)
                max_fft = local_max if local_max > max_fft else max_fft

                display.plot_fft(frequencies, fft,
                                 style[self.__style_service.Keys.DEFAULT_COLOR],
                                 style[self.__style_service.Keys.LABEL])

        display.set_asymmetry_plot_limits(max_asymmetry, min_asymmetry)
        display.set_fft_plot_limits(max_fft)
        display.finish_plotting(fast)

        self._view.legend_display.set_legend(legend_values)

    @QtCore.pyqtSlot()
    def update(self, runs_changed=False):
        self.__logger.debug("Accepted Signal")
        run_datasets = self.__run_service.get_runs()
        alphas = {'{:.5f}'.format(run.asymmetries[run.FULL_ASYMMETRY].alpha) for run in run_datasets if
                  run.asymmetries[run.FULL_ASYMMETRY] is not None}

        self.__update_alpha = False
        if len(alphas) == 1:
            self._view.support_panel.asymmetry_param_box.alpha_input.setText(alphas.pop())
        else:
            self._view.support_panel.asymmetry_param_box.alpha_input.setText('1.0')
        self.__update_alpha = True

        for run in run_datasets:
            self.__style_service.add_style_for_run(run, False, True)

        if runs_changed:
            self._start_update('both')

        self._populate_settings()

    def update_after_change(self):
        self.update(True)

    def update_alpha(self):
        if not self.__update_alpha:
            return

        try:
            alpha = float(self._view.support_panel.asymmetry_param_box.alpha_input.text())
        except ValueError:
            return

        ids = self._view.support_panel.item_tree.get_selected()
        if len(ids) > 0:
            self.__run_service.update_alphas(ids, [alpha])

    def get_fft_data(self, time, asymmetry, xmin, xmax, bin_size):
        num_bins = self.get_num_bins(xmin, xmax, bin_size)
        start_bin = self.get_start_bin(xmin, bin_size)
        fft = domain.FFT(asymmetry[start_bin:start_bin + num_bins], time[start_bin:start_bin + num_bins])
        return fft.z, fft.fft / max(fft.fft)

    def get_num_bins(self, xmin, xmax, bin_size):
        return int((float(xmax) - float(xmin)) / (float(bin_size) / 1000))

    def get_start_bin(self, xmin, bin_size):
        return int(float(xmin) / (float(bin_size) / 1000))

    def _style_parameter_changed(self, key, value):
        if not self.__populating_settings:
            ids = self._view.support_panel.item_tree.get_selected()
            self.__style_service.change_style_parameter(ids, key, value)

            self._start_update('both')

    def _populate_settings(self):
        self.__populating_settings = True  # Because this sends a lot of signals because QComboBoxes are changing

        ids = self._view.support_panel.item_tree.get_selected()
        runs = self.__run_service.get_runs_by_ids(ids)
        styles = [self.__style_service.get_style_by_run_id(rid) for rid in ids]

        alphas = {'{:.5f}'.format(run.asymmetries[run.FULL_ASYMMETRY].alpha) for run in runs if
                  run.asymmetries[run.FULL_ASYMMETRY] is not None}
        if len(alphas) == 1:
            self._view.support_panel.asymmetry_param_box.alpha_input.setText(alphas.pop())
        else:
            self._view.support_panel.asymmetry_param_box.alpha_input.setText('1.0')

        self.__update_alpha = True
        if len(styles) > 1:
            self._populate_with_multiple_selected(styles)
        elif len(styles) == 1:
            self._populate_with_single_selected(styles)
        else:
            pass
        self.__populating_settings = False

    def _populate_with_single_selected(self, styles):
        style = styles[0]

        # self._view.support_panel.set_alpha
        self._view.support_panel.set_errorbar_color(
            self.__style_service.color_options_extra[style[self.__style_service.Keys.ERRORBAR_COLOR]])
        self._view.support_panel.set_default_color(
            self.__style_service.color_options[style[self.__style_service.Keys.DEFAULT_COLOR]])
        self._view.support_panel.set_fit_color(
            self.__style_service.color_options_extra[style[self.__style_service.Keys.FIT_COLOR]])
        self._view.support_panel.set_errorbar_style(
            self.__style_service.errorbar_styles[style[self.__style_service.Keys.ERRORBAR_STYLE]])
        self._view.support_panel.set_errorbar_width(
            self.__style_service.errorbar_width[style[self.__style_service.Keys.ERRORBAR_WIDTH]])
        self._view.support_panel.set_fillstyle(
            self.__style_service.fillstyle_options[style[self.__style_service.Keys.FILLSTYLE]])
        self._view.support_panel.set_line_color(
            self.__style_service.color_options_extra[style[self.__style_service.Keys.LINE_COLOR]])
        self._view.support_panel.set_line_width(
            self.__style_service.line_width_options[style[self.__style_service.Keys.LINE_WIDTH]])
        self._view.support_panel.set_linestyle(
            self.__style_service.linestyle_options[style[self.__style_service.Keys.LINESTYLE]])
        self._view.support_panel.set_marker(
            self.__style_service.marker_options[style[self.__style_service.Keys.MARKER]])
        self._view.support_panel.set_marker_color(
            self.__style_service.color_options_extra[style[self.__style_service.Keys.MARKER_COLOR]])
        self._view.support_panel.set_marker_size(
            self.__style_service.marker_size_options[style[self.__style_service.Keys.MARKER_SIZE]])

    def _populate_with_multiple_selected(self, styles):
        values = {self.__style_service.color_options[style[self.__style_service.Keys.DEFAULT_COLOR]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_default_color("*")
        else:
            self._view.support_panel.set_default_color(values.pop())

        values = {self.__style_service.errorbar_width[style[self.__style_service.Keys.ERRORBAR_WIDTH]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_errorbar_width("*")
        else:
            self._view.support_panel.set_errorbar_width(values.pop())

        values = {self.__style_service.color_options_extra[style[self.__style_service.Keys.ERRORBAR_COLOR]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_errorbar_color("*")
        else:
            self._view.support_panel.set_errorbar_color(values.pop())

        values = {self.__style_service.color_options_extra[style[self.__style_service.Keys.FIT_COLOR]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_fit_color("*")
        else:
            self._view.support_panel.set_fit_color(values.pop())

        values = {self.__style_service.errorbar_styles[style[self.__style_service.Keys.ERRORBAR_STYLE]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_errorbar_style("*")
        else:
            self._view.support_panel.set_errorbar_style(values.pop())

        values = {self.__style_service.marker_size_options[style[self.__style_service.Keys.MARKER_SIZE]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_marker_size("*")
        else:
            self._view.support_panel.set_marker_size(values.pop())

        values = {self.__style_service.line_width_options[style[self.__style_service.Keys.LINE_WIDTH]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_line_width("*")
        else:
            self._view.support_panel.set_line_width(values.pop())

        values = {self.__style_service.linestyle_options[style[self.__style_service.Keys.LINESTYLE]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_linestyle("*")
        else:
            self._view.support_panel.set_linestyle(values.pop())

        values = {self.__style_service.fillstyle_options[style[self.__style_service.Keys.FILLSTYLE]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_fillstyle("*")
        else:
            self._view.support_panel.set_fillstyle(values.pop())

        values = {self.__style_service.color_options_extra[style[self.__style_service.Keys.MARKER_COLOR]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_marker_color("*")
        else:
            self._view.support_panel.set_marker_color(values.pop())

        values = {self.__style_service.color_options_extra[style[self.__style_service.Keys.LINE_COLOR]] for style in
                  styles}
        if len(values) > 1:
            self._view.support_panel.set_line_color("*")
        else:
            self._view.support_panel.set_line_color(values.pop())

        values = {self.__style_service.marker_options[style[self.__style_service.Keys.MARKER]] for style in styles}
        if len(values) > 1:
            self._view.support_panel.set_marker("*")
        else:
            self._view.support_panel.set_marker(values.pop())
