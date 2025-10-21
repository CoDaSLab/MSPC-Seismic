import json
import os
import re
import ast
import csv
import numpy as np
from datetime import datetime, timedelta, timezone
from collections import defaultdict

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
        list: List of available stations, in the form of (network, station, channels) tuples.
    """
    if not isinstance(tolerance, timedelta):
        tolerance = timedelta(minutes=tolerance)

    stations = set()
    not_avail_stations = set()
    channels_dict = defaultdict(set)
    now = datetime.now(timezone.utc)

    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Parse latest pull time
            try:
                latest_pull_time = datetime.strptime(row['latest_pull_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            
            stations.add((row["network"], row['station']))

            # Check availability
            if now - latest_pull_time > tolerance:
                not_avail_stations.add((row["network"], row['station']))
            else:
                channels_dict[row["station"]].add(row["channel"])

    avail_stations = stations - not_avail_stations

    if not avail_stations:
        print(f"No data for any station (tolerance: {tolerance}).")

    avail_stations = sorted(avail_stations)
    avail_stations = [t + (tuple(sorted(channels_dict[t[1]])),) for t in avail_stations]

    return avail_stations


def check_nocs(csv_path = "data/involcan/metadata/noc_list.csv", stations = None, 
                  noc_types=('static', 'dynamic'), noc_length=None, additional_matches=None, 
                  nocs_path='data/involcan/nocs', edit_csv = False, verbose=False):
    """
    Finds the names of the NOCs in the list that meet certain conditions.

    Parameters
    ----------
    csv_path (str)
        Path to the CSV file with the list of NOCs.
    stations (list)
        List of stations.
    noc_types (list or tuple)
        Types of NOC to look for. Default is 'static' and 'dynamic'.
    noc_length (int)
        Expected length (in days) of training data. Only checked for dynamic NOCs.
    additional_matches (dict)
        Optional. Extra conditions that the NOC metadata need to match.
    nocs_path (str)
        Path to the directory where NOCs are saved.
    edit_csv (str)
        If additional_matches is given, marks NOCs that do not match the conditions
        as unavailable.
    verbose (bool)
        If True, displays messages. Default is False.

    Returns
    -------
        list: List of tuples (NOC name, station).
    """
    noc_names = []
    if isinstance(stations, str):
        stations = [stations]
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
                        # In case that row["station"] is a list of stations
                        station = ast.literal_eval(row["station"])
                    except (ValueError, SyntaxError):
                        station = row["station"]
                    
                    # Check station matches
                    if isinstance(station, list):
                        stations_in_list = [s in stations for s in station]
                        if all(stations_in_list):
                            add_noc = True
                        else:
                            unmatched_nocs[row["name"]] = 'inactive'
                    else:
                        if station in stations:
                            add_noc = True
                            stations_in_list = station
                        else:
                            unmatched_nocs[row["name"]] = 'inactive'
                    
                    # Check time range
                    if noc_length and row["type"] == 'dynamic':
                        stime = datetime.strptime(row["start_time"], "%Y-%m-%dT%H:%M:%SZ")
                        etime = datetime.strptime(row["end_time"], "%Y-%m-%dT%H:%M:%SZ")
                        difference = etime - stime
                        days = difference.total_seconds() / 86400
                        if not np.isclose(days, noc_length):
                            add_noc = False
                            unmatched_nocs[row["name"]] = 'unavailable'
                            if verbose:
                                print(f"NOC {row["name"]} should have a length of {noc_length} days, not {days}.")

                    # Check additional matches
                    if additional_matches:
                        noc = NOC.load(os.path.join(nocs_path, row["name"]).replace('\\', '/'))
                        for key in additional_matches.keys():
                            if key in noc.metadata and additional_matches[key] != noc.metadata[key]:
                                add_noc = False
                                unmatched_nocs[row["name"]] = 'unavailable'
                                if verbose:
                                    print(f"Parameter {key} for NOC {noc.name} should be {noc.metadata[key]}, not {additional_matches[key]}.")
                                
                    if add_noc:
                        noc_names.append((row['name'], station))

        # Mark NOCs that do not match additional conditions as unavailable
        if edit_csv:
            for name in unmatched_nocs:
                noc = NOC.load(os.path.join(nocs_path, name).replace('\\', '/'))
                noc.type = unmatched_nocs[name]
                noc.save(os.path.join(nocs_path, name).replace('\\', '/'))

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


def delete_old_nocs(directory_path: str, date_format: str, cutoff_date: str, log_path: str, noc_types: tuple) -> None:
    """
    Deletes NOC files in the given directory whose names end with a date in the specified format,
    only if the date is earlier than the given cutoff date. Also removes the corresponding
    rows from the NOC list CSV file.

    Parameters
    ----------
        directory_path (str): 
            Path to the directory to scan.
        date_format (str): 
            Date format to match at the end of file names (e.g., '%Y-%m-%d').
        cutoff_date (str): 
            The cutoff date in the same format as date_format.
        log_path (str):
            Path to the NOC list CSV file.
        noc_types (tuple):
            Types of NOC to delete, e.g. ('dynamic', 'static').
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
    
    type_letters = [t[0] for t in noc_types]

    if type_letters:
        allowed_letters = "".join(type_letters)
        pattern = re.compile(rf"^(.*)_([{allowed_letters}])_({regex_date})$")
    else:
        pattern = re.compile(rf"^(.*)({regex_date})$")

    files_to_delete = []

    # Search for old files
    for file_name in os.listdir(directory_path):
        full_path = os.path.join(directory_path, file_name)

        if os.path.isfile(full_path):
            name_without_ext, _ = os.path.splitext(file_name)
            match = pattern.match(name_without_ext)
            if match:
                # Date is at the end of file name
                date_str = match.groups()[-1]  
                try:
                    file_date = datetime.strptime(date_str, date_format).replace(tzinfo=timezone.utc)
                    if file_date < cutoff_date:
                        os.remove(full_path)
                        files_to_delete.append(name_without_ext)  # Save to remove from CSV
                except ValueError:
                    continue  # Skip files con fecha inválida

    # Update CSV if files were deleted
    if files_to_delete and os.path.isfile(log_path):
        rows_kept = []
        with open(log_path, mode="r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            for row in reader:
                if row["name"] not in files_to_delete:
                    rows_kept.append(row)

        # Re-add unchanged rows to CSV
        with open(log_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_kept)


def delete_mseeds(directory_path:str, networks:list, stations:list, channels:list, 
                  start_day:datetime, end_day:datetime):
    """
    Deletes MSEED files that fall inside a time range.
    """
    from preprocessing.sismo import get_filenames

    files = get_filenames(networks, stations, channels, start_day, end_day)
    for file in files:
        filename = os.path.join(directory_path, file).replace('\\', '/')
        if os.path.exists(filename):
            os.remove(filename)


def create_noc(network, station, channels, starttime:datetime, endtime:datetime, config:dict, noc_params:dict=None, 
               attempt_find:bool=False):
    """
    Calculates features and creates a NOC using parameters from the JSON configuration file.
    If `attempt_find` is True, it will try to find existing features before calculating. 
    """
    data_path = config["paths"]["data"]  # Path to the directory where seismic data files are saved.
    features_path = config["paths"]["features"]  # Path to the directory where feature files are saved.
    nocs_path = config["paths"]["nocs"]  # Path to the directory where NOC files are saved.
    noc_log_path = config["paths"]["noc_log"]  # Path to a CSV for saving NOC information
    window_size = config["features"]["window_size"]  # Size in seconds of the windows
    window_shift = window_size if config["features"]["window_shift"] is None else config["features"]["window_shift"]  # Time in seconds between the start times of 2 consecutive windows.
    detrend = config["features"]["detrend"]  # Detrending method. False for no detrending.
    windowing = config["features"]["windowing"]  # Windowing method.
    feature_types = config["features"]["types"]  # Types of features
    fft_points = config["features"]["stft_params"]["fft_points"]  # Number of FFT points (spectral resolution)
    merge_method = config["features"]["merge_method"]  # Trace merging method (see ObsPy documentation)
    merge_fill_value = config["features"]["merge_fill_value"]  # Value for filling a gap in the middle of a signal ('interpolate' for interpolation)
    pad_fill_value = config["features"]["pad_fill_value"]  # Value for filling a signal if it does not start at 'starttime' or end at 'endtime'
    verbose = config["monitoring"]["verbose"]  # Whether to print extra messages.

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
                                max_missing_rate=config["monitoring"]["max_missing_rate"], verbose=verbose)
        if features:
            print("Features found")
            # Get labels (assuming labels indicate end time of the window)
            labels = []
            current_time = starttime
            while current_time < endtime:
                current_time += timedelta(seconds=window_shift)
                labels.append(current_time.strftime('Y-%m-%dT%H:%M:%SZ'))

            if len(labels) != len(features["times_label"]) or any(labels != features["times_label"]):
                calculate = True
        else:
            print("Features not found. Calculating....")
            calculate = True        
    
    if calculate:
        features = calculate_fft_rt(starttime, endtime, network, station, channels, 
                                    window_size, window_shift, detrend=detrend, windowing=windowing, n_bins=fft_points, 
                                    merge_method=merge_method, merge_fill_value=merge_fill_value,
                                    pad_fill_value=pad_fill_value, data_path=data_path, verbose=verbose)
    
    # Create new NOC
    new_features = np.hstack([features[key] for key in feature_types])
    if noc_params:
        new_noc = NOC(new_name, new_features, features['times_label'], network, station, channels, type=noc_params["type"],
                        preprocessing = noc_params["preprocessing"], n_components = noc_params["n_components"], 
                        quantile_threshold = noc_params["quantile_threshold"])
    else:
        new_noc = NOC(new_name, new_features, features['times_label'], network, station, channels, type='dynamic',
                        preprocessing = 1, n_components = 1, quantile_threshold = 0.99, csv_path=noc_log_path)
    new_noc.set_metadata(starttime, endtime, window_size, window_shift, detrend, windowing, fft_points, 
                            merge_method, merge_fill_value, pad_fill_value)
    new_noc.save(os.path.join(nocs_path, new_noc.name).replace('\\', '/'))

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