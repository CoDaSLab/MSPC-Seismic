import paramiko
import os
from monitoring import utils

def download_mysql_table(config_path='config.json'):
    """
    Connects to a remote server via SSH, executes a MySQL query, and saves the output
    to a local .dat file.

    Parameters
    ----------
    config_path : str
        Path to the JSON configuration file containing SSH and MySQL connection details,
        as well as file paths for saving results.
    """
    # ---------------------------- Load configuration -----------------------------

    config = utils.load_config(config_path)

    # SSH connection parameters
    ssh_user = config["connection"]["server_user"]
    ssh_key_path = config["connection"]["ssh_key_path"]
    server_IP = config["connection"]["server_IP"]

    # MySQL connection parameters
    mysql_user = config["connection"]["mysql_connection"]["user"]
    mysql_password = config["connection"]["mysql_connection"]["password"]
    mysql_database_name = config["connection"]["mysql_connection"]["database_name"]
    mysql_query = config["connection"]["mysql_connection"]["query"]

    # Output file path (where the .dat will be stored locally)
    station_catalog_path = config["paths"]["station_catalog"]

    # ---------------------------- Build MySQL command -----------------------------

    # The 2>/dev/null part hides warnings or password messages
    command = (
        f"mysql -u {mysql_user} -p{mysql_password} {mysql_database_name} "
        f"-e \"{mysql_query}\" 2>/dev/null"
    )

    # ---------------------------- Connect via SSH -----------------------------

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Normalize the SSH key path (handle ~ and Windows paths)
    key_path = os.path.expanduser(ssh_key_path).replace('\\', '/')

    print(f"Connecting to {server_IP} as {ssh_user}...")
    client.connect(server_IP, username=ssh_user, key_filename=key_path,
                   disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})

    # ---------------------------- Execute query -----------------------------

    print("Executing remote MySQL query...")
    stdin, stdout, stderr = client.exec_command(command)

    # Read command output
    output = stdout.read().decode()
    errors = stderr.read().decode()

    if errors:
        print("Warning or errors from remote command:")
        print(errors)

    # ---------------------------- Save results -----------------------------

    print(f"Saving query results to {station_catalog_path}...")
    with open(station_catalog_path, "w", encoding="utf-8") as f:
        f.write(output)

    # ---------------------------- Close SSH connection -----------------------------

    client.close()
    print("SSH connection closed.")
    print("Process completed successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download a MySQL query result from a remote server using SSH and save it as a .dat file."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the JSON configuration file containing SSH, MySQL, and output settings."
    )

    args = parser.parse_args()

    # Run main function
    download_mysql_table(args.config)
