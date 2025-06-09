
"""
Last update: 16/05/2025

file name: SISMO.py

Description:
This file contains the SISMO class, used to calculate features the same way the HDAS class does it.
This class is a child class of the HDAS class
"""

from preprocessing.HDAS import HDAS
import obspy
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
from data.scripts.get_filenames import get_filenames

import multiprocessing as mp
import warnings

class SISMO(HDAS):

    def __init__(self, network, sensor, channel, starttime, endtime,
                 detrend = False, windowing = False, merge_method = 0, merge_fill_value = None, 
                 cpus = 2, data_path = "data/involcan/mseed", verbose=False):
   
        # Get the filenames to read according to the starttime and endtime
        start_day = starttime.replace(hour=0, minute=0, second=0) - timedelta(days=1)
        filenames = [data_path.rstrip('/') + '/' + file for file in get_filenames(network, sensor, channel, start_day, endtime)]

        assert len(filenames) > 0, "No data files in the selected time period"
        
        self.existing_files = filenames

        # Initialize values
        self.windowing = windowing
        self.detrend = detrend # This detrend method is independent from the window by window demeaning when calculating FFTs
        self.Coherent_noise_removed = False
        self.merge_method = merge_method
        self.merge_fill_value = merge_fill_value
        self.verbose = verbose

        # Fixed values for consistency with HDAS
        self.nsens = 1
        self.dx = -1
        self.sps = [0]

        # CPUs for parallelization
        self.cpus = cpus
        assert type(cpus) == int and cpus > 0, "Select a valid number of cpus"
        assert cpus <= mp.cpu_count(), "Specified number of CPUs is larger than available."

        # Determine initial starttime and endtime based on found files to read
        day = int(filenames[0][-3:])
        year = int(filenames[0][-8:-4])
        self.stime = datetime(year, 1, 1) + timedelta(days=day - 1)
        day = int(filenames[-1][-3:])
        year = int(filenames[-1][-8:-4])
        self.etime = datetime(year, 1, 1) + timedelta(days=day)

        # Read files in parallel
        self.read_files_in_parallel(filenames)

        # Get the metadata of the trace
        self.srate = self.tr.stats.sampling_rate
        self.dt = self.tr.stats.delta

        self.fmax = self.srate / 2
        self.fmin = 0

        self.cutT(starttime, endtime)
        if self.detrend:
            self.tr.detrend(self.detrend,) # Detrend following the specified method
            if self.verbose: print(f"Trend removed from trace via {self.detrend}")    

        dd = self.tr.data.reshape(1, -1)
        dd = np.nan_to_num(dd)
        self.da = dd.astype(float)
        self.xpos = np.arange(self.nsens) * self.dx
        self.nsamp = self.tr.stats.npts
        self.trel = np.arange(self.nsamp) * self.dt

        # Extra info
        self.stime = self.tr.stats.starttime
        self.etime = self.tr.stats.endtime
        self.network = self.tr.stats.network
        self.sensor = self.tr.stats.station
        self.channel = self.tr.stats.channel

    def process_file(self, filename):
        """
        Method for processing a file individually.
        """
        try:
            if self.verbose:
                print(f"Reading file: {filename}")
            st = obspy.read(filename)  # Leer el archivo usando obspy
            return st
        except FileNotFoundError:
            print(f"File '{filename}' not found. It will be skipped.")
            return None

    def read_files_in_parallel(self, filenames):
        """
        Read the files in parallel using ThreadPoolExecutor.
        """
        total_traces = 0
        total_points = 0
        ST = obspy.Stream()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.process_file, filename): filename for filename in filenames}

            for future in concurrent.futures.as_completed(futures):
                st = future.result()
                if st is not None:
                    for tr in st:
                        total_traces += 1
                        total_points += tr.stats.npts
                        ST.append(tr)
            if self.verbose: print(f"Total number of traces: {total_traces}")

            # Merge all stream traces
            ST.merge(method = self.merge_method, fill_value = self.merge_fill_value)

        print(ST)
        assert len(ST) == 1, "Number of traces in stream should be 1"
        tr = ST[0]

        # Warn about filled values
        filled_points = tr.stats.npts - total_points
        if filled_points > 0:
            warnings.warn(f"{filled_points} values filled as {self.merge_fill_value}.")

        self.tr = tr
        return

    def cutT(self, starttime=None, endtime=None):
        if starttime!=None:
            starttimeUTC = obspy.UTCDateTime(starttime)
        else: starttimeUTC = None

        if endtime!=None:
            endtimeUTC   = obspy.UTCDateTime(endtime)
        else: endtimeUTC = None

        if self.verbose: print(f"Cutting trend from {starttime} to {endtime}")

        self.tr.trim(
            starttime = starttimeUTC,
            endtime   = endtimeUTC)
        
        self.nsamp = self.tr.stats.npts

        self.da = np.reshape(self.tr.data, (1,self.nsamp))
        self.trel = np.arange(self.nsamp) * self.dt
        self.stime = starttime
        self.etime = endtime
        return
    
    def plot_seismogram(self, outfile, ylim = None, save = True):
        import matplotlib.pyplot as plt

        import matplotlib.dates as mdates
        assert len(self.tr) > 0, "No data to plot"

        fig, ax = plt.subplots(figsize=(10,4))
        if ylim !=None:
            plt.ylim(ylim[0], ylim[1])

        times_mpl = self.tr.times(type = 'matplotlib')
        ax.plot(times_mpl, self.tr, label=self.tr.stats.channel,
                color='black')
        ax.set_xlim(times_mpl[0], times_mpl[-1])
        ax.set_xlabel("UTC Time")

        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

        plt.title(self.sensor)
        plt.legend(loc='upper left')
        if save:
            plt.savefig(outfile)
            print(f"Plot saved at {outfile}")

        return fig
    
    def plot_fft(self, window_id, outfile, ylim=None, save=True):
        import matplotlib.pyplot as plt
        assert len(self.tr) > 0, "No data to plot"

        fig, ax = plt.subplots(figsize=(10,4))
        if ylim !=None:
            plt.ylim(ylim[0], ylim[1])

        x = np.linspace(self.fmin, self.fmax,  self.fft.shape[2])
        y = self.fft[0]
        t_delta = timedelta(seconds= self.window_shift)
        first_window = timedelta(seconds=self.window_size)

        ax.bar(x, y[window_id], 0.1,
               label = f"{self.channel}: {self.stime + first_window + t_delta*(window_id)}")

        ax.set_xlabel("Frequency (Hz)")
        ax.set_xlim(x[0]-1, x[-1]+1)

        plt.title(self.sensor)
        plt.legend(loc='upper right')
        if save:
            plt.savefig(outfile)
            print(f"Plot saved at {outfile}")

        return fig 


    def energy_check(self):
        """Verify the conservation of energy"""
        # Time domain
        centered_signal = []
        for window_id in range(self.n_windows):
            window_data = self.get_window_data(0, window_id)
            window_data = window_data - np.mean(window_data)
            centered_signal.append(window_data)
        centered_signal = np.array(centered_signal)

        # Frequency domain
        FFTs=self.fft[0]
        FFT_points = FFTs.shape[-1]

        E_t = np.sum(centered_signal**2)
        E_f = np.sum(FFTs**2)/FFT_points

        return E_t, E_f
    

