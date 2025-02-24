"""
pull.py

This script connects to SFTP servers, filters seismic files based on a specified date range, sensor, and channel, and downloads the corresponding files to a local directory structure.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Read a CSV file containing metadata of available files and filter the rows based on the provided sensor, channel, and date range.
- Request user credentials for the SFTP servers if they are not available as environment variables.
- Connect to the SFTP servers and download the filtered files to a local directory structure.

Usage:
    python pull.py <starttime> <endtime> <sensor> <channel> [<path>]

Arguments:
    starttime - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime   - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    sensor    - Sensor name.
    channel   - Channel name.
    path      - Local directory path where the files will be saved (optional, default is 'data/seismic/').

Example:
    python pull.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' 'PPMA' 'HHZ'
"""

import paramiko
import csv
from datetime import datetime
import os
import getpass

def download_files(starttime, endtime, sensor, channel, path='data/seismic/'):
    # Convert starttime and endtime to datetime objects
    if type(starttime) == str:
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if type(endtime) == str:
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    # Read the CSV file and filter the rows based on the provided sensor, channel, and date range
    files_to_download = []
    with open('data/metadata/available_files.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            file_sensor = row['sensor']
            file_channel = row['channel']
            file_year = int(row['year'])
            file_month = int(row['month'])
            file_day = int(row['day'])
            file_date = datetime(file_year, file_month, file_day)

            if (file_sensor == sensor and
                file_channel == channel and
                starttime.replace(hour=0, minute=0, second=0, microsecond=0) <= file_date <= endtime):
                files_to_download.append(row)

    if len(files_to_download) > 0:
        servers = set(file_info['server'] for file_info in files_to_download)
        credentials = {}
        for server in servers:
            env_username = os.getenv(f"{server.replace('.', '_').upper()}_user")
            env_password = os.getenv(f"{server.replace('.', '_').upper()}_pasw")
            if env_username and env_password:
                credentials[server] = (env_username, env_password)
            else:
                username = input(f"Username for server {server}: ")
                password = getpass.getpass(f"Password for server {server}: ")
                credentials[server] = (username, password)
        
    else:
        print("No files found for this query")
        return False

    # Connect to the SFTP server and download the files
    for file_info in files_to_download:
        print(f"Downloading {file_info['filename']} from {file_info['server']}...")
        server = file_info['server']
        filepath = file_info['path'] + '/' + file_info['filename']
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username, password = credentials[server]
        
        try:
            client.connect(server, username=username, password=password)
        except paramiko.AuthenticationException:
            print(f"Authentication failed for server {server} with environment variables. Please enter credentials manually.")
            username = input(f"Username for server {server}: ")
            password = getpass.getpass(f"Password for server {server}: ")
            client.connect(server, username=username, password=password)

        sftp = client.open_sftp()
        
        # Create local directory structure
        local_dir = os.path.join(path, sensor, f"{file_info['year']}_{channel}")
        os.makedirs(local_dir, exist_ok=True)
        
        local_filepath = os.path.join(local_dir, file_info['filename'])
        sftp.get(filepath, local_filepath)
        
        sftp.close()
        client.close()
    return True

# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Donwload seismic files from a remote directory.")
    parser.add_argument("starttime", help="starttime")
    parser.add_argument("endtime", help="endtime")
    parser.add_argument("sensor", help="sensor")
    parser.add_argument("channel", help="channel")
    parser.add_argument("--path", default='data/seismic/', help="path to store downloaded files")


    args = parser.parse_args()
    download_files(args.starttime, args.endtime, args.sensor, args.channel, args.path)