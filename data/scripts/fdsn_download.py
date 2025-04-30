"""
fdsn_download.py

This script utilizes the ObsPy library to interact with FDSN (Federation of Digital Seismograph Networks) clients.

Main functionalities:
- List available FDSN services and their URLs.
- Connect to a specified FDSN service.
- Download station metadata from a service, allowing specification of a time range, and save the output to a CSV file.
- Download seismic event data from a service, allowing filtering by time range and magnitude, and save the output to a CSV file.
- Download waveform data (seismic time series) from a service for a given network and station within a specified time window. Data is saved in MSEED format, segmented by day.

Usage:
    python fdsn_download.py <function> [--service <service_name>] [--output_dir <path>] [--filename <name>] [--starttime <YYYY-MM-DDTHH:MM:SS>] [--endtime <YYYY-MM-DDTHH:MM:SS>] [--minmagnitude <float>] [--maxmagnitude <float>] [--network <network_code>] [--station <station_code>]

Arguments:
    function          - The function to execute (available_services, service_connect, download_station_metadata, download_events, download_waveforms).
    --service         - Name of the FDSN service to connect to. Required for functions other than 'available_services'.
    --output_dir      - Local directory path where the output files will be saved (optional, default is 'data').
    --filename        - Name of the output CSV file (optional, default is 'output.csv').
    --starttime       - Start date and time for data requests in the format 'YYYY-MM-DDTHH:MM:SS' (optional).
    --endtime         - End date and time for data requests in the format 'YYYY-MM-DDTHH:MM:SS' (optional).
    --minmagnitude    - Minimum magnitude for event downloads (optional).
    --maxmagnitude    - Maximum magnitude for event downloads (optional).
    --network         - Network code for waveform downloads (optional, default is '*').
    --station         - Station code for waveform downloads (optional, default is '*').

Example:
    python fdsn_download.py available_services
    python fdsn_download.py service_connect  IRIS
    python fdsn_download.py download_station_metadata GEOFON --starttime 2021-03-18T00:00:00 --endtime 2021-03-19T00:00:00 --output_dir data/GEOFON/metadata/ --filename stations.csv
    python fdsn_download.py download_events USGS --starttime 2023-03-15T00:00:00 --endtime 2023-03-20T00:00:00 --minmagnitude 6.0 --output_dir data/USGS/metadata/ --filename events.csv
    python fdsn_download.py download_waveforms GEOFON --starttime 2021-03-19T00:00:00 --endtime 2021-03-19T00:10:00 --oputput_dir data/GEOFON/mseed/ --network 9F --station NUPH
"""

from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import pandas as pd
import os
import argparse

def available_services():
    """
    Returns a dictionary with FDSN service names as keys
    and their corresponding URLs as values.
    """
    services = {}
    for key in sorted(URL_MAPPINGS.keys()):
        services[key] = URL_MAPPINGS[key]
    return services


def service_connect(service):
    """
    Connects to a given service
    """
    try:
        client = Client(service)
        print(f"Connected to {service}")
    except: 
        client = None
        print(f"Could not connect to {service}")
    return client

