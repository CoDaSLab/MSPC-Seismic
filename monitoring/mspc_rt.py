import os
from mspc_pca.mspc import DyQ_tt, plot_DyQ
from datetime import datetime, timedelta
import csv

def mspc(nocs, test, starttime, endtime, window_size, window_shift=None, plot=False,
         anomaly_log_path="data/involcan/metadata/anomaly_log.csv", 
         noc_log_path = "data/involcan/metadata/noc_list.csv", 
         nocs_path = "data/involcan/nocs/", verbose=False):
    """
    Multivariate Statistical Process Control with PCA. Uses NOC instances to calculate
    the D and Q values for test data. Updates the NOC instances.

    Parameters
    ----------
        nocs (list of NOC instances): 
            NOCs used for monitoring. 
        starttime (datetime): 
            Start time of the first window.
        endtime (datetime): 
            End time of the last window.
        window_size (int): 
            Time window size in seconds. Used for calculating anomaly times.
        window_shift (int): 
            Interval between the start of windows in seconds.
            Used for calculating anomaly times (default: window_size).
        plot (bool):
            If True, plots the D and Q statisttics, along with the thresholds.
        anomaly_log_path (str): 
            Path to the CSV file that stores information about anomalies 
            (default: "data/involcan/metadata/anomaly_log.csv").
        noc_log_path (str): 
            Path to the CSV file that stores information about NOCs
            (default: "data/involcan/metadata/noc_list.csv").
        nocs_path (str):
            Directory where nocs are saved (default: "data/involcan/nocs").
        verbose (bool): 
            Whether to print detailed messages (default: False).
    """
    
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Error: Start date cannot be after end date."
    
    if window_shift is None:
        window_shift = window_size

    time0 = datetime.now()

    rows = []
    for noc in nocs:
        if verbose:
            print(f"Calculating for NOC {noc.name}...")
        # Calculate D and Q statistics
        _, _, D_test, Q_test, D_threshold, Q_threshold = DyQ_tt(noc.features, test, noc.n_components, noc.preprocessing, 
                                                                alpha=noc.alpha, plot=False, 
                                                                percentile_threshold=noc.percentile_threshold)

        # Indices of anomalous windows
        # Considered anomaly if three consecutive windows have D or Q values above the threshold
        anomaly_D_ids = set()
        for i in range(len(D_test) - 2):
            if D_test[i] > noc.D_threshold and D_test[i+1] > noc.D_threshold and D_test[i+2] > noc.D_threshold:
                anomaly_D_ids.update((i, i+1, i+2))

        anomaly_Q_ids = set()
        for i in range(len(Q_test) - 2):
            if Q_test[i] > noc.Q_threshold and Q_test[i+1] > noc.Q_threshold and Q_test[i+2] > noc.Q_threshold:
                anomaly_Q_ids.update((i, i+1, i+2))

        anomaly_ids = list(anomaly_D_ids.union(anomaly_Q_ids))

        # Times for the start and end of the anomalous windows
        start_times = [starttime + timedelta(seconds=window_shift * i) for i in range(test.shape[0])]
        start_times = [datetime.strftime(label, '%Y-%m-%dT%H:%M:%SZ') for label in start_times]
        end_times = [starttime + timedelta(seconds=window_shift * i + window_size) for i in range(test.shape[0])]
        end_times = [datetime.strftime(label, '%Y-%m-%dT%H:%M:%SZ') for label in end_times]
        anomaly_start_times = [start_times[i] for i in anomaly_ids]
        anomaly_end_times = [end_times[i] for i in anomaly_ids]

        for i in range(len(anomaly_ids)):
            rows.append({'network':noc.network, 'station':noc.station, 
                        'anomaly_start_time':anomaly_start_times[i], 'anomaly_end_time':anomaly_end_times[i],
                        'control_start_time':starttime, 'control_end_time':endtime,
                        'D_anomaly':D_test[i], 'Q_anomaly':Q_test[i], 'D_threshold':D_threshold, 'Q_threshold':Q_threshold,
                        'NOC':noc.name})
        
        # Update dynamic NOCs if there are no anomalies
        if len(anomaly_ids) == 0 and noc.type == 'dynamic':
            noc.update(new_features=test, new_obs_labels=end_times)

            # Save NOC
            noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
            if verbose:
                print(f"NOC {noc.name} updated.")
        noc.write_csv(noc_log_path)

        # Plot D and Q statistics with thresholds for all NOCs
        if plot:
            plot_DyQ(D_test, Q_test, D_threshold, Q_threshold, event_index=anomaly_ids)

    # Create CSV file parent directory if it does not exist
    os.makedirs(os.path.dirname(anomaly_log_path), exist_ok=True)
    
    # Save anomaly data in CSV file
    no_file = not os.path.isfile(anomaly_log_path) or os.path.getsize(anomaly_log_path) == 0
    with open(anomaly_log_path, mode="a", newline='', encoding="utf-8") as file:
        fields = ["network", "station", "anomaly_start_time", "anomaly_end_time", "control_start_time", 
                  "control_end_time", "D_anomaly", "Q_anomaly", "D_threshold", "Q_threshold", "NOC"]
        writer = csv.DictWriter(file, fieldnames=fields)
        
        if no_file:
            writer.writeheader()
        writer.writerows(rows)
    
    if verbose:
        print(f"Finished all MSPC calculations. Time taken: {datetime.now() - time0}.")
    