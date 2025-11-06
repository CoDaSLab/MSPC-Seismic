import obspy
from obspy.core import UTCDateTime

from msa.feature_extraction import features
from msa.visualization import plot

import concurrent.futures
from itertools import product
import warnings

import json

import numpy as np
from datetime import datetime, timedelta

# Read paths from configuration file
with open("config.json", 'r') as f:
    config = json.load(f)
data_path = config["paths"]["data"]


def get_filenames(network=None, station=None, channel=None, start_day=None, end_day=None):
    """
    Generate ObsPy-style MiniSEED filenames based on network, station, channel, and date range.

    Parameters
    ----------
    network : str or list of str, optional
        Network code(s), can be comma-separated string or list. Default is '*' (all networks).
    station : str or list of str, optional
        Station code(s), can be comma-separated string or list. Default is '*' (all stations).
    channel : str or list of str, optional
        Channel code(s), can be comma-separated string or list. Default is '*' (all channels).
    start_day : str or datetime, optional
        Start date in 'YYYY-MM-DD' format or as datetime object.
    end_day : str or datetime, optional
        End date in 'YYYY-MM-DD' format or as datetime object.

    Returns
    -------
    filenames : list of str
        List of generated filenames in the format:
        "NET.STA..CHA.D.YYYY.JJJ", where JJJ is the Julian day.
        If no start_day/end_day is given, wildcards '*' are used for date fields.

    Notes
    -----
    - If the date range is provided, filenames are generated for each day within the range.
    - The function handles both single strings and lists for network, station, and channel inputs.
    """

    def parse_list(x):
        if x is None:
            return ['*']
        return x.split(',') if isinstance(x, str) else x

    networks = parse_list(network)
    stations = parse_list(station)
    channels = parse_list(channel)

    filenames = []

    if start_day and end_day:
        try:
            if isinstance(start_day, str):
                start_day = datetime.strptime(start_day, "%Y-%m-%d")
            if isinstance(end_day, str):
                end_day = datetime.strptime(end_day, "%Y-%m-%d")

            current_day = start_day
            while current_day <= end_day:
                year = current_day.year
                jday = current_day.timetuple().tm_yday
                jday_str = f"{jday:03d}"
                year_str = str(year)

                for net, sta, cha in product(networks, stations, channels):
                    filenames.append(f"{net}.{sta}..{cha}.D.{year_str}.{jday_str}")
                current_day += timedelta(days=1)

        except ValueError:
            print("Error: Invalid date format. Please use YYYY-MM-DD.")
            return []

    else:
        for net, sta, cha in product(networks, stations, channels):
            filenames.append(f"{net}.{sta}..{cha}.D.*.*")

    return filenames


def process_file(filename, verbose=False, stime=None, etime=None, demean=True):
    """
    Read a MiniSEED file using ObsPy and return a Stream object.

    Parameters
    ----------
    filename : str
        Name of the file to read. The function prepends `data_path` automatically.
    verbose : bool, optional
        If True, prints messages about the file being read. Default is False.
    stime : UTCDateTime or datetime, optional
        Start time for reading the file. If None, reads from the beginning of the file.
    etime : UTCDateTime or datetime, optional
        End time for reading the file. If None, reads until the end of the file.

    Returns
    -------
    st : obspy.Stream or None
        ObsPy Stream containing the traces from the file. Returns None if the file is not found.

    Notes
    -----
    - If the file contains no data in the specified time range, the entire file is read.
    - FileNotFoundError is caught and a message is printed; the function then returns None.
    """

    # Convert to obspy's UTCDateTime format if necessary
    stime = UTCDateTime(stime)
    etime = UTCDateTime(etime)
    try:
        if verbose:
            print(f"Reading file: {filename}")
        st = obspy.read(f"{data_path}/{filename}", starttime=stime, endtime=etime)
        if len(st) == 0:
            st = obspy.read(f"{data_path}/{filename}")
        if demean == True:
            st.detrend(type="demean")
        return st
    except FileNotFoundError:
        print(f"File '{filename}' not found. It will be skipped.")
        return None



