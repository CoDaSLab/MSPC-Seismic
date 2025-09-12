import json
import os
import numpy as np
from datetime import datetime, timedelta, timezone
from scipy.io import savemat, loadmat
from collections import defaultdict
from pickle import UnpicklingError

from preprocessing.fft_rt import calculate_fft_rt, delete_fft, list_fft_files
from monitoring.mspc_rt import mspc, plot_anomalies_DQ
from monitoring.NOC import NOC
from monitoring import utils

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
    config = utils.load_config(config_path)
    config_str = json.dumps(config)  # config in string form

    update_frequency = config["general"]["update_frequency"]  # Frequency of update in minutes
    delay = config["general"]["delay"]  # Delay in minutes of calculations with respect to the current time 
    data_path = config["paths"]["data"]  # Path to the directory where seismic data files are saved.
    features_path = config["paths"]["features"]  # Path to the directory where feature files are saved.
    nocs_path = config["paths"]["nocs"]  # Path to the directory where NOC files are saved.
    save_plots = config["plots"]["save"]  # Whether to save plots
    plots_path = config["paths"]["plots"]  # Path to the directory where MSPC plots are saved.
    latest_pulls_log_path = config["paths"]["latest_pulls_log"]  # Path to a CSV with information on the latest data downloads
    noc_log_path = config["paths"]["noc_log"]  # Path to a CSV for saving NOC information
    anomaly_log_path = config["paths"]["anomaly_log"]  # Path to a CSV for saving anomalous window information
    network = config["data"]["network"]  # Network code
    stations = config["data"]["stations"]  # Station codes
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
    anomaly_criterion = config["plots"]["anomaly_criterion"]  # Criterion for anomaly detection
    verbose = config["general"]["verbose"]  # Whether to print extra messages.
    num_days_before_delete = config["general"]["num_days_before_delete"]  # Number of days to keep saved features.
    num_hours_plot = config["plots"]["num_hours"]  # Length in hours of the time range shown in MSPC plots
    num_days_noc_update_frequency = config["general"]["num_days_noc_update_frequency"]  # Number of days between dynamic NOC updates
    num_days_noc_length = config["general"]["num_days_noc_length"]  # Number of days used as training data

    time0 = datetime.now()
    
    # Set start and end times
    if config["data"]["starttime"] == 'auto' or config["data"]["endtime"] == 'auto':
        starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), update_frequency, delay)
    else:
        starttime = datetime.strptime(config["data"]["starttime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        endtime = datetime.strptime(config["data"]["endtime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    # Check available stations
    try:
        avail_stations = utils.get_available_stations(latest_pulls_log_path, 1.5 * update_frequency)
        avail_stations = avail_stations.intersection(stations)
    except Exception as e:
        print(f"Error retrieving available stations: {e}. Attempting calculation for all stations...")
        avail_stations = set(stations)

    # Load Normal Operation Conditions (NOCs) for all available stations
    noc_names = utils.get_noc_names(noc_log_path, avail_stations)

    # Create NOC for available stations that do not have one
    noc_stations = set([sta for _, sta in noc_names])
    no_noc_stations = avail_stations - noc_stations
    if len(no_noc_stations) > 0:
        for station in no_noc_stations:
            # Get features to create NOC
            if verbose:
                print(f"Creating new NOC for station {station}...")
            noc_end = endtime.replace(hour=0, minute=0, second=0)
            noc_start = noc_end - timedelta(days=num_days_noc_length)
            if isinstance(station, list):
                new_name = "-".join(station) + '_' + 'd' + '_' + endtime.strftime('%Y-%m-%d')
            else:
                new_name = station + '_' + 'd' + '_' + endtime.strftime('%Y-%m-%d')
            try:
                utils.create_noc(station, noc_start, noc_end, config)

                noc_names.append((new_name, station))
            except Exception as e:
                if verbose:
                    print(f"NOC for station {station} could not be created: {e}.")

    nocs = defaultdict(list)
    for name, station in noc_names:
        noc_path = os.path.join(nocs_path, name).replace('\\', '/')
        nocs[station].append(noc_path)

    # Dates for plots and updates
    plot_start = endtime - timedelta(hours=num_hours_plot)
    plot_start = plot_start.replace(tzinfo=timezone.utc)
    update_start = endtime - timedelta(days=num_days_noc_update_frequency)  # Dynamic NOCs created before this date will be updated
    update_start = update_start.replace(tzinfo=timezone.utc)
    delete_date = endtime - timedelta(days = num_days_before_delete)  # files from before this date will be deleted

    starttime_original = starttime
    endtime_original = endtime

    for station in avail_stations:
        # If previous runs failed, attempt to recalculate features. Only attempts to recalculate up to 10 failed runs
        max_failed_runs = 10
        previous_files = list_fft_files(features_path, station, starttime - timedelta(minutes=max_failed_runs * update_frequency), 
                                        starttime, verbose=verbose)
        i = 1
        previous_success = False
        while i <= len(previous_files) and not previous_success:
            previous_filename = previous_files[-i]
            previous_filepath = os.path.join(features_path, previous_filename).replace('\\', '/')
            if os.path.isfile(previous_filepath):
                previous_features = loadmat(previous_filepath)
                previous_missing_rates = previous_features['missing_rates']
                if np.mean(previous_missing_rates) > 0.1:
                    if verbose:
                        print(f"Warning: High missing rates in previous features for station {station}. Recalculating features...")
                    # If previous features have high missing rates, recalculate them and delete previous file
                    starttime = starttime - timedelta(minutes=update_frequency)
                    os.remove(previous_filepath)
                else:
                    previous_success = True
            else:
                starttime = starttime - timedelta(minutes=update_frequency)
            i += 1
        
        # Calculate features
        features = calculate_fft_rt(starttime, endtime, network, station, channels, 
                                    window_size, window_shift, detrend=detrend, windowing=windowing, fft_points=fft_points, 
                                    merge_method=merge_method, merge_fill_value=merge_fill_value,
                                    pad_fill_value = pad_fill_value, data_path=data_path, cpus=cpus, verbose=verbose)

        # Save features files
        features['config'] = config_str
        if isinstance(station, list):
            file_station = "-".join(station)
        else:
            file_station = station
        file_name = file_station + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
        mat_path = os.path.join(features_path, file_name).replace('\\', '/')
        savemat(mat_path, features)

        # Perform MSPC for all NOCs associated with the station
        test_data = np.hstack([features[key] for key in feature_types])  # one or more of [ffts, deltas_ffts, deltas_deltas_ffts]
        mspc(nocs[station], test_data, starttime, endtime, window_size, window_shift, 
            missing_rates=features['missing_rates'], plot=False, update_log=True, 
            anomaly_log_path=anomaly_log_path, nocs_path=nocs_path, verbose=verbose)

        # Delete old features files
        delete_fft(features_path, station, datetime.min.replace(tzinfo=timezone.utc), delete_date)

        for noc_path in nocs[station]:
            try:
                noc = NOC.load(noc_path)
                if save_plots:
                    # Save MSPC plot
                    plot_filename = noc.name + '_' + plot_start.strftime('%Y%m%dT%H%M%SZ') + '_' + endtime.strftime('%Y%m%dT%H%M%SZ')
                    plot_filepath = os.path.join(plots_path, plot_filename)
                    plot_anomalies_DQ(noc, plot_start, endtime, criterion=anomaly_criterion, save=True,
                                save_path=plot_filepath, show=False)

                # Update dynamic NOCs
                last_noc_update = datetime.strptime(noc.last_update_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                if noc.type != 'static':
                    if update_start > last_noc_update:
                        # Get paths of the feature files to update NOCs
                        filenames = list_fft_files(features_path, station, endtime-timedelta(days=num_days_noc_length), endtime, verbose=verbose)
                        filepaths = [os.path.join(features_path, filename).replace('\\', '/') for filename in filenames]
                        files = [loadmat(filepath) for filepath in filepaths]
                        new_features = np.vstack([np.hstack([f[key] for key in feature_types]) for f in files if np.mean(f['missing_rates']) < 0.1])
                        new_labels = []
                        for file in files:
                            if np.mean(file['missing_rates']) < 0.1:
                                new_labels.extend(file['obs_labels'])

                        # Create new NOC
                        if isinstance(station, list):
                            new_name = "-".join(station) + '_' + 'd' + '_' + noc_end.strftime('%Y-%m-%d')
                        else:
                            new_name = station + '_' + 'd' + '_' + starttime.strftime('%Y-%m-%d')
                        new_noc = NOC(new_name, new_features, new_labels, network=network, station=station,
                                    type='dynamic', preprocessing=noc.preprocessing, n_components='auto', 
                                    quantile_threshold=noc.quantile_threshold, csv_path = noc_log_path)
                        new_noc.set_metadata(endtime-timedelta(days=num_days_noc_length), endtime, window_size, window_shift, detrend, 
                                            windowing, fft_points, merge_method, merge_fill_value, pad_fill_value)
                        new_noc.save(os.path.join(nocs_path, new_noc.name).replace('\\', '/'))
                        new_noc.write_csv(noc_log_path)
                        
                        # Make previous NOC inactive
                        noc.type = 'inactive'

                if delete_date > last_noc_update:
                    noc.type = 'unavailable'

                # Delete old D and Q-statistic test values and save changes
                noc.delete_DQ_test(delete_date)
                noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                noc.write_csv(noc_log_path)

            except UnpicklingError:
                # Recreate a NOC if it fails to load
                name = os.path.basename(noc_path)
                print(f"NOC {name} failed to load. Recreating NOC...")

                noc_info = utils.noc_info(name, noc_log_path)
                noc_start = datetime.strptime(noc_info["start_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                noc_end = datetime.strptime(noc_info["start_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                utils.create_noc(station, noc_start, noc_end, config, attempt_find=True)
            
        starttime = starttime_original
        endtime = endtime_original

    # Delete old NOCs
    utils.delete_old_files(nocs_path, '%Y-%m-%d', delete_date)

    # Delete old plots
    utils.delete_old_files(plots_path, '%Y%m%dT%H%M%SZ', delete_date)

    print(f"Updated process control. Total time: {datetime.now() - time0}.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Real-time monitoring using MSPC-PCA.")
    parser.add_argument("--config", default="monitoring/config.json", help="Path to the JSON configuration file.")
    args = parser.parse_args()

    monitoring(args.config)