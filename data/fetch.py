"""
fetch.py

This script connects to an SFTP server, searches for seismic files in a specified directory, and saves the information of the found files in a CSV file.

Main functionalities:
- Connect to an SFTP server using the provided credentials.
- Search for seismic files in the specified directory and its subdirectories.
- Filter files based on the following conditions:
  - The file name must end with ".{julian_day}".
  - The system of the file must be "C7" (temporary condition).
  - The sensor of the file must be from "La Palma" (hard-coded).
  - The channel of the file must start with "HH" followed by any character.
- Write the information of the found files to a CSV file in the `data/metadata/` directory.
- Operation mode "overwrite" or "append" for the CSV file:
  - "overwrite": Create a new CSV file from scratch.
  - "append": Add the found files to the existing CSV file, avoiding duplicates.
- Print the total time taken by the process in a readable format (hours, minutes, and seconds).

Usage:
    python fetch.py <server> <port> <user> <pasw> <path> [--mode overwrite|append]

Arguments:
    server  - SFTP server address.
    port    - Port number.
    user    - Username.
    pasw    - Password.
    path    - Remote directory path.
    --mode  - Operation mode for the CSV file: "overwrite" or "append" (default: "append").

Example:
    python fetch.py 192.168.1.1 22 user password /path/to/directory --mode append
"""
import paramiko
import stat
import os
import re
from datetime import datetime, timedelta
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

"""
Check if a given file is a seismic data file.
By convention, the name of seismic data files ends in ".{julian_day}".
We use this to identify seismic data files.
"""
def is_seismic(file_name):
    return re.match(r'.*\.\d{3}$', file_name) is not None

"""
Find seismic files in the specified path on the SFTP server.
For each seismic file found, write its details to the CSV file.
"""
def find_seismic_files(sftp, path, writer, server, existing_files):
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_directory, sftp, root, files, writer, server, existing_files) 
                   for root, dirs, files in sftp_walk(sftp, path)]
        for future in as_completed(futures):
            future.result()

def process_directory(sftp, root, files, writer, server, existing_files):
    for file in files:
        if is_seismic(file):
            file_path = os.path.join(root, file).replace('\\', '/')
            file_name = os.path.basename(file_path)
            if file_name not in existing_files:
                system, sensor, channel, year, month, day = parse_filename(file_name)
                # Temporary condition to only include files with system == "C7"
                # Only add stations from La Palma
                # Only add channels HH*
                lp_stations = [
                    "PA00","PA01","PA02","PA03","PA04","PA05","PA06","PA07","PA08","PA09","PAB"
                    ,"PBB2","PBBA","PCOR","PFUE","PFVI","PGAR","PLPI","PML2","PMLU","PMOZ","PN01",
                    "PN02","PN03","PN04","PPAS","PPMA","PSAB","PTAB","TC13"]
                if system == "C7" and (sensor in lp_stations) and re.match(r'^HH.', channel):
                    writer.writerow([sensor, channel, year, month, day, 0, 0, 0, server, root.replace('\\', '/'), file_name])

"""
Walk through the directories and subdirectories on the SFTP server.
Yield the path, folders, and files in each directory.
"""
def sftp_walk(sftp, remotepath):
    path = remotepath
    files = []
    folders = []
    print(f"Checking directory: {remotepath}")  # Debugging line
    for f in sftp.listdir_attr(remotepath):
        if stat.S_ISDIR(f.st_mode):
            folders.append(f.filename)
        else:
            files.append(f.filename)
    yield path, folders, files
    for folder in folders:
        new_path = os.path.join(remotepath, folder).replace('\\', '/')
        for x in sftp_walk(sftp, new_path):
            yield x

"""
Convert a Julian day to a month and day.
"""
def julian_to_date(year, julian_day):
    date = datetime(year, 1, 1) + timedelta(days=julian_day - 1)
    return date.month, date.day

"""
Parse the filename to extract system, sensor, channel, year, month, and day.
"""
def parse_filename(file_name):
    parts = file_name.split('.')
    system = parts[0]
    sensor = parts[1]
    channel = parts[3]
    year = int(parts[5])
    julian_day = int(parts[6])
    month, day = julian_to_date(year, julian_day)
    return system, sensor, channel, year, month, day

"""
Main function to connect to the SFTP server, find seismic files,
and write their details to a CSV file. The mode parameter determines
whether to overwrite the CSV file or append to it.
"""
def main(server, port, user, password, path, mode='append'):
    start_time = time.time()
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port=port, username=user, password=password)

    sftp = client.open_sftp()
    
    if mode == 'overwrite':
        write_mode = 'w'
        existing_files = set()
    else:
        write_mode = 'a'
        # Read existing filenames from the CSV to avoid duplicates
        if os.path.exists('data/metadata/available_files.csv'):
            with open('data/metadata/available_files.csv', mode='r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                existing_files = {row[-1] for row in reader}
        else:
            write_mode = 'w'
            existing_files = set()
    
    with open('data/metadata/available_files.csv', mode=write_mode, newline='') as file:
        writer = csv.writer(file)
        if mode == 'overwrite' or write_mode == 'w':
            writer.writerow(['sensor', 'channel', 'year', 'month', 'day', 'hour', 'minute', 'second', 'server', 'path', 'filename'])
        find_seismic_files(sftp, path, writer, server, existing_files)
    
    sftp.close()
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
    parser.add_argument("user", help="Username")
    parser.add_argument("pasw", help="Password")
    parser.add_argument("path", help="Remote directory path")
    parser.add_argument("--mode", choices=['overwrite', 'append'], default='append', help="Mode to write the CSV file: overwrite or append (default: append)")

    args = parser.parse_args()
    main(args.server, args.port, args.user, args.pasw, args.path, args.mode)