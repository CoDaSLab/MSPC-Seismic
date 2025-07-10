import os
import re
from datetime import datetime, timedelta
import numpy as np
from scipy.io import savemat

from preprocessing.SISMO import SISMO

def calculate_fft_rt(starttime, endtime, network, sensor, channels=['HHE', 'HHN', 'HHZ'], 
                    window_size=10, window_shift=None, detrend=False, fft_points=256, 
                    merge_method=0, merge_fill_value = None, pad_fill_value=False,
                    data_path="data/involcan/mseed", cpus=1, verbose=False, save=False, 
                    save_path="data/involcan/features"):
    """
    Extracts FFT coefficients and derivatives from seismic signals over a specified time range 
    for multiple sensors and channels. This function is meant for use in real time monitoring.

    Parameters
    ----------
        starttime (datetime): Start time for data extraction.
        endtime (datetime): End time for data extraction.
        network (str): Seismic network identifier.
        sensor (str): Station codes.
        channels (list of str): List of channels (default: ['HHE', 'HHN', 'HHZ']).
        window_size (int): Time window size in seconds (default: 10).
        window_shift (int): Interval between the start of windows in seconds (default: window_size).
        detrend (bool): Whether to remove linear trend from signals (default: False).
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
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    time0 = datetime.now()
    if verbose:
        print(f"Extracting features...")

    if window_shift is None:
        window_shift = window_size

    features = {'ffts': [], 
                'deltas_ffts': [],
                'deltas_deltas_ffts': []}
    
    for channel in channels:
        if verbose:
            print(f"""
                Extracting SISMO features 
                network: {network}, sensor: {sensor}, channel: {channel}
                from {starttime} to {endtime}
                window size: {window_size} s
                window shift: {window_shift} s
                """)

        S = SISMO(
            network, sensor, channel, 
            starttime, endtime, detrend=detrend,
            merge_method=merge_method, merge_fill_value=merge_fill_value,
            pad_fill_value=pad_fill_value, cpus=cpus, data_path=data_path
        )
        if verbose:
            S.check()
        
        # Set window size and overlap
        S.set_windows(window_size, window_shift)

        # Calculate FFT coefficients
        S.fft_bin(fft_points)
        channel_features = {'ffts': np.squeeze(S.fft), 
                            'deltas_ffts': np.squeeze(S.deltas_fft),
                            'deltas_deltas_ffts': np.squeeze(S.deltas_deltas_fft)}

        for key, array in channel_features.items():        
            features[key].append(array)

    # Concatenate features for all channels along the columns
    for key in features.keys():
        if features[key]: 
            features[key] = np.concatenate(features[key], axis=1)
        else:
            features[key] = np.array([])

    # Rate of missing values for every window
    features['missing_rates'] = np.squeeze(S.get_missing_samples(rate=True))

    # Observation labels (window end times)
    n_obs, n_vars = features['ffts'].shape
    window_times = [starttime + timedelta(seconds=window_shift * i + window_size) for i in range(n_obs)]
    features['obs_labels'] = [datetime.strftime(label, '%Y-%m-%dT%H:%M:%SZ') for label in window_times]

    # Variable labels (frequencies)
    n_vars_per_channel = n_vars // len(channels)
    frequencies = np.round(np.linspace(S.fmin, S.fmax, n_vars), 4)
    features['var_labels'] = frequencies.tolist() * len(channels)

    # Variable classes (channels)
    features['var_classes'] = [ch for ch in channels for _ in range(n_vars_per_channel)]

    if verbose:
        print(f"Extracted FFT coefficients. Time taken: {datetime.now() - time0}")

    if save:
        file_name = sensor + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime.strftime('%Y-%m-%dT%H-%M-%SZ')
        mat_path = os.path.join(save_path, file_name).replace('\\', '/')
        savemat(mat_path, features)

    return features


def delete_fft(path, sensor, starttime, endtime, verbose = False):
    """
    Deletes files in a directory that match a sensor name and fall within a date range.

    Parameters
    ----------
        path (str): Path to the directory containing the files.
        sensor (str): Name of the sensor.
        starttime (str or datetime): The start date of the range.
        endtime (str or datetime): The end date of the range.
    """
    # Convert date strings to datetime objects for comparison
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Error: Start date cannot be after end date."
    
    try:
        # Regex pattern to extract sensor name and dates
        # Example filename: sensorname_2025-06-16T09-00-00Z_2025-06-18T11-00-00Z.mat
        pattern = re.compile(rf"^{re.escape(sensor)}_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z)_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z).*$")

        deleted_files = []

        for filename in os.listdir(path):
            match = pattern.match(filename)
            if match:
                # Extract file's start and end date strings
                file_starttime = match.group(1)
                file_endtime = match.group(2)

                try:
                    # Convert file dates to datetime objects
                    file_starttime = datetime.strptime(file_starttime, '%Y-%m-%dT%H-%M-%SZ')
                    file_endtime = datetime.strptime(file_endtime, '%Y-%m-%dT%H-%M-%SZ')

                    # Remove files in the time range
                    if file_starttime >= starttime and file_endtime <= endtime:
                        full_file_path = os.path.join(path, filename)
                        os.remove(full_file_path)
                        deleted_files.append(filename)

                except ValueError:
                    print(f"Warning: Could not parse date from file '{filename}'. Skipping.")

        if verbose:  
            if deleted_files:
                print(f"\nSuccessfully deleted the following files for sensor '{sensor}' in the range {starttime} to {endtime}:")
                for f in deleted_files:
                    print(f"- {f}")
            else:
                print(f"\nNo files found to delete for sensor '{sensor}' in the range {starttime} to {endtime}.")

    except FileNotFoundError:
        print(f"Error: The directory '{path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
