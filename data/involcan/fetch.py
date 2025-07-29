"""
fetch.py

This script connects to an SFTP server, searches for seismic files in a specified directory, and saves the information of the found files in a CSV file.

Main functionalities:
- Connect to an SFTP server using the provided credentials (username and SSH key, or username and password)
- Search for seismic files in the specified directory and its subdirectories.
- Filter files based on the following conditions:
  - The file name must end with ".{julian_day}".
  - The system of the file must be "C7" (temporary condition).
  - The station of the file must be from "La Palma" (hard-coded).
  - The channel of the file must start with "HH" followed by any character.
- Write the information of the found files to a CSV file in the `data/involcan/metadata/` directory.
- Operation mode "overwrite" or "append" for the CSV file:
  - "overwrite": Create a new CSV file from scratch.
  - "append": Add the found files to the existing CSV file, avoiding duplicates.
- Raises a warning when new files for a station are not found.
- Print the total time taken by the process in a readable format (hours, minutes, and seconds).

Usage:
    python fetch.py <server> <port> <remote_path> <user> [-pw <password>] [-kp <key_path>] [-pp <passphrase>]
      [-lp <log_path>] [-m overwrite|append] [-v]

Arguments:
    server            - SFTP server address.
    port              - Port number.
    remote_path       - Remote directory path.
    user              - Username.
    -pw, --pasw       - Password. Default is None.
    -kp, --key_path   - SSH key path. Default is '~/.ssh/id_rsa'.
    -pp, --passphrase - Passphrase of the SSH key. Default is None.
    -lp, --log_path   - CSV file path. Default is 'data/involcan/metadata/available_files.csv'.
    -m, --mode        - Operation mode for the CSV file: "overwrite" or "append". Default is "append".
    -v, --verbose     - Print extra messages. Default is False.

Example:
    python data/involcan/fetch.py 193.147.109.7 22 /path/to/directory user --pasw password --mode append -v
"""
import paramiko
import stat
import os
import re
from datetime import datetime, timedelta
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def is_seismic(file_name):
    """
    Check if a given file is a seismic data file.
    By convention, the name of seismic data files ends in ".{julian_day}".
    We use this to identify seismic data files.
    """
    return re.match(r'.*\.\d{3}$', file_name) is not None

def find_seismic_files(sftp, remote_path, writer, server, existing_files, expected_stations, found_stations, verbose):
    """
    Find seismic files in the specified path on the SFTP server.
    For each seismic file found, write its details to the CSV file.
    Also, keep track of stations for which new files are found.
    """
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_directory, root, files, writer, server, existing_files, expected_stations, found_stations) 
                   for root, dirs, files in sftp_walk(sftp, remote_path, verbose)]
        for future in as_completed(futures):
            future.result()

def process_directory(root, files, writer, server, existing_files, expected_stations, found_stations):
    """
    Process files within a given directory, writing seismic file details and tracking found stations.
    """
    # List of La Palma stations (temporary condition remains)

    for file in files:
        if is_seismic(file):
            file_path = os.path.join(root, file).replace('\\', '/')
            file_name = os.path.basename(file_path)
            
            # Only process if the file does not already exist in the CSV
            if file_name not in existing_files:
                network, station, channel, starttime = parse_filename(file_name)
                endtime = starttime + timedelta(days=1)

                # Format dates as strings
                starttime_str = starttime.strftime('%Y-%m-%dT%H:%M:%SZ')
                endtime_str = endtime.strftime('%Y-%m-%dT%H:%M:%SZ')

                # Apply filtering conditions
                if network == "C7" and (station in expected_stations) and re.match(r'^HH.', channel):
                    writer.writerow([network, station, channel, starttime_str, endtime_str, server, root.replace('\\', '/'), file_name])
                    # Add the station to the set of stations with new files
                    found_stations.add(station)

def sftp_walk(sftp, remotepath, verbose):
    """
    Walk through the directories and subdirectories on the SFTP server.
    Yield the path, folders, and files in each directory.
    """
    path = remotepath
    files = []
    folders = []
    if verbose:
        print(f"Checking directory: {remotepath}")
    try:
        for f in sftp.listdir_attr(remotepath):
            if stat.S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)
        yield path, folders, files
        for folder in folders:
            new_path = os.path.join(remotepath, folder).replace('\\', '/')
            for x in sftp_walk(sftp, new_path, verbose):
                yield x
    except IOError as e:
        print(f"Error accessing directory {remotepath}: {e}. Skipping this directory.")
        yield path, [], [] # Return empty lists for this path to continue processing

def julian_to_date(year, julian_day):
    """
    Convert a Julian day to a month and day.
    """
    date = datetime(year, 1, 1) + timedelta(days=julian_day - 1)
    return date.month, date.day

