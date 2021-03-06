from dataclasses import dataclass
from dateutil import parser
import numpy 
import scipy.special.cython_special
from scipy.interpolate import BSpline
from scipy import signal
import scipy
import soundfile as sf
import xlrd
from PySide2.QtCore import QThread, QObject, Signal, Slot                            

# CALIBRATION
ROW_OFFSET = 5
SHEET_NO = 1
WINDOWS = {"Tukey" : signal.tukey, "Hamming" : signal.hamming, "Hann" : signal.hann, "Boxcar" : signal.boxcar, "Blackman" : signal.blackman} # TODO fix parameters for each type of window

class Interrupt(Exception):
    pass

class Signals(QObject):
    progress = Signal(tuple)
    centroids_signal = Signal(list)

# Helper function
#function taken from https://stackoverflow.com/questions/54032515/spectral-centroid-of-numpy-array
def spectral_centroid(x, samplerate = 44100):
    magnitudes = numpy.abs(numpy.fft.rfft(x))
    length = len(x)
    freqs = numpy.abs(numpy.fft.fftfreq(length, 1.0/samplerate)[:length//2+1])
    magnitudes = magnitudes[:length//2+1]
    return numpy.sum(magnitudes*freqs) / numpy.sum(magnitudes)

# Logic for converting blood glucose levels into soundfiles
class Model(QThread):

    def __init__(self, chosen_filename, sample_rate, buffer_size,
                window_size, is_wavetable, 
                window_type, amt_output, output_filename = "", parent = None):
        QThread.__init__(self)

        self.filename = chosen_filename
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.window_size = window_size
        self.is_wavetable = is_wavetable
        self.window_type = window_type
        self.amt_output = amt_output
        self.output_filename = output_filename

        self.signals = Signals()
        self.signals.progress.connect(parent.update_progressbar)
        self.signals.centroids_signal.connect(parent.update_centroids)

    def run(self):
        self.window = WINDOWS[self.window_type](self.buffer_size, self.window_size if self.window_type == "Tukey" else None) #window function, to smoothen buffer TODO make selectable
        try:
            self.update_progressbar((5, "Opening datafile"))

            self.sheet = xlrd.open_workbook(self.filename).sheet_by_index(SHEET_NO) 
            self.update_progressbar((10, "Parsing data"))

            self.times, self.values = self.parse_data(self.sheet)
            self.update_progressbar((15, "Creating spline"))

            self.spl = BSpline(self.times, self.values, k = 1)
            self.update_progressbar((20, "Extracting output"))

            self.progress = 20
            self.extract_output(self.spl)
            self.update_progressbar((100, "Done"))
        except Interrupt:
            return 

    def update_progressbar(self, args):
        if self.isInterruptionRequested():
            raise (Interrupt())
        self.signals.progress.emit(args)

    def parse_data(self, sheet):
        amt_data = sheet.nrows - ROW_OFFSET
        base_time = 0
        times = []
        values = []
        for row in range(amt_data):
            ### read and interpret data.
            date_string = sheet.cell_value(rowx = ROW_OFFSET + row, colx = 0)
            glucose_level = sheet.cell_value(rowx = ROW_OFFSET + row, colx = 1)

            date = parser.parse(date_string)
            values.append(glucose_level)

            if base_time == 0:
                base_time = date
            times.append((int)((date-base_time).total_seconds()/60))
        return times, values

    ### output extraction
    def extract_output(self, spl):
        centroids = list()
        progress_division = (100-self.progress)/(self.amt_output*3) 
        for sample_index in range(0, self.amt_output):
            self.progress += progress_division 
            self.update_progressbar((self.progress, "Processing file {} out of {}".format(sample_index+1, self.amt_output)))

            sample = []
            for x in range(self.buffer_size*sample_index, self.buffer_size*(sample_index+1)):
                sample.append(spl(x))
            sample = [(x-min(sample)) for x in sample]
            sample = [ 2*(x/(max(sample)-min(sample))-0.5) for x in sample] #normalize and center sound

            self.progress += progress_division 
            self.update_progressbar((self.progress, None))

            for ind, w_sample in enumerate(self.window):
                sample[ind] = sample[ind]*w_sample

            centroids.append(spectral_centroid(sample, self.sample_rate)) #prints spectral centroids (before formatting as wavetable but after windowing!)
            self.signals.centroids_signal.emit(centroids)

            if self.is_wavetable: #SuperCollider wavetable format
                for ind, c_sample in enumerate(sample):
                    if ind % 2 == 0:
                        sample[ind] = 2*sample[ind] - sample[ind+1]
                    else:
                        sample[ind] = sample[ind] - sample[ind-1]

            self.progress += progress_division 
            self.update_progressbar((self.progress, None))

            sf.write(self.output_filename.format(sample_index+1), sample, self.sample_rate) 
