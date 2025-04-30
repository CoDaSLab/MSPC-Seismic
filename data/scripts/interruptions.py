"""
interruptions.py

This scripts scans mseed data in the given time range and calculates the interruptions or gaps (empty and overlaps).
Saves the interruptions and information about the scan times in CSV files.

Usage:
    python interruptions.py <starttime> <endtime> <sensors> <channels> [<--gaps_path>] [<--scans_path>] [<--verbose>]

Main functionalities:
    - Converts start and end times of the scans to datetime objects.
    - Reads a CSV file containing metadata on previous scans and finds overlaps in scan times with the current scan.
    - Reads mseed data corresponding to the given sensor and channel in the time range
    - Finds interruptions in the signals in those time ranges that had not been scanned previously (within the given
        range).
    - Writes information about the gaps that were found in a CSV file.
    - Writes information about the scans performed in another CSV file.

Arguments:
    starttime    - Start of the time interval to check.
    endtime      - End of the time interval to check.
    --sensors    - Names of the sensors.
    --channels   - Names of the channels.
    --gaps_path  - Path to the file where interruptions are stored. Default is 'data/involcan/metadata/interruptions.csv'.
    --scans_path - Path to the file where scans metadata are stored. Default is 'data/involcan/metadata/scans.csv'.
    --verbose    - 0: no messages. 
                   1: shows when the process starts and ends (default).
                   2: same as 1 but also details overlaps with previous scans. 

Example:
    python interruptions.py '2021-09-16 04:00:00' '2021-09-19 08:20:00' --sensors 'PA00' 'PA01' --channels 'HHE' 'HHN' 
"""

from datetime import datetime
import pandas as pd
from data.scripts.data_check import get_filenames
import os
import obspy
import concurrent.futures
import time
import argparse