def read_files(
    filenames,
    process_file,
    starttime, endtime, pad_fill_value,

    verbose=False,
    merge_method=0,
    merge_fill_value="interpolate",
):
    """
    Read multiple MiniSEED files in parallel, merge their traces, and return all outputs
    in a dictionary. The tensor preserves the absolute time alignment of ObsPy traces.

    Parameters
    ----------
    filenames : list of str
        List of filenames to read.
    process_file : callable
        Function that reads a single file and returns an obspy.Stream.
    verbose : bool, optional
        If True, prints progress messages and summary information. Default is False.
    merge_method : str, optional
        Method to merge traces in ObsPy Stream.merge(). Default is "interpolate".
    merge_fill_value : int or float, optional
        Value used to fill missing samples when traces have different lengths. Default is 0.

    Returns
    -------
    result : dict
        Dictionary containing:
        - 'X_tensor' : np.ndarray
            3D array (num_stations, num_channels, num_samples) of trace data.
        - 'streams' : np.ndarray
            2D array of shape (num_stations, num_channels), dtype=object.
            Each element is the ObsPy Stream corresponding to that trace (or None if no trace).
        - 'missing_values' : np.ndarray
            Binary 3D array (same shape as 'X_tensor'), 0 = real value, 1 = filled.
        - 'stats' : np.ndarray
            2D array of ObsPy Stats objects (num_stations, num_channels).
        - 'starttime' : obspy.UTCDateTime
            Global start time of all traces.
        - 'endtime' : obspy.UTCDateTime
            Global end time of all traces.
    """
    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    ST = obspy.Stream()

    # Read files in parallel and keep individual Streams
    streams_raw = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file, filename): filename for filename in filenames}
        for future in concurrent.futures.as_completed(futures):
            st = future.result()
            if st is not None:
                ST += st
                streams_raw.append(st)

    if verbose:
        print(f"Total number of traces: {len(ST)}")

    # Merge all traces
    ST.merge(method=merge_method, fill_value=merge_fill_value)

    ST.trim(starttime = starttime, endtime = endtime,
                pad = True, fill_value=pad_fill_value)
    for tr in ST:
        mask = tr.data == pad_fill_value
        if np.any(mask):
            tr.data = np.ma.masked_array(tr.data, mask=mask, fill_value = pad_fill_value)

    if len(ST) == 0:
        raise ValueError(f"No traces found after reading the following files: {filenames}.")

    stations = sorted(set(tr.stats.station for tr in ST))
    channels = sorted(set(tr.stats.channel for tr in ST))

    # Global starttime and endtime
    starttime_global = min(tr.stats.starttime for tr in ST)
    endtime_global = max(tr.stats.endtime for tr in ST)
    dt = ST[0].stats.delta
    npts_total = int(round((endtime_global - starttime_global) / dt)) + 1

    # Initialize arrays
    X_tensor = np.full((len(stations), len(channels), npts_total), pad_fill_value, dtype=float)
    mask_tensor = np.ones((len(stations), len(channels), npts_total), dtype=int)
    stats_array = np.empty((len(stations), len(channels)), dtype=object)
    streams_array = np.empty((len(stations), len(channels)), dtype=object)

    # Fill arrays respecting absolute time and populate streams_array
    for tr in ST:
        i = stations.index(tr.stats.station)
        j = channels.index(tr.stats.channel)
        offset = int(round((tr.stats.starttime - starttime_global) / dt))
        npts = tr.stats.npts
        X_tensor[i, j, offset:offset+npts] = tr.data
        if isinstance(tr.data, np.ma.MaskedArray):
            mask_tensor[i, j, offset:offset+npts] = tr.data.mask
        else:
            mask_tensor[i, j, offset:offset+npts] = 0
        stats_array[i, j] = tr.stats
        # Create a Stream for this single trace
        streams_array[i, j] = obspy.Stream(traces=[tr.copy()])

    result = {
        'X_tensor': X_tensor,
        'streams': streams_array,
        'missing_values': mask_tensor,
        'stats': stats_array,
        'starttime': starttime_global,
        'endtime': endtime_global
    }

    return result

