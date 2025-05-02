"""
get_filenames.py

This script generates a filename string (or a single wildcard string)
based on the provided network, station, channel, year, and date range.
The filename format is: {network}.{station}..{channel}.D.{year}.{julian_day}

Main functionalities:
- Accepts optional input parameters for network, station, channel, year, start day, and end day.
- If no parameters are provided, it returns a fully wildcarded string: "*.*..*.D.*.*".
- Supports list inputs for network, station, and channel, which are converted to wildcard ranges (e.g., [A-C], [10-12]) or sets (e.g., {HHZ,HHE}) in the output string.
- Converts start and end day strings (in 'YYYY-MM-DD' UTC format) to Julian day wildcards, handling year transitions.
- Returns a single string representing all possible filename combinations based on the input.

Usage:
    python get_filenames.py [-n <network>] [-s <station>] [-c <channel>] [-sd <start_day>] [-ed <end_day>]

Arguments:
    -n, --network   Network code(s) (single string or comma-separated list).
    -s, --station   Station code(s) (single string or comma-separated list).
    -c, --channel   Channel code(s) (single string or comma-separated list).
    -sd, --start_day Start date in UTC format 'YYYY-MM-DD'.
    -ed, --end_day   End date in UTC format 'YYYY-MM-DD'.

Example:
    python get_filenames.py -n C7 -s PFUE -c HHE -sd 2017-10-22 -ed 2017-10-22
    python get_filenames.py -n C7,GE -s PFUE,ROSA 
    python get_filenames.py -sd 2023-01-01 -ed 2023-01-05
    python get_filenames.py -n C -n D -n E
    python get_filenames.py -c HHZ,HHE
    python get_filenames.py -s 10,11,12,15
    python get_filenames.py -sd 2024-12-30 -ed 2025-01-03
    python get_filenames.py
"""
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import product

def get_filenames(network=None, station=None, channel=None, start_day=None, end_day=None):
    # Parse input strings into lists
    def parse_list(x):
        if x is None:
            return ['*']
        return x.split(',') if isinstance(x, str) else x

    networks = parse_list(network)
    stations = parse_list(station)
    channels = parse_list(channel)

    filenames = []

    if start_day and end_day:
        try:
            start_date = datetime.strptime(start_day, "%Y-%m-%d")
            end_date = datetime.strptime(end_day, "%Y-%m-%d")

            current_date = start_date
            while current_date <= end_date:
                year = current_date.year
                jday = current_date.timetuple().tm_yday
                jday_str = f"{jday:03d}"
                year_str = str(year)

                # Combine all possibilities
                for net, sta, cha in product(networks, stations, channels):
                    filenames.append(f"{net}.{sta}..{cha}.D.{year_str}.{jday_str}")
                current_date += timedelta(days=1)

        except ValueError:
            print("Error: Invalid date format. Please use YYYY-MM-DD.")
            return []

    else:
        # If no date provided, return a single wildcarded filename
        for net, sta, cha in product(networks, stations, channels):
            filenames.append(f"{net}.{sta}..{cha}.D.*.*")

    return filenames

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a filename wildcard string for seismic data.")
    parser.add_argument('-n', '--network', help='Network code(s) (single string or comma-separated list)')
    parser.add_argument('-s', '--station', help='Station code(s) (single string or comma-separated list)')
    parser.add_argument('-c', '--channel', help='Channel code(s) (single string or comma-separated list)')
    parser.add_argument('-sd', '--start_day', help='Start date in UTC format YYYY-MM-DD')
    parser.add_argument('-ed', '--end_day', help='End date in UTC format YYYY-MM-DD')

    args = parser.parse_args()

    result = get_filenames(args.network, args.station, args.channel, args.start_day, args.end_day)
    if result:
        print(result)