import json
import os
import numpy as np
from datetime import datetime, timedelta, timezone
from scipy.io import savemat, loadmat
from collections import defaultdict
from pickle import UnpicklingError

from preprocessing.fft_rt import calculate_fft_rt, delete_fft, find_features
from monitoring.mspc_rt import mspc, plot_anomalies_DQ
from monitoring import NOC
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
    # ------------------------ Read configuration file -------------------------- 

    # Get all parameters for monitoring from the configuration file
    config = utils.load_config(config_path)

    update_frequency = config["monitoring"]["update_frequency"]  # Frequency of update in minutes
    delay = config["monitoring"]["delay"]  # Delay in minutes of calculations with respect to the current time 
    data_path = config["paths"]["data"]  # Path to the directory where seismic data files are saved.
    features_path = config["paths"]["features"]  # Path to the directory where feature files are saved.
    nocs_path = config["paths"]["nocs"]  # Path to the directory where NOC files are saved.
    save_plots = config["monitoring"]["plots"]["save"]  # Whether to save plots
    plots_path = config["paths"]["plots"]  # Path to the directory where MSPC plots are saved.
    latest_pulls_log_path = config["paths"]["latest_pulls_log"]  # Path to a CSV with information on the latest data downloads
    noc_log_path = config["paths"]["noc_log"]  # Path to a CSV for saving NOC information
    anomaly_log_path = config["paths"]["anomaly_log"]  # Path to a CSV for saving anomalous window information

    groups_dict = config["groups"]  # Groups of stations. Each group has a separate monitoring system
    groups = [g for g in groups_dict.keys() if groups_dict[g]["active"]]
    stations_all = []
    for g in groups:
        stations_all.extend([(groups_dict[g]["network"], st, tuple(sorted(groups_dict[g]["channels"]))) 
                             for st in groups_dict[g]["stations"]])

    window_size = config["features"]["window_size"]  # Size in seconds of the windows
    if config["features"]["window_shift"] is None:
        config["features"]["window_shift"] = window_size
    window_shift = config["features"]["window_shift"]  # Time in seconds between the start times of 2 consecutive windows.
    detrend = config["features"]["detrend"]  # Detrending method. False for no detrending.
    windowing = config["features"]["windowing"]  # Windowing method.
    feature_types = config["features"]["types"]  # Types of features
    fft_points = config["features"]["stft_params"]["fft_points"]  # Number of FFT points (spectral resolution)
    merge_method = config["features"]["merge_method"]  # Trace merging method (see ObsPy documentation)
    merge_fill_value = config["features"]["merge_fill_value"]  # Value for filling a gap in the middle of a signal ('interpolate' for interpolation)
    pad_fill_value = config["features"]["pad_fill_value"]  # Value for filling a signal if it does not start at 'starttime' or end at 'endtime'
    noc_params = config["features"]["noc_params"]  # Default parameters for NOC creation
    noc_params["type"] = "dynamic"
    anomaly_criterion = config["monitoring"]["criteria"]["type"]  # Criterion for anomaly detection
    n_consecutive = config["monitoring"]["criteria"]["amount"]  # Number of consecutive windows over threshold needed to label an anomaly
    verbose = config["monitoring"]["verbose"]  # Whether to print extra messages.
    num_days_before_delete = config["monitoring"]["num_days_before_delete"]  # Number of days to keep saved features.
    num_hours_plot = config["monitoring"]["plots"]["num_hours"]  # Length in hours of the time range shown in MSPC plots
    num_days_noc_update_frequency = config["monitoring"]["num_days_noc_update_frequency"]  # Number of days between dynamic NOC updates
    num_days_noc_length = config["monitoring"]["num_days_noc_length"]  # Number of days used as training data
    
    config_str = json.dumps(config)  # config in string form

    time0 = datetime.now()

    # -------------------------- Parameter and station check ----------------------------
    
    # Set start and end times
    if config["monitoring"]["starttime"] == 'auto' or config["monitoring"]["endtime"] == 'auto':
        starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), update_frequency, delay)
    else:
        starttime = datetime.strptime(config["monitoring"]["starttime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        endtime = datetime.strptime(config["monitoring"]["endtime"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    # Check available stations
    avail_data = utils.get_available_stations(latest_pulls_log_path, 1.5 * update_frequency)
    avail_data = set(avail_data).intersection(stations_all)
    avail_stations = [st for _, st, _ in sorted(avail_data)]

    avail_data_dict = defaultdict(dict)
    for ad in avail_data:
        network, station, channels = ad
        avail_data_dict[station]["network"] = network
        avail_data_dict[station]["channels"] = list(channels)
    
    if len(avail_data) == 0:
        print(f"No stations are available at the moment. Process aborted after {datetime.now() - time0}")
        return
    
    # Load Normal Operation Conditions (NOCs) for all available stations
    noc_names = utils.check_nocs(noc_log_path, avail_stations, noc_length=num_days_noc_length, 
                                    additional_matches=config["features"], 
                                    nocs_path=nocs_path, edit_csv=True, verbose=verbose)

    # --------------- Create NOC for individual stations that do not have one --------------------

    noc_stations = set([sta for _, sta in noc_names if isinstance(sta, str)])  # Stations with NOC
    no_noc_stations = [st for st in avail_stations if st not in noc_stations]  # Stations without NOC
    no_noc_stations = sorted(no_noc_stations)
    combined_stations = [list(t) for t in {tuple(st) for _, st in noc_names if isinstance(st, list)}]  # Station combinations with a NOC
    
    if verbose:
        print("Station status:")
        print(f"    Available stations: {avail_stations}")
        print(f"    Station combinations: {combined_stations}")
        print(f"    Stations with NOCs: {noc_stations}")
        print(f"    NOCs to create: {no_noc_stations}")

    # Create NOCs for individual stations
    if len(no_noc_stations) > 0:
        for station in no_noc_stations:
            # Get features to create NOC
            print(f"Creating new NOC for station {station}...")
            noc_end = endtime.replace(hour=0, minute=0, second=0)
            noc_start = noc_end - timedelta(days=num_days_noc_length)
            try:
                if isinstance(station, list):
                    # Try to fuse existing NOCs
                    nocs_to_fuse = []
                    sts = []
                    for name, st in noc_names:
                        if isinstance(st, str) and st in station and st not in sts:
                            sts.append(st)
                            nocs_to_fuse.append(name)
                    try:
                        noc = NOC.fuse_nocs(nocs_to_fuse, n_components=noc_params["n_components"], verbose=verbose)
                    except Exception as e:
                        print(f"Could not fuse NOCs: {e}. Creating combined NOC from scratch...")
                        noc = utils.create_noc(avail_data_dict[sts[0]]["network"], sts, avail_data_dict[sts[0]]["channels"],
                                               noc_start, noc_end, config, noc_params)
                    combined_stations.append(noc.station)
                else:
                    noc = utils.create_noc(avail_data_dict[station]["network"], station, avail_data_dict[station]["channels"],
                                            noc_start, noc_end, config, noc_params)
                    noc_stations.add(station)

                    no_noc_groups = [g for g in groups if station in groups_dict[g]["stations"]]  # Groups without NOC
                    
                    # Remove stations combination associated with the new NOC's group so a new combined NOC can be created
                    for st in combined_stations:
                        st_groups = [g for g in groups if all([s in groups_dict[g]["stations"] for s in st])]
                        if st_groups and any([g in no_noc_groups for g in st_groups]):
                            combined_stations.remove(st)
                
                noc_names.append((noc.name, noc.station))
            except Exception as e:
                print(f"NOC for station {station} could not be created: {e}")
    

    # ---------------------------- Create a combined NOC for each group ------------------------------
    
    for group_key in groups:
        group = groups_dict[group_key]
        group_avail_stations = [st for st in avail_stations if st in group["stations"]]
        noc_names_combined = utils.check_nocs(noc_log_path, group_avail_stations, noc_types=["dynamic"], 
                                                noc_length=num_days_noc_length, additional_matches=config["features"],
                                                nocs_path=nocs_path, verbose=verbose)
        st_names = [st for _, st in noc_names_combined if isinstance(st, str)]
        combined_st_names = [st for _, st in noc_names_combined if isinstance(st, list)]

        if (len(np.unique(st_names)) == len(st_names) and len(combined_st_names) == 0) or sorted(st_names) not in combined_stations:
            nocs_to_fuse = [noc for noc, st in noc_names_combined if isinstance(st, str)]
            try:
                noc = NOC.fuse_nocs(nocs_to_fuse, n_components=noc_params["n_components"], verbose=verbose)
            except Exception as e:
                print(f"Could not fuse NOCs: {e}. Creating combined NOC from scratch...")
                noc = utils.create_noc(group["network"], st_names, group["channels"], noc_start, noc_end, config, noc_params)
            
            combined_stations.append(noc.station)
            noc_names.append((noc.name, noc.station))

            # Make other multi-station NOCs inactive
            if len(combined_stations) > 1:
                nocs_inactive = [noc for noc, st in noc_names_combined if isinstance(st, list)]
                for noc_name in nocs_inactive:
                    noc_path = os.path.join(nocs_path, noc_name).replace('\\', '/')
                    noc = NOC.NOC.load(noc_path)
                    if verbose:
                        print(f"NOC {noc.name} does not contain all available stations. Deactivating NOC.")
                    noc.type = 'inactive'
                    noc.save(noc_path)

    nocs = defaultdict(list)
    combined_nocs = defaultdict(list)
    for name, station in noc_names:
        noc_path = os.path.join(nocs_path, name).replace('\\', '/')
        if not isinstance(station, list):
            nocs[station].append(noc_path)
        else:
            combined_nocs[tuple(station)].append(noc_path)

    # -------------------------- Dates for plots and updates -----------------------------

    plot_start = endtime - timedelta(hours=num_hours_plot)
    plot_start = plot_start.replace(tzinfo=timezone.utc)
    update_start = endtime - timedelta(days=num_days_noc_update_frequency)  # Dynamic NOCs created before this date will be updated
    update_start = update_start.replace(tzinfo=timezone.utc)
    delete_date = endtime - timedelta(days = num_days_before_delete)  # files from before this date will be deleted

    lowest_starttime = starttime

    # --------------------------- MSPC for individual stations ---------------------------

    updated_noc = False
    for group in groups:
        # Network, station and channels for each group
        network = config["groups"][group]["network"]
        stations = [st for st in avail_stations if st in config["groups"][group]["stations"]]
        channels = config["groups"][group]["channels"]
        group_name = config["groups"][group]["name"]
        
        for station in stations:
            if verbose:
                print(f"Started process for station {station}.")

            # If previous runs failed, attempt to recalculate features. Only attempts to recalculate up to 10 failed runs
            max_failed_runs = 10
            previous_success = False
            i = 1
            previous_start = starttime
            fft_starttimes = [starttime]  # start times for stft calculation
            while i <= max_failed_runs and not previous_success:
                previous_end = previous_start 
                previous_start = previous_start - timedelta(minutes=update_frequency)
                previous_filename = station + '_' + previous_start.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + previous_end.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
                previous_filepath = os.path.join(features_path, previous_filename).replace('\\', '/')
                # If a features file from a previous execution does not exist or contains missing values, it is recalculated
                if os.path.isfile(previous_filepath):
                    previous_feat = loadmat(previous_filepath, squeeze_me=True)
                    if np.mean(previous_feat["missing_rates"]) == 0:
                        previous_success = True
                    else:
                        if verbose:
                            print(f"High missing values for {station} from {previous_start} to {previous_end}. Features will be recalculated.")
                        fft_starttimes.insert(0, previous_start)
                else:
                    print(f"No feature file found for {station} from {previous_start} to {previous_end}. Features will be recalculated.")
                    fft_starttimes.insert(0, previous_start)
                i += 1
            
            # Calculate features
            all_feat = []
            test_missing = []
            for stime in fft_starttimes:
                etime = stime + timedelta(minutes=update_frequency)
                features = calculate_fft_rt(stime, etime, network, station, channels, 
                                            window_size, window_shift, detrend=detrend, windowing=windowing, n_bins=fft_points, 
                                            merge_method=merge_method, merge_fill_value=merge_fill_value,
                                            pad_fill_value = pad_fill_value, data_path=data_path, verbose=verbose)

                # Save features files
                features['config'] = config_str
                if isinstance(station, list):
                    file_station = "-".join(station)
                else:
                    file_station = station
                file_name = file_station + '_' + stime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + etime.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
                mat_path = os.path.join(features_path, file_name).replace('\\', '/')
                savemat(mat_path, features)

                all_feat.append(np.hstack([features[key] for key in feature_types]))
                test_missing.extend(features["missing_rates"])
            
            if fft_starttimes[0] < lowest_starttime:
                lowest_starttime = fft_starttimes[0]
            
            # Perform MSPC for all NOCs associated with the station
            test_data = np.vstack(all_feat)
            
            mspc(nocs[station], test_data, fft_starttimes[0], endtime, window_size, window_shift, 
                missing_rates=test_missing, plot=False, update_log=True, 
                anomaly_log_path=anomaly_log_path, group=group_name, nocs_path=nocs_path, verbose=verbose)

            # Delete old features files
            delete_fft(features_path, station, datetime.min.replace(tzinfo=timezone.utc), delete_date)

            for noc_path in nocs[station]:
                try:
                    noc = NOC.NOC.load(noc_path)
                    if save_plots:
                        # Save MSPC plot
                        plot_filename = noc.name + '_' + plot_start.strftime('%Y%m%dT%H%M%SZ') + '_' + endtime.strftime('%Y%m%dT%H%M%SZ')
                        plot_filepath = os.path.join(plots_path, plot_filename)
                        plot_anomalies_DQ(noc, plot_start, endtime, criterion=anomaly_criterion, n_consecutive=n_consecutive,
                                          save=True, save_path=plot_filepath, show=False)
                        
                    # Make old NOCs unavailable
                    last_noc_update = datetime.strptime(noc.last_update_time, '%Y-%m-%dT%H:%M:%SZ').replace(hour=0, minute=15, second=0, tzinfo=timezone.utc)
                    if delete_date > last_noc_update:
                        noc.type = 'unavailable'

                    # Delete old D and Q-statistic test values and save changes
                    noc.delete_DQ_test(delete_date)
                    noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                    noc.write_csv(noc_log_path)

                    # Update dynamic NOCs
                    if noc.type != 'static':
                        if update_start > last_noc_update:
                            if verbose:
                                print(f"Updating {noc}...")
                            # Make previous NOC inactive
                            noc.type = 'inactive'
                            noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                            noc.write_csv(noc_log_path)

                            # Update NOC
                            updated_noc_params = {'type': 'dynamic', 'n_components': noc_params["n_components"], 
                                                'preprocessing': noc.preprocessing, 'quantile_threshold': noc.quantile_threshold}
                            noc_end = endtime.replace(hour=0, minute=0, second=0)
                            noc_start = noc_end - timedelta(days=num_days_noc_length)
                            _ = utils.create_noc(noc.network, station, noc.channels, noc_start, noc_end, config, 
                                                 updated_noc_params, attempt_find=False)
                            updated_noc = True

                except UnpicklingError:
                    # Recreate a NOC if it fails to load
                    name = os.path.basename(noc_path)
                    print(f"    NOC {name} failed to load. Recreating NOC...")

                    noc_info = utils.noc_info(name, noc_log_path)
                    updated_noc_params = {'type': noc_info["type"], 'n_components': noc_info["n_components"], 
                                        'preprocessing': noc_info["preprocessing"], 'quantile_threshold': noc_info["quantile_threshold"]}
                    noc_start = datetime.strptime(noc_info["start_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                    noc_end = datetime.strptime(noc_info["end_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                    _ = utils.create_noc(noc_info["network"], station, noc_info["channels"], noc_start, noc_end, config, 
                                         updated_noc_params, attempt_find=True)
                

    # -------------------------- MSPC for combined stations -----------------------------

    for group in groups:
        group_name = groups_dict[group]["name"]
        for st in combined_stations:
            if all(elem in groups_dict[group]["stations"] for elem in st):
                cst = st
                break
        if verbose:
            print(f"Started process for group {group_name}.")
        
        combined_endtime = endtime - timedelta(minutes=update_frequency) if delay < update_frequency else endtime
        features = find_features(features_path, cst, lowest_starttime, combined_endtime, 
                                 feature_types=feature_types, additional_matches=config["features"], 
                                 max_missing_rate=1, force_all_stations=True, verbose=verbose)
        if features:
            if features["missing_stations"]:
                print(f"    No test features found for stations {features["missing_stations"]}.")

            # Perform MSPC for all NOCs associated with the station
            test_data = np.hstack([features[key] for key in feature_types])
            mspc(combined_nocs[tuple(cst)], test_data, lowest_starttime, combined_endtime, window_size, window_shift, 
                missing_rates=features['missing_rates'], plot=False, update_log=True, 
                anomaly_log_path=anomaly_log_path, group=group_name, nocs_path=nocs_path, verbose=verbose)
        else:
            print(f"    No combined data available for group {group_name}. One or more stations might be unavailable.")        
            
        for noc_path in combined_nocs[tuple(cst)]:
            try:
                noc = NOC.NOC.load(noc_path)
                if save_plots:
                    # Save MSPC plot
                    plot_filename = noc.name + '_' + plot_start.strftime('%Y%m%dT%H%M%SZ') + '_' + combined_endtime.strftime('%Y%m%dT%H%M%SZ')
                    plot_filepath = os.path.join(plots_path, plot_filename)
                    plot_anomalies_DQ(noc, plot_start, combined_endtime, criterion=anomaly_criterion, n_consecutive=n_consecutive,
                                      save=True, save_path=plot_filepath, show=False)
                
                # Make old NOCs unavailable
                last_noc_update = datetime.strptime(noc.last_update_time, '%Y-%m-%dT%H:%M:%SZ').replace(hour=0, minute=15, second=0, tzinfo=timezone.utc)
                if delete_date > last_noc_update:
                    noc.type = 'unavailable'
                       
                # Delete old D and Q-statistic test values and save changes
                noc.delete_DQ_test(delete_date)
                noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                noc.write_csv(noc_log_path)

                # Update dynamic NOCs
                if noc.type != 'static':
                    if update_start > last_noc_update:
                        if verbose:
                            print(f"Updating {noc}...")

                        # Make previous NOC inactive
                        noc.type = 'inactive'
                        noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
                        noc.write_csv(noc_log_path)

                        # Update NOC
                        noc_end = combined_endtime.replace(hour=0, minute=0, second=0)
                        noc_start = noc_end - timedelta(days=num_days_noc_length)
                        noc_params = {'type': noc.type, 'n_components': 1, 'preprocessing': noc.preprocessing, 
                                    'quantile_threshold': noc.quantile_threshold}
                        noc_names = utils.check_nocs(noc_log_path, cst, noc_types=["dynamic"], noc_length=num_days_noc_length,
                                                        additional_matches=config["features"], nocs_path=nocs_path, verbose=verbose)
                        st_names = [st for _, st in noc_names if isinstance(st, str)]

                        if len(np.unique(st_names)) == len(st_names):
                            nocs_to_fuse = [noc for noc, st in noc_names if isinstance(st, str)]
                            try:
                                _ = NOC.fuse_nocs(nocs_to_fuse, n_components=noc_params["n_components"], verbose=verbose)
                            except Exception as e:
                                print(f"    Could not fuse NOCs: {e}. Creating combined NOC from scratch...")
                                _ = utils.create_noc(avail_data_dict[cst[0]]["network"], cst, avail_data_dict[cst[0]]["channels"],
                                                     noc_start, noc_end, config, noc_params=noc_params)
                        else:
                            if verbose:
                                print(f"    Creating combined NOC...")
                            _ = utils.create_noc(avail_data_dict[cst[0]]["network"], cst, avail_data_dict[cst[0]]["channels"],
                                                 noc_start, noc_end, config, noc_params=noc_params)
                        updated_noc = True

            except UnpicklingError:
                # Recreate a NOC if it fails to load
                name = os.path.basename(noc_path)
                print(f"    NOC {name} failed to load. Recreating NOC...")

                noc_info = utils.noc_info(name, noc_log_path)
                noc_params = {'type': noc_info["type"], 'n_components': noc_info["n_components"], 
                            'preprocessing': noc_info["preprocessing"], 'quantile_threshold': noc_info["quantile_threshold"]}
                noc_start = datetime.strptime(noc_info["start_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                noc_end = datetime.strptime(noc_info["end_time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                _ = utils.create_noc(noc_info["network"], station, noc_info["channels"], 
                                     noc_start, noc_end, config, noc_params, attempt_find=True)

    # ---------------------------- Delete old files -------------------------------
    
    if updated_noc:  # Old files are deleted with the same frequency as NOC updates
        if verbose:
            print(f"Deleting files created before {delete_date}...")

        # Delete old NOCs
        utils.delete_old_nocs(nocs_path, '%Y-%m-%d', delete_date, noc_log_path, noc_types=('dynamic', 'inactive', 'unavailable'))

        # Delete old plots
        utils.delete_old_files(plots_path, '%Y%m%dT%H%M%SZ', delete_date)

        # Delete old mseed (raw data) files
        utils.delete_mseeds(data_path, network, stations, channels, start_day=delete_date - timedelta(days=10), 
                            end_day=delete_date)

    print(f"Updated process control. Total time: {datetime.now() - time0}.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Real-time monitoring using MSPC-PCA.")
    parser.add_argument("--config", default="monitoring/config.json", help="Path to the JSON configuration file.")
    args = parser.parse_args()

    monitoring(args.config)