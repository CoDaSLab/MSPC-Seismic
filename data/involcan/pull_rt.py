"""
pull_rt.py

This script connects to SFTP servers, filters seismic files based on a specified date range, station, and channel, and downloads 
the corresponding files to a local directory structure. It also keeps track of the latest download times for each channel-station
combination in a CSV file. It is intended for downloading data for real-time monitoring. Unlike pull.py, this script 
does not make use of the list of available files created by fetch.py.

Main functionalities:
- Convert start and end time strings to datetime objects.
- Try to connect to the host using an SSH key.
- If an SSH key is not found, attempt connection with username and password.
- Connect to the INVOLCAN server and download the filtered files to a local directory structure.
- Saves the latest pull times for each station-channel combination in another CSV file.

Usage:
    python pull_rt.py <starttime> <endtime> <server> <user> [-s <station1> <station2> ...] [-c <channel1> <channel2> ...] 
        [-pw <password>] [-pp <passphrase>] [-dp <data_path>] [-lp <log_path] [-kp <key_path>] [-p <port>] [-i] [-v]

Arguments:
    starttime               - Start date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    endtime                 - End date and time in the format 'YYYY-MM-DD HH:MM:SS'.
    server                  - IP address of the remote server.
    user                    - Remote server username.
    network,                - Network name.
    -s, --stations          - Station names.
    -c, --channels          - Channel names.
    -dp, --data_path        - Local directory path where the files will be saved (optional, default is 'data/involcan/mseed/').
    -lp, --log_path         - Local directory path where the pull times log is saved (optional, default is 
                                'data/involcan/metadata/latest_pulls.csv').
    -kp, --key_path         - Path to the SSH key (optional, default is '~/.ssh/id_rsa')
    -pp, --passphrase       - Passphrase for an SSH key (optional, default is None).
    -pw, --pasw             - Remote server password (optional, default is None).
    -p, --port              - Port number (optional, default is 22).
    -i, --allow_input       - If present, allows the user to input credentials manually after a failed login attempt (optional, default is False)
    -u, --update_latest     - Updates the latest pull database with this download
    -v, --verbose           - Print extra messages (optional, default is False).

Example:
    python -m data.involcan.pull_rt '2021-09-17 00:10:00' '2021-09-20 19:59:59' 193.147.109.7 user C7 -s 'PPMA' 'PLPI' -c 'HHZ' 'HHN' -p 22 -i -v
"""

import paramiko
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import getpass
from preprocessing.sismo import get_filenames

