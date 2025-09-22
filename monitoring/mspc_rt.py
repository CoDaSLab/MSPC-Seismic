import os
from mspc_pca.plot import plot_DQ
from datetime import datetime, timedelta, timezone
import csv
import numpy as np
import matplotlib.pyplot as plt
from monitoring.NOC import NOC

def mspc(nocs, test, starttime, endtime, window_size, window_shift=None, 
         missing_rates=None, plot=False, update_log=True,
         anomaly_log_path="data/involcan/metadata/anomaly_log.csv",
         nocs_path = "data/involcan/nocs/", verbose=False):
    """
    Multivariate Statistical Process Control with PCA. Uses NOC instances to calculate
    the D and Q values for test data. Updates the NOC instances.

    Parameters
    ----------
        nocs (list of str or list of NOC)
            Paths to the NOCs (or the NOCs themselves) used for training. 
        test (numpy array)
            Test data
        starttime (datetime)
            Start time of the first window (UTC).
        endtime (datetime)
            End time of the last window (UTC).
        window_size (int)
            Time window size in seconds. Used for calculating anomaly times.
        window_shift (int)
            Interval between the start of windows in seconds.
            Used for calculating anomaly times (default: window_size).
        missing_rates (list)
            Rate of missing values for each observation in the test data 
            (default: None).
        plot (bool)
            If True, plots the D and Q statistics, along with the thresholds.
        update_log (bool)
            If True, updated the anomaly log with the windows that surpass the threshold
            (default: True)
        anomaly_log_path (str)
            Path to the CSV file that stores information about anomalies 
            (default: "data/involcan/metadata/anomaly_log.csv").
        nocs_path (str)
            Directory where nocs are saved (default: "data/involcan/nocs").
        verbose (bool)
            Whether to print detailed messages (default: False).
    """
    
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    if not isinstance(nocs, list):
        nocs = [nocs]

    assert starttime <= endtime, "Error: Start date cannot be after end date."
    
    if window_shift is None:
        window_shift = window_size

    time0 = datetime.now()

    # Start and end times of windows
    start_times = [starttime + timedelta(seconds=window_shift * i) for i in range(test.shape[0])]
    start_times = [datetime.strftime(label, '%Y-%m-%dT%H:%M:%SZ') for label in start_times]
    end_times = [starttime + timedelta(seconds=window_shift * i + window_size) for i in range(test.shape[0])]
    end_times = [datetime.strftime(label, '%Y-%m-%dT%H:%M:%SZ') for label in end_times]

    rows = []
    for noc in nocs:
        if isinstance(noc, str):
            try:
                noc = NOC.load(noc)
            except Exception as e:
                print(f"Could not run MSPC on the NOC at {noc}: {e}")
                continue
        if verbose:
            print(f"Calculating for NOC {noc.name}...")

        # Calculate D and Q statistics
        D_test, Q_test = noc.calculate_DQ_test(test, end_times, missing_rates=missing_rates,
                              store_dq=True)
        noc.save(os.path.join(nocs_path, noc.name).replace('\\', '/'))
        
        # Indices of anomalous windows (surpass the threshold)
        anomaly_D_ids = set([i for i, value in enumerate(noc.D_test[-test.shape[0]:]) if value > noc.D_threshold])
        anomaly_Q_ids = set([i for i, value in enumerate(noc.Q_test[-test.shape[0]:]) if value > noc.Q_threshold])
        anomaly_ids = sorted(list(anomaly_D_ids.union(anomaly_Q_ids)))

        # Times for the start and end of the anomalous windows
        anomaly_start_times = [start_times[i] for i in anomaly_ids]
        anomaly_end_times = [end_times[i] for i in anomaly_ids]

        for i in range(len(anomaly_ids)):
            rows.append({'network':noc.network, 'station':noc.station, 
                        'anomaly_start_time':anomaly_start_times[i], 'anomaly_end_time':anomaly_end_times[i],
                        'control_start_time':starttime.strftime('%Y-%m-%dT%H:%M:%SZ'), 'control_end_time':endtime.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'D_anomaly':D_test[i], 'Q_anomaly':Q_test[i], 
                        'D_threshold':round(noc.D_threshold,4), 'Q_threshold':round(noc.Q_threshold,4),
                        'NOC':noc.name})

        # Plot D and Q statistics with threshold
        if plot:
            plot_DQ(D_test, Q_test, noc.D_threshold, noc.Q_threshold, event_index=anomaly_ids)
    
    # Save anomaly data in CSV file
    if update_log:
        # Create CSV file parent directory if it does not exist
        os.makedirs(os.path.dirname(anomaly_log_path), exist_ok=True)

        no_file = not os.path.isfile(anomaly_log_path) or os.path.getsize(anomaly_log_path) == 0
        with open(anomaly_log_path, mode="a", newline='', encoding="utf-8") as file:
            fields = ["network", "station", "anomaly_start_time", "anomaly_end_time", "control_start_time", 
                    "control_end_time", "D_anomaly", "Q_anomaly", "D_threshold", "Q_threshold", "NOC"]
            writer = csv.DictWriter(file, fieldnames=fields)
            
            if no_file:
                writer.writeheader()
            writer.writerows(rows)
    elif verbose:
        print(f"Values over the threshold for NOC {noc.name}:")
        for row in rows:
            print(row)
    
    if verbose:
        print(f"Finished all MSPC calculations. Time taken: {datetime.now() - time0}.")
    

