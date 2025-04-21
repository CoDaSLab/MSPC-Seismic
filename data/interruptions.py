"""
interruptions.py

This scripts scans seismic data in the given time range and calculates the interruptions or gaps (empty and overlaps).
Saves the interruptions and information about the scan times in CSV files.

Usage:
    python interruptions.py <starttime> <endtime> <sensor> <channel> [<--gaps_path>] [<--scans_path>] [<--verbose>]

Main functionalities:
    - Converts start and end times of the scans to datetime objects.
    - Reads a CSV file containing metadata on previous scans and finds overlaps in scan times with the current scan.
    - Reads seismic data corresponding to the given sensor and channel in the time range
    - Finds interruptions in the signals in those time ranges that had not been scanned previously (within the given
        range).
    - Writes information about the gaps that were found in a CSV file.
    - Writes information about the scans performed in another CSV file.

Arguments:
    starttime    - Start of the time interval to check.
    endtime      - End of the time interval to check.
    sensor       - Name of the sensor.
    channel      - Name of the channel.
    --gaps_path  - Path to the file where interruptions are stored. Default is 'data/metadata/interruptions.csv'.
    --scans_path - Path to the file where scans metadata are stored. Default is 'data/metadata/scans.csv'.
    --verbose    - 0: no messages. 
                   1: shows when the process starts and ends.
                   2: same as 1 but also details overlaps with previous scans. 

Example:
    python interruptions.py '2021-09-16 04:00:00' '2021-09-19 08:20:00' PA00 HHE 
"""

from datetime import datetime
import pandas as pd
from data_check import get_filenames
import os
import obspy
import concurrent.futures
import time
import argparse

"""
function: save_interruptions(sensor, channel, starttime, endtime, 
                            gaps_path = 'data/metadata/interruptions.csv',
                            scans_path = 'data/metadata/scans.csv', verbose = 1)

Main function of the script. Calculates interruptions in seismic data.

Inputs
starttime: datetime or string. Start of the time interval to check.
endtime: datetime or string. End of the time interval to check.
sensor: string. Name of the sensor.
channel: string. Name of the channel.
gaps_path: string. Path to the file where interruptions are stored.
scans_path: string. Path to the file where scans metadata are stored.
verbose: int. 0: no messages. 
              1: shows when the process starts and ends.
              2: same as 1 but also details overlaps with previous scans. 
Outputs
None
"""

