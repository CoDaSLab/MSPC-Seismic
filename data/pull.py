"""
pull.py

This script connects to SFTP servers, filters seismic files based on a specified date range, sensor, and channel, and downloads the corresponding files to a local directory structure.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Read a CSV file containing metadata of available files and filter the rows based on the provided sensor, channel, and date range.
- Try to connect to the host using an SSH key.
- If an SSH key is not found, request user credentials for the SFTP servers if they are not available as environment variables.
- Connect to the SFTP servers and download the filtered files to a local directory structure.

Usage:
    python pull.py <starttime> <endtime> <sensor> <channel> [<user>] [<passphrase>] [<data_path>] [<key_path>]

Arguments:
    starttime  - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime    - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    sensor     - Sensor name.
    channel    - Channel name.
    --user       - Remote server username (optional, default is local username).
    --passphrase - Passphrase for an SSH key (optional, default is None).
    --data_path  - Local directory path where the files will be saved (optional, default is 'data/seismic/').
    --key_path   - Path to the SSH key (optional, default is '~/.ssh/id_rsa')

Example:
    python pull.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' 'PPMA' 'HHZ'
"""

import paramiko
import csv
from datetime import datetime
import os
import getpass

def download_files(starttime, endtime, sensors, channels, user=None, passphrase=None, 
                   data_path='data/seismic/', key_path='~/.ssh/id_rsa'):
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

            if (file_sensor in sensors and
                file_channel in channels and
                starttime.replace(hour=0, minute=0, second=0, microsecond=0) <= file_date <= endtime):
                files_to_download.append(row)

    if not files_to_download:
        print("No files found for this query")
        return False

    servers = set(file_info['server'] for file_info in files_to_download)
    credentials = {}

    for server in servers:
        print(server)

        # Try SSH key-based login first
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        username = os.getlogin() if user is None else user

        try:
            key_path = os.path.expanduser(key_path)  # Or customize as needed
            private_key = paramiko.RSAKey.from_private_key_file(key_path, passphrase)
            client.connect(server, username=username, pkey=private_key,
                           disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            print(f"Connected to {server} using SSH key.")
            credentials[server] = ('key', private_key)
        except Exception as e:
            print(f"SSH key authentication failed for server {server}: {e}")

            # Fallback to environment variables
            env_username = os.getenv(f"{server.replace('.', '_').upper()}_user")
            env_password = os.getenv(f"{server.replace('.', '_').upper()}_pasw")
            if env_username and env_password:
                credentials[server] = (env_username, env_password)
            else:
                # Manual input of credentials if there are no environment variables
                username = input(f"Username for server {server}: ") if user is None else user
                password = getpass.getpass(f"Password for server {server}: ")
                credentials[server] = (username, password)
        finally:
            client.close()

    # Connect to the SFTP server and download the files
    for file_info in files_to_download:
        print(f"Downloading {file_info['filename']} from {file_info['server']}...")
        server = file_info['server']
        filepath = file_info['path'] + '/' + file_info['filename']

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if credentials[server][0] == 'key':
            try:
                client.connect(server, username=user, pkey=credentials[server][1],
                            disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            except paramiko.AuthenticationException:
                print(f"Authentication for server {server} failed with SSH key. Please enter credentials manually.")
        else:
            username, password = credentials[server]
            try:
                client.connect(server, username=username, password=password)
            except paramiko.AuthenticationException:
                print(f"Authentication for server {server} failed. Please enter credentials manually.")
                username = input(f"Username for server {server}: ")
                password = getpass.getpass(f"Password for server {server}: ")
                client.connect(server, username=username, password=password)

        sftp = client.open_sftp()

        # Create local directory structure
        local_dir = os.path.join(data_path, file_info['sensor'], f"{file_info['year']}_{file_info['channel']}")
        os.makedirs(local_dir, exist_ok=True)

        local_filepath = os.path.join(local_dir, file_info['filename'])
        sftp.get(filepath, local_filepath)

        sftp.close()
        client.close()
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Donwload seismic files from a remote directory.")
    parser.add_argument("starttime", help="starttime")
    parser.add_argument("endtime", help="endtime")
    parser.add_argument("sensor", help="sensor")
    parser.add_argument("channel", help="channel")
    parser.add_argument("--user", default=None, help="Remote server username")
    parser.add_argument("--passphrase", default=None, help="SSH key passphrase")
    parser.add_argument("--data_path", default='data/seismic/', help="Path to store downloaded files")
    parser.add_argument("--key_path", default='~/.ssh/id_rsa', help="Path to an SSH key")
    

    args = parser.parse_args()
    download_files(args.starttime, args.endtime, args.sensor, args.channel, args.user, args.passphrase, 
                   args.data_path, args.key_path)