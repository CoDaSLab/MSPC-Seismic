import os
import re
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy.io import savemat, loadmat
from collections import defaultdict
import json

from preprocessing.SISMO import SISMO
from preprocessing.sismo import *
from data.scripts.get_filenames import get_filenames

def calculate_fft_rt(starttime, endtime, network, stations, channels=['HHE', 'HHN', 'HHZ'], 
                    window_size=10, window_shift=None, detrend=False, windowing=False, fft_points=256, 
                    merge_method=0, merge_fill_value = None, pad_fill_value=False,
                    data_path="data/involcan/mseed", cpus=1, verbose=False, save=False, 
                    save_path="data/involcan/features"):
    """
    Extracts FFT coefficients and derivatives from seismic signals over a specified time range 
    for multiple stations and channels. This function is meant for use in real time monitoring.

    Parameters
    ----------
        starttime (datetime): Start time for data extraction (UTC).
        endtime (datetime): End time for data extraction (UTC).
        network (str): Seismic network identifier.
        stations (str): Station codes.
        channels (list of str): List of channels (default: ['HHE', 'HHN', 'HHZ']).
        window_size (int): Time window size in seconds (default: 10).
        window_shift (int): Interval between the start of windows in seconds (default: window_size).
        detrend (bool): Whether to remove linear trend from signals (default: False).
        windowing: Windowing function. If False, no function is applied (default: False).
        fft_points (int or 'auto'): Number of FFT points. If set to `'auto'`, uses the number of 
            points per window.
        merge_method (int): Method used for merging waveform segments (see documentation for the 
            `Trace` class from the ObsPy module).
        merge_fill_value (any): Value used to fill gaps when merging if applicable
            (see documentation for the `Stream.merge` method from the ObsPy module).
        pad_fill_value (any): Value used to fill gaps at the start or end of the time range if
            the signal is contained within the given time range. If False, no padding is applied.
        data_path (str): Directory path containing seismic data (default: "data/involcan/mseed").
        cpus (int): Number of CPU cores to use for processing (default: 1).
        verbose (bool): Whether to print detailed messages during feature extraction (default: False).
        save (bool): Whether to save the features in a .mat file (default: False).
        save_path (str): Path to the directory where features are stored (default: "data/involcan/features").

    Returns
    -------
        features (dict): A dictionary containing the following extracted features:
            - 'ffts' (numpy array): FFT coefficients for each time window.
            - 'deltas_ffts' (numpy array): First-order differences of FFTs.
            - 'deltas_deltas_ffts' (numpy array): Second-order differences of FFTs.
            - 'missing_rates' (numpy array): Proportion of missing samples in each time window.
            - 'obs_labels' (list): Observation (row) labels, the corresponding end time for each window.
            - 'var_labels' (list): Variable (column) labels, the corresponding frequency for each column.
            - 'var_classes' (list): Variable (column) classes, the corresponding channel for each column.

    """
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    if not isinstance(stations, list):
        stations = [stations]
    if not isinstance(channels, list):
        channels = [channels]

    stations = sorted(stations)
    channels = sorted(channels)

    time0 = datetime.now()
    if verbose:
        print(f"Extracting features...")

    if window_shift is None:
        window_shift = window_size

    features = {}
    filenames = get_filenames("C7", stations, channels, starttime.datetime, endtime.datetime)

    data = read_files(filenames,
    process_file=lambda f: process_file(f, verbose=True, stime=starttime, etime=endtime),
    verbose=False,)

    Sxxs, times, freqs = calculate_spectrogram(data, window_length, shift, n_bins,)

    X, freqs_label, station_class, channel_class = unfold_spectrogram(Sxxs, freqs, stations, channels)

    timeUTC = np.arange(starttime, endtime, timedelta(seconds=shift), dtype='datetime64[s]').tolist()
    timeUTC=[x.strftime('%Y-%m-%dT%H:%M:%SZ') for x in timeUTC ]

    features["streams"] =  data["streams"]
    features["times_label"] = timeUTC
    features["spectrogram_unfold"] = X
    features["station_class"] = station_class
    features["channel_class"] = channel_class
    features["freqs_label"] = freqs_label
    # features["missing_rates"] = [] # Calculate missing rate per window in calculate_spectrogrma and add here
    features["missing_rates"] = np.zeros(Sxxs.shape[2]) # Calculate missing rate per window in calculate_spectrogrma and add here

    if save:
        file_name = "-".join(stations) + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime.strftime('%Y-%m-%dT%H-%M-%SZ')
        mat_path = os.path.join(save_path, file_name).replace('\\', '/')
        savemat(mat_path, features)

    if verbose:
        print(f"Extracted FFT coefficients. Time taken: {datetime.now() - time0}")

    return features


