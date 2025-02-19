"""
clear.py

This script deletes the seismic files downloaded by pull.py from the local directory structure and removes any empty directories.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Identify the local files based on the provided sensor, channel, and date range.
- Delete the identified files.
- Check for and delete any empty directories within the specified path.

Usage:
    python clear.py <starttime> <endtime> <sensor> <channel> [<path>]

Arguments:
    starttime - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime   - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    sensor    - Sensor name.
    channel   - Channel name.
    path      - Local directory path where the files are saved (optional, default is 'data/seismic/').

Example:
    python clear.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' 'PPMA' 'HHZ'
"""

import os
from datetime import datetime, timedelta

def clear_files(starttime, endtime, sensor, channel, path='data/seismic/'):
    # Convert starttime and endtime to datetime objects
    starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    # Iterate through the date range and delete corresponding files
    current_time = starttime
    while current_time <= endtime:
        dir_to_check = os.path.join(path, sensor, f"{current_time.year}_{channel}").replace('\\', '/')
        if os.path.exists(dir_to_check):
            for filename in os.listdir(dir_to_check):
                file_path = os.path.join(dir_to_check, filename)
                try:
                    if os.path.isfile(file_path):
                        print(f"Deleting file: {file_path}")
                        os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"Directory not found: {dir_to_check}")
        current_time += timedelta(days=1)

    # Check for and delete empty directories
    for root, dirs, files in os.walk(path, topdown=False):
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
    parser.add_argument("sensor", help="Sensor name")
    parser.add_argument("channel", help="Channel name")
    parser.add_argument("--path", default='data/seismic/', help="Local directory path where the files are saved")

    args = parser.parse_args()
    clear_files(args.starttime, args.endtime, args.sensor, args.channel, args.path)