def save_interruptions(starttime, endtime, sensor, channel,
                       gaps_path = 'data/metadata/interruptions.csv',
                       scans_path = 'data/metadata/scans.csv', verbose = 1):
    
    # Convert starttime and endtime to datetime objects
    if type(starttime) == str:
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if type(endtime) == str:
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime < endtime, "Start date cannot be later than end date."

    if verbose>=1: print("Scanning for interruptions...")

    # Check if the interruptions were already calculated
    scans = pd.read_csv(scans_path)

    # Previous scans that are contained within the current scan
    scans_overlap_contained = scans[(scans["sensor"] == sensor) & \
                                (scans["channel"] == channel) & \
                                (starttime < pd.to_datetime(scans["scan_start"])) & \
                                (pd.to_datetime(scans["scan_start"]) <= pd.to_datetime(scans["scan_end"])) & \
                                (pd.to_datetime(scans["scan_end"]) < endtime)]
    
    if not scans_overlap_contained.empty:
        if verbose>=2: print("A previous scan is contained within the time range of the current scan.")

    # Start and end times of the intervals to be scanned
    starttimes = [starttime] + pd.to_datetime(scans_overlap_contained["signal_end"]).to_list()
    endtimes = [endtime] + pd.to_datetime(scans_overlap_contained["signal_start"]).to_list()

    starttimes.sort()
    endtimes.sort()    

    for stime, etime in zip(starttimes, endtimes):
        stime_original = stime
        etime_original = etime

        # Previous scans that overlap with the beginning of the current scan
        scans_overlap_at_start = scans[(scans["sensor"] == sensor) & \
                                    (scans["channel"] == channel) & \
                                    (pd.to_datetime(scans["scan_start"]) <= stime) & \
                                    (stime <= pd.to_datetime(scans["scan_end"]))]
        
        if not scans_overlap_at_start.empty:
            if verbose>=2: print("A previous scan overlaps with the start time of the current scan.")
            stime = max(pd.to_datetime(scans_overlap_at_start["signal_end"]))

        # Previous scans that overlap with the end of the current scan
        scans_overlap_at_end = scans[(scans["sensor"] == sensor) & \
                                    (scans["channel"] == channel) & \
                                    (pd.to_datetime(scans["scan_start"]) <= etime) & \
                                    (etime <= pd.to_datetime(scans["scan_end"]))]
        
        if not scans_overlap_at_end.empty:
            if verbose>=2: print("A previous scan overlaps with the end time of the current scan.")
            etime = min(pd.to_datetime(scans_overlap_at_end["signal_start"]))


        t0 = time.time()

        if stime < etime:
            if verbose>=1: 
                print(f'Scanning from {stime.strftime("%Y-%m-%d %H:%M:%S")} to {etime.strftime("%Y-%m-%d %H:%M:%S")}...')

            # Obtain file paths
            start_day = stime.replace(hour=0, minute=0, second=0)
            filenames = get_filenames(start_day, etime, sensor, channel)[0]
            
            # Check if the data for the first or last day in the time range are missing
            if not os.path.isfile(filenames[0]):
                raise FileNotFoundError(f"Data for the first day ({filenames[0]}) not found. Interruptions could not be calculated.")
            elif not os.path.isfile(filenames[len(filenames)-1]):
                raise FileNotFoundError(f"Data for the last day ({filenames[len(filenames)-1]}) not found. Interruptions could not be calculated.")

            # Read seismic data
            st = read_files_in_parallel(filenames)
            st.trim(obspy.UTCDateTime(stime), obspy.UTCDateTime(etime))  # remove data from the previous and following day

            # Create interruptions table
            gaps = st.get_gaps()

            # Start and end times of the signal in the scanned time interval
            st = st.sort(['starttime', 'endtime'])
            signal_start = st[0].stats.starttime.datetime  # start of the first trace
            signal_end = st[len(st)-1].stats.endtime.datetime  # end of the last trace

            if len(gaps) > 0:  # if there are gaps

                gaps = pd.DataFrame(gaps)
                gaps = gaps.drop(gaps.columns[[0, 2]], axis=1)
                gaps.columns = ["sensor", "channel", "gap_start", "gap_end", "delta", "n_samples"]
                
                gaps["gap_start"] = gaps["gap_start"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                gaps["gap_end"] = gaps["gap_end"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") + "." + str(x.microsecond)[:2])
                gaps["gap_type"] = gaps["delta"].apply(lambda x: "empty" if x > 0 else "overlap")

                # Swap start and end times of gap if it is an overlap
                overlap_mask = gaps["gap_type"] == "overlap"
                gaps.loc[overlap_mask, ["gap_start", "gap_end"]] = gaps.loc[overlap_mask, ["gap_end", "gap_start"]].values

                # Save gaps to csv
                gaps_table = pd.read_csv(gaps_path)
                gaps_table = pd.concat([gaps_table if not gaps_table.empty else None, gaps.round(2)], ignore_index=True)
                gaps_table = gaps_table.sort_values(by=["sensor", "channel"])
                gaps_table.to_csv(gaps_path, header=True, index=False)
                if verbose>=1: print(f"Gaps identified and added to {gaps_path}.")

            elif verbose>=1: print("No gaps were found.")

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
            scans = pd.concat([scans if not scans.empty else None, scans_new.round(4)])

            scans.to_csv(scans_path, header=True, index=False)
            if verbose >=1: print(f"Scan metadata added to {scans_path}.")

        elif verbose>=1: print(f"The time range from {stime_original} to {etime_original} was already scanned.")


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
    parser = argparse.ArgumentParser(description="Scan seismic data for interruptions and save metadata.")

    parser.add_argument("starttime", type=str, help="Start time in YYYY-MM-DD HH:MM:SS format.")
    parser.add_argument("endtime", type=str, help="End time in YYYY-MM-DD HH:MM:SS format.")
    parser.add_argument("sensor", type=str, help="Name of the sensor.")
    parser.add_argument("channel", type=str, help="Name of the channel.")

    parser.add_argument("--gaps_path", type=str, default="data/metadata/interruptions.csv",
                        help="Path to save interruptions data.")
    parser.add_argument("--scans_path", type=str, default="data/metadata/scans.csv",
                        help="Path to save scan metadata.")
    parser.add_argument("--verbose", type=int, choices=[0, 1, 2], default=1,
                        help="Verbose level: 0 = silent, 1 = basic, 2 = detailed.")
    args = parser.parse_args()

    save_interruptions(args.starttime, args.endtime, args.sensor, args.channel,
                       args.gaps_path, args.scans_path, args.verbose)