def get_anomalies(test, threshold, criterion='consecutive', n_consecutive=3):
    """
    Applies a criterion to obtain the indices of anomalous windows given a list of
    values and threshold.

    Parameters
    ----------
    test (list)
        Test values.
    threshold (float)
        Upper control limit for the control statistic
    criterion (str)
        Criterion for considering an observation anomalous.
        - `'consecutive'` (default): All observations in a group of `n_consecutive` 
            consecutive observations above the threshold are anomalous.
    n_consecutive (int)
        If `criterion == 'consecutive'`, number of consecutive observations
        above the threshold to be considered an anomaly (default: 3).

    Returns
    -------
    anomaly_ids (set)
        Set of anomaly indices.
    """
    n_obs = len(test)
    anomaly_ids = set()
    
    if criterion == 'consecutive':
        assert n_obs >= n_consecutive, f"At least {n_consecutive} observations are needed, but {n_obs} were given."

        for i in range(n_obs - n_consecutive + 1):
            if np.all(test[i:i+n_consecutive] > threshold):
                anomaly_ids.update(np.arange(i, i+n_consecutive))

    return anomaly_ids 


def get_anomalies_DQ(D_test, Q_test, D_threshold, Q_threshold, 
                  criterion='consecutive', n_consecutive=3):
    """
    Applies a criterion to obtain the indices of anomalous windows given the D and Q statistics
    values and threshold.

    Parameters
    ----------
    D_test (list)
        D-statistic values.
    Q_test (list)
        Q-statistic values.
    D_threshold (float)
        Upper control limit for the D-statistic
    Q_threshold (float)
        Upper control limit for the Q-statistic
    criterion (str)
        Criterion for considering an observation anomalous.
        - `'consecutive'` (default): All observations in a group of `n_consecutive` 
            consecutive observations above the threshold are anomalous.
    n_consecutive (int)
        If `criterion == 'consecutive'`, number of consecutive observations
        above the threshold to be considered an anomaly (default: 3).

    Returns
    -------
    anomaly_D_ids (set)
        Set of anomaly indices for the D-statistic.
    anomaly_Q_ids (set)
        Set of anomaly indices for the Q-statistic.
    """
    assert len(D_test) == len(Q_test), "The number of D values and the number of Q values are not the same."

    n_obs = len(D_test)
    anomaly_D_ids = set()
    anomaly_Q_ids = set()
    
    if criterion == 'consecutive':
        assert n_obs >= n_consecutive, f"At least {n_consecutive} observations are needed, but only {n_obs} were given."

        for i in range(n_obs - n_consecutive + 1):
            if np.all(D_test[i:i+n_consecutive] > D_threshold):
                anomaly_D_ids.update(np.arange(i, i+n_consecutive))

            if np.all(Q_test[i:i+n_consecutive] > Q_threshold):
                anomaly_Q_ids.update(np.arange(i, i+n_consecutive))

    return anomaly_D_ids, anomaly_Q_ids


