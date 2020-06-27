
import enum
import os
import sys

import requests
from PyQt5 import QtWidgets

from app.util import widgets
from app.model.model import FileContext
from app.model import files


# noinspection PyArgumentList
class MusrDownloadDialog(QtWidgets.QDialog):
    class Codes(enum.IntEnum):
        NEW_FILES = 1
        NO_NEW_FILES = 2

    def __init__(self, args=None):
        super(MusrDownloadDialog, self).__init__()

        self.status_bar = QtWidgets.QStatusBar()
        self.input_area = QtWidgets.QLineEdit()
        self.input_year = QtWidgets.QLineEdit()
        self.input_runs = QtWidgets.QLineEdit()
        self.input_file = QtWidgets.QLineEdit()
        self.input_expt = QtWidgets.QLineEdit()
        self.output_web = QtWidgets.QPlainTextEdit()
        self.select_button = widgets.StyleTwoButton('Save to')
        self.download_button = widgets.StyleOneButton('Download')
        self.search_button = widgets.StyleOneButton('Search')
        self.done_button = widgets.StyleOneButton('Done')
        self._label_description = QtWidgets.QLabel('Provide the information below to search and/or download runs from '
                                                   'musr.ca.\n * indicates required for download. You can search'
                                                   ' based on incomplete info.')

        self._set_widget_dimensions()
        self._set_widget_attributes()
        self._set_widget_layout()

        self._presenter = MusrDownloadDialogPresenter(self)

    def set_status_message(self, message):
        self.status_bar.showMessage(message)

    def _set_widget_dimensions(self):
        self.input_area.setFixedWidth(70)
        self.input_expt.setFixedWidth(70)
        self.input_year.setFixedWidth(70)
        self.select_button.setFixedWidth(80)
        self.download_button.setFixedWidth(80)
        self.done_button.setFixedWidth(80)
        self.search_button.setFixedWidth(80)
        self.output_web.setFixedHeight(150)
        self.setFixedWidth(400)

    def _set_widget_attributes(self):
        self.input_area.setPlaceholderText('*Area')
        self.input_year.setPlaceholderText('*Year (YYYY)')
        self.input_runs.setPlaceholderText('*Range of Runs (N-N)')
        self.input_file.setPlaceholderText('Save Directory (default is current)')
        self.input_expt.setPlaceholderText('Expt #')

        self.output_web.setEnabled(True)
        self.output_web.appendPlainText('No queries or downloads attempted.\n')

        self.set_status_message('Ready.')

    def _set_widget_layout(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._label_description)
        main_layout.addSpacing(5)

        row_1 = QtWidgets.QHBoxLayout()
        row_1.addWidget(self.input_expt)
        row_1.addWidget(self.input_year)
        row_1.addWidget(self.input_area)
        row_1.addWidget(self.input_runs)
        main_layout.addLayout(row_1)

        row_2 = QtWidgets.QHBoxLayout()
        row_2.addWidget(self.select_button)
        row_2.addWidget(self.input_file)
        main_layout.addLayout(row_2)
        main_layout.addSpacing(10)

        row_3 = QtWidgets.QHBoxLayout()
        row_3.addStretch()
        row_3.addWidget(self.search_button)
        row_3.addSpacing(10)
        row_3.addWidget(self.download_button)
        row_3.addSpacing(10)
        row_3.addWidget(self.done_button)
        row_3.addStretch()
        main_layout.addLayout(row_3)
        main_layout.addSpacing(10)

        row_4 = QtWidgets.QHBoxLayout()
        row_4.addWidget(self.output_web)
        main_layout.addLayout(row_4)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    def set_file(self, file_path):
        self.input_file.setText(file_path)

    def get_area(self):
        return self.input_area.text()

    def get_year(self):
        return self.input_year.text()

    def get_runs(self):
        return self.input_runs.text()

    def get_file(self):
        return self.input_file.text()

    def get_experiment_number(self):
        return self.input_expt.text()

    def log_message(self, message):
        self.output_web.insertPlainText(message)

    @staticmethod
    def launch(args=None):
        dialog = MusrDownloadDialog(args)
        return dialog.exec()