if __name__=='__main__':

    network = 'C7'
    sensor  = 'PPMA'
    channel = 'HHE'

    starttime  = datetime(2021, 9, 14, 0, 0, 0)
    endtime    = datetime(2021, 9, 15, 0, 0, 0)

    S = SISMO(network, sensor, channel, starttime, endtime,
              verbose=False, detrend=None, windowing = False)

    S.set_windows(3600)
    FFT_points = int(S.points_per_window * 1.0)
    S.fft_bin(FFT_points)
    
    E_t_14, E_f_14 = S.energy_check()

    starttime  = datetime(2021, 9, 19, 0, 0, 0)
    endtime    = datetime(2021, 9, 20, 0, 0, 0)

    S = SISMO(network, sensor, channel, starttime, endtime,
            verbose=False, detrend=None, windowing = False)

    S.set_windows(3600)
    FFT_points = int(S.points_per_window * 1.0)
    S.fft_bin(FFT_points)

    print(f"FFT points: {FFT_points}")

    E_t_19, E_f_19 = S.energy_check()

    print(f"Energía 14 Sept en el dominio del tiempo:       {E_t_14}")
    print(f"Energía 19 Sept en el dominio del tiempo:       {E_t_19}")
    print()
    print(f"Energía 14 Sept en el dominio de la frecuencia:       {E_f_14}")
    print(f"Energía 19 Sept en el dominio de la frecuencia:       {E_f_19}")

    print(S.tr.stats)