def _scan_interruptions(starttime, endtime, sensor, channel, scans, verbose):
    """Auxiliary function that scans for interruptions for a single sensor and channel."""
    if verbose>=1: print(f'Scanning {sensor} - {channel}...')

    # Previous scans that are contained within the current scan
    scans_overlap_contained = scans[(scans["sensor"] == sensor) & \
                                    (scans["channel"] == channel) & \
                                    (starttime < pd.to_datetime(scans["scan_start"])) & \
                                    (pd.to_datetime(scans["scan_start"]) <= pd.to_datetime(scans["scan_end"])) & \
                                    (pd.to_datetime(scans["scan_end"]) < endtime)]

    if not scans_overlap_contained.empty:
        if verbose>=2: print(f"A previous scan for {sensor} - {channel} is contained within the time range of the current scan.")

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
        scans_overlap_at_start = scans[(scans["sensor"] == sensor) & \
                                        (scans["channel"] == channel) & \
                                        (pd.to_datetime(scans["scan_start"]) <= stime) & \
                                        (stime <= pd.to_datetime(scans["scan_end"]))]

        if not scans_overlap_at_start.empty:
            if verbose>=2: print(f"A previous scan for {sensor} - {channel} overlaps with the start time of the current scan.")
            stime = max(pd.to_datetime(scans_overlap_at_start["signal_end"]))

        # Previous scans that overlap with the end of the current scan
        scans_overlap_at_end = scans[(scans["sensor"] == sensor) & \
                                      (scans["channel"] == channel) & \
                                      (pd.to_datetime(scans["scan_start"]) <= etime) & \
                                      (etime <= pd.to_datetime(scans["scan_end"]))]

        if not scans_overlap_at_end.empty:
            if verbose>=2: print(f"A previous scan for {sensor} - {channel} overlaps with the end time of the current scan.")
            etime = min(pd.to_datetime(scans_overlap_at_end["signal_start"]))

        t0 = time.time()

        if stime < etime:
            if verbose>=1:
                print(f'Scanning {sensor} - {channel} from {stime.strftime("%Y-%m-%d %H:%M:%S")} to {etime.strftime("%Y-%m-%d %H:%M:%S")}...')

            # Obtain file paths
            start_day = stime.replace(hour=0, minute=0, second=0)
            try:
                filenames = get_filenames(start_day, etime, sensor, channel)[0]

                # Check if the data for the first or last day in the time range are missing
                if not os.path.isfile(filenames[0]):
                    raise FileNotFoundError(f"Data for the first day ({filenames[0]}) for {sensor} - {channel} not found. Interruptions could not be calculated.")
                elif not os.path.isfile(filenames[len(filenames)-1]):
                    raise FileNotFoundError(f"Data for the last day ({filenames[len(filenames)-1]}) for {sensor} - {channel} not found. Interruptions could not be calculated.")

                # Read mseed data
                st = read_files_in_parallel(filenames)
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
                        gaps_df = gaps_df.drop(gaps_df.columns[[0, 2]], axis=1)
                        gaps_df.columns = ["sensor", "channel", "gap_start", "gap_end", "delta", "n_samples"]

                        gaps_df["gap_start"] = gaps_df["gap_start"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                        gaps_df["gap_end"] = gaps_df["gap_end"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                        gaps_df["gap_type"] = gaps_df["delta"].apply(lambda x: "empty" if x > 0 else "overlap")

                        # Swap start and end times of gap if it is an overlap
                        overlap_mask = gaps_df["gap_type"] == "overlap"
                        gaps_df.loc[overlap_mask, ["gap_start", "gap_end"]] = gaps_df.loc[overlap_mask, ["gap_end", "gap_start"]].values
                        all_gaps.append(gaps_df.round(2))

                        if verbose>=1: print(f"Gaps identified for {sensor} - {channel}.")

                    elif verbose>=1: print(f"No gaps were found for {sensor} - {channel}.")

                    t1 = time.time()

                    # Save scan metadata to csv
                    scans_new = pd.DataFrame({
                        "sensor": [sensor],
                        "channel": [channel],
                        "scan_start": [stime.strftime("%Y-%m-%d %H:%M:%S")],
                        "scan_end": [etime.strftime("%Y-%m-%d %H:%M:%S")],
                        "signal_start": [signal_start.strftime("%Y-%m-%d %H:%M:%S") + "." + str(signal_start.microsecond)[:2]],
                        "signal_end": [signal_end.strftime("%Y-%m-%d %H:%M:%S") + "." + str(signal_end.microsecond)[:2]],
                        "execution_time": [round(t1-t0, 6)],
                        "save_time": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    })
                    all_scans_new.append(scans_new.round(4))
                    if verbose >=1: print(f"Scan metadata added for {sensor} - {channel}.")
                elif verbose>=1: print(f"No data found in the specified time range for {sensor} - {channel}.")

            except FileNotFoundError as e:
                print(e)

        elif verbose>=1: print(f"The time range from {stime_original} to {etime_original} for {sensor} - {channel} was already scanned.")

    return all_gaps, all_scans_new


def save_interruptions(starttime, endtime, sensors, channels,
                     gaps_path = 'data/involcan/metadata/interruptions.csv',
                     scans_path = 'data/involcan/metadata/scans.csv', verbose = 1):
    """
    Calculates interruptions in mseed data in the given time range and saves the results and metadata in CSV files.

    Inputs
    starttime: datetime or string. Start of the time interval to check.
    endtime: datetime or string. End of the time interval to check.
    sensors: string or list of strings. Names of the sensors.
    channels: string or list of strings. Names of the channels.
    gaps_path: string. Path to the file where interruptions are stored.
    scans_path: string. Path to the file where scans metadata are stored.
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

    # Allows for single sensor and single channel input
    if isinstance(sensors, str):
        sensors = [sensors]
    if isinstance(channels, str):
        channels = [channels]

    if verbose>=1: print("Scanning for interruptions...")

    # Check if the interruptions were already calculated
    try:
        scans = pd.read_csv(scans_path)
    except FileNotFoundError:
        scans = pd.DataFrame(columns=["sensor", "channel", "scan_start", "scan_end", "signal_start", "signal_end", "execution_time", "save_time"])

    tasks = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for sensor in sensors:
            for channel in channels:
                tasks.append(executor.submit(_scan_interruptions, starttime, endtime, sensor, channel, scans.copy(), verbose))

        all_results_gaps = []
        all_results_scans = []
        for future in concurrent.futures.as_completed(tasks):
            gaps_result, scans_result = future.result()
            all_results_gaps.extend(gaps_result)
            all_results_scans.extend(scans_result)

    # Save all identified gaps
    if all_results_gaps:
        try:
            gaps_table = pd.read_csv(gaps_path)
        except FileNotFoundError:
            gaps_table = pd.DataFrame(columns=["sensor", "channel", "gap_start", "gap_end", "delta", "n_samples", "gap_type"])
        gaps_table = pd.concat([gaps_table if not gaps_table.empty else None, pd.concat(all_results_gaps)], ignore_index=True)
        gaps_table = gaps_table.sort_values(by=["sensor", "channel"])
        gaps_table.to_csv(gaps_path, header=True, index=False)
        if verbose>=1: print(f"All identified gaps added to {gaps_path}.")
    elif verbose>=1 and not sensors:
        print("No sensors provided for scanning.")
    elif verbose>=1 and sensors and not channels:
        print("No channels provided for scanning.")
    elif verbose>=1 and sensors and channels:
        print("No new gaps were found in the scanned intervals.")

    # Save all scan metadata
    if all_results_scans:
        scans = pd.concat([scans if not scans.empty else None, pd.concat(all_results_scans)], ignore_index=True)
        scans.to_csv(scans_path, header=True, index=False)
        if verbose >=1: print(f"All scan metadata added to {scans_path}.")


def process_file(filename, verbose=False):
    """
    Process a file individually.
    """
    try:
        if verbose:
            print(f"Reading file: {filename}")
        st = obspy.read(filename, format="MSEED")  # Read the file using obspy
        return st
    except FileNotFoundError:
        print(f"File '{filename}' not found. It will be skipped.")
        return None


def read_files_in_parallel(filenames):
    """
    Read the files in parallel using ThreadPoolExecutor.
    """
    ST = obspy.Stream()
    with concurrent.futures.ThreadPoolExecutor() as executor:
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
    parser.add_argument("--sensors", nargs='+', help="Name of the sensor.")
    parser.add_argument("--channels", nargs='+', help="Name of the channel.")

    parser.add_argument("--gaps_path", type=str, default="data/involcan/metadata/interruptions.csv",
                        help="Path to save interruptions data.")
    parser.add_argument("--scans_path", type=str, default="data/involcan/metadata/scans.csv",
                        help="Path to save scan metadata.")
    parser.add_argument("--verbose", type=int, choices=[0, 1, 2], default=1,
                        help="Verbose level: 0 = silent, 1 = basic, 2 = detailed.")
    args = parser.parse_args()

    save_interruptions(args.starttime, args.endtime, args.sensors, args.channels,
                       args.gaps_path, args.scans_path, args.verbose)