class MusrDownloadDialogPresenter:
    def __init__(self, view: MusrDownloadDialog):
        self._view = view
        self._search_url = "http://musr.ca/mud/runSel.php"
        self._data_url = "http://musr.ca/mud/data/"
        self._new_files = False
        self._context = FileContext()

        self._set_callbacks()

    def _set_callbacks(self):
        self._view.search_button.released.connect(lambda: self._search_clicked())
        self._view.download_button.released.connect(lambda: self._download_clicked())
        self._view.done_button.released.connect(lambda: self._done_clicked())
        self._view.select_button.released.connect(lambda: self._save_to_clicked())

    def _assemble_query(self):
        query = "?"

        area = self._view.get_area()
        if len(area) > 0:
            query += "area={}&".format(area)

        year = self._view.get_year()
        if len(year) > 0:
            if len(year) == 4:
                try:
                    int(year)
                except ValueError:
                    self._view.log_message("Give year as 4 digits.\n")
                    return
                query += "year={}&".format(year)
            else:
                self._view.log_message("Give year as 4 digits.\n")
                return

        expt = self._view.get_experiment_number()
        if len(expt) > 0:
            try:
                int(expt)
            except ValueError:
                self._view.log_message("Experiment number should be an integer.\n")
                return
            query += "expt={}&".format(expt)

        return query

    def _assemble_downloads(self):
        download_string = ""

        area = self._view.get_area()
        if len(area) == 0:
            return
        download_string += "{}/".format(area)

        year = self._view.get_year()
        if len(year) == 0:
            return
        download_string += "{}/".format(year)

        runs = self._view.get_runs()
        if len(runs) == 0:
            return

        runs = runs.split('-')
        if len(runs) == 1:
            download_string += '{0:06d}.msr'.format(int(runs[0]))
            return [download_string]

        return [download_string + '{0:06d}.msr'.format(download) for download in range(int(runs[0]), int(runs[1])+1)]

    def _assemble_save(self, download):
        directory = self._view.get_file()

        if len(directory) == 0:
            directory = os.getcwd()

        if sys.platform == 'win32':
            separator = "\\"
        else:
            separator = "/"

        return directory + "{}{}".format(separator, download.split('/')[-1])

    def _search_clicked(self):
        self._view.set_status_message('Querying ... ')
        query = self._assemble_query()

        if query is None:
            return

        if len(query) < 2:
            self._view.log_message("No query parameters filled.\n")
        else:
            self._view.log_message("Sending query : {}\n".format(query))

        full_url = self._search_url + query

        try:
            response = requests.get(full_url)
        except requests.exceptions.ConnectionError:
            self._view.log_message("Error: Check your internet connection.\n")
            return

        if response.status_code != 200:
            self._view.log_message("Error : {}\n".format(response.status_code))
            return

        printed_response = False
        for x in response.text.split('TR>'):
            y = x.split('<TD')
            if len(y) > 2:
                year = y[2][1:5]
                area = y[3].split('<i>')[1].split('</i>')[0]
                expt = y[4].split('>')[1].split('<')[0]
                expt_type = y[5].split('>')[3].split('<')[0]
                run_numbers = y[6].split('"')
                if len(run_numbers) > 4:
                    run_number = run_numbers[3].split()[2]
                    self._view.log_message('{}  Year: {}, Area: {}, '
                                                           'Expt: {}, Type: {}\n'.format(run_number, year, area,
                                                                                         expt, expt_type))
                    printed_response = True

        if not printed_response:
            self._view.log_message("No runs found.")

        self._view.set_status_message('Done.')

    def _download_clicked(self):
        self._view.set_status_message('Downloading ... ')

        downloads = self._assemble_downloads()
        if downloads is None:
            self._view.log_message('No runs specified.\n')
            return

        good = 0
        new_files = []
        for i, download in enumerate(downloads):
            full_url = self._data_url + download

            try:
                response = requests.get(full_url)
            except requests.exceptions.ConnectionError:
                self._view.log_message('Failed to download {}. Connection Error\n'.format(full_url))
                continue

            if response.status_code != 200:
                self._view.log_message('Failed to download {}. Error {}\n'.format(full_url, response.status_code))
                continue

            save_file = self._assemble_save(download)
            with open(save_file, 'wb') as fb:
                for chunk in response.iter_content(100000):
                    fb.write(chunk)
            new_files.append(save_file)
            self._new_files = True
            self._view.log_message('Successfully downloaded {}.\n'.format(full_url))
            good += 1

        self._context.add_files(new_files)
        self._view.log_message('{}/{} Files downloaded successfully.\n'.format(good, len(downloads)))
        self._view.set_status_message('Done.')

    def _done_clicked(self):
        if self._new_files:
            self._view.done(MusrDownloadDialog.Codes.NEW_FILES)
        else:
            self._view.done(MusrDownloadDialog.Codes.NO_NEW_FILES)

    # noinspection PyCallByClass
    def _save_to_clicked(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self._view, 'Select directory to save MUD files to',
                                                          files.load_last_used_directory(),
                                                          options=QtWidgets.QFileDialog.ShowDirsOnly)
        if path:
            files.set_last_used_directory(path)
            self._view.set_file(path)