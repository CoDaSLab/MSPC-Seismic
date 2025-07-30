"""
interruptions.py

This scripts scans mseed data in the given time range and calculates the interruptions or gaps (empty and overlaps).
Saves the interruptions and information about the scan times in CSV files.

Usage:
    python interruptions.py <starttime> <endtime> [-n <network1> <network2> ...] [-s <station1> <station2> ...] 
        [-c <channel1> <channel2> ...] [-dp <data_path>] [-nc <n_cpus>] [-v <verbose>]

Main functionalities:
    - Converts start and end times of the scans to datetime objects.
    - Reads a CSV file containing metadata on previous scans and finds overlaps in scan times with the current scan.
    - Reads mseed data corresponding to the given station and channel in the time range
    - Finds interruptions in the signals in those time ranges that had not been scanned previously (within the given
        range).
    - Writes information about the gaps that were found in a CSV file.
    - Writes information about the scans performed in another CSV file.

Arguments:
    starttime         - Start of the time interval to check.
    endtime           - End of the time interval to check.
    -n, --networks    - Names of the networks.
    -s, --stations    - Names of the stations.
    -c, --channels    - Names of the channels.
    -dp, --data_path  - Path to the folder where data is stored. Defaults is 'data/involcan/mseed/'.
    -gp, --gaps_path  - Path to the file where interruptions are stored. Default is /metadata/interruptions.csv' 
                        in the parent folder of `data_path`.
    -sp, --scans_path - Path to the file where scans metadata are stored. Default is '/metadata/scans.csv'
                        in the parent folder of `data_path`.
    -nc, --n_cpus      - Maximum number of CPUs for parallelization. Default is 1.
    -v, --verbose     - 0: no messages. 
                        1: shows when the process starts and ends (default).
                        2: same as 1 but also details overlaps with previous scans. 

Example:
    python interruptions.py '2021-09-16 04:00:00' '2021-09-19 08:20:00' -n 'C7' -s 'PA00' 'PA01' -c 'HHE' 'HHN' -nc 2
"""

from datetime import datetime
import pandas as pd
from data.scripts.get_filenames import get_filenames
import os
import obspy
import concurrent.futures
import time
import argparse
import warnings


