"""
clear.py

This script deletes the mseed files downloaded by pull.py from the local directory structure and removes any empty directories.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Identify the local files based on the provided network, station, channel, and date range.
- Delete the identified files.
- Check for and delete any empty directories within the specified path.

Usage:
    python clear.py <starttime> <endtime> [-n <network1> <network2> ...] [-s <station1> <station2> ...] 
        [-c <channel1> <channel2> ...] [-p <path>]

Arguments:
    starttime       - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime         - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    -n, --networks  - Network names.
    -s, --stations   - Station names.
    -c, --channels  - Channel names.
    -p, --path      - Local directory path where the files are saved (optional, default is 'data/involcan/mseed/').

Example:
    python clear.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' -n 'C7' -s 'PPMA' -c 'HHZ' 'HHN' 'HHE'
"""

import os
from datetime import datetime, timedelta
from get_filenames import get_filenames

def delete_files(starttime, endtime, networks, stations, channels, path='data/involcan/mseed/'):
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

    # Iterate through the date range and delete corresponding files
    if os.path.exists(path):
        file_list = []
        start_day = starttime.replace(hour=0, minute=0, second=0)
        end_day = endtime.replace(hour=0, minute=0, second=0)

        for network in networks:
            for station in stations:
                for channel in channels:
                    file_list.extend(get_filenames(network, station, channel, start_day, end_day))

        for file in file_list:
            file_path = os.path.join(path, file)
            try:
                if os.path.isfile(file_path):
                    print(f"Deleting file: {file_path}")
                    os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        print(f"Directory not found: {path}")

    # Check for and delete empty directories
    for root, dirs, _ in os.walk(path, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                try:
                    print(f"Deleting empty directory: {dir_path}")
                    os.rmdir(dir_path)
                except Exception as e:
                    print(f"Failed to delete directory {dir_path}. Reason: {e}")

# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Delete seismic files from the local directory and remove empty directories.")
    parser.add_argument("starttime", help="Start date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("endtime", help="End date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("-n", "--networks", nargs='+', help="Network names.")
    parser.add_argument("-s", "--sensors", "--stations", nargs='+', help="Station names.")
    parser.add_argument("-c", "--channels", nargs='+', help="Channel names.")
    parser.add_argument("-p", "--path", default='data/involcan/mseed/', help="Local directory path where the files are stored")

    args = parser.parse_args()
    delete_files(args.starttime, args.endtime, args.networks, args.stations, args.channels, args.path)