"""
pull.py

This script connects to SFTP servers, filters seismic files based on a specified date range, sensor, and channel, and downloads the corresponding files to a local directory structure.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Read a CSV file containing metadata of available files and filter the rows based on the provided sensor, channel, and date range.
- Try to connect to the host using an SSH key.
- If an SSH key is not found, check is credentials are available as environment variables.
- If credentials are not available as environment variables, attempt connection with credentials manually entered by the user.
- Connect to the SFTP servers and download the filtered files to a local directory structure.

Usage:
    python pull.py <starttime> <endtime> <sensor> <channel> [<user>] [<pasw>] [<passphrase>] [<data_path>] [<key_path>]

Arguments:
    starttime  - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime    - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    sensor     - Sensor name.
    channel    - Channel name.
    --user       - Remote server username (optional, default is local username).
    --pasw       - Remote server password (optional, default is None).
    --passphrase - Passphrase for an SSH key (optional, default is None).
    --data_path  - Local directory path where the files will be saved (optional, default is 'data/seismic/').
    --key_path   - Path to the SSH key (optional, default is '~/.ssh/id_rsa')

Example:
    python data/pull.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' 'PPMA' 'HHZ'
"""

import paramiko
import csv
from datetime import datetime
import os
import getpass
import multiprocessing

def download_files(starttime, endtime, sensors, channels, data_path='data/seismic/', file_log = 'data/metadata/available_files.csv',
                    user=None, key_path = None, passphrase=None, pasw=None, # Authentication
                    cpu_counts = 1):
    # Convert starttime and endtime to datetime objects
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    # Read the CSV file and filter the rows based on the provided sensor, channel, and date range
    files_to_download = []
    with open(file_log, mode='r') as file:
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
        print("No files found for this query.")
        return 0, 0

    # Stablish the conenction to the server using the credentials
    servers = set(file_info['server'] for file_info in files_to_download)
    credentials = {}

    for server in servers:
        print(f"Connecting to {server}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username = os.getlogin() if user is None else user
        try:
            key_path = os.path.expanduser(key_path).replace('\\', '/')
            private_key = paramiko.RSAKey.from_private_key_file(key_path, passphrase)
            client.connect(server, username=username, pkey=private_key,
                           disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            print(f"Connected to {server} using SSH key.")
            credentials[server] = ('key', private_key)
        except Exception as e:
            print(f"SSH key authentication failed for {server}: {e}")
            print(f"Attempting login with username and password.")
            username = input(f"Username for {server}: ") if user is None else user
            password = getpass.getpass(f"Password for {server}: ") if pasw is None else pasw
            credentials[server] = (username, password)
        finally:
            client.close()

    # Pool download process
    start = datetime.now()
    if cpu_counts > 1:
        with multiprocessing.Pool(processes=cpu_counts) as pool:
            tasks = [(file_info, credentials, data_path) for file_info in files_to_download]
            results = pool.starmap(_download_single_file, tasks)

            successful_downloads = results.count(True)
            failed_downloads = len(results) - successful_downloads
    else:
        successful_downloads = [_download_single_file(files_to_download[0], credentials, data_path)]

    print(f"Process completed. Total time: {datetime.now()-start}")
    print(f"{successful_downloads} successful downloads. {failed_downloads} failed downloads.")
    return successful_downloads, failed_downloads

def _download_single_file(file_info, credentials, data_path):
    """Downloads a single file."""
    print(f"Downloading {file_info['filename']} from {file_info['server']}...")
    server = file_info['server']
    filepath = file_info['path'] + '/' + file_info['filename']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    success = False
    try:
        if credentials[server][0] == 'key':
            client.connect(server, username=os.getlogin(), pkey=credentials[server][1],
                           disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
        else:
            username, password = credentials[server]
            client.connect(server, username=username, password=password)

        sftp = client.open_sftp()

        # Create local directory structure
        local_dir = os.path.join(data_path, file_info['sensor'], f"{file_info['year']}_{file_info['channel']}")
        os.makedirs(local_dir, exist_ok=True)

        local_filepath = os.path.join(local_dir, file_info['filename'])
        sftp.get(filepath, local_filepath)

        sftp.close()
        success = True

    except paramiko.AuthenticationException:
        print(f"Authentication error for {server}.")
    except Exception as e:
        print(f"Error downloading {file_info['filename']} from {server}: {e}")
    finally:
        client.close()

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Donwload seismic files from a remote directory.")
    parser.add_argument("starttime", help="starttime")
    parser.add_argument("endtime", help="endtime")
    parser.add_argument("sensor", help="sensor")
    parser.add_argument("channel", help="channel")
    parser.add_argument("--data_path", default='data/seismic/', help="Path to store downloaded files")
    parser.add_argument("--file_log", default='data/metadata/available_files.csv', help="Path to the dowloaded files log")
    parser.add_argument("--user", type=str, default=None, help="Remote server username")
    parser.add_argument("--key_path", default='~/.ssh/id_rsa', help="Path to an SSH key")
    parser.add_argument("--passphrase", type=str, default=None, help="SSH key passphrase")
    parser.add_argument("--pasw", type=str, default=None, help="Remote server password")
    parser.add_argument("--cpu_counts", type=int, default=1, help="Number of CPUs to use por parallelization")
    

    args = parser.parse_args()

    download_files(args.starttime, args.endtime, args.sensor, args.channel, args.data_path, args.file_log,
                   args.user, args.key_path, args.passphrase, args.pasw,
                   args.cpu_counts)