def delete_fft(path, station, starttime, endtime, verbose = False):
    """
    Deletes files in a directory that match a station name and fall within a date range.

    Parameters
    ----------
        path (str): Path to the directory containing the files.
        station (str): Name of the station.
        starttime (str or datetime): The start date of the range (UTC).
        endtime (str or datetime): The end date of the range (UTC).
    """
    # Convert date strings to datetime objects for comparison
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."
    
    try:
        # Regex pattern to extract station name and dates
        # Example filename: stationname_2025-06-16T09-00-00Z_2025-06-18T11-00-00Z.mat
        pattern = re.compile(rf"^{re.escape(station)}_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z)_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z).*$")

        deleted_files = []

        for filename in os.listdir(path):
            match = pattern.match(filename)
            if match:
                # Extract file's start and end date strings
                file_starttime = match.group(1)
                file_endtime = match.group(2)

                try:
                    # Convert file dates to datetime objects
                    file_starttime = datetime.strptime(file_starttime, '%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc)
                    file_endtime = datetime.strptime(file_endtime, '%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc)

                    # Remove files in the time range
                    if file_starttime >= starttime and file_endtime <= endtime:
                        full_file_path = os.path.join(path, filename)
                        os.remove(full_file_path)
                        deleted_files.append(filename)

                except ValueError:
                    print(f"Warning: Could not parse date from file '{filename}'. Skipping.")

        if verbose:  
            if deleted_files:
                print(f"\nSuccessfully deleted the following files for station '{station}' in the range {starttime} to {endtime}:")
                for f in deleted_files:
                    print(f"- {f}")
            else:
                print(f"\nNo files found to delete for station '{station}' in the range {starttime} to {endtime}.")

    except FileNotFoundError:
        print(f"Error: The directory '{path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def list_fft_files(path, station, starttime, endtime, intersect=False, verbose=False):
    """
    Lists .mat files in a directory that match a station name and fall within a date range.

    Parameters
    ----------
        path (str): Path to the directory containing the files.
        station (str): Name of the station.
        starttime (str or datetime): The start date of the range (UTC).
        endtime (str or datetime): The end date of the range (UTC).
        intersect (bool): Whether to include files that intersect with the date range
            but do not fall completely within the time range.
        verbose (bool): Whether to print information about matched files.

    Returns
    -------
        list: List of matching filenames.
    """
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    pattern = re.compile(rf"^{re.escape(station)}_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z)_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z).*\.mat$")
    matching_files = []

    try:
        for filename in os.listdir(path):
            match = pattern.match(filename)
            if match:
                file_start_str = match.group(1)
                file_end_str = match.group(2)

                try:
                    file_start = datetime.strptime(file_start_str, '%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc)
                    file_end = datetime.strptime(file_end_str, '%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc)

                    if intersect: 
                        if file_start <= endtime and file_end >= starttime:
                            matching_files.append(filename)
                            if verbose:
                                print(f"Matched file: {filename}")
                    else:
                        if file_start >= starttime and file_end <= endtime:
                            matching_files.append(filename)
                            if verbose:
                                print(f"Matched file: {filename}")

                except ValueError:
                    if verbose:
                        print(f"Warning: Skipping file with unparseable dates: {filename}")

        if verbose and not matching_files:
            print(f"\nNo files found for station '{station}' in the range {starttime} to {endtime}.")

    except FileNotFoundError:
        print(f"Error: The directory '{path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return sorted(matching_files)


def find_features(path, stations, starttime, endtime, feature_types:list, additional_matches:dict=None, 
                  max_missing_rate:float=0.1, verbose:bool=False):
    """
    Reads feature files from a given list of stations and time range in the specified path and returns 
    the corresponding features dictionary.

    Parameters
    ----------
    path (str)
        Path to the directory containing the files.
    stations (str)
        Name of the stations.
    starttime (str or datetime)
        The start date of the range (UTC).
    endtime (str or datetime)
        The end date of the range (UTC).
    feature_types (list)
        List of features (e.g. "ffts") to retrieve.
    additional_matches (dict)
        Other parameters that the file needs to match. Default is None.
    max_missing_rate (float)
        Maximum rate of missing values allowed for any station. Default is 0.1.
    verbose (bool)
        Whether to print information about matched files. Default is False.

    Returns
    -------
    dict
        features object (similar to the output of calculate_fft_rt)
    """
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    if isinstance(stations, str):
        stations = [stations]

    time0 = datetime.now()
    
    # Initialize features dictionary
    features_all = {}
    features = {}
    avail_stations = []

    for station in stations:
        features[station] = defaultdict(list)
        if verbose:
            print(f"Searching for features for station {station}...")
        # Find feature files
        files = list_fft_files(path, station, starttime, endtime, intersect=True, verbose=verbose)
        first_match = True
        for file in files:
            # Load file         
            feat = loadmat(os.path.join(path, file), squeeze_me=True)

            # Check additional matches
            match = True
            if additional_matches:
                for key in additional_matches.keys():
                    if 'config' in feat.keys():
                        config = json.loads(feat["config"])
                        if additional_matches[key] != config["features"][key]:
                            match = False
            if match:                
                for key in feature_types:
                    features[station][key].append(feat[key])

                if first_match:
                    features[station]["var_labels"] = feat["var_labels"]
                    features[station]["var_classes"] = feat["var_classes"]
                    first_match = False
                features[station]["obs_labels"].extend(feat["obs_labels"])
                features[station]["missing_rates"].extend(feat["missing_rates"])
                
        if files and not first_match:
            # Filter dates and remove duplicates
            obs = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in features[station]["obs_labels"]]
            obs_idx = [i for i, label in enumerate(obs) if label > starttime and label <= endtime]
            features[station]["obs_labels"] = [label for i, label in enumerate(features[station]["obs_labels"]) if i in obs_idx]
            features[station]["missing_rates"] = [label for i, label in enumerate(features[station]["missing_rates"]) if i in obs_idx]
            features[station]["obs_labels"], unique_idx = np.unique(features[station]["obs_labels"], return_index=True)
            features[station]["missing_rates"] = np.array(features[station]["missing_rates"])[unique_idx]
            
            for key in feature_types:
                features[station][key] = np.vstack(features[station][key])
                features[station][key] = features[station][key][obs_idx, :]
                features[station][key] = features[station][key][unique_idx, :]
            
            if np.mean(features[station]["missing_rates"]) < max_missing_rate:
                avail_stations.append(station)
                if verbose:
                    print(f"Features found for station {station}.")
                    
    if not avail_stations:
        if verbose:
            print("No features available for the given time range.")
        return {}

    # Combine observation labels
    all_obs = sorted(set().union(*[features[st]["obs_labels"] for st in avail_stations]))
    all_obs = np.array(all_obs)
    features_all["obs_labels"] = all_obs

    # Combine missing rates
    mr_blocks = []
    for st in avail_stations:
        st_obs = np.array(features[st]["obs_labels"])
        idx_map = {obs: i for i, obs in enumerate(st_obs)}

        aligned_missing = np.ones(len(all_obs))
        for i, obs in enumerate(all_obs):
            if obs in idx_map:
                aligned_missing[i] = features[st]["missing_rates"][idx_map[obs]]
        if np.mean(aligned_missing) < max_missing_rate:
            mr_blocks.append(aligned_missing.reshape(-1, 1))
        else:
            avail_stations.remove(st)
    features_all["missing_rates"] = np.mean(np.hstack(mr_blocks), axis=1)

    # Combine features
    for key in feature_types:
        station_blocks = []
        for st in avail_stations:
            st_obs = np.array(features[st]["obs_labels"])
            idx_map = {obs: i for i, obs in enumerate(st_obs)}

            data = features[st][key]
            n_var = data.shape[1]
            aligned_data = np.zeros((len(all_obs), n_var))
            for i, obs in enumerate(all_obs):
                if obs in idx_map:
                    aligned_data[i, :] = data[idx_map[obs], :]
            station_blocks.append(aligned_data)

        features_all[key] = np.hstack(station_blocks)

    # Combine variable labels and classes
    all_var_labels = []
    all_var_classes = []
    for st in avail_stations:
        all_var_labels.extend(features[st]["var_labels"])
        all_var_classes.extend([f"{st}.{lbl}" for lbl in features[st]["var_classes"]])
    features_all["var_labels"] = np.array(all_var_labels)
    features_all["var_classes"] = np.array(all_var_classes)

    if verbose:
        print(f"Search complete. Features found for the following stations: {avail_stations}. " \
              f"Time taken: {datetime.now()- time0}")
    
    return features_all