def calculate_spectrogram(data: dict, window_length, shift, n_bins=None, window="blackman", padding="zeros", detrend="linear"):
    """
    Compute spectrograms for all stations and channels in the input data dictionary.

    Parameters
    ----------
    data : dict
        Dictionary returned by `read_files`, containing at least:
        - 'X_tensor' : np.ndarray, shape (num_stations, num_channels, num_samples)
        - 'stats' : np.ndarray of ObsPy Stats objects, shape (num_stations, num_channels)
    window_length : float
        Length of the sliding window in seconds for computing the spectrogram.
    shift : float
        Time shift between consecutive windows in seconds (hop size).
    n_bins : int, optional
        Number of frequency bins for the spectrogram. If None, frequency resolution
        is determined by 1/window_length. Default is None.
    window : str, optional
        Window function to apply to each segment. Default is "blackman".
    padding : str, optional
        Padding method for the signal. Options may include "zeros". Default is "zeros".
    detrend : str, optional
        Method to detrend each segment. Default is "linear".

    Returns
    -------
    Sxxs : np.ndarray
        4D array of shape (num_stations, num_channels, num_time_windows, num_frequency_bins),
        containing the magnitude of the spectrogram for each station and channel.
    times : np.ndarray
        3D array of shape (num_stations, num_channels, num_time_windows),
        containing the time vector for each spectrogram.
    freqs : np.ndarray
        3D array of shape (num_stations, num_channels, num_frequency_bins),
        containing the frequency vector for each spectrogram.

    Notes
    -----
    - The sampling rate is inferred from `data["stats"][0,0].sampling_rate`.
    - The function loops over every station and channel in the data tensor to compute
      individual spectrograms.
    - `Sxxs[i,j,:,:]` corresponds to the spectrogram of station `i`, channel `j`.
    - `times[i,j,:]` and `freqs[i,j,:]` provide the corresponding time and frequency axes.
    """

    X = data["X_tensor"]
    sr = data["stats"][0,0].sampling_rate
    window_samples = int(window_length*sr)
    hop = int(shift*sr)

    start_index = np.arange(0, X.shape[-1] - window_samples + 1, hop)
    end_index = start_index + window_samples


    f_max = sr/2
    f_min = 0

    if n_bins is None:
        df = 1/window_length
    else:
        df = 1/(n_bins/sr)

    Ns =  X.shape[0] # Number of stations
    Nc =  X.shape[1] # Number of channels
    Nt = int(X.shape[2]/hop) # Number of times
    Nf = int((f_max - f_min)/df)+1 # Number of frequencies

    Sxxs  = np.zeros((Ns, Nc, Nf, Nt))
    times = np.zeros((Ns, Nc, Nt))
    freqs = np.zeros((Ns, Nc, Nf))

    N_win = len(start_index)
    missing_rate_window = np.zeros((Ns, Nc, N_win))

    for i in range(Ns): # Loop for every sensor
        for j in range(Nc): # Loop for every channel
            time, freq, Sxx = features.spectrogram(data["X_tensor"][i,j], sr, window_samples, hop, window, padding, detrend, n_bins)
            Sxxs[i,j,:,:] = Sxx[:,1:]
            times[i,j,:]  = time[1:]
            freqs[i,j,:]  = freq
            
            for k in range(N_win):
                missing_rate_window[i,j,k] = np.mean(data["missing_values"][i, j, start_index[k]:end_index[k]])

    return Sxxs, times, freqs, missing_rate_window

