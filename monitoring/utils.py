import json
import os
import re
import ast
import csv
import numpy as np
from datetime import datetime, timedelta, timezone

from preprocessing.fft_rt import calculate_fft_rt, find_features
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
            
            stations.add(row['station'])

            # Check availability
            if now - latest_pull_time > tolerance:
                not_avail_stations.add(row['station'])

    avail_stations = stations - not_avail_stations

    if not avail_stations:
        print(f"No data for any station (tolerance: {tolerance}).")

    return avail_stations


def get_noc_names(csv_path = "data/involcan/metadata/noc_list.csv", stations = None, 
                  noc_types=('static', 'dynamic'), additional_matches=None, nocs_path='data/involcan/nocs',
                  edit_csv = False):
    """
    Finds the names of the NOCs in the list associated with the stations.

    Parameters
    ----------
    csv_path (str)
        Path to the CSV file with the list of NOCs.
    stations (list)
        List of stations.
    noc_types (list or tuple)
        Types of NOC to look for. Default is 'static' and 'dynamic'.
    additional_matches (dict)
        Optional. Extra conditions that the NOC metadata need to match.
    nocs_path (str)
        Path to the directory where NOCs are saved.
    edit_csv (str)
        If additional_matches is given, marks NOCs that do not match the conditions
        as unavailable.
    Returns
    -------
        list: List of tuples (NOC name, station).
    """
    noc_names = []
    stations = sorted(stations)
    unmatched_nocs = {}
    os.makedirs(nocs_path, exist_ok=True)

    if os.path.isfile(csv_path):
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                add_noc = False
                if row['type'] in noc_types:
                    try:
                        # In case the row["station"] is a list of stations
                        station = ast.literal_eval(row["station"])
                    except (ValueError, SyntaxError):
                        station = row["station"]
                    
                    # Check station matches
                    if isinstance(station, list):
                        stations_in_list = [s for s in station if s in stations]
                        if len(stations_in_list) > 0:
                            add_noc = True
                        else:
                            unmatched_nocs[row["name"]] = 'inactive'
                    else:
                        if station in stations:
                            add_noc = True
                            stations_in_list = station
                        else:
                            unmatched_nocs[row["name"]] = 'inactive'

                    # Check additional matches
                    if additional_matches:
                        noc = NOC.load(os.path.join(nocs_path, row["name"]).replace('\\', '/'))
                        for key in additional_matches.keys():
                            if key in noc.metadata and additional_matches[key] != noc.metadata[key]:
                                add_noc = False
                                print(key, additional_matches[key], noc.metadata[key])
                                unmatched_nocs[row["name"]] = 'unavailable'
                                
                    if add_noc:
                        noc_names.append((row['name'], station))

        # Mark NOCs that do not match additional conditions as unavailable
        if edit_csv:
            for name in unmatched_nocs:
                noc = NOC.load(os.path.join(nocs_path, name).replace('\\', '/'))
                noc.type = unmatched_nocs[name]
                noc.metadata["window_shift"] = noc.metadata["window_size"]  # BORRAR !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! <------------------
                noc.save(os.path.join(nocs_path, name).replace('\\', '/'))
                noc.write_csv(csv_path)

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
        .replace('%d', r'\d{2}') \
        .replace('%H', r'\d{2}') \
        .replace('%M', r'\d{2}') \
        .replace('%S', r'\d{2}')
    
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


