"""
Last update: 25/10/2024

file name: HDAS.py

Description:
This file contains the code for the HDAS class.
This class is used to read the data from the DAS sensors and extract useful features from the signals
"""


import numpy as np
import datetime
from scipy.signal import butter, sosfilt, spectrogram
from math import ceil
from os.path import basename
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import antropy as ant
from scipy.signal import periodogram, welch
import librosa.display
from features.base import logfbank 
from features.base import delta
from scipy import signal


from HDAS_File_Open import Load_2D_Data_bin
import concurrent.futures
import os
import multiprocessing as mp



class HDAS:
    
    def __init__(self, dir, filenames, facx=-1, dectype='simple',
                 windowing = False,
                 cpus = 2, plot=False, verbose=False):
        # Inicialización de los parámetros de la clase
        self.verbose = verbose
        self.plot = plot
        self.sensor = 'DAS'
        self.channel = ''
        self.dir = dir
        self.filenames = filenames
        self.facx = facx
        self.dectype = dectype

        self.windowing = windowing
        self.Trend_removed = False
        self.Coherent_noise_removed = False

        # CPUs for parallelization
        self.cpus = cpus
        assert type(cpus)==int and cpus >0, "Select a valid number of cpus"
        assert cpus <= mp.cpu_count(), "Specified number of CPUs is larger than available."

        mats = []
        existing_files = []  # Lista para almacenar la existencia de los archivos

        # Lectura paralela de los archivos
        self.read_files_in_parallel(mats, existing_files)

        # Combinar todas las matrices leídas
        self.da = np.hstack(tuple(mats))
        self.da = self.da.astype('float32')

        if facx > 0:
            self.dx = self.dx * facx
            self.nsens = self.da.shape[0]

        self.xpos = np.arange(self.nsens) * self.dx

        self.nsamp = self.da.shape[1]
        self.trel = np.arange(self.nsamp) * self.dt

        """
        Calculating the tabs takes a long time and it is only used for plotting
        """
        self.tabs = [None]
        if plot:
            self.tabs = [self.stime + datetime.timedelta(milliseconds=int(i * self.dt * 1000)) for i in range(self.nsamp)]

        self.etime = self.stime + datetime.timedelta(seconds=self.nsamp * self.dt)

        if verbose:
            print("Original size (x,t) : ", self.da.shape)

        # Añadir la lista de existencia de archivos al diccionario
        self.existing_files = existing_files

    def process_file(self, index, file_path):
        """
        Método para procesar un archivo individual.
        index: índice del archivo para mantener el orden.
        """
        try:
            # Mostrar mensaje del archivo que se está leyendo
            if self.verbose:
                print(f"Reading file: {file_path}")
            
            # Cargar los datos del archivo
            dd, header = Load_2D_Data_bin(file_path)
            dd = np.nan_to_num(dd)
            return index, dd, header, '1'  # Retornar el índice, la matriz de datos, el header y '1' como indicador de éxito
        except FileNotFoundError:
            print(f"El archivo '{file_path}' no se encontró. Se omitirá.")
            return index, None, None, '0'  # Retornar el índice y '0' si el archivo no fue encontrado

    def read_files_in_parallel(self, mats, existing_files):
        """
        Método que realiza la lectura paralela de archivos utilizando ThreadPoolExecutor.
        """
        # Primer archivo (fuera del paralelo para inicializar variables dependientes del header)
        if self.verbose:
            print("Reading file:", self.filenames[0])

        first_file_path = os.path.join(self.dir, self.filenames[0])
        dd, header = Load_2D_Data_bin(first_file_path)
        dd = np.nan_to_num(dd)

        if self.facx > 0:
            dd = self._decimateX(dd, self.facx, self.dectype)

        mats.append(dd)
        existing_files.append('1')  # Indicar que el primer archivo existe

        # Leer metadatos del primer archivo
        self.nsens = dd.shape[0]
        self.dx = header[1]
        self.srate = header[6] / header[15] / header[98]
        self.dt = 1. / self.srate
        self.sps = np.arange(0, self.nsens)

        ff = basename(self.filenames[0])
        YY = int(ff[0:4])
        MM = int(ff[5:7])
        DD = int(ff[8:10])
        HH = int(ff[11:13])
        MI = int(ff[14:16])
        SS = int(ff[17:19])

        self.stime = datetime.datetime(YY, MM, DD, HH, MI, SS)

        self.fmax = self.srate / 2
        self.fmin = 0

        # Lista de rutas completas para los archivos restantes (excepto el primero)
        file_paths = [os.path.join(self.dir, filename) for filename in self.filenames[1:]]

        # Crear una lista vacía para almacenar los resultados temporales
        temp_results = [None] * len(file_paths)

        # Lectura en paralelo de los archivos restantes
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_file, i, file_paths[i]) for i in range(len(file_paths))]

            for future in concurrent.futures.as_completed(futures):
                index, dd, header, file_exists = future.result()

                # Insertar el resultado en la posición correspondiente
                temp_results[index] = (dd, header, file_exists)

        # Procesar los resultados en el orden correcto
        for dd, header, file_exists in temp_results:
            if file_exists == '1':
                if self.facx > 0:
                    dd = self._decimateX(dd, self.facx, self.dectype)
                mats.append(dd)
            existing_files.append(file_exists)


    def _decimateX(self, dd, facx, dectype):
        # Function for internal use only
        if self.plot:
            self.tabs = [self.stime + datetime.timedelta(milliseconds=int(i * self.dt * 1000)) for i in range(self.nsamp)]

        if dectype == 'simple':
            return dd[::facx, :]

        elif dectype == 'median':
            newsens = int(self.nsens / facx)
            newdd = np.zeros((newsens, self.nsamp), dtype='float32')
            for i in range(newsens):
                ss = dd[i * facx:(i + 1) * facx, :]
                newdd[i, :] = np.median(ss, 0)

            return newdd

    def cutX(self, x1, x2):
        # Cut a spatial range
        # x1,x2: lower and upper limits (in m) of the distance along the cable

        i1 = int((x1 / self.dx))
        i2 = int((x2 / self.dx))
        self.da = self.da[i1:i2, :]
        self.nsens = self.da.shape[0]
        self.xpos = x1 + np.arange(self.nsens) * self.dx
        self.sps = (self.xpos / self.dx).astype(int)
        
        if self.verbose:
            print("Cut along X (x,t) : ", self.da.shape)

    def decimateX(self, facx, dectype):
        # Spatial decimation
        # facx: spatial decimation factor (-1=no decimation)
        # dectype: type of spatial decimation (if used):
        #          simple: stack between adjacent traces
        #          median: median between adjacent traces

        if dectype == 'simple:':
            self.da = self.da[::facx, :]
            self.xpos = self.xpos[::facx]

        elif dectype == 'median':
            newsens = int(self.nsens / facx)
            newda = np.zeros((newsens, self.nsamp), dtype='float32')
            for i in range(newsens):
                ss = self.da[i * facx:(i + 1) * facx, :]
                newda[i, :] = np.median(ss, 0)

            self.da = newda

        self.dx = self.dx * facx
        self.nsens = self.da.shape[0]

        if dectype == 'simple':
            self.xpos = self.xpos[0] + np.arange(self.nsens) * self.dx
        elif dectype == 'median':
            self.xpos = self.xpos[0] + np.arange(self.nsens) * self.dx + (self.dx * facx / 2)

        if self.verbose:
            print("Decimate along X (x,t) : ", self.da.shape)

    @staticmethod
    def _removeTrend(xx, dr):
        """
        xx = np.arange(self.nsamp)
        dr = self.da[i, :]
        """
        try:
            po = np.polyfit(xx, dr, 1)
        except:
            print(dr)
            exit(1)
        mo = np.polyval(po, xx)

        return dr - mo


    def removeTrend(self, cpus = 4):
        assert type(cpus)==int and cpus > 0, "Select a valid number of cpus"
        assert cpus <= mp.cpu_count(), "Specified number of CPUs is larger than available."
        if self.verbose: print(f"Initializing multiprocessing pool for {len(self.sps)} tasks and {cpus} cpus...")

        xx = np.arange(self.nsamp)
        pool = mp.Pool(cpus)
        tasks = [(xx, self.da[i, :] ) for i in range(self.da.shape[0])]
        
        if self.verbose: print(f"Removing Trend ...")
        result = pool.starmap(self._removeTrend, tasks)
        pool.close() 
        pool.join()

        self.da = np.array(result)

        self.Trend_removed = True

        return

    def removeCoherentNoise(self, method='median'):
        # Remove coherent synchronous noise from all the traces
        # The trace used for filtering is computed by doing the median
        # of all the individual traces
        #
        # method: filtering type:
        #         simple: subtracts the median from individual traces
        #         fit: compute the best fit correction factor befor subtracting the median

        if self.verbose: print("Removing coherent noise ...")
        md = np.median(self.da, 0) # This is the slow part of this process

        if method == 'simple':
            for i in range(self.da.shape[1]):
                self.da[:, i] = self.da[:, i] - md[i]

        elif method == 'fit':
            den = np.sum(md * md)
            for i in range(self.da.shape[0]):
                dd = self.da[i, :]
                am = np.sum(dd * md) / den
                self.da[i, :] = dd - am * md

        self.Coherent_noise_removed = method

    def cutT(self, t1, t2):
        # Cut a temporal range
        # t1,t2: lower and upper limits (in s) of the time window to cut

        j1 = int(t1 / self.dt)
        j2 = int(t2 / self.dt)
        self.da = self.da[:, j1:j2]

        self.nsamp = self.da.shape[1]

        self.etime = self.stime + datetime.timedelta(seconds=self.nsamp * self.dt)
        self.stime = self.stime + datetime.timedelta(seconds=t1)

        self.trel = np.arange(self.nsamp) * self.dt
        self.tabs = [self.stime + datetime.timedelta(seconds=i * self.dt) for i in range(self.nsamp)]

        if self.verbose:
            print("Cut along T (x,t) : ", self.da.shape)
    
    def len(self):
        # Returns the temporal length of the traces

        return self.dt*self.nsamp

    def decimateT(self, fact):
        # Temporal decimation
        # fact: decimation factor
        # !!! low-pass filtering below Nyquist is not perfmed here

        self.da = self.da[:, ::fact]
        self.dt = self.dt * fact
        self.srate = self.srate / fact

        self.nsamp = self.da.shape[1]

        self.etime = self.stime + datetime.timedelta(seconds=self.nsamp * self.dt)

        self.trel = np.arange(self.nsamp) * self.dt
        self.tabs = [self.stime + datetime.timedelta(seconds=i * self.dt) for i in range(self.nsamp)]

        if self.verbose:
            print("Decimate along T (x,t) : ", self.da.shape)
            print("Fmax ", self.fmax, " New Nyquist  ", self.srate / 2)

    def filter(self, f1, f2):
        # Band-pass filtering of individual traces
        # Butterworth filter with 4 poles is used
        # f1,f2: lower and upper frequency of the filter

        if self.verbose:
            print("Filter")

        sos = butter(4, [f1, f2], 'bandpass', fs=1. / self.dt, output='sos')

        for i in range(self.da.shape[0]):
            dd = self.da[i, :]
            dd = sosfilt(sos, dd)
            self.da[i, :] = dd.astype(int)
        self.da = self.da.astype(float)
        self.fmax = f2
        self.fmin = f1

    def normalize(self, type='rms_c'):
        # Trace normalization
        # type, type of normalization
        #       rms: normalization of the whole DAS image by its RMS
        #       rms_c: normalization of individual traces by their RMS
        #       mad: normalization of the whole DAS image by its MAD (Median Absolute Deviation)
        #       mad_c: normalization of individual traces by their MAD

        if self.verbose:
            print("Normalize ", type)

        if type == 'rms':
            self.da = self.da / np.std(self.da)

        elif type == 'rms_c':
            rms = np.std(self.da, 1)
            for i in range(len(rms)):
                self.da[i, :] = self.da[i, :] / rms[i]

        elif type == 'mad':
            mad = np.median(np.abs(self.da))
            self.da = 0.5 * self.da / mad

        elif type == 'mad_c':
            for i in range(self.nsens):
                mad = np.median(np.abs(self.da[i, :]))
                self.da[i, :] = 0.5 * self.da[i, :] / mad

    def mute(self, perc=95):
        # Muting of noisy traces based on their RMS
        # perc: percentile of RMS above which mute (set to zero) a trace
        # 0 means all the traces muted, 100 no trace is muted

        st = np.std(self.da, axis=1)
        thr = np.percentile(st,perc)
        idx = (st>=thr)
        self.da[idx,:] = 0.

    def check(self):
        # Check the object for debugging purposes
        # writing some of the relevant paramaeters

        print(">>> CHECK HFD5DAS")
        print("NSENS ", self.nsens)
        print("NSAMP ", self.nsamp)
        print("shape ", self.da.shape)
        print("dx,len ", self.dx, self.dx * self.nsens)
        print("xpos ", self.xpos[0], self.xpos[-1])
        print("dt,len ", self.dt, self.dt * self.nsamp)
        print("srate ", self.srate)
        print("stime ", self.stime)
        print("etime ", self.etime)
        print("len ", self.etime - self.stime)
        print("trel ", self.trel[0], self.trel[-1])
        # print("tabs ", self.tabs[0], self.tabs[-1])
        print("fmin ", self.fmin)
        print("fmax ", self.fmax)

    def checkHTML(self):
        # Same as check but in HTML format

        print(">>> CHECK HFD5DAS</br>")
        print("NSENS ", self.nsens,"</br>")
        print("NSAMP ", self.nsamp,"</br>")
        print("shape ", self.da.shape,"</br>")
        print("dx,len ", self.dx, self.dx * self.nsens,"</br>")
        print("xpos ", self.xpos[0], self.xpos[-1],"</br>")
        print("dt,len ", self.dt, self.dt * self.nsamp,"</br>")
        print("srate ", self.srate,"</br>")
        print("stime ", self.stime,"</br>")
        print("etime ", self.etime,"</br>")
        print("len ", self.etime - self.stime,"</br>")
        print("trel ", self.trel[0], self.trel[-1],"</br>")
        print("tabs ", self.tabs[0], self.tabs[-1],"</br>")
        print("fmax ", self.fmax,"</br>")

    def plot(self, outfile, palette='seismic', vv=2.0, figsize=None, vel=None, dpi=1200):
        # Plot DAS data as an image
        # outfile: name of the output file (with the correct extension)
        # palette: a matplotlib compatible palette name
        # vv: palette range
        # figsize: figure size in format (X,Y)
        # vel: array of apparent velocities to plot as a reference curves

        if self.verbose:
            print("Plot", flush=True)

        gx, gy = np.meshgrid(self.tabs, self.xpos / 1000.)

        if figsize == None:
            plt.figure()
        else:
            plt.figure(figsize=figsize)

        plt.pcolormesh(gx, gy, self.da, vmin=-vv, vmax=vv, cmap=palette, shading='auto')

        plt.ylabel('Distance (km)')
        plt.xlabel('Time (s)')
        myFmt = mdates.DateFormatter('%H:%M:%S')
        plt.gca().xaxis.set_major_formatter(myFmt)
        # plt.xticks(rotation=90)

        # Vel
        if vel != None:
            dmax = self.nsens * self.dx
            for v in vel:
                tv = dmax / v
                t1 = self.stime + datetime.timedelta(seconds=tv)
                t2 = self.etime - datetime.timedelta(seconds=tv)
                plt.plot([self.stime, t1], [self.xpos[0], self.xpos[-1]], 'k:')
                plt.plot([self.etime, t2], [self.xpos[0], self.xpos[-1]], 'k:')

        plt.grid(axis='x', color='k', linestyle=':', linewidth=2)

        if self.verbose:
            print("Writing Image", flush=True)

        plt.savefig(outfile, dpi=dpi)
        plt.close('all')
        
    def plot_seismogram(self, outfile, sp, palette='seismic', vv=2.0, ylim=None,  figsize=None):     
        # Plot strain-varation signal of the 1D signal in spatian point sp
        # outfile: geerated file name
        # sp: spatial point under analysis
        if figsize == None:
            plt.figure()
        else:
            plt.figure(figsize=figsize)
        if ylim !=None:
            plt.ylim(ylim[0], ylim[1])
        plt.ylabel(r'Strain Variation ($\mu\epsilon$)')
        plt.xlabel('Time (s)')
        labels = [self.tabs[0], self.tabs[ceil(self.nsamp/3)], self.tabs[2*ceil(self.nsamp/3)], self.tabs[-1]]
        plt.xticks(labels)
        myFmt = mdates.DateFormatter('%H:%M:%S')
        plt.gca().xaxis.set_major_formatter(myFmt)
        plt.plot(self.tabs, self.da[sp,:], 'k')
        plt.suptitle('Earthquake in sp = ' + str(sp*10) + ' m')
        plt.title('Bandwith: ' + str(self.fmin) + '-' + str(self.fmax) + 'Hz')
        plt.savefig(outfile + '_sp' + str(sp*10) + '_' + str(self.fmin) + 'to' + str(self.fmax) + 'Hz.png', dpi=1200)
        plt.close('all')


    def plot_spectrogram(self, outfile, sp, nfft, maxfreq, txttitle, palette='seismic', vv=2.0, figsize=None):
        # Plot frquency spectrogram of the 1D signal in spatian point sp
        # outfile: geerated file name
        # sp: spatial point under analysis
        # nfft: number of points used in the spectrogram analysis
        # maxfreq: maximum frequency of interest in the spectrogram figure (only visual purpose)
        # txttitle: event name 
        f, t, Sxx = spectrogram(self.da[sp,:], self.srate, nfft=nfft)
        freq_interest=[i for i in range(len(f)) if f[i] < maxfreq]
        plt.pcolormesh(t, f[freq_interest], Sxx[0:len(freq_interest),:] ,cmap='seismic', shading ='auto')
        plt.ylabel('Frequency (Hz)',fontsize=10)
        plt.xlabel('Time (s)',fontsize=10)
        plt.title('Spectrogram ' + str(self.fmin) + '-' + str(self.fmax) + 'Hz, sp=' + str(sp*10), fontsize=10 )   
        cbar = plt.colorbar()
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        cbar.ax.tick_params(labelsize=10)
        plt.suptitle(txttitle)
        plt.savefig(outfile + '_sp' + str(sp*10) + '_' + str(self.fmin) + 'to' + str(self.fmax) + 'Hz.png', dpi=1200)
        plt.close('all')

    def plotsismo(self, outfile, sismot, sismodat, palette='seismic', vv=2.0, figsize=None, vel=None):
        # Plot DAS data as an image adding a reference seismogram
        # outfile: name of the output file (with the correct extension)
        # sismot: array of times of the seismogram
        # sismodat: array of amplitudes of the seismogram
        # palette: a matplotlib compatible palette name
        # vv: palette range
        # figsize: figure size in format (X,Y)
        # vel: array of apparent velocities to plot as a reference curves

        if self.verbose:
            print("Plot", flush=True)

        print(self.xpos[0], self.xpos[-1])
        gx, gy = np.meshgrid(self.tabs, self.xpos / 1000.)

        if figsize == None:
            plt.figure()
        else:
            plt.figure(figsize=figsize)

        f, (a0, a1) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [4, 1]})

        a0.pcolormesh(gx, gy, self.da, vmin=-vv, vmax=vv, cmap=palette, shading='auto')

        a0.set_ylabel('Distance (km)')
        # a0.set_xlabel('Time (s)')
        # myFmt = mdates.DateFormatter('%H:%M:%S')
        # a0.xaxis.set_major_formatter(myFmt)
        # a0.xaxis.set_label_position('top')
        # plt.xticks(rotation=90)
        a0.set_xticklabels([])

        # Vel
        if vel != None:
            dmax = self.nsens * self.dx
            for v in vel:
                tv = dmax / v
                t1 = self.stime + datetime.timedelta(seconds=tv)
                t2 = self.etime - datetime.timedelta(seconds=tv)
                a0.plot([self.stime, t1], [self.xpos[0], self.xpos[-1]], 'k:')
                a0.plot([self.etime, t2], [self.xpos[0], self.xpos[-1]], 'k:')

        a0.grid(axis='x', color='k', linestyle=':', linewidth=2)

        a1.plot(sismot, sismodat, 'k')
        a1.set_xlim([sismot[0], sismot[-1]])
        a1.set_ylim([-1.1, 1.1])
        a1.set_xlabel('Time (s)')
        myFmt = mdates.DateFormatter('%H:%M:%S')
        a1.xaxis.set_major_formatter(myFmt)

        if self.verbose:
            print("Writing Image", flush=True)

        plt.savefig(outfile, dpi=1200)
        plt.close('all')

    def plot_mel_spectrogram(self, n_mels=128, target_max_frequency=20):
        
        # Define the duration of each window and overlapping
        hop_length = int((self.window_size - self.window_shift) * self.srate)
    
        # Calculate the spectrogram of mel
        mel_spectrogram = librosa.feature.melspectrogram(y=self.da[0, :], sr=self.srate, n_mels=n_mels, hop_length=hop_length)
    
        # Convert to decibels
        mel_spectrogram_db = librosa.power_to_db(mel_spectrogram, ref=np.max)
    
        # Adjust the number of pixels on the y-axis to display only the range 0 to 20 Hz.
        mel_freqs = librosa.mel_frequencies(n_mels=n_mels, fmax=self.srate/2)
        specified_bins = np.where(mel_freqs <= target_max_frequency)[0][-1] + 1
        mel_spectrogram_db = mel_spectrogram_db[:specified_bins, :]
    
        # Create an array of times for the x-axis
        times_x = np.arange(0, len(mel_spectrogram_db[0]), 1) * hop_length / self.srate
    
        # Format for the x-axis of the graphs
        times_x = [self.stime + datetime.timedelta(seconds=t) for t in times_x]
    
        # Display mel spectrogram with adjusted range on y-axis
        plt.figure(figsize=(12, 8))
        librosa.display.specshow(mel_spectrogram_db, x_axis='time', y_axis='mel', sr=self.srate, hop_length=hop_length, cmap='viridis', x_coords=times_x, y_coords=np.linspace(0, target_max_frequency, mel_spectrogram_db.shape[0]))
        
        
        #To represent the red line equivalent to the earthquake:
        
        # Calculate the number of points in each window and overlapping
        points_per_window = int(self.window_size * self.srate)
        shift_points = int(self.window_shift * self.srate)
    
        # Create an array of times for the x-axis
        times = np.arange(0, self.nsamp - points_per_window + 1, shift_points) * self.dt
        
        # Format for the x-axis of the graphs
        times = [self.stime + datetime.timedelta(seconds=t) for t in times]

    def dump(self, filename):
        # Dump the DAS data matrix in a Numpy compressed file

        if self.verbose:
            print("Dumping data matrix ", self.da.shape)
        np.savez_compressed(filename, da=self.da)
        
                
    def set_windows(self, window_size, shift=None):
        self.window_size = window_size
        if shift == None: self.window_shift = window_size
        else: self.window_shift = shift
        

        self.points_per_window = int(self.window_size * self.srate)
        self.shift_points = int(self.window_shift * self.srate)

        overlap_points = self.points_per_window - self.shift_points

        # self.n_windows = self.nsamp // self.shift_points
        self.n_windows = (self.nsamp - overlap_points) \
                        // (self.points_per_window - overlap_points)

        self.window_start_index = np.arange(0, self.nsamp - self.points_per_window + 1, self.shift_points)
        
        return




    def fft_10bin(self, fft_points=128):
        # Number of points in each window
        points_per_window = int(self.window_size * self.srate)
    
        # Number of overlapping points
        shift_points = int(self.window_shift * self.srate)
    
        # Array of times for x-axis
        times_x = np.arange(0, self.nsamp - points_per_window + 1, shift_points) * self.dt
    
        # Format for the x-axis of the graphs
        times_x = [self.stime + datetime.timedelta(seconds=t) for t in times_x]
    
        # We initialize the matrix to store FFT results.
        matrix_fft = np.zeros((len(times_x), fft_points // 2 + 1))
    
        # We initialize vectors to accumulate frequency values.
        val_for_fbin = [np.zeros(len(times_x)) for _ in range(10)]
    
        # Iterate over the overlapping windows and perform the Fourier transform.
        for i, index in enumerate(range(0, self.nsamp - points_per_window + 1, shift_points)):
            # We define the start and end indexes for the current window.
            start_index = index
            end_index = start_index + points_per_window
    
            # We extract the data from the current window
            data_current_window = self.da[:, start_index:end_index]
    
            # We calculate the frequencies and the FFT of the current window.
            freq, spectrum = np.fft.fftfreq(fft_points, d=1/self.srate), np.fft.fft(data_current_window, n=fft_points, axis=1)
           
            # We select only the positive frequencies
            freq_positive = freq >= 0
            
            # We calculate the variations of magnitude in frequency (absolute value).
            magnitude_variations_fft = np.abs(spectrum[:, freq_positive][0])
    
            # We make sure that magnitude_variations_fft has the right dimension
            magnitude_variations_fft = np.pad(magnitude_variations_fft, (0, matrix_fft.shape[1] - len(magnitude_variations_fft)))
    
            # We update accumulated vectors for the 10 selected bins.
            for bin_index in range(2, 12):
                val_for_fbin[bin_index - 2][i] = magnitude_variations_fft[bin_index]
    
        # Calculate the width of each bin in terms of frequency.  
        width_bin = float(50 / 63)
        
        # We plot the 10 vectors in separate graphs.

        for bin_index, values_over_time in enumerate(val_for_fbin):
            start_freq = (bin_index + 2) * width_bin
            end_freq = (bin_index + 3) * width_bin
            plt.figure(figsize=(4, 3))
            plt.plot(times_x, values_over_time)
            plt.title(f'Frecuencia Bin {bin_index + 2} - {start_freq:.3f} Hz a {end_freq:.3f} Hz\nVariación a lo largo del tiempo')
            plt.xlabel('Tiempo')
            plt.ylabel('Magnitud')
    
            # We customize the x-axis format
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
            plt.grid()
            plt.show()
    
        # We plot the 10 vectors on the same plot
        plt.figure(figsize=(10, 6))
        for bin_index, values_over_time in enumerate(val_for_fbin):
            start_freq = (bin_index + 2) * width_bin
            end_freq = (bin_index + 3) * width_bin
            plt.plot(times_x, values_over_time, label=f'Frecuencia Bin {bin_index + 2} - {start_freq:.3f} Hz a {end_freq:.3f} Hz')
        plt.title('Variación a lo largo del tiempo para Bins Seleccionados')
        plt.xlabel('Tiempo')
        plt.ylabel('Magnitud')
    
        # We customize the x-axis format
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
        plt.legend()
        plt.grid()
        plt.show()
        
        
    def get_window_data(self, sp, window_id):
        start_index = self.window_start_index[window_id]
        end_index = start_index + self.points_per_window
        window_data = self.da[sp, start_index:end_index] # shape: (sps, n_windows)
        return window_data

    """
    Run the calculations for just one window and one spatial point
    """  
    def _calculate_hjorth_parameters(self, sp, window_id):
        window_data = self.get_window_data(sp, window_id)

        mobility, complexity = ant.hjorth_params(window_data)
        variance = np.var(window_data)

        return mobility, complexity, variance

    """
    Run parallel calculations for all sps and windows
    """
    def calculate_hjorth_parameters(self):
        self.mobility_vals      = np.zeros((len(self.sps), self.n_windows))
        self.complexity_vals    = np.zeros((len(self.sps), self.n_windows))
        self.variance_vals      = np.zeros((len(self.sps), self.n_windows))

        # Prepare paralellization tasks
        tasks = [(sp, window_id)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._calculate_hjorth_parameters, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.mobility_vals[sp, window_id]   = results[result_id][0]
                self.complexity_vals[sp, window_id] = results[result_id][1]
                self.variance_vals[sp, window_id]   = results[result_id][2]
                result_id += 1

        # Calculate derivatives
        self.deltas_mob          = delta(self.mobility_vals , 2   )
        self.deltas_deltas_mob   = delta(self.deltas_mob , 2      )  
        self.deltas_com          = delta(self.complexity_vals , 2 )
        self.deltas_deltas_com   = delta(self.deltas_com , 2      )  
        self.deltas_var          = delta(self.variance_vals , 2   )
        self.deltas_deltas_var   = delta(self.deltas_var , 2      )  
        return

    def _LFB(self, sp, window_id, hop_length, n_LFB):
        window_data = self.get_window_data(sp, window_id)

        LFB = np.float32(logfbank(1+window_data, samplerate=self.srate,
                                  winlen=self.window_size, winstep=self.window_shift,
                                  nfilt=n_LFB, nfft=hop_length, lowfreq=0, highfreq=None,
                                  preemph=0.97))

        return LFB

    def LFB(self, hop_length=512, n_LFB=16):
        self.LFB_matrix_vals    = np.zeros((len(self.sps), self.n_windows, n_LFB)) 
        self.deltas_LFB         = np.zeros((len(self.sps), self.n_windows, n_LFB)) 
        self.deltas_deltas_LFB  = np.zeros((len(self.sps), self.n_windows, n_LFB)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id, hop_length, n_LFB)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._LFB, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.LFB_matrix_vals[sp, window_id]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_LFB[sp]         = delta(self.LFB_matrix_vals[sp], 2)
            self.deltas_deltas_LFB[sp]  = delta(self.deltas_LFB[sp], 2)
        return
        

    def _spectral_entropy(self, sp, window_id, method, nperseg, normalize):
        window_data = self.get_window_data(sp, window_id)
    
        # Choose between fft or Welch
        if method == 'fft':
            _, psd = periodogram(window_data, fs=self.srate)
        elif method == 'welch':
            _, psd = welch(window_data, fs=self.srate, nperseg=nperseg)

        # Calculate the probability distribution function of psd
        prob_psd = psd/sum(psd)
        # Calculate spectral entropy
        entropy = -np.sum(prob_psd * np.log2(prob_psd + 1e-10))  # Agregar pequeño valor para evitar log(0)
        # Normalize if necessary
        if normalize:
            entropy /= np.log2(psd.size)
        
        return entropy

    def spectral_entropy(self, method='welch', nperseg=None, normalize=True):
        
        self.entropy_vals = np.zeros((len(self.sps), self.n_windows)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id, method, nperseg, normalize)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._spectral_entropy, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.entropy_vals[sp, window_id]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        self.deltas_ent         = delta(self.entropy_vals, 2)
        self.deltas_deltas_ent  = delta(self.deltas_ent, 2)
        return
    
    def _scal_log_esp_power(self, sp, window_id, method, nperseg, normalize):
        window_data = self.get_window_data(sp, window_id)

        # Choose between fft or Welch
        if method == 'fft':
            _, psd = periodogram(window_data, fs=self.srate)
        elif method == 'welch':
            _, psd = welch(window_data, fs=self.srate, nperseg=nperseg)

        # Calculate spectral entropy
        entropy = -np.sum(psd * np.log2(psd + 1e-10))  # Agregar pequeño valor para evitar log(0)

        # Normalize if necessary
        if normalize:
            entropy /= np.log2(psd.size)

        return entropy

    def scal_log_esp_power(self, method='welch', nperseg=None, normalize=True):
        
        self.scal_log_esp_power_vals = np.zeros((len(self.sps), self.n_windows)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id, method, nperseg, normalize)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._scal_log_esp_power, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.scal_log_esp_power_vals[sp, window_id]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        self.deltas_scal_log_esp_power         = delta(self.scal_log_esp_power_vals, 2)
        self.deltas_deltas_scal_log_esp_power  = delta(self.deltas_scal_log_esp_power, 2)
        return
    
    def _approximate_entropy(self, sp, window_id, order, metric):
        window_data = self.get_window_data(sp, window_id)

        approx_entropy = ant.app_entropy(window_data, order=order, metric=metric)
        return approx_entropy

    def approximate_entropy(self, order=2, metric='chebyshev'):
        self.approx_entropy_vals = np.zeros((len(self.sps), self.n_windows)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id, order, metric)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._approximate_entropy, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.approx_entropy_vals[sp, window_id]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        self.deltas_ent_app         = delta(self.approx_entropy_vals, 2)
        self.deltas_deltas_ent_app  = delta(self.deltas_ent_app, 2)

    def _calculate_top_fft_amplitudes_and_frequencies(self, sp, window_id, num_top):
        window_data = self.get_window_data(sp, window_id)
        
        # Aplicar la ventana de Hamming a la copia de los datos
        data_window_with_hamming_fft = np.copy(window_data)
        hamming_window = np.hamming(self.points_per_window)
        data_window_with_hamming_fft *= hamming_window 
        # Calculate FFT of the signal
        fft_vals = np.fft.fft(data_window_with_hamming_fft, n=256)
        # Calculate amplitude spectrum
        amplitude_spectrum = np.abs(fft_vals)[:len(fft_vals)//2]
        # Find the indices of the top num_top amplitudes
        top_indices = np.argsort(amplitude_spectrum)[::-1][:num_top]
        # Get the corresponding amplitudes
        top_amplitudes = amplitude_spectrum[top_indices]
        top_frequencies = np.fft.fftfreq(len(amplitude_spectrum), d=1/self.srate)[top_indices]

        return top_amplitudes, top_frequencies            
        
    def calculate_top_fft_amplitudes_and_frequencies(self, num_top=3):
        self.top_fft_amplitudes_vals  = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.top_fft_frequencies_vals = np.zeros((len(self.sps), self.n_windows, num_top)) 

        self.deltas_fft_amp = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.deltas_deltas_fft_amp = np.zeros((len(self.sps), self.n_windows, num_top)) 

        self.deltas_fft_frec = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.deltas_deltas_fft_frec = np.zeros((len(self.sps), self.n_windows, num_top)) 
        
        
        # Prepare paralellization tasks
        tasks = [(sp, window_id, num_top)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._calculate_top_fft_amplitudes_and_frequencies, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.top_fft_amplitudes_vals[sp, window_id]    = results[result_id][0]
                self.top_fft_frequencies_vals[sp, window_id]   = results[result_id][1]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_fft_amp[sp]         = delta(self.top_fft_amplitudes_vals[sp], 2)
            self.deltas_deltas_fft_amp[sp]  = delta(self.deltas_fft_amp[sp], 2)

            self.deltas_fft_frec[sp]         = delta(self.top_fft_frequencies_vals[sp], 2)
            self.deltas_deltas_fft_frec[sp]  = delta(self.deltas_fft_frec[sp], 2)
        return

    def _percentiles(self, sp, window_id):
        window_data = self.get_window_data(sp, window_id)

        # Calculate cumulative sum
        cumsum = np.cumsum(np.abs(window_data))

        # Calculate percentiles
        percentile_20_val = np.percentile(cumsum, 20)
        percentile_50_val = np.percentile(cumsum, 50)
        percentile_80_val = np.percentile(cumsum, 80)

        return percentile_20_val, percentile_50_val, percentile_80_val

    def percentiles(self):
        self.percentiles_matrix = np.zeros((len(self.sps), self.n_windows, 3)) 
        self.deltas_perc        = np.zeros((len(self.sps), self.n_windows, 3)) 
        self.deltas_deltas_perc = np.zeros((len(self.sps), self.n_windows, 3)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._percentiles, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.percentiles_matrix[sp, window_id, :]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_perc[sp]         = delta(self.percentiles_matrix[sp], 2)
            self.deltas_deltas_perc[sp]  = delta(self.deltas_perc[sp], 2)
        return

    def _lpc(self, sp, window_id, order):
        window_data = self.get_window_data(sp, window_id)

        lpc_coefficients = librosa.lpc(window_data, order=order)
        # Discard the first coefficient (always 1)
        lpc_coefficients = lpc_coefficients[1:]

        return lpc_coefficients
            
    def lpc(self, order=8):
        self.lpc_matrix         = np.zeros((len(self.sps), self.n_windows, order)) 
        self.deltas_LPC         = np.zeros((len(self.sps), self.n_windows, order)) 
        self.deltas_deltas_LPC  = np.zeros((len(self.sps), self.n_windows, order)) 

        # Prepare paralellization tasks
        tasks = [(sp, window_id, order)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._lpc, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.lpc_matrix[sp, window_id, :]   = results[result_id]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_LPC[sp]         = delta(self.lpc_matrix[sp], 2)
            self.deltas_deltas_LPC[sp]  = delta(self.deltas_LPC[sp], 2)
        return


    def lpc_5(self, sp, coefficient_number=6, order=8):
            
        # Calculate the number of points in each window
        points_per_window = int(self.window_size * self.srate)
        shift_points = int(self.window_shift * self.srate)
        self.fifth_lpc_coefficients = []
    
        # Iterate over the windows and calculate the fifth LPC coefficient
        for i, index in enumerate(range(0, self.nsamp - points_per_window + 1, shift_points)):
            start_index = index
            end_index = start_index + points_per_window
            data_current_window = self.da[:, start_index:end_index]
    
            # Calculate LPC coefficients using librosa.lpc
            lpc_librosa = librosa.lpc(data_current_window[sp], order=order)
    
            # Append the fifth LPC coefficient to the list
            self.fifth_lpc_coefficients.append(lpc_librosa[coefficient_number])
    
        
    def _calculate_top_lpc_amplitudes_and_frequencies(self, sp, window_id, num_top):
        window_data = self.get_window_data(sp, window_id)
        
        # Aplicar la ventana de Hamming a la copia de los datos
        data_window_with_hamming = np.copy(window_data)
        hamming_window = np.hamming(self.points_per_window)
        data_window_with_hamming *= hamming_window 
        
        # Calculate LPC coefficients
        lpc_coeffs = librosa.lpc(data_window_with_hamming, order=8)
        
        # Generate LPC filter using LPC coefficients
        w, h = signal.freqz(1, lpc_coeffs, 256, fs=self.srate)   
        
        # Calculate LPC spectrum
        lpc_spectrum = np.abs(h)
        
        # Find the indices of the top num_top amplitudes
        top_indices = np.argsort(lpc_spectrum)[::-1][:num_top]
        
        # Get the corresponding amplitudes and frequencies
        top_amplitudes = lpc_spectrum[top_indices]
        
        # Calculate the frequency corresponding to each top index using fftfreq
        fft_freqs = np.fft.fftfreq(len(lpc_spectrum), d=1/self.srate)
        top_frequencies = fft_freqs[top_indices]

        return top_amplitudes, top_frequencies    

    def calculate_top_lpc_amplitudes_and_frequencies(self, num_top=3):
        self.top_lpc_amplitudes_vals  = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.top_lpc_frequencies_vals = np.zeros((len(self.sps), self.n_windows, num_top)) 

        self.deltas_lpc_amp = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.deltas_deltas_lpc_amp = np.zeros((len(self.sps), self.n_windows, num_top)) 

        self.deltas_lpc_frec = np.zeros((len(self.sps), self.n_windows, num_top)) 
        self.deltas_deltas_lpc_frec = np.zeros((len(self.sps), self.n_windows, num_top)) 
        
        
        # Prepare paralellization tasks
        tasks = [(sp, window_id, num_top)
            for sp in range(len(self.sps))
            for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._calculate_top_lpc_amplitudes_and_frequencies, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.top_lpc_amplitudes_vals[sp, window_id]    = results[result_id][0]
                self.top_lpc_frequencies_vals[sp, window_id]   = results[result_id][1]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_lpc_amp[sp]         = delta(self.top_lpc_amplitudes_vals[sp], 2)
            self.deltas_deltas_lpc_amp[sp]  = delta(self.deltas_lpc_amp[sp], 2)

            self.deltas_lpc_frec[sp]         = delta(self.top_lpc_frequencies_vals[sp], 2)
            self.deltas_deltas_lpc_frec[sp]  = delta(self.deltas_lpc_frec[sp], 2)
        return
    
    """
    Run the calculations for just one window and one spatial point
    """
    def _fft_bin(self, sp, window_id, fft_points = None):
        window_data = self.get_window_data(sp, window_id)
        # Demean the trace of the window
        window_data = window_data - np.mean(window_data)

        windowing = self.windowing
        if windowing != False:
            window_data = window_data*windowing(self.points_per_window)

        freq, spectrum = np.fft.fftfreq(fft_points, d=1/self.srate), np.fft.fft(window_data, n=fft_points)
        freq_positive = freq >= 0
        FFTs = np.abs(spectrum[freq_positive])

        return FFTs


    """
    Run parallel calculations for all sps and windows
    """
    def fft_bin(self, fft_points=256):

        if fft_points == 'Auto': fft_points = self.points_per_window

        self.fft = np.zeros((len(self.sps), self.n_windows, fft_points//2))
        self.deltas_fft = np.zeros((len(self.sps), self.n_windows, fft_points//2))
        self.deltas_deltas_fft = np.zeros((len(self.sps), self.n_windows, fft_points//2))

        tasks = [(sp, window_id, fft_points)
                 for sp in range(len(self.sps))
                 for window_id in range(self.n_windows)]

        pool = mp.Pool(self.cpus)
        results = pool.starmap(self._fft_bin, tasks)

        # Compile the results
        result_id = 0
        for sp in range(len(self.sps)):
            for window_id in range(self.n_windows):
                self.fft[sp, window_id, : ] = results[result_id]
                result_id += 1

        # Calculate derivatives
        for sp in range(len(self.sps)):
            self.deltas_fft[sp]         = delta(self.fft[sp], 2)
            self.deltas_deltas_fft[sp]  = delta(self.deltas_fft[sp], 2)  

        return

    if __name__ == '__main__':
        path = "./data/DAS/2021/11/20"
        filename = "2021_11_20_00h01m37s_HDAS_2Dmap_Strain.bin"

        from datetime import datetime
        starttime = datetime(2021, 11, 26, 0, 0)
        endtime   = datetime(2021, 11, 26, 0, 20)
        from data_check import get_filenames
        filepaths,  _, _ = get_filenames(starttime, endtime, 'DAS', '')

        from HDAS import HDAS

        # print(path)
        H = HDAS(".", filepaths, cpus=10, verbose = True)       
        # H.cutX(100*H.dx,  110*H.dx)
        H.check()
        H.set_windows(4.0, 4.0)
        # H.fft_128bin()
        # H.calculate_hjorth_parameters()
        # H.LFB()
        # H.spectral_entropy()
        # H.scal_log_esp_power()
        # H.approximate_entropy()
        # H.calculate_top_fft_amplitudes_and_frequencies()
        # H.percentiles()
        # H.lpc()
        # H.calculate_top_lpc_amplitudes_and_frequencies()
        H.calculate_top_fft_amplitudes_and_frequencies()
        print(H.top_fft_amplitudes_vals)
        print(H.top_fft_frequencies_vals)

        
        # H = HDAS(path, [filename], verbose = True)        
        # H.removeCoherentNoise(method='fit')


        # print(H1.da == H2.da)

        # H.plot_seismogram("digivolcan/figures/test_das", sp = 2)
        # H.filter(1.5, 20)

        # H.check()

        # print(f" SPs: {(H.xpos / H.dx).astype(int)}")

        # H.window_size = 4.0
        # H.window_shift = 3.5
        # H.calculate_hjorth_parameters(0)