def download_files_rt(starttime, endtime, server, user, network, stations, channels, 
                      data_path='data/involcan/mseed/', log_path = 'data/involcan/metadata/latest_pulls.csv',
                      key_path = '~/.ssh/id_rsa', passphrase=None, pasw=None, port=22, 
                      allow_input=False, update_latest=True, verbose=False):
    """
    Downloads seismic files filtered by date, station, and channel from SFTP server.
    Performs a single SSH connection to download all corresponding files.
    """

    # Convert starttime and endtime to datetime objects
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Start date cannot be later than end date."

    # Allows for single station and single channel input
    if isinstance(stations, str):
        stations = [stations]
    if isinstance(channels, str):
        channels = [channels]

    successful_downloads = 0
    failed_downloads = 0

    input_time = timedelta(seconds=0)  # Time the user spent entering credentials
    start_time = datetime.now()

    # Establish connection with the server
    print(f"Connecting to {server}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    username = os.getlogin() if user is None else user
    sftp = None

    # Attempt connection via SSH key first, then username and password
    key_path = os.path.expanduser(key_path).replace('\\', '/')
    if allow_input:
        try:
            client.connect(server, port=port, username=username, password=pasw, key_filename=key_path, passphrase=passphrase,
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
                client.connect(server, port=port, username=username, password=password)
                print(f"Connected to {server} using username and password.")
                sftp = client.open_sftp()
            except Exception as e:
                print(f"Error connecting to {server}: {e}")
    else:
        client.connect(server, port=port, username=username, password=pasw, key_filename=key_path, passphrase=passphrase,
                        disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
        print(f"Connected to {server}.")
        sftp = client.open_sftp()

    if sftp:
        # Create local directory structure
        os.makedirs(data_path, exist_ok=True)

        file_list = pd.DataFrame(columns=["network", "station", "channel", "latest_file", "start_time", "latest_pull_time"])
        total_files = 0
        if not verbose: print("Downloading files...")
        for station in stations:
            for channel in channels:
                filenames = get_filenames(network, station, channel, starttime, endtime) 
                total_files += len(filenames)

                for filename in filenames:
                    parts = filename.split('.')
                    year = parts[5]

                    # Convert Julian day in file name to date
                    stime = datetime(int(year), 1, 1) + timedelta(days = int(parts[6]) - 1)
                    stime = stime.strftime('%Y-%m-%dT%H:%M:%SZ')

                    path = os.path.join('/involcan/mseed/', year, network, station, channel + ".D").replace('\\', '/')
                    filepath = os.path.join(path, filename).replace('\\', '/')
                    local_filepath = os.path.join(data_path, filename).replace('\\', '/')

                    # Download the file from the server
                    try:
                        if verbose: print(f"Downloading {filename}...")
                        sftp.get(filepath, local_filepath)
                        successful_downloads += 1
                        pull_time = datetime.now(timezone.utc)
                    except Exception as e:
                        if verbose:
                            print(f"Error downloading {filepath}: {e}")
                    else:
                        row = pd.DataFrame({'network' : [network], 'station' : [station], 'channel' : [channel], 'latest_file' : [filename],
                                            'start_time' : [stime], 'latest_pull_time' : [pull_time.strftime('%Y-%m-%dT%H:%M:%SZ')]})
                        file_list = pd.concat([file_list, row])
        
        sftp.close()
    client.close()
    
    # Read or create log
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if os.path.exists(log_path) and os.stat(log_path).st_size != 0:
        log = pd.read_csv(log_path)
    else:
        log = pd.DataFrame(columns=["network", "station", "channel", "latest_file", "start_time", "latest_pull_time"])

    # Find latest download times
    log = pd.concat([log, file_list], ignore_index=True)
    log['latest_pull_time'] = pd.to_datetime(log['latest_pull_time'], format='%Y-%m-%dT%H:%M:%SZ')
    latest_rows = log.groupby(['station', 'channel'])['latest_pull_time'].idxmax()
    latest_files = log.loc[latest_rows].reset_index(drop=True)
    # Save CSV
    if update_latest:
        latest_files.to_csv(log_path, header=True, index=False, date_format='%Y-%m-%dT%H:%M:%SZ')

    failed_downloads = total_files - successful_downloads

    print(f"Process completed. Total time: {datetime.now()-start_time-input_time}")
    print(f"{successful_downloads} successful downloads. {failed_downloads} failed downloads.")
    return successful_downloads, failed_downloads


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Downloads mseed files from a remote directory.")
    parser.add_argument("starttime", help="Start date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("endtime", help="End date and time in the format 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("server", help="Server address")
    parser.add_argument("user", type=str, help="Remote server username")
    parser.add_argument("network", type=str, help="Network name.")
    parser.add_argument("-s", "--stations", nargs='+', required=True, help="Station names.")
    parser.add_argument("-c", "--channels", nargs='+', required=True, help="Channel names.")
    parser.add_argument("-dp", "--data_path", default='data/involcan/mseed/', help="Path to store downloaded files")
    parser.add_argument("-lp", "--log_path", default='data/involcan/metadata/latest_pulls.csv', help="Path to the pull times log")
    parser.add_argument("-kp", "--key_path", default='~/.ssh/id_rsa', help="Path to an SSH key")
    parser.add_argument("-pp", "--passphrase", type=str, default=None, help="SSH key passphrase")
    parser.add_argument("-pw", "--pasw", type=str, default=None, help="Remote server password")
    parser.add_argument("-p", "--port", type=int, default=22, help="Port number (default: 22)")
    parser.add_argument("-i", "--allow_input", action='store_true', help="Allow user to enter credentials manually (off by default)")
    parser.add_argument("-u", "--update_latest", action='store_true', help="Save this download as the latest pull (use in real time)")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print extra messages (default: False)")

    args = parser.parse_args()

    download_files_rt(args.starttime, args.endtime, args.server, args.user, args.network, args.stations, args.channels, args.data_path,
                   args.log_path, args.key_path, args.passphrase, args.pasw, args.port, args.allow_input, args.update_latest, args.verbose)