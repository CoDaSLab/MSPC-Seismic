"""
cron_setup.py

This Python script updates the user's crontab to periodically run the monitoring script.
It reads the execution frequency (in minutes) from a JSON configuration file.
If the script is already scheduled in the crontab with a different frequency, the old entry is replaced with the new one.
"""

import json
import subprocess
import sys, os
script_path=sys.argv[0]
repo_path = os.path.abspath(os.path.join(script_path, "..", ".."))

# Path to the JSON configuration file and path to the monitoring script
CONFIG_JSON = repo_path+"/config.json"

# Read configuration from the JSON file
def read_config(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)
        return data.get("monitoring", {}).get("update_frequency")

# Get the current crontab content
def get_current_crontab():
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        # If the user has no crontab, return an empty string
        return ""

# Write updated crontab content
def write_new_crontab(content):
    process = subprocess.run(["crontab", "-"], input=content, text=True)
    if process.returncode == 0:
        print("Crontab successfully updated.")
    else:
        print("Failed to update crontab.")

# Generate crontab line based on frequency
def generate_cron_line(command, frequency="daily"):
    if frequency == "daily":
        freq_field = "@daily"
    elif frequency == 1:
        freq_field = "* * * * *"
    elif 60 % frequency == 0:
        freq_field = f"*/{frequency} * * * *"
    else:
        print("Invalid frequency.")
        return None
    return f"{freq_field} bash {command}"

# Main function
def main(commands, frequency=None):
    if frequency is None:
        frequency = read_config(CONFIG_JSON)

    if not commands:
        print(f"No commands entered.")
        return

    for command in commands:
        cron_line = generate_cron_line(command, frequency)
        if not cron_line:
            return

        current_crontab = get_current_crontab()

        if cron_line in current_crontab:
            print(f"The task {cron_line} is already present in the crontab.")
        else:
            new_crontab = current_crontab.strip() + "\n" + cron_line + "\n"
            write_new_crontab(new_crontab)

if __name__ == "__main__":
    command_monitoring = [repo_path+"/monitoring/monitoring.sh"]
    main(command_monitoring)

    command_update_stations = [repo_path+"/monitoring/update_stations.sh"]
    main(command_update_stations, "daily")
