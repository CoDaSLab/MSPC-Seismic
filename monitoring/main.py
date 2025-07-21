import json
import os
import re
import csv
import numpy as np
from datetime import datetime, timedelta, timezone
from scipy.io import savemat, loadmat
from collections import defaultdict

from preprocessing.fft_rt import calculate_fft_rt, delete_fft, list_fft_files
from monitoring.mspc_rt import mspc, plot_anomalies
from monitoring.NOC import NOC


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


def start_and_end_times(now: datetime, update_frequency: int, delay: int):
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
        endtime = now.replace(minute=rounded_minutes, second=0, microsecond=0) - timedelta(minutes=delay)
    else:
        # Aligned from midnight
        total_minutes = now.hour * 60 + now.minute
        rounded_total = (total_minutes // update_frequency) * update_frequency
        endtime = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=rounded_total - delay)
    
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
    if not isinstance(tolerance, timedelta):
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
            
            stations.add(row['sensor'])

            # Check availability
            if now - latest_pull_time > tolerance:
                not_avail_stations.add(row['sensor'])

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


def delete_old_files(directory_path: str, date_format: str, cutoff_date: str) -> None:
    """
    Deletes files in the given directory whose names end with a date in the specified format,
    only if the date is earlier than the given cutoff date.

    Parameters
    ----------
        directory_path (str): 
            Path to the directory to scan.
        date_format (str): 
            Date format to match at the end of file names (e.g., '%Y-%m-%d').
        cutoff_date_str (str): 
            The cutoff date in the same format as date_format.
    """
    if not os.path.isdir(directory_path):
        raise ValueError(f"Directory does not exist: {directory_path}")

    if isinstance(cutoff_date, str):
        cutoff_date = datetime.strptime(cutoff_date, date_format).replace(tzinfo=timezone.utc)

    # Convert the date format to a regex pattern
    regex_date = date_format \
        .replace('%Y', r'\d{4}') \
        .replace('%m', r'\d{2}') \
        .replace('%d', r'\d{2}')
    
    pattern = re.compile(rf"^(.*)({regex_date})$")

    for file_name in os.listdir(directory_path):
        full_path = os.path.join(directory_path, file_name)

        if os.path.isfile(full_path):
            name_without_ext, _ = os.path.splitext(file_name)
            match = pattern.match(name_without_ext)
            if match:
                date_str = match.group(2)
                try:
                    file_date = datetime.strptime(date_str, date_format).replace(tzinfo=timezone.utc)
                    if file_date < cutoff_date:
                        os.remove(full_path)
                except ValueError:
                    continue  # Skip files with invalid dates


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
    delay = config["delay"]  # Delay in minutes of calculations with respect to the current time 
    data_path = config["data_path"]  # Path to the directory where seismic data files are saved.
    features_path = config["features_path"]  # Path to the directory where feature files are saved.
    nocs_path = config["nocs_path"]  # Path to the directory where NOC files are saved.
    save_plots = config["save_plots"]  # Whether to save plots
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
    num_days_for_noc_update = config["num_days_for_noc_update"]  # Number of days between dynamic NOC updates

    time0 = datetime.now()
    
    # Set start and end times
    if config["starttime"] == 'auto' or config["endtime"] == 'auto':
        starttime, endtime = start_and_end_times(datetime.now(timezone.utc), update_frequency, delay)
    else:
        starttime = datetime.strptime(config["starttime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        endtime = datetime.strptime(config["endtime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

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

    # Dates for plots and updates
    plot_start = endtime - timedelta(hours=num_hours_for_plot)
    plot_start = plot_start.replace(tzinfo=timezone.utc)
    update_start = endtime - timedelta(days=num_days_for_noc_update)  # Dynamic NOCs created before this date will be updated
    update_start = update_start.replace(tzinfo=timezone.utc)
    delete_date = endtime - timedelta(days = days_before_delete)  # files from before this date will be deleted

    # Calculate features
    for station in avail_stations:
        # Check previous features files
        previous_starttime = starttime - timedelta(minutes=update_frequency)
        previous_filename = station + '_' + previous_starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
        if os.path.isfile(os.path.join(features_path, previous_filename).replace('\\', '/')):
            previous_features = loadmat(os.path.join(features_path, previous_filename).replace('\\', '/'))
            previous_missing_rates = previous_features['missing_rates']
            if np.mean(previous_missing_rates) > 0.1:
                if verbose:
                    print(f"Warning: High missing rates in previous features for station {station}. Recalculating features...")
                # If previous features have high missing rates, recalculate them
                starttime = previous_starttime.replace(tzinfo=timezone.utc)

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
        delete_fft(features_path, station, datetime.min.replace(tzinfo=timezone.utc), delete_date)

        for noc in nocs[station]:
            if save_plots:
                # Save MSPC plot
                plot_filename = noc.name + '_' + plot_start.strftime('%Y%m%dT%H%M%SZ') + '_' + endtime.strftime('%Y%m%dT%H%M%SZ')
                plot_filepath = os.path.join(plots_path, plot_filename)
                plot_anomalies(noc, plot_start, endtime, criterion=anomaly_criterion, save=True,
                            save_path=plot_filepath, show=False)
            
            # Update dynamic NOCs
            if noc.type == 'dynamic':  
                last_noc_update = datetime.strptime(noc.last_update_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                if update_start > last_noc_update:
                    # Get paths of the feature files to update NOCs
                    filenames = list_fft_files(features_path, station, update_start, endtime, verbose=verbose)
                    filepaths = [os.path.join(features_path, filename).replace('\\', '/') for filename in filenames]
                    files = [loadmat(filepath) for filepath in filepaths]
                    new_features = np.vstack([np.hstack([f[key] for key in feature_types]) for f in files])
                    new_labels = []
                    for file in files:
                        new_labels.extend(file['obs_labels'])

                    # Create new NOC for the new week
                    new_name = noc.station + '_' + 'd' + '_' + starttime.strftime('%Y-%m-%d')
                    new_noc = NOC(new_name, new_features, new_labels, network=network, station=station,
                                type='dynamic', preprocessing=noc.preprocessing, n_components=noc.n_components, 
                                alpha=noc.alpha, percentile_threshold=noc.percentile_threshold, 
                                q_method = noc.q_method, csv_path = noc_log_path)
                    new_noc.save(os.path.join(nocs_path, new_noc.name).replace('\\', '/'))
                    new_noc.write_csv(noc_log_path)
                    
                    # Make previous NOC inactive
                    noc.type = 'inactive'
                    noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                    noc.write_csv(noc_log_path)

            # Delete old D and Q-statistic test values
            noc.delete_DQ_test(delete_date)

    # Delete old NOCs
    delete_old_files(nocs_path, '%Y-%m-%d', delete_date)

    # Delete old plots
    delete_old_files(plots_path, '%Y%m%dT%H%M%SZ', delete_date)

    print(f"Updated process control. Total time: {datetime.now() - time0}.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Real-time monitoring using MSPC-PCA.")
    parser.add_argument("--config", default="monitoring/config.json", help="Path to the JSON configuration file.")
    args = parser.parse_args()

    monitoring(args.config)