def _scan_interruptions(starttime, endtime, network, station, channel, data_path, scans, n_cpus, verbose):
    """Auxiliary function that scans for interruptions for a single station and channel."""
    if verbose>=1: print(f'Scanning {network}.{station}..{channel}...')

    # Previous scans that are contained within the current scan
    scans_overlap_contained = scans[(scans["station"] == station) & \
                                    (scans["channel"] == channel) & \
                                    (starttime < pd.to_datetime(scans["scan_start"])) & \
                                    (pd.to_datetime(scans["scan_start"]) <= pd.to_datetime(scans["scan_end"])) & \
                                    (pd.to_datetime(scans["scan_end"]) < endtime)]

    if not scans_overlap_contained.empty:
        if verbose>=2: print(f"A previous scan for {network}.{station}..{channel} is contained within the time range of the current scan.")

    # Start and end times of the intervals to be scanned
    starttimes = [starttime] + pd.to_datetime(scans_overlap_contained["signal_end"]).to_list()
    endtimes = [endtime] + pd.to_datetime(scans_overlap_contained["signal_start"]).to_list()

    starttimes.sort()
    endtimes.sort()

    all_gaps = []
    all_scans_new = []

    for stime, etime in zip(starttimes, endtimes):
        stime_original = stime
        etime_original = etime

        # Previous scans that overlap with the beginning of the current scan
        scans_overlap_at_start = scans[(scans["station"] == station) & \
                                        (scans["channel"] == channel) & \
                                        (pd.to_datetime(scans["scan_start"]) <= stime) & \
                                        (stime <= pd.to_datetime(scans["scan_end"]))]

        if not scans_overlap_at_start.empty:
            if verbose>=2: print(f"A previous scan for {network}.{station}..{channel} overlaps with the start time of the current scan.")
            stime = max(pd.to_datetime(scans_overlap_at_start["signal_end"]))

        # Previous scans that overlap with the end of the current scan
        scans_overlap_at_end = scans[(scans["station"] == station) & \
                                      (scans["channel"] == channel) & \
                                      (pd.to_datetime(scans["scan_start"]) <= etime) & \
                                      (etime <= pd.to_datetime(scans["scan_end"]))]

        if not scans_overlap_at_end.empty:
            if verbose>=2: print(f"A previous scan for {network}.{station}..{channel} overlaps with the end time of the current scan.")
            etime = min(pd.to_datetime(scans_overlap_at_end["signal_start"]))

        t0 = time.time()

        if stime < etime:
            if verbose>=1:
                print(f'Scanning {network}.{station}..{channel} from {stime.strftime("%Y-%m-%d %H:%M:%S")} to {etime.strftime("%Y-%m-%d %H:%M:%S")}...')

            try:
                # Obtain file paths
                filenames = [data_path.rstrip('/') + '/' + file for file in get_filenames(network, station, channel, stime, etime)]

                # Check if the data for the first or last day in the time range are missing
                if not os.path.isfile(filenames[0]):
                    warnings.warn(f"Data for the first day ({filenames[0]}) for {network}.{station}..{channel} not found. " + \
                                   "The scan start time will be different than the one entered.")
                elif not os.path.isfile(filenames[len(filenames)-1]):
                    warnings.warn(f"Data for the last day ({filenames[len(filenames)-1]}) for {network}.{station}..{channel} not found. " + \
                                   "The scan end time will be different than the one entered.")

                # Read mseed data
                st = read_files_in_parallel(filenames, n_cpus)
                st.trim(obspy.UTCDateTime(stime), obspy.UTCDateTime(etime))  # remove data from the previous and following day

                # Create interruptions table
                gaps = st.get_gaps()

                # Start and end times of the signal in the scanned time interval
                st = st.sort(['starttime', 'endtime'])
                if st:
                    signal_start = st[0].stats.starttime.datetime  # start of the first trace
                    signal_end = st[len(st)-1].stats.endtime.datetime  # end of the last trace

                    if len(gaps) > 0:  # if there are gaps
                        gaps_df = pd.DataFrame(gaps)
                        gaps_df = gaps_df.drop(gaps_df.columns[2], axis=1)
                        gaps_df.columns = ["network", "station", "channel", "gap_start", "gap_end", "delta", "n_samples"]

                        gaps_df["gap_start"] = gaps_df["gap_start"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                        gaps_df["gap_end"] = gaps_df["gap_end"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                        gaps_df["gap_type"] = gaps_df["delta"].apply(lambda x: "empty" if x > 0 else "overlap")

                        # Swap start and end times of gap if it is an overlap
                        overlap_mask = gaps_df["gap_type"] == "overlap"
                        gaps_df.loc[overlap_mask, ["gap_start", "gap_end"]] = gaps_df.loc[overlap_mask, ["gap_end", "gap_start"]].values
                        all_gaps.append(gaps_df.round(2))

                        if verbose>=1: print(f"Gaps identified for {network}.{station}..{channel}.")

                    elif verbose>=1: print(f"No gaps were found for {network}.{station}..{channel}.")

                    t1 = time.time()

                    # Save scan metadata to csv
                    scans_new = pd.DataFrame({
                        "network": [network],
                        "station": [station],
                        "channel": [channel],
                        "scan_start": [stime.strftime("%Y-%m-%d %H:%M:%S")],
                        "scan_end": [etime.strftime("%Y-%m-%d %H:%M:%S")],
                        "signal_start": [signal_start.strftime("%Y-%m-%d %H:%M:%S") + "." + str(signal_start.microsecond)[:2]],
                        "signal_end": [signal_end.strftime("%Y-%m-%d %H:%M:%S") + "." + str(signal_end.microsecond)[:2]],
                        "execution_time": [round(t1-t0, 6)],
                        "save_time": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    })
                    all_scans_new.append(scans_new.round(4))
                    if verbose >=1: print(f"Scan metadata added for {network}.{station}..{channel}.")
                elif verbose>=1: print(f"No data found in the specified time range for {network}.{station}..{channel}.")

            except FileNotFoundError as e:
                print(e)

        elif verbose>=1: print(f"The time range from {stime_original} to {etime_original} for {network}.{station}..{channel} was already scanned.")

    return all_gaps, all_scans_new


def save_interruptions(starttime, endtime, networks, stations, channels, data_path = 'data/involcan/mseed/',
                       gaps_path = None, scans_path = None, n_cpus = 1, verbose = 1):
    """
    Calculates interruptions in mseed data in the given time range and saves the results and metadata in CSV files.

    Inputs
    starttime: datetime or string. Start of the time interval to check.
    endtime: datetime or string. End of the time interval to check.
    stations: string or list of strings. Names of the stations.
    channels: string or list of strings. Names of the channels.
    data_path: string. Path to the directory where data is stored.
    n_cpus: int. Maximum number of threads (default is 1).
    verbose: int. 0: no messages. 
                1: shows when the process starts and ends.
                2: same as 1 but also details overlaps with previous scans. 
    Outputs
    None
    """

    # Convert starttime and endtime to datetime objects
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime < endtime, "Start date cannot be later than end date."

    # Allows for single station and single channel input
    if isinstance(networks, str):
        networks = [networks]
    if isinstance(stations, str):
        stations = [stations]
    if isinstance(channels, str):
        channels = [channels]

    # CSV file names
    if scans_path is None:
        meta_path = os.path.join(os.path.dirname(data_path.rstrip('/')), 'metadata').replace('\\', '/')
        scans_path = os.path.join(meta_path, 'scans.csv').replace('\\', '/')
    if gaps_path is None:
        meta_path = os.path.join(os.path.dirname(data_path.rstrip('/')), 'metadata').replace('\\', '/')
        gaps_path = os.path.join(meta_path, 'interruptions.csv').replace('\\', '/')

    if verbose>=1: print("Scanning for interruptions...")

    # Check if the interruptions were already calculated
    try:
        os.makedirs(os.path.dirname(scans_path), exist_ok=True)
        scans = pd.read_csv(scans_path)
    except FileNotFoundError:
        scans = pd.DataFrame(columns=["station", "channel", "scan_start", "scan_end", "signal_start", "signal_end", "execution_time", "save_time"])

    t0 = datetime.now()

    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_cpus) as executor:
        for network in networks:
            for station in stations:
                for channel in channels:
                    tasks.append(executor.submit(_scan_interruptions, starttime, endtime, network, station, channel, 
                                                 data_path, scans.copy(), n_cpus, verbose))

        all_results_gaps = []
        all_results_scans = []
        for future in concurrent.futures.as_completed(tasks):
            gaps_result, scans_result = future.result()
            all_results_gaps.extend(gaps_result)
            all_results_scans.extend(scans_result)
    
    t1 = datetime.now()

    # Save all identified gaps
    if all_results_gaps:
        os.makedirs(os.path.dirname(gaps_path), exist_ok=True)
        try:
            gaps_table = pd.read_csv(gaps_path)
        except FileNotFoundError:
            gaps_table = pd.DataFrame(columns=["station", "channel", "gap_start", "gap_end", "delta", "n_samples", "gap_type"])
        gaps_table = pd.concat([gaps_table if not gaps_table.empty else None, pd.concat(all_results_gaps)], ignore_index=True)
        gaps_table = gaps_table.sort_values(by=["network", "station", "channel"])
        gaps_table.to_csv(gaps_path, header=True, index=False)
        if verbose>=1: print(f"All identified gaps added to {gaps_path}.")
    elif verbose>=1 and not stations:
        print("No stations provided for scanning.")
    elif verbose>=1 and stations and not channels:
        print("No channels provided for scanning.")
    elif verbose>=1 and stations and channels:
        print("No new gaps were found in the scanned intervals.")

    # Save all scan metadata
    if all_results_scans:
        scans = pd.concat([scans if not scans.empty else None, pd.concat(all_results_scans)], ignore_index=True)
        scans.to_csv(scans_path, header=True, index=False)
        if verbose >=1: print(f"All scan metadata added to {scans_path}.")
    
    print(f"Process completed. Total time: {t1-t0}.")


def process_file(filename):
    """
    Process a file individually.
    """
    try:
        st = obspy.read(filename, format="MSEED")  # Read the file using obspy
        return st
    except FileNotFoundError:
        print(f"File '{filename}' not found. It will be skipped.")
        return None


def read_files_in_parallel(filenames, n_cpus):
    """
    Read the files in parallel using ThreadPoolExecutor.
    """
    ST = obspy.Stream()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_cpus) as executor:
        futures = {executor.submit(process_file, filename): filename for filename in filenames}

        for future in concurrent.futures.as_completed(futures):
            st = future.result()
            if st is not None:
                for tr in st:
                    ST.append(tr)

    return ST


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan mseed data for interruptions and save metadata.")

    parser.add_argument("starttime", type=str, help="Start time in YYYY-MM-DD HH:MM:SS format.")
    parser.add_argument("endtime", type=str, help="End time in YYYY-MM-DD HH:MM:SS format.")
    parser.add_argument("-n", "--networks", nargs='+', help="Network names.")
    parser.add_argument("-s", "--stations", nargs='+', help="Station names.")
    parser.add_argument("-c", "--channels", nargs='+', help="Channel names.")
    parser.add_argument("-dp", "--data_path", type=str, default="data/involcan/mseed/",
                        help="Path to data folder.")
    parser.add_argument("-gp", "--gaps_path", type=str, default=None,
                         help="Path to save interruptions data.")
    parser.add_argument("-sp", "--scans_path", type=str, default=None,
                         help="Path to save scan metadata.")
    parser.add_argument("-nc", "--n_cpus", type=int, default=1, help="Maximum number of CPUS for parallelization.")
    parser.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2], default=1,
                        help="Verbose level: 0 = silent, 1 = basic, 2 = detailed.")
    args = parser.parse_args()

    save_interruptions(args.starttime, args.endtime, args.networks, args.stations, args.channels, args.data_path,
                       args.gaps_path, args.scans_path, args.n_cpus, args.verbose)