def create_noc(station, starttime:datetime, endtime:datetime, config:dict, noc_params:dict=None, 
               attempt_find:bool=False):
    """
    Calculates features and creates a NOC using parameters from the JSON configuration file.
    If `attempt_find` is True, it will try to find existing features before calculating. 
    """
    data_path = config["paths"]["data"]  # Path to the directory where seismic data files are saved.
    features_path = config["paths"]["features"]  # Path to the directory where feature files are saved.
    nocs_path = config["paths"]["nocs"]  # Path to the directory where NOC files are saved.
    noc_log_path = config["paths"]["noc_log"]  # Path to a CSV for saving NOC information
    network = config["data"]["network"]  # Network code
    channels = config["data"]["channels"]  # Channel codes
    window_size = config["features"]["window_size"]  # Size in seconds of the windows
    window_shift = window_size if config["features"]["window_shift"] is None else config["features"]["window_shift"]  # Time in seconds between the start times of 2 consecutive windows.
    detrend = config["features"]["detrend"]  # Detrending method. False for no detrending.
    windowing = config["features"]["windowing"]  # Windowing method.
    feature_types = config["features"]["types"]  # Types of features (one or more of 'ffts', 'deltas_ffts', 'deltas_deltas_ffts')
    fft_points = config["features"]["fft_points"]  # Number of FFT points (spectral resolution)
    merge_method = config["features"]["merge_method"]  # Trace merging method (see ObsPy documentation)
    merge_fill_value = config["features"]["merge_fill_value"]  # Value for filling a gap in the middle of a signal ('interpolate' for interpolation)
    pad_fill_value = config["features"]["pad_fill_value"]  # Value for filling a signal if it does not start at 'starttime' or end at 'endtime'
    cpus = config["features"]["cpus"]  # Number of CPUs used for FFT calculation
    verbose = config["general"]["verbose"]  # Whether to print extra messages.

    if isinstance(station, list):
        new_name = "-".join(station) + '_' + 'd' + '_' + endtime.strftime('%Y-%m-%d')
        station = sorted(station)
    else:
        new_name = station + '_' + 'd' + '_' + endtime.strftime('%Y-%m-%d')

    time0 = datetime.now()
    
    calculate = not attempt_find
    if attempt_find:  # Try to find existing features
        additional_matches = config["features"]
        additional_matches["window_shift"] = window_shift
        features = find_features(features_path, station, starttime, endtime, feature_types, 
                                additional_matches=additional_matches, 
                                max_missing_rate=config["general"]["max_missing_rate"], verbose=verbose)
        if features:
            print("Features found")
            # Get labels (assuming labels indicate end time of the window)
            labels = []
            current_time = starttime
            while current_time < endtime:
                current_time += timedelta(seconds=window_shift)
                labels.append(current_time.strftime('Y-%m-%dT%H:%M:%SZ'))

            if len(labels) != len(features["obs_labels"]) or any(labels != features["obs_labels"]):
                calculate = True
        else:
            print("Features not found. Calculating....")
            calculate = True        
    
    if calculate:
        features = calculate_fft_rt(starttime, endtime, network, station, channels, 
                                    window_size, window_shift, detrend=detrend, windowing=windowing, fft_points=fft_points, 
                                    merge_method=merge_method, merge_fill_value=merge_fill_value,
                                    pad_fill_value=pad_fill_value, data_path=data_path, cpus=cpus, verbose=verbose)
    
    # Create new NOC
    new_features = np.hstack([features[key] for key in feature_types])
    if noc_params:
        new_noc = NOC(new_name, new_features, features['obs_labels'], network, station, type=noc_params["type"],
                        preprocessing = noc_params["preprocessing"], n_components = noc_params["n_components"], 
                        quantile_threshold = noc_params["quantile_threshold"])
    else:
        new_noc = NOC(new_name, new_features, features['obs_labels'], network, station, type='dynamic',
                        preprocessing = 1, n_components = 'ckf', quantile_threshold = 0.99, csv_path=noc_log_path)
    new_noc.set_metadata(starttime, endtime, window_size, window_shift, detrend, windowing, fft_points, 
                            merge_method, merge_fill_value, pad_fill_value)
    new_noc.save(os.path.join(nocs_path, new_noc.name).replace('\\', '/'))
    new_noc.write_csv(noc_log_path)

    if verbose:
        print(f"Created NOC {new_noc.name}. Time taken: {datetime.now() - time0}.")

    return new_noc


def noc_info(noc_name, csv_path='data/involcan/metadata/noc_list.csv'):
    """
    Retrieves information about a NOC from a CSV file.
    """
    info = {}
    if os.path.isfile(csv_path):
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["name"] == noc_name:
                    info = row
    return info