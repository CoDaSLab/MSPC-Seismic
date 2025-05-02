"""
get_filename.py

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
    python get_filename.py [-n <network>] [-s <station>] [-c <channel>] [-y <year>] [-sd <start_day>] [-ed <end_day>]

Arguments:
    -n, --network   Network code(s) (single string or comma-separated list).
    -s, --station   Station code(s) (single string or comma-separated list).
    -c, --channel   Channel code(s) (single string or comma-separated list).
    -y, --year      Year (integer).
    -sd, --start_day Start date in UTC format 'YYYY-MM-DD'.
    -ed, --end_day   End date in UTC format 'YYYY-MM-DD'.

Example:
    python get_filename.py -n C7 -s PFUE -c HHE -y 2017 -sd 2017-10-22 -ed 2017-10-22
    python get_filename.py -n C7,GE -s PFUE,ROSA -y 2022
    python get_filename.py -sd 2023-01-01 -ed 2023-01-05
    python get_filename.py -n C -n D -n E -y 2024
    python get_filename.py -c HHZ,HHE
    python get_filename.py -s 10,11,12,15
    python get_filename.py -sd 2024-12-30 -ed 2025-01-03 -y 2024
    python get_filename.py
"""
import argparse
from datetime import datetime, timedelta

def format_wildcard(values):
    if values is None or values == []:
        return '*'
    elif isinstance(values, str):
        return values
    elif isinstance(values, list) and len(values) == 1:
        return values[0]
    elif isinstance(values, list):
        def create_ranges(data):
            ranges = []
            if not data:
                return []
            data = sorted(list(set(data)))
            start = data[0]
            end = data[0]
            for i in range(1, len(data)):
                if isinstance(start, str) and isinstance(data[i], str) and ord(data[i]) == ord(end) + 1:
                    end = data[i]
                elif isinstance(start, int) and isinstance(data[i], int) and data[i] == end + 1:
                    end = data[i]
                else:
                    if start == end:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"[{start}-{end}]")
                    start = data[i]
                    end = data[i]
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"[{start}-{end}]")
            return "".join(ranges)

        if all(isinstance(item, str) and len(item) == 1 for item in values):
            range_str = create_ranges(values)
            if len(range_str) < len(",".join(values)): # Use range if shorter
                return range_str
            else:
                return "{" + ",".join(sorted(list(set(values)))) + "}"
        elif all(isinstance(item, int) for item in values):
            str_values = [str(v) for v in values]
            range_str = create_ranges([int(v) for v in str_values])
            if len(range_str) < len(",".join(str_values)): # Use range if shorter
                return range_str
            else:
                return "{" + ",".join(sorted(str_values)) + "}"
        else:
            return "{" + ",".join(sorted(list(set(values)))) + "}"

def generate_single_string(network=None, station=None, channel=None, year=None, start_day=None, end_day=None):
    network_wc = format_wildcard(network.split(',') if isinstance(network, str) and ',' in network else network)
    station_wc = format_wildcard(station.split(',') if isinstance(station, str) and ',' in station else station)
    channel_wc = format_wildcard(channel.split(',') if isinstance(channel, str) and ',' in channel else channel)
    year_wc = str(year) if year is not None else '*'
    julian_day_wc = '*'

    from collections import defaultdict

    year_day_map = defaultdict(set)

    if start_day and end_day:
        try:
            start_date = datetime.strptime(start_day, "%Y-%m-%d")
            end_date = datetime.strptime(end_day, "%Y-%m-%d")
            current_date = start_date

            while current_date <= end_date:
                year_key = current_date.year
                year_day_map[year_key].add(current_date.timetuple().tm_yday)
                current_date += timedelta(days=1)  # Mejor que manipular fechas manualmente

            # Genera combinación año + día
            year_wc_parts = []
            for y in sorted(year_day_map):
                days = sorted(year_day_map[y])
                day_strs = [f"{d:03d}" for d in days]
                digit_positions = list(zip(*day_strs))

                wildcard_digits = []
                for digits in digit_positions:
                    unique_digits = sorted(set(digits))
                    if len(unique_digits) == 1:
                        wildcard_digits.append(unique_digits[0])
                    else:
                        if all(d.isdigit() for d in unique_digits):
                            min_d, max_d = min(unique_digits), max(unique_digits)
                            if ord(max_d) == ord(min_d) + len(unique_digits) - 1:
                                wildcard_digits.append(f"[{min_d}-{max_d}]")
                            else:
                                wildcard_digits.append("{" + ",".join(unique_digits) + "}")
                        else:
                            wildcard_digits.append("{" + ",".join(unique_digits) + "}")

                day_wc = "".join(wildcard_digits)
                year_wc_parts.append(f"{y}.{day_wc}")

            # Une todas las combinaciones
            if len(year_wc_parts) == 1:
                year_wc, julian_day_wc = year_wc_parts[0].split('.')
            else:
                year_wc = "{" + ",".join([p.split('.')[0] for p in year_wc_parts]) + "}"
                julian_day_wc = "{" + ",".join([p.split('.')[1] for p in year_wc_parts]) + "}"

        except ValueError:
            print("Error: Invalid date format. Please use YYYY-MM-DD.")
            return None

    elif year is not None:
        julian_day_wc = '*'

    return f"{network_wc}.{station_wc}..{channel_wc}.D.{year_wc}.{julian_day_wc}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a filename wildcard string for seismic data.")
    parser.add_argument('-n', '--network', help='Network code(s) (single string or comma-separated list)')
    parser.add_argument('-s', '--station', help='Station code(s) (single string or comma-separated list)')
    parser.add_argument('-c', '--channel', help='Channel code(s) (single string or comma-separated list)')
    parser.add_argument('-y', '--year', type=int, help='Year')
    parser.add_argument('-sd', '--start_day', help='Start date in UTC format YYYY-MM-DD')
    parser.add_argument('-ed', '--end_day', help='End date in UTC format YYYY-MM-DD')

    args = parser.parse_args()

    result = generate_single_string(args.network, args.station, args.channel, args.year, args.start_day, args.end_day)
    if result:
        print(result)   