# Model for BEAMS application

# BEAMS specific modules
import BeamsUtility

# Standard Library modules
import os

# Installed modules
import numpy as np
import scipy.interpolate as sp

# Signals from Model to Controllers
FILE_CHANGED = 1
PARAMETER_CHANGED = 2
RUN_LIST_CHANGED = 3
RUN_DATA_CHANGED = 4


class BEAMSModel:
    """ Manages the data, logic and rules of the application. """
    def __init__(self):
        """Initializes the empty model"""
        self.all_full_filepaths = {}
        self.plot_parameters = {}
        self.used_colors = []
        self.run_list = []
        self.current_formats = {}

        # The controllers will register themselves in this dictionary to the signals they need to be notified of.
        self.observers = {FILE_CHANGED: [],
                          PARAMETER_CHANGED: [],
                          RUN_LIST_CHANGED: [],
                          RUN_DATA_CHANGED: []}

        # For debugging currently
        self.debugging_signals = {FILE_CHANGED: 'FILE_CHANGED',
                                  PARAMETER_CHANGED: 'PARAMETER_CHANGED',
                                  RUN_LIST_CHANGED: 'RUN_LIST_CHANGED',
                                  RUN_DATA_CHANGED: 'RUN_DATA_CHANGED'}

        self.color_options = ["blue", "red", "green", "orange", "purple",
                              "brown", "yellow", "gray", "olive", "cyan", "pink"]

    def update_colors(self, color=None, used=False, custom=False):
        """ Updates the used and un-used color lists so as to keep track of which colors are available
                when plotting new runs without having two runs of identical color."""
        if not custom:  # Don't want to save custom colors in the library
            if used:
                if color in self.color_options:
                    self.color_options.remove(color)
                if color not in self.used_colors:
                    self.used_colors.append(color)
            else:
                if color in self.used_colors:
                    self.used_colors.remove(color)
                if color not in self.color_options:
                    self.color_options.append(color)
        return True

    def update_run_color(self, file=None, color=None):
        """ Updates the color of a specific run. Calls update_colors() to update the used and available color lists. """
        if color in self.color_options:
            self.update_colors(color=color, used=True)

        for run in self.run_list:
            if run.filename == file:
                if run.color in self.used_colors:
                    self.update_colors(color=run.color, used=False)
                run.color = color

        self.notify(RUN_DATA_CHANGED)

    def update_runs(self, formats):
        """ Updates the list of runs by removing any old runs not selected by user and adding the new ones."""
        current_files = [file for file in self.current_formats.keys()]
        for filename in current_files:  # First checks if any old filenames are not in the new list
            if filename not in formats.keys():
                for run in self.run_list:
                    if run.filename == filename:
                        self.update_colors(color=run.color, used=False)  # Update color availability
                        self.run_list.remove(run)  # Remove the no longer selected run.
                self.current_formats.pop(filename)

        for filename in formats.keys():  # Second checks if any filenames in the new list are not in the old
            if filename not in self.current_formats.keys():
                # print('Adding', formats[filename])
                self.run_list.append(RunData(filename=filename, f_format=formats[filename],
                                             color=self.color_options[0]))
                self.update_colors(color=self.color_options[0], used=True)
                self.current_formats.update({filename: formats[filename]})

        self.notify(RUN_LIST_CHANGED)  # Notifies the Run Display Panel

    def update_plot_parameters(self):
        """ Prompts the re-plotting of data by notifying the PlotPanel"""
        self.notify(PARAMETER_CHANGED)  # Notifies the Plot Panel

    def update_file_list(self, file_name=None, file_path=None):
        """ Adds full filepaths to model file dictionary. """
        # If file path is not reachable, add 'Not Found' tag to the file name.
        if not BeamsUtility.is_found(file_path):
            file_name = file_name + ' (Not Found) '
            # e.g. user opened a session with deleted files or files from another computer. The data is fine, files not

        # Else if it is reached and their is a tagged version of it in the list, remove it (user specified correct path)
        elif (file_name + ' (Not Found) ') in self.all_full_filepaths.keys():
            self.all_full_filepaths.pop((file_name + ' (Not Found) '))

        self.all_full_filepaths[file_name] = file_path
        self.notify(FILE_CHANGED)  # Notifies the File Manager Panel

    def update_visibilities(self, file=None, isolate=False):
        """ Updates the visibility of specified plot. """
        if isolate:  # If a run is isolated, set visibility of all other runs to False
            for run in self.run_list:
                if run.filename == file:
                    run.visibility = True
                else:
                    run.visibility = False
        else:  # If no runs are isolated set all visibilities to True
            for run in self.run_list:
                run.visibility = True

        self.notify(RUN_DATA_CHANGED)

    def open_save_session(self, run_list):
        self.run_list = run_list
        for run in run_list:
            file_root = os.path.split(run.filename)[1]
            self.update_file_list(file_root, run.filename)
            self.current_formats[run.filename] = run.f_formats
        self.notify(RUN_LIST_CHANGED)
        self.notify(RUN_DATA_CHANGED)

    def notify(self, signal):
        """ Calls the update() function in any controller registered with the passed in signal. """
        for controller in self.observers[signal]:
            if 'update' in dir(controller):
                print('Notifying {} of {}'.format(str(controller), self.debugging_signals[signal]))
                controller.update(signal)

    def write_file(self, old_filename=None, new_filename=None, checked_items=None):
        pass