def unfold_spectrogram(Sxxs, freqs=None, stations=None, channels=None):
    """
    Unfold a 4D tensor into a 2D array suitable for machine learning or analysis,
    and optionally generate labels for frequencies, stations, and channels.

    Parameters
    ----------
    Sxxs : np.ndarray
        4D array of spectrograms with shape 
        (num_stations, num_channels, num_time_windows, num_frequency_bins), 
        as returned by `calculate_spectrogram`.
    freqs : np.ndarray, optional
        3D array of frequency vectors with shape (num_stations, num_channels, num_frequency_bins),
        as returned by `calculate_spectrogram`. Default is None.
    stations : list of str, optional
        List of station names corresponding to the first dimension of `Sxxs`. Default is None.
    channels : list of str, optional
        List of channel names corresponding to the second dimension of `Sxxs`. Default is None.

    Returns
    -------
    X : np.ndarray
        2D array of shape (num_time_windows*num_stations*num_channels, num_frequency_bins),
        where the spectrograms have been unfolded along the first two dimensions.
    freqs_label : np.ndarray or None
        1D array of frequency labels as strings (e.g., "0.5Hz"), repeated for each station and channel,
        or None if `freqs` is not provided.
    station_class : np.ndarray or None
        1D array of station labels, repeated for each frequency bin and channel,
        or None if `stations` is not provided.
    channel_class : np.ndarray or None
        1D array of channel labels, repeated for each frequency bin and station,
        or None if `channels` is not provided.

    Notes
    -----
    - The function stacks the spectrograms from all stations and channels along the first dimension.
    - This format is convenient for machine learning models or statistical analysis where each
      row corresponds to a single spectrogram vector for one station-channel combination.
    - Frequency, station, and channel labels are optional but useful for tracking metadata.
    """

    X = np.vstack(np.vstack(Sxxs)).T

    Ns = Sxxs.shape[0]
    Nc = Sxxs.shape[1]
    Nf = Sxxs.shape[3]
    freqs_label, station_class, channel_class = None, None, None

    if freqs is not None:
        freqs_label = np.array([f"{round(x, 2)}Hz" for x in freqs[0,0]]*Ns*Nc) # Add for several stations 

    if stations is not None:
        station_class = np.repeat(stations, Nf*Ns)

    if channels is not None:
        channel_class = np.repeat(channels, Nf*Nc)

    return X, freqs_label, station_class, channel_class

if __name__ == "__main__":
    starttime = UTCDateTime(2025, 9, 14, 0)
    endtime = UTCDateTime(2025, 9, 16, 0)

    stations = ["PSAB"]
    channels = ["HHE", "HHN"]

    filenames = get_filenames("C7", stations, channels, starttime.datetime, endtime.datetime)
    print(filenames)

    data = read_files(
        filenames,
        lambda f: process_file(f, verbose=True, stime=starttime, etime=endtime),
        starttime, endtime, 0,
        verbose=True,
    )

    print("Data tensor:", data["X_tensor"].shape)
    print("Number of missing values on each station and channel:\n", np.sum(data["missing_values"], axis=2))

    window_length = 20 # s
    shift = 3600 #s
    n_bins = None
    # window = "blackman"
    # padding = "zeros"
    # detrend = "linear"

    timeUTC = np.arange(starttime, endtime, timedelta(seconds=shift), dtype='datetime64[s]')

    Sxxs, times, freqs, _ = calculate_spectrogram(data, window_length, shift, n_bins,)


    X, freq_label, station_class, channel_class = unfold_spectrogram(Sxxs, freqs, stations, channels)


    i, j = 0,0
    print(times.shape, freqs.shape, Sxxs.shape)
    fig, _ , _ = plot.spectrogram(times[i,j], freqs[i,j], Sxxs[i,j], logscale=True)
    fig.show()

    timeUTC = np.arange(starttime, endtime, timedelta(seconds=shift), dtype='datetime64[s]').tolist()

    timeUTC=[x.strftime('%Y-%m-%dT%H:%M:%SZ') for x in timeUTC ]

    print(timeUTC)
    print(type(timeUTC))

    data["streams"][0,0].plot()
    # input()