"""
pull.py

This script connects to SFTP servers, filters seismic files based on a specified date range, sensor, and channel, and downloads 
the corresponding files to a local directory structure.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Read a CSV file containing metadata of available files and filter the rows based on the provided sensor, channel, and date range.
- Try to connect to the host using an SSH key.
- If an SSH key is not found, check is credentials are available as environment variables.
- If credentials are not available as environment variables, attempt connection with credentials manually entered by the user.
- Connect to the SFTP servers and download the filtered files to a local directory structure.

Usage:
    python pull.py <starttime> <endtime> [-s <sensor1> <sensor2> ...] [-c <channel1> <channel2> ...] [-u <user>] [-pw <password>] 
        [-pp <passphrase>] [-dp <data_path>] [-l <file_log>] [-kp <key_path>] [--compress]

Arguments:
    starttime         - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime           - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    -s, --sensors     - Sensor names.
    -c, --channels    - Channel names.
    -dp, --data_path  - Local directory path where the files will be saved (optional, default is 'data/involcan/mseed/').
    -l, --file_log    - Local directory path where the file log is be saved (optional, default is 'data/involcan/metadata/available_files.csv').
    -u, --user        - Remote server username (optional, default is local username).
    -kp, --key_path   - Path to the SSH key (optional, default is '~/.ssh/id_rsa')
    -pp, --passphrase - Passphrase for an SSH key (optional, default is None).
    -pw, --pasw       - Remote server password (optional, default is None).
    --compress        - Optional flag to compress files on the remote server before downloading. Not recommended
                            if the server does not have much available storage.

Example:
    python data/involcan/pull.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' -s 'PPMA' 'PLPI' -c 'HHZ' 'HHN' --user username
"""

import paramiko
import csv
from datetime import datetime, timedelta
import os
import getpass
from collections import defaultdict
import tarfile