def plot_anomalies_T(noc:NOC, starttime, endtime, T_weight=None, T_norm_quantile=0.5, T_threshold_quantile=None,
                     criterion='consecutive', n_consecutive=3, save=True, save_path="data/involcan/nocs/plots", 
                     opacity=None, plot_train=True, logscale=False, bar_width=0.8, show=False):
    """
    Plots T-scores and highlights anomalies (according to a criterion) in a different color.

    Parameters
    ----------
    noc (NOC)
        NOC instance.
    starttime (datetime)
        Start of the time range to plot (UTC)
    endtime (datetime)
        End of the time range to plot (UTC)
    T_weight (float)
        Weight for T-score calculation.
    T_norm_quantile (float)
        Quantile of D and Q values used for normalization in T-score calculation 
        (default: 0.5).
    T_threshold_quantile (float)
        Quantile of T-scores used as threshold for detecting anomalies. `noc.quantile_threshold`
        by default.
    save (bool)
        If True, saves the graph in `save_path` (default: True)
    save_path (str)
        Path to save the plot.
    criterion (str)
        Criterion for considering an observation anomalous.
        - `'consecutive'` (default): All observations in a group of `n_consecutive` 
            consecutive observations above the threshold are anomalous.
            This is the only method implemented so far.
    n_consecutive (int)
        If `criterion == 'consecutive'`, number of consecutive observations
        above the threshold to be considered an anomaly (default: 3).
    opacity (list or None)
        Opacity of the bars in the plot. If None, uses rate of missing values 
        as opacity.
    plot_train (bool)
        If True, plots T values for both training and test data. 
        If False, only plots T for test data.
    logscale (bool)
        If True, uses a logarithmic scale (default: False).
    bar_width (float)
        Width of the bars on the plot (default: 0.8).
    show (bool)
        If True, shows graph (default: False).
    """
    # Obtain T values to plot
    T_train, T_test = noc.calculate_T_test(weight=T_weight, norm_quantile=T_norm_quantile)
    if T_threshold_quantile is None:
        T_threshold_quantile = noc.quantile_threshold
    T_threshold = np.quantile(T_train, T_threshold_quantile)
    time_labels = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in noc.test_labels]
    T_plot = [value for value, date in zip(T_test, time_labels) if starttime < date <= endtime]

    # Get anomalies according to the new criterion
    anomaly_ids = get_anomalies(T_plot, T_threshold, criterion = criterion, n_consecutive = n_consecutive)
    anomaly_ids = sorted(list(anomaly_ids))
    
    if plot_train:
        anomaly_ids = [i + len(T_train) for i in anomaly_ids]

    # Plot D and Q values and highlight anomalies
    event_index = anomaly_ids if len(anomaly_ids) > 0 else None
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig, axes = noc.plot_T_test(T_train, T_test, starttime, endtime, threshold_quantiles=T_threshold_quantile, 
                                plot_train=False, logscale=logscale, event_index=event_index, opacity=opacity, bar_width=bar_width)
    plt.tight_layout()

    if save:
        plt.savefig(os.path.join(save_path))
    if show:
        plt.show()
    
    return fig, axes


def plot_anomalies_DQ(noc:NOC, starttime, endtime, criterion='consecutive', n_consecutive=3, 
                   save=True, save_path="data/involcan/nocs/plots", opacity=None,
                   plot_train=True, logscale=False, bar_width=0.8, show=False):
    """
    Plots D and Q-statistics and highlights anomalies (according to a criterion) in a different color.

    Parameters
    ----------
    noc (NOC)
        NOC instance.
    starttime (datetime)
        Start of the time range to plot (UTC)
    endtime(datetime)
        End of the time range to plot (UTC)
    save (bool)
        If True, saves the graph in `save_path` (default: True)
    save_path (str)
        Path to save the plot.
    criterion (str)
        Criterion for considering an observation anomalous.
        - `'consecutive'` (default): All observations in a group of `n_consecutive` 
            consecutive observations above the threshold are anomalous.
            This is the only method implemented so far.
    n_consecutive (int)
        If `criterion == 'consecutive'`, number of consecutive observations
        above the threshold to be considered an anomaly (default: 3).
    opacity (list or None)
        Opacity of the bars in the plot. If None, uses rate of missing values 
        as opacity.
    plot_train (bool)
        If True, plots D and Q values for both training and test data. 
        If False, only plots D and Q for test data.
    logscale (bool)
        If True, uses a logarithmic scale (default: False).
    bar_width (float)
        Width of the bars on the plot (default: 0.8).
    show (bool)
        If True, shows graph (default: False).
    """
    # Obtain D and Q values to plot
    time_labels = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in noc.test_labels]
    D_plot = [value for value, date in zip(noc.D_test, time_labels) if starttime < date <= endtime]
    Q_plot = [value for value, date in zip(noc.Q_test, time_labels) if starttime < date <= endtime]

    # Get anomalies according to the new criterion
    anomaly_D_ids, anomaly_Q_ids = get_anomalies_DQ(D_plot, Q_plot, noc.D_threshold, noc.Q_threshold,
                                                 criterion = criterion, n_consecutive = n_consecutive)
    anomaly_ids = sorted(list(anomaly_D_ids.union(anomaly_Q_ids)))
    
    if plot_train:
        anomaly_ids = [i + len(noc.D) for i in anomaly_ids]

    # Plot D and Q values and highlight anomalies
    event_index = anomaly_ids if len(anomaly_ids) > 0 else None
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig, axes = noc.plot_DQ_test(starttime, endtime, plot_train=False, logscale=logscale, 
                                 event_index=event_index, opacity=opacity, bar_width=bar_width)
    plt.tight_layout()

    if save:
        plt.savefig(os.path.join(save_path))
    if show:
        plt.show()
    
    return fig, axes