class RunData:
    """ Stores all data relevant to a run.
        Required Parameters:
            filename : file path for the data to be used for this run.
            f_format : dictionary containing (at least):
                - Histogram titles for the file
                - Number of header rows for the file
                - Histograms to be used in calculating asymmetry [hist_one, hist_two]
                - Good bins 1 and 2, the initial and final bins for calculating asymmetry
                - Background 1 and 2, the initial and final bins for calculating background
                - Size of the time bins in the file (in µs)
            visibility : bool that will determine if this run is plotted
            color : color of the run on the plots

        Instance Variables (self.):
            [Parameters passed in]
            asymmetry : the full asymmetry calculated from the user specified histograms
            uncertainty : the full uncertainty array calculated from user specified histograms

        Public Methods:
            bin_data(self, final_bin_size, begin_time, end_time, slider_moving) : Returns binned asymmetry, time and
                uncertainty arrays.
            calculate_fft(bin_size, asymmetry, times) : Returns smoothed frequencies and magnitudes for plotting.
    """
    def __init__(self, filename=None, f_format=None, visibility=True, color=None):
        """Initialize a RunData object based on filename and format"""
        self.f_formats = f_format
        self.visibility = visibility
        self.color = color
        self.filename = filename

        self.histogram_data = self.retrieve_histogram_data()

        self.uncertainty = self.calculate_uncertainty(hist_one=self.f_formats['CalcHists'][0],
                                                      hist_two=self.f_formats['CalcHists'][1])
        bkg_one, bkg_two = self.calculate_background_radiation(hist_one=self.f_formats['CalcHists'][0],
                                                               hist_two=self.f_formats['CalcHists'][1])
        self.asymmetry = self.calculate_asymmetry(hist_one=self.f_formats['CalcHists'][0],
                                                  hist_two=self.f_formats['CalcHists'][1],
                                                  bkg_one=bkg_one, bkg_two=bkg_two)
        del self.histogram_data

    def __bool__(self):
        return self.visibility

    def retrieve_histogram_data(self, specific_hist=None):
        """ Retrieves histogram data from a BEAMS formatted file. """
        histogram_data = BeamsUtility.get_histograms(self.filename, int(self.f_formats['HeaderRows']))
        histogram_data.columns = self.f_formats['HistTitles']

        if not specific_hist:
            return histogram_data
        else:
            return histogram_data[specific_hist]

    def calculate_uncertainty(self, hist_one=None, hist_two=None):
        """ Calculates the uncertainty based on histograms. """
        d_front = np.sqrt(self.histogram_data[hist_two])
        d_back = np.sqrt(self.histogram_data[hist_one])
        uncertainty = np.array(np.sqrt(np.power((2*self.histogram_data[hist_one] /
                                                 np.power(self.histogram_data[hist_two] +
                                                          self.histogram_data[hist_one], 2)*d_front), 2) +
                                       np.power((2*self.histogram_data[hist_two] /
                                                 np.power(self.histogram_data[hist_two] +
                                                          self.histogram_data[hist_one], 2)*d_back), 2)))
        np.nan_to_num(uncertainty, copy=False)
        return uncertainty

    def calculate_background_radiation(self, hist_one=None, hist_two=None):
        """ Calculates the background radiation based on histogram data before positrons are being detected. """
        # Get the portion of histogram before positrons from muon decay are being detected
        background = self.histogram_data.loc[
                     int(self.f_formats['BkgdOne'][hist_one]):int(self.f_formats['BkgdTwo'][hist_one]), hist_one].values
        bkg_one = np.mean(background)  # Find mean on new array

        background = self.histogram_data.loc[
                     int(self.f_formats['BkgdOne'][hist_two]):int(self.f_formats['BkgdTwo'][hist_two]), hist_two].values
        bkg_two = np.mean(background)

        del background
        return [bkg_one, bkg_two]

    def calculate_asymmetry(self, hist_one=None, hist_two=None, bkg_one=None, bkg_two=None):
        """ Calculate asymmetry based on histograms. """
        # We want to ensure the start and ends of the arrays match, while staying in 'Good' area.
        start_bin = int(self.f_formats['GoodBinOne'][hist_one])
        if start_bin < int(self.f_formats['GoodBinOne'][hist_two]):
            start_bin = int(self.f_formats['GoodBinOne'][hist_two])

        end_bin = int(self.f_formats['GoodBinTwo'][hist_one])
        if end_bin > int(self.f_formats['GoodBinTwo'][hist_two]):
            end_bin = int(self.f_formats['GoodBinTwo'][hist_two])

        asymmetry = ((self.histogram_data.loc[start_bin:end_bin, hist_one] - bkg_one) -
                     (self.histogram_data.loc[start_bin:end_bin, hist_two] - bkg_two)) / \
                    ((self.histogram_data.loc[start_bin:end_bin, hist_two] - bkg_two) +
                     (self.histogram_data.loc[start_bin:end_bin, hist_one] - bkg_one))
        asymmetry.fillna(0.0, inplace=True)
        return asymmetry

    @staticmethod
    def calculate_fft(bin_size, asymmetry, times):
        """ Calculates fast fourier transform on asymmetry. """
        n = len(asymmetry)
        k = np.arange(n)
        frequencies = k / (n * bin_size / 1000)
        frequencies = frequencies[range(int(n/2))]
        y_values = np.fft.fft([asymmetry, times]) / n
        y_values = abs(y_values[0, range(int(n/2))])
        y_values[0] = 0

        # Calculate the spline for the graph
        x_smooth = np.linspace(frequencies.min(), frequencies.max(), 300)
        np.insert(x_smooth, 0, 0)

        y_smooth = sp.UnivariateSpline(frequencies, y_values)
        y_smooth.set_smoothing_factor(0)
        y_smooth = y_smooth(x_smooth)
        return [x_smooth, y_smooth]

    def bin_data(self, final_bin_size=None, begin_time=None, end_time=None, slider_moving=False):
        """ Bins the asymmetry based on user specified bin size. """
        # Get the initial and new bin sizes in micro-seconds
        bin_full = float(self.f_formats['binsize'])/1000
        bin_binned = float(final_bin_size)/1000

        # Based on the chosen x values we can single out an area of the data we are going to bin
        # Section of full array that is of interest [initial_bin:final_bin]
        initial_bin = int(np.floor(begin_time / bin_full))

        # Determine how large the bins and binned arrays will be so we can pre-allocate them (much faster).
        binned_indices_per_bin = int(np.floor(bin_binned/bin_full))
        binned_indices_total = int(np.floor((float(end_time)-float(begin_time))/bin_binned))

        # Pre-allocate Asymmetry
        binned_asymmetry = np.empty(binned_indices_total)

        # Create the Time Array
        binned_time = [begin_time + (index * bin_binned) for index in np.arange(binned_indices_total)]

        binned_bins = initial_bin
        if slider_moving:  # If slider is moving we won't calculate the uncertainty
            binned_uncertainty = []
            
            for new_index in range(binned_indices_total):
                # Takes the mean of one full section of the area and stores it in one bin.
                binned_asymmetry[new_index] = np.mean(self.asymmetry[binned_bins:(binned_bins+binned_indices_per_bin)])
                binned_bins += binned_indices_per_bin

        else:  # If slider is moving we will pre-allocate it here with np.empty()
            binned_uncertainty = np.empty(binned_indices_total)
            
            for new_index in range(binned_indices_total):
                binned_asymmetry[new_index] = np.mean(self.asymmetry[binned_bins:(binned_bins+binned_indices_per_bin)])
                binned_uncertainty[new_index] = np.sqrt(np.sum([u**2 for u in self.uncertainty[binned_bins:(binned_bins
                                                + binned_indices_per_bin)]]))/binned_indices_per_bin
                binned_bins += binned_indices_per_bin

        return [binned_asymmetry, binned_time, binned_uncertainty]