def download_files(starttime, endtime, sensors, channels, data_path='data/involcan/mseed/', file_log = 'data/involcan/metadata/available_files.csv',
                    user=None, key_path = '~/.ssh/id_rsa', passphrase=None, pasw=None, compress=False):
    """
    Downloads seismic files filtered by date, sensor, and channel from SFTP servers.
    Performs a single SSH connection per server to download all corresponding files.
    """

    # Convert starttime and endtime to datetime objects
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime < endtime, "Start date cannot be later than end date."

    # Allows for single sensor and single channel input
    if isinstance(sensors, str):
        sensors = [sensors]
    if isinstance(channels, str):
        channels = [channels]

    # Read the CSV file and filter rows based on sensor, channel, and date range
    files_to_download = []
    with open(file_log, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            file_sensor = row['sensor']
            file_channel = row['channel']
            file_date = datetime.strptime(row['start_time'], "%Y-%m-%dT%H:%M:%SZ")

            if (file_sensor in sensors and file_channel in channels and
                starttime.replace(hour=0, minute=0, second=0, microsecond=0) <= file_date <= endtime):
                files_to_download.append(row)

    if not files_to_download:
        print("No files found for this query.")
        return 0, 0 # 0 successful downloads, 0 failed downloads

    # Group files by server
    files_by_server = defaultdict(list)
    for file_info in files_to_download:
        server = file_info['server']
        files_by_server[server].append(file_info)

    successful_downloads = 0
    failed_downloads = 0

    input_time = timedelta(seconds=0)  # Time the user spent entering credentials
    start_time = datetime.now()

    # Iterate over each server and download the files
    for server, file_list in files_by_server.items():
        print(f"Connecting to {server}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username = os.getlogin() if user is None else user
        sftp = None
        
        # Attempt connection via SSH key first, then username and password
        try:
            key_path = os.path.expanduser(key_path).replace('\\', '/')
            client.connect(server, username=username, password=pasw, key_filename=key_path, passphrase=passphrase,
                           disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            print(f"Connected to {server}.")
            sftp = client.open_sftp()
        except Exception as e:
            input_start_time = datetime.now()
            print(f"Connection to {server} via SSH key failed: {e}")
            print(f"Please enter username and password.")
            username = input(f"Username for {server}: ")
            password = getpass.getpass(f"Password for {server}: ")
            input_time += datetime.now() - input_start_time
            
            try:
                client.connect(server, username=username, password=password)
                print(f"Connected to {server} using username and password.")
                sftp = client.open_sftp()
            except Exception as e:
                print(f"Error connecting to {server}: {e}")

        if sftp:
            remote_tar_file = None
            local_tar_file = None
            if compress:
                remote_files_to_tar = [f"{f['path']}/{f['filename']}" for f in file_list]
                common_dir = os.path.commonpath(remote_files_to_tar).replace('\\','/')
                remote_files_to_tar = [os.path.relpath(f, common_dir).replace('\\', '/') for f in remote_files_to_tar]
                
                remote_tar_file = f'/home/{username}/data.tar.gz'
                local_tar_file = os.path.join(data_path, 'data.tar.gz').replace('\\', '/')

                # Create a tar.gz archive on the remote server
                print("Compressing files...")
                tar_command = f"cd {common_dir} && tar -czvf {remote_tar_file} {' '.join(remote_files_to_tar)}"
                _, stdout, stderr = client.exec_command(tar_command)

                exit_status = stdout.channel.recv_exit_status()

                # Read command output
                print("Compressed files:")
                print(stdout.read().decode())
                print(stderr.read().decode())

                if exit_status != 0:
                    print(f"Compressed file could not be created: {exit_status}")

                # Create local directory
                os.makedirs(data_path, exist_ok=True)

                # Download the compressed file
                print(f"Downloading compressed file from {server}...")
                sftp.get(remote_tar_file, local_tar_file)
                successful_downloads += len(file_list) # Count all files as successfully downloaded
                print(f"Successfully downloaded compressed file.")
                sftp.remove(remote_tar_file)  # Remove tar file from the remote server

                # Decompress the tar.gz file locally
                print(f"Extracting {local_tar_file}...")
                with tarfile.open(local_tar_file, "r:gz") as tar:
                    tar.extractall(path=data_path, filter='data')
                print(f"Successfully extracted data to {data_path}")
                os.remove(local_tar_file) # Remove the archive after decompression

            else:
                for file_info in file_list:
                    filepath = file_info['path'] + '/' + file_info['filename']

                    # Create local directory structure
                    os.makedirs(data_path, exist_ok=True)
                    local_filepath = os.path.join(data_path, file_info['filename'])

                    # Download the file from the server
                    try:
                        print(f"Downloading {file_info['filename']} from {file_info['server']}...")
                        sftp.get(filepath, local_filepath)
                        successful_downloads += 1
                    except Exception as e:
                        print(f"Error downloading {file_info['filename']} from {server}: {e}")

            sftp.close()
        client.close()

    failed_downloads = len(files_to_download) - successful_downloads

    print(f"Process completed. Total time: {datetime.now()-start_time-input_time}")
    print(f"{successful_downloads} successful downloads. {failed_downloads} failed downloads.")
    return successful_downloads, failed_downloads


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Downloads mseed files from a remote directory.")
    parser.add_argument("starttime", help="Start date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("endtime", help="End date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("-s", "--sensors", "--stations", nargs='+', required=True, help="Sensor names.")
    parser.add_argument("-c", "--channels", nargs='+', required=True, help="Channel names.")
    parser.add_argument("-dp", "--data_path", default='data/involcan/mseed/', help="Path to store downloaded files")
    parser.add_argument("-l", "--file_log", default='data/involcan/metadata/available_files.csv', help="Path to the available files log")
    parser.add_argument("-u", "--user", type=str, default=None, help="Remote server username")
    parser.add_argument("-kp", "--key_path", default='~/.ssh/id_rsa', help="Path to an SSH key")
    parser.add_argument("-pp", "--passphrase", type=str, default=None, help="SSH key passphrase")
    parser.add_argument("-pw", "--pasw", type=str, default=None, help="Remote server password")
    parser.add_argument("--compress", action='store_true', help="Compress files on the remote server before downloading")

    args = parser.parse_args()

    download_files(args.starttime, args.endtime, args.sensors, args.channels, args.data_path, args.file_log,
                   args.user, args.key_path, args.passphrase, args.pasw, args.compress)