def parse_filename(file_name):
    """
    Parse the filename to extract system, station, channel, and UTC datetime as a string.
    """
    parts = file_name.split('.')
    network = parts[0]
    station = parts[1]
    channel = parts[3]
    year = int(parts[5])
    julian_day = int(parts[6])

    # UTC date
    date = datetime(year, 1, 1) + timedelta(days=julian_day - 1)

    return network, station, channel, date

def fetch_files(server, port, remote_path, user, password=None, key_path='~/.ssh/id_rsa', passphrase=None, 
                log_path='data/involcan/metadata/available_files.csv', mode='append', verbose=False):
    """
    Main function to connect to the SFTP server, find seismic files,
    and write their details to a CSV file. The mode parameter determines
    whether to overwrite the CSV file or append to it.
    It also checks for stations without new files and alerts accordingly.
    """
    start_time = time.time()
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Set to store stations for which new files were found
    found_stations = set()

    # Stations expected to have files (hard-coded). La Palma Stations
    expected_stations = {
        "PA00","PA01","PA02","PA03","PA04","PA05","PA06","PA07","PA08","PA09","PAB",
        "PBB2","PBBA","PCOR","PFUE","PFVI","PGAR","PLPI","PML2","PMLU","PMOZ","PN01",
        "PN02","PN03","PN04","PPAS","PPMA","PSAB","PTAB","TC13"
    }

    sftp = None
    try:
        key_path = os.path.expanduser(key_path).replace('\\', '/')
        client.connect(server, port=port, username=user, password=password, key_filename=key_path, passphrase=passphrase,
                       disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})

        sftp = client.open_sftp()
        
        if mode == 'overwrite':
            write_mode = 'w'
            existing_files = set()
        else:
            write_mode = 'a'
            # Read existing filenames from the CSV to avoid duplicates
            if os.path.exists(log_path):
                with open(log_path, mode='r') as file:
                    reader = csv.reader(file)
                    try:
                        next(reader)  # Skip header
                    except StopIteration:
                        # If the file is empty after reading header, treat as 'w'
                        write_mode = 'w' 
                        existing_files = set()
                    else:
                        existing_files = {row[-1] for row in reader}
            else:
                write_mode = 'w'
                existing_files = set()
        
        # Ensure the log directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, mode=write_mode, newline='') as file:
            writer = csv.writer(file)
            if mode == 'overwrite' or write_mode == 'w':
                writer.writerow(['network', 'station', 'channel', 'start_time', 'end_time', 'server', 'path', 'filename'])
            
            # Pass the found_stations set to the search function
            find_seismic_files(sftp, remote_path, writer, server, existing_files, expected_stations, found_stations, verbose)

        # Check which expected stations did not have new files
        missing_stations = expected_stations - found_stations
        if missing_stations:
            print("\n--- WARNING ---")
            print("No new files were found for the following stations:")
            for station in sorted(list(missing_stations)):
                print(f"- {station}")
            print("-----------------\n")
        else:
            print("\nNew files were found for all expected stations.")

    except paramiko.AuthenticationException as e:
        print(f"Authentication failed for {server}: {e}")
    except Exception as e:
        print(f"Error connecting to {server}: {e}")
    finally:
        if sftp:
            sftp.close()
        if client:
            client.close()

    end_time = time.time()
    elapsed_time = end_time - start_time
    # Convert elapsed time to hours, minutes, and seconds
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    # Print the elapsed time in a readable format
    print(f"Process completed in {int(hours)} hours {int(minutes)} minutes {seconds:.2f} seconds")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find seismic files in a remote directory.")
    parser.add_argument("server", help="Server address")
    parser.add_argument("port", type=int, help="Port number")
    parser.add_argument("remote_path", type=str, help="Remote directory path")
    parser.add_argument("user", type=str, help="Username")
    parser.add_argument("-pw", "--pasw", type=str, default=None, help="Password")
    parser.add_argument("-kp", "--key_path", type=str, default='~/.ssh/id_rsa', help="SSH key path")
    parser.add_argument("-pp", "--passphrase", type=str, default=None, help="SSH key passphrase")
    parser.add_argument("-lp", "--log_path", type=str, default='data/involcan/metadata/available_files.csv', help="CSV file path")
    parser.add_argument("-m", "--mode", choices=['overwrite', 'append'], default='append', help="Mode to write the CSV file: overwrite or append (default: append)")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print extra messages (default: False)")

    args = parser.parse_args()
    fetch_files(args.server, args.port, args.remote_path, args.user, args.pasw, args.key_path, args.passphrase, args.log_path, args.mode, args.verbose)