def download_station_metadata(client, output_dir="data/metadata", filename="stations.csv", starttime=None, endtime=None):
    """
    Downloads metadata for all available GEOFON stations and saves it to a CSV file,
    allowing you to specify a time period.

    Args:
        client: An FDSN client object (e.g., from obspy.client.FDSN).
        output_dir (str, optional): The directory where the CSV file will be saved.
            Defaults to "data/metadata".
        filename (str, optional): The name of the CSV file. Defaults to "stations.csv".
        starttime (obspy.UTCDateTime, optional): Start time for the metadata request.
            Defaults to None (no start time restriction).
        endtime (obspy.UTCDateTime, optional): End time for the metadata request.
            Defaults to None (no end time restriction).

    Returns:
        None.  The function saves the data to a CSV file.  It prints a message
        indicating the file location upon successful completion, or an error
        message if an exception occurs or no data is obtained.
    """
    if type(client)==str: client = service_connect(client)
    print(f"Fetching metadata of stations from {starttime} to {endtime}")

    # List to store station data
    data = []
    try:
        # Get station information
        inventory = client.get_stations(starttime=starttime, endtime=endtime)
        print(f"{len(inventory)} stations found in catalog. Starting download ...")

        # Extract relevant information and add it to the list
        for net in inventory:
            for sta in net:
                data.append({
                    "network_code": net.code,
                    "station_code": sta.code,
                    "latitude": sta.latitude,
                    "longitude": sta.longitude,
                    "elevation_in_m": sta.elevation,
                    "site_name": sta.site.name,
                    "start_date": sta.start_date,
                    "end_date": sta.end_date
                })
    except Exception as e:
        print(f"Error obtaining station metadata: {e}")
        return

    # If no data was obtained, exit.
    if not data:
        print("No station data obtained.")
        return

    # Create a pandas DataFrame with the data
    df = pd.DataFrame(data)

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save the DataFrame to a CSV file
    output_file = os.path.join(output_dir, filename)
    df.to_csv(output_file, index=False)  # index=False to not save the DataFrame index

    print(f"Station metadata saved in: {output_file}")


def download_events(client, output_dir="data/metadata", filename="events.csv", starttime=None, endtime=None,
                    minmagnitude=None, maxmagnitude=None):
    """
    Downloads information about seismic events and saves it to a CSV file,
    allowing you to specify a time period and magnitude range.

    Args:
        client: An FDSN client object (e.g., from obspy.client.FDSN).
        output_dir (str, optional): The directory where the CSV file will be saved.
            Defaults to "data/metadata".
        filename (str, optional): The name of the CSV file. Defaults to "events.csv".
        starttime (obspy.UTCDateTime, optional): Start time for the event request.
            Defaults to None (no start time restriction).
        endtime (obspy.UTCDateTime, optional): End time for the event request.
            Defaults to None (no end time restriction).
        minmagnitude (float, optional): Minimum magnitude of events to download.
            Defaults to None (no minimum magnitude restriction).
        maxmagnitude (float, optional): Maximum magnitude of events to download.
            Defaults to None (no maximum magnitude restriction).

    Returns:
        None. The function saves the event data to a CSV file.  It prints a message
        indicating the file location upon successful completion, or an error
        message if an exception occurs or no data is obtained.
    """
    if type(client)==str: client = service_connect(client)
    print(f"Fetching events recorded from {starttime} to {endtime}")
    # List to store event data
    data = []
    try:
        # Get event information
        catalog = client.get_events(starttime=starttime, endtime=endtime,
                                     minmagnitude=minmagnitude, maxmagnitude=maxmagnitude)
        print(f"{len(catalog)} events found in catalog. Starting download ...")
        # Extract relevant information and add it to the list
        for event in catalog:
            if event.preferred_origin():
                origin = event.preferred_origin()
                data.append({
                    "event_id": event.resource_id.id,
                    "latitude": origin.latitude,
                    "longitude": origin.longitude,
                    "depth_in_km": origin.depth / 1000,  # Convert to km
                    "origin_time": origin.time,
                })
            elif len(event.origins) > 0:
                origin = event.origins[0]
                data.append({
                    "event_id": event.resource_id.id,
                    "latitude": origin.latitude,
                    "longitude": origin.longitude,
                    "depth_in_km": origin.depth / 1000,  # Convert to km
                    "origin_time": origin.time,
                })
            else:
                data.append({
                    "event_id": event.resource_id.id,
                    "latitude": None,
                    "longitude": None,
                    "depth_in_km": None,
                    "origin_time": None,
                })
            if event.preferred_magnitude():
                magnitude_value = event.preferred_magnitude().mag
                data[-1]["magnitude"] = magnitude_value
            elif len(event.magnitudes) > 0:
                magnitude_value = event.magnitudes[0].mag
                data[-1]["magnitude"] = magnitude_value
            else:
                data[-1]["magnitude"] = None

    except Exception as e:
        print(f"Error obtaining event data: {e}")
        return

    # If no data was obtained, exit.
    if not data:
        print("No event data obtained.")
        return

    # Create a pandas DataFrame with the data
    df = pd.DataFrame(data)

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save the DataFrame to a CSV file
    output_file = os.path.join(output_dir, filename)
    df.to_csv(output_file, index=False)  # index=False to not save the DataFrame index

    print(f"Event data saved in {output_file}")


def download_waveforms(client, starttime, endtime, output_dir="data/mseed/", network="*", station="*"):
    """
    Downloads waveforms and segments them into day-long files if the
    start and end times span multiple days.

    Args:
        client: Obspy client object.
        starttime (UTCDateTime): Start time of the data request.
        endtime (UTCDateTime): End time of the data request.
        output_dir (str, optional): The directory where the CSV file will be saved.
            Defaults to "data/mseed".
        network (str): Network code (default: "*").
        station (str): Station code (default: "*").
    """
    if type(client)==str: client = service_connect(client)
    from datetime import timedelta
    current_time = starttime
    while current_time < endtime:
        next_day = current_time.date + timedelta(days=1)
        segment_end_time = min(endtime, UTCDateTime(next_day))

        print(f"Fetching data from {network}.{station} [{current_time}-{segment_end_time}]")

        try:
            st = client.get_waveforms(network, station, "*", "*", current_time, segment_end_time)
            if st:
                for trace in st:
                    network = trace.stats.network
                    station = trace.stats.station
                    channel = trace.stats.channel
                    segment_start = trace.stats.starttime
                    year = segment_start.year
                    julian_day = f"{segment_start.julday:03d}"

                    os.makedirs(os.path.dirname(output_dir), exist_ok=True)
                    filename = f"{network}.{station}..{channel}.D.{year}.{julian_day}"
                    trace.write(output_dir + filename, format="MSEED")
                    print(f"Downloaded trace at {output_dir + filename}")
        except Exception as e: print(f"Error obtaining mseed data:{e}")
        finally: current_time = segment_end_time
    return

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obspy FDSN Client Script")
    parser.add_argument("function", help="Function to execute (available_services, service_connect, download_station_metadata, download_events, download_waveforms)")
    parser.add_argument("service", help="FDSN service name")
    parser.add_argument("--output_dir", default="data/metadata", help="Output directory")
    parser.add_argument("--filename", default="output.csv", help="Output filename")
    parser.add_argument("--starttime", help="Start time (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--endtime", help="End time (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--minmagnitude", type=float, help="Minimum magnitude")
    parser.add_argument("--maxmagnitude", type=float, help="Maximum magnitude")
    parser.add_argument("--network", default="*", help="Network code")
    parser.add_argument("--station", default="*", help="Station code")

    args = parser.parse_args()

    if args.function == "available_services":
        services = available_services()
        print("Available services:")
        for key, value in services.items():
            print(f"{key}: {value}")
    elif args.function == "service_connect":
        if args.service:
            client = service_connect(args.service)
        else:
            print("Error: --service argument is required for service_connect")
    elif args.function == "download_station_metadata":
        if args.service:
            client = service_connect(args.service)
            starttime = UTCDateTime(args.starttime) if args.starttime else None
            endtime = UTCDateTime(args.endtime) if args.endtime else None
            if client:
                download_station_metadata(client, args.output_dir, args.filename, starttime, endtime)
        else:
            print("Error: --service argument is required for download_station_metadata")
    elif args.function == "download_events":
        if args.service:
            client = service_connect(args.service)
            starttime = UTCDateTime(args.starttime) if args.starttime else None
            endtime = UTCDateTime(args.endtime) if args.endtime else None
            if client:
                download_events(client, args.output_dir, args.filename, starttime, endtime, args.minmagnitude, args.maxmagnitude)
        else:
            print("Error: --service argument is required for download_events")
    elif args.function == "download_waveforms":
        if args.service and args.starttime and args.endtime:
            client = service_connect(args.service)
            starttime = UTCDateTime(args.starttime)
            endtime = UTCDateTime(args.endtime)
            if client:
                download_waveforms(client, args.service, starttime, endtime, args.network, args.station)
        else:
            print("Error: --service, --starttime, and --endtime arguments are required for download_waveforms")
    else:
        print(f"Error: Function '{args.function}' not recognized.")
    
