import json
import os
import csv
import numpy as np
import numbers
from datetime import datetime, timedelta, timezone
from scipy.io import savemat, loadmat

from preprocessing.fft_rt import calculate_fft_rt, delete_fft, list_fft_files
from monitoring.mspc_rt import mspc, plot_anomalies
from monitoring.NOC import NOC
from collections import defaultdict

def load_config(file_path):
    """
    Loads a JSON configuration file from a given file path.

    Parameters
    ----------
        file_path (str): The path to the JSON configuration file.

    Returns
    -------
        config (dict): A dictionary representing the loaded configuration, or None if an error occurs.
    """
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config


def start_and_end_times(now: datetime, update_frequency: int):
    """
    Returns the two most recent times aligned with an interval (in minutes)
    before the given datetime.

    - If `update_frequency <= 60`: aligned to the current hour (like '*/n * * * *')
    - If `update_frequency > 60`: aligned from midnight (00:00), e.g., every 90 minutes
    
    For example, if the current date and time is 2025-07-09 16:59:03, and
    update_frequency is 5, it returns 2025-07-09 16:50:00 and 2025-07-09 16:55:00.
    """
    if update_frequency <= 60:
        # Aligned to the current hour
        rounded_minutes = (now.minute // update_frequency) * update_frequency
        endtime = now.replace(minute=rounded_minutes, second=0, microsecond=0)
    else:
        # Aligned from midnight
        total_minutes = now.hour * 60 + now.minute
        rounded_total = (total_minutes // update_frequency) * update_frequency
        endtime = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=rounded_total)
    
    starttime = endtime - timedelta(minutes=update_frequency)
    return starttime, endtime
    

def get_available_stations(csv_path = "data/involcan/metadata/latest_pulls.csv", tolerance = 5):
    """
    Returns a sorted list of unique station names whose latest download time
    is within the last `minutes` minutes from now (UTC).
    
    Parameters
    ----------
        csv_path (str): Path to the latest pulls CSV file.
        tolerance (int or timedelta): Tolerance for considering a station 
            available. If int, minutes are assumed (default: 5).
        
    Returns
    -------
        list: List of available station names.
    """
    if isinstance(tolerance, numbers.Number):
        tolerance = timedelta(minutes=tolerance)

    stations = set()
    not_avail_stations = set()
    now = datetime.now(timezone.utc)

    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Parse latest pull time
            try:
                latest_pull_time = datetime.strptime(row['latest_pull_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            
            stations.add(row['station'])

            # Check availability
            if now - latest_pull_time > tolerance:
                not_avail_stations.add(row['station'])

    avail_stations = stations - not_avail_stations

    if not avail_stations:
        print(f"No data for any station (tolerance: {tolerance}).")

    return avail_stations


def get_noc_names(csv_path = "data/involcan/metadata/noc_list.csv", stations = None):
    """
    Finds the names of the NOCs in the list associated with the stations.

    Parameters
    ----------
    csv_path (str)
        Path to the CSV file with the list of NOCs.
    stations (list)
        List of stations.

    Returns
    -------
        list: List of tuples (NOC name, station).
    """
    noc_names = []

    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            station = row['station']
            if station in stations and row['type'] in ('static', 'dynamic'):
                noc_names.append((row['name'], row['station']))

    return noc_names


def monitoring(config_path = 'config.json'):
    """
    Main monitoring function. Calculates FFT coefficients and performs MSPC-PCA on all
    available stations.

    Parameters
    ----------
    config_path (str):
        Path to a JSON file with all necessary parameters.
    """
    # Get all parameters for monitoring from the configuration file
    config = load_config(config_path)
    config_str = json.dumps(config)  # config in string form

    update_frequency = config["update_frequency"]  # Frequency of update in minutes
    data_path = config["data_path"]  # Path to the directory where seismic data files are saved.
    features_path = config["features_path"]  # Path to the directory where feature files are saved.
    nocs_path = config["nocs_path"]  # Path to the directory where NOC files are saved.
    plots_path = config["plots_path"]  # Path to the directory where MSPC plots are saved.
    latest_pulls_log_path = config["latest_pulls_log_path"]  # Path to a CSV with information on the latest data downloads
    noc_log_path = config["noc_log_path"]  # Path to a CSV for saving NOC information
    anomaly_log_path = config["anomaly_log_path"]  # Path to a CSV for saving anomalous window information
    network = config["network"]  # Network code
    stations = config["stations"]  # Station codes
    channels = config["channels"]  # Channel codes
    window_size = config["window_size"]  # Size in seconds of the windows
    window_shift = window_size if config["window_shift"] is None else config["window_shift"]  # Time in seconds between the start times of 2 consecutive windows.
    detrend = config["detrend"]  # Detrending method. False for no detrending.
    feature_types = config["feature_types"]  # Types of features (one or more of 'ffts', 'deltas_ffts', 'deltas_deltas_ffts')
    fft_points = config["fft_points"]  # Number of FFT points (spectral resolution)
    merge_method = config["merge_method"]  # Trace merging method (see ObsPy documentation)
    merge_fill_value = config["merge_fill_value"]  # Value for filling a gap in the middle of a signal ('interpolate' for interpolation)
    pad_fill_value = config["pad_fill_value"]  # Value for filling a signal if it does not start at 'starttime' or end at 'endtime'
    cpus = config["cpus"]  # Number of CPUs used for FFT calculation
    anomaly_criterion = config["anomaly_criterion"]  # Criterion for anomaly detection
    verbose = config["verbose"]  # Whether to print extra messages.
    days_before_delete = config["days_before_delete"]  # Number of days to keep saved features.
    num_hours_for_plot = config["num_hours_for_plot"]  # Length in hours of the time range shown in MSPC plots

    time0 = datetime.now()
    
    # Set start and end times
    if config["starttime"] == 'auto' or config["endtime"] == 'auto':
        starttime, endtime = start_and_end_times(datetime.now(timezone.utc), update_frequency)
    else:
        starttime = datetime.strptime(config["starttime"], '%Y-%m-%dT%H:%M:%SZ')
        endtime = datetime.strptime(config["endtime"], '%Y-%m-%dT%H:%M:%SZ')

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    # Update NOCs once a week
    if starttime.weekday() == 0 and starttime.hour == 0 and starttime.minute == 0:  # Monday at 00:00 UTC
        update_nocs = True
    else:
        update_nocs = False

    # Check available stations
    try:
        avail_stations = get_available_stations(latest_pulls_log_path, 1.5 * update_frequency)
        avail_stations = avail_stations.intersection(stations)
    except Exception as e:
        print(f"Error retrieving available stations: {e}. Attempting calculation for all stations...")
        avail_stations = stations

    # Load Normal Operation Conditions (NOCs) for all available stations
    noc_names = get_noc_names(noc_log_path, avail_stations)
    nocs = defaultdict(list)
    for name, station in noc_names:
        noc_path = os.path.join(nocs_path, name).replace('\\', '/')
        noc = NOC.load(noc_path)
        nocs[station].append(noc)

    # Calculate features
    for station in avail_stations:
        features = calculate_fft_rt(starttime, endtime, network, station, channels, 
                                    window_size, window_shift, detrend=detrend, fft_points=fft_points, 
                                    merge_method=merge_method, merge_fill_value=merge_fill_value,
                                    pad_fill_value = pad_fill_value, data_path=data_path, cpus=cpus, verbose=verbose)

        # Save features files
        features['config'] = config_str
        file_name = station + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
        mat_path = os.path.join(features_path, file_name).replace('\\', '/')
        savemat(mat_path, features)

        # Perform MSPC for all NOCs associated with the station
        test_data = np.hstack([features[key] for key in feature_types])  # one or more of [ffts, deltas_ffts, deltas_deltas_ffts]
        mspc(nocs[station], test_data, starttime, endtime, window_size, window_shift, 
             missing_rates=features['missing_rates'], plot=False, update_log=True, 
             anomaly_log_path=anomaly_log_path, nocs_path=nocs_path, verbose=verbose)

        # Delete old features files
        delete_date = endtime - timedelta(days = days_before_delete)
        delete_fft(features_path, station, datetime.min, delete_date)

        for noc in nocs[station]:
            # Save MSPC plot
            plot_start = endtime - timedelta(hours=num_hours_for_plot)
            plot_filename = noc.name + '_' + plot_start.strftime('%Y%m%dT%H%M%SZ') + '_' + endtime.strftime('%Y%m%dT%H%M%SZ')
            plot_filepath = os.path.join(plots_path, plot_filename)
            plot_anomalies(noc, plot_start, endtime, criterion=anomaly_criterion, save=True,
                           save_path=plot_filepath, show=False)
            
            # Update dynamic NOCs
            if update_nocs and noc.type == 'dynamic':                
                noc.type = 'inactive'
                noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))

                update_start = endtime - timedelta(days=7)  # HARDCODED: 1 week

                # Get paths of the feature files to update NOCs
                filenames = list_fft_files(features_path, station, update_start, endtime, verbose=verbose)
                filepaths = [os.path.join(features_path, filename).replace('\\', '/') for filename in filenames]
                files = [loadmat(filepath) for filepath in filepaths]
                new_features = np.vstack([np.hstack([f[key] for key in feature_types]) for f in files])
                new_labels = []
                for file in files:
                    new_labels.extend(file['obs_labels'])

                # Create new NOC for the new week
                new_name = noc.station + '_' + 'd' + '_' + endtime.strftime('%Y-%m-%d')
                new_noc = NOC(new_name, new_features, new_labels, network=network, station=station,
                              type='dynamic', preprocessing=noc.preprocessing, n_components=noc.n_components, 
                              alpha=noc.alpha, percentile_threshold=noc.percentile_threshold, 
                              q_method = noc.q_method, csv_path = noc_log_path)
                new_noc.save(os.path.join(nocs_path, new_noc.name).replace('\\', '/'))

            # Delete old D and Q-statistic test values
            noc.delete_DQ_test(delete_date)

    print(f"Updated process control. Total time: {datetime.now() - time0}.")
