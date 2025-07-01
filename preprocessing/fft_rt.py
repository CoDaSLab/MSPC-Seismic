import os
import re
from datetime import datetime
import numpy as np
from scipy.io import savemat

from preprocessing.SISMO import SISMO

def calculate_fft_rt(starttime, endtime, network, sensor, channels=['HHE', 'HHN', 'HHZ'], 
            window=10, overlap=0, windowing=False, detrend=False, fft_points=256, merge_method=0,
            merge_fill_value = None, resampling_factor=1, 
            data_path="data/involcan/mseed", cpus=1, verbose=False, 
            save=False, save_path="data/involcan/features"):
    """
    Extracts FFT coefficients and derivatives from seismic signals over a specified time range 
    for multiple sensors and channels. This function is meant for use in real time monitoring.

    Parameters
    ----------
        starttime (datetime): Start time for data extraction.
        endtime (datetime): End time for data extraction.
        network (str): Seismic network identifier.
        sensors (list of str): List of station codes.
        channels (list of str): List of channels (default: ['HHE', 'HHN', 'HHZ']).
        window (int): Time window size in seconds (default: 10).
        overlap (int): Overlap between windows in seconds (default: 0).
        windowing (bool): Whether to apply a window function to each segment (default: False).
        detrend (bool): Whether to remove linear trend from signals (default: False).
        fft_points (int or 'auto'): Number of FFT points. If set to `'auto'`, uses the number of 
            points per window.
        merge_method (int): Method used for merging waveform segments (see documentation for the 
            `Trace` class from the ObsPy module).
        merge_fill_value (any): Value used to fill gaps when merging if applicable
            (see documentation for the `Stream.merge` method from the ObsPy module).
        resampling_factor (int): Resampling factor for FFT features (default: 1 = no resampling).
        data_path (str): Directory path containing seismic data (default: "data/involcan/mseed").
        cpus (int): Number of CPU cores to use for processing (default: 1).
        verbose (bool): Whether to print detailed messages during feature extraction (default: False).
        save (bool): Whether to save the features in a .mat file (default: False).
        save_path (str): Path to the directory where features are stored (default: "data/involcan/features").

    Returns
    -------
        features (dict): A dictionary containing the following extracted features:
            - 'ffts': FFT coefficients for each time window.
            - 'deltas_ffts': First-order differences of FFTs.
            - 'deltas_deltas_ffts': Second-order differences of FFTs.
            - 'missing_rates': Proportion of missing samples in each time window.

    """
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Error: Start date cannot be after end date."

    time0 = datetime.now()
    print(f"Extracting features...")

    shift = window - overlap

    features = {'ffts': [], 
                'deltas_ffts': [],
                'deltas_deltas_ffts': []}
    
    for channel in channels:
        if verbose:
            print(f"""
                Extracting SISMO features 
                network: {network}, sensor: {sensor}, channel: {channel}
                from {starttime} to {endtime}
                window: {window} s
                overlap: {overlap} s
                windowing: {windowing}
                resampling_factor: {resampling_factor}
                """)

        S = SISMO(
            network, sensor, channel, 
            starttime, endtime,
            detrend, windowing,
            merge_method=merge_method, merge_fill_value=merge_fill_value,
            cpus=cpus, data_path=data_path
        )
        if verbose:
            S.check()
        
        # Set window size and overlap
        S.set_windows(window, shift)

        # Calculate FFT coefficients
        S.fft_bin(fft_points)
        channel_features = {'ffts': np.squeeze(S.fft), 
                            'deltas_ffts': np.squeeze(S.deltas_fft),
                            'deltas_deltas_ffts': np.squeeze(S.deltas_deltas_fft)}

        # Resampling of the FFTs
        for key, array in channel_features.items():
            if resampling_factor > 1:
                w, f = array.shape
                if f % resampling_factor != 0:
                    raise ValueError(f"The number of columns in '{key}' ({f}) is not a multiple of {resampling_factor}.")
                
                # Average blocks of columns
                channel_features[key] = array.reshape(w, f // resampling_factor, resampling_factor).mean(axis=2)
        
            features[key].append(array)

    # Concatenate features for all channels along the columns
    for key in features.keys():
        if features[key]: 
            features[key] = np.concatenate(features[key], axis=1)
        else:
            features[key] = np.array([])

    # Rate of missing values for every window
    features['missing_rates'] = np.squeeze(S.get_missing_samples(rate=True))

    print(f"Extracted FFT coefficients. Time taken: {datetime.now() - time0}")

    if save:
        file_name = sensor + '_' + starttime.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime.strftime('%Y-%m-%dT%H-%M-%SZ')
        mat_path = os.path.join(save_path, file_name).replace('\\', '/')
        savemat(mat_path, features)

    return features


def delete_fft(path, sensor, starttime, endtime, verbose = False):
    """
    Deletes files in a directory that match a sensor name and fall within a date range.

    Parameters
    ----------
        path (str): Path to the directory containing the files.
        sensor (str): Name of the sensor.
        starttime (str, datetime): The start date of the range.
        endtime (str, datetime): The end date of the range.
    """
    # Convert date strings to datetime objects for comparison
    if isinstance(starttime, str):
        starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    if isinstance(endtime, str):
        endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')

    assert starttime <= endtime, "Error: Start date cannot be after end date."
    
    try:
        # Regex pattern to extract sensor name and dates
        # Example filename: sensorname_2025-06-16T09-00-00Z_2025-06-18T11-00-00Z.mat
        pattern = re.compile(rf"^{re.escape(sensor)}_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z)_(\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}Z).*$")

        deleted_files = []

        for filename in os.listdir(path):
            match = pattern.match(filename)
            if match:
                # Extract file's start and end date strings
                file_starttime = match.group(1)
                file_endtime = match.group(2)

                try:
                    # Convert file dates to datetime objects
                    file_starttime = datetime.strptime(file_starttime, '%Y-%m-%dT%H-%M-%SZ')
                    file_endtime = datetime.strptime(file_endtime, '%Y-%m-%dT%H-%M-%SZ')

                    # Remove files in the time range
                    if file_starttime >= starttime and file_endtime <= endtime:
                        full_file_path = os.path.join(path, filename)
                        os.remove(full_file_path)
                        deleted_files.append(filename)

                except ValueError:
                    print(f"Warning: Could not parse date from file '{filename}'. Skipping.")

        if verbose:  
            if deleted_files:
                print(f"\nSuccessfully deleted the following files for sensor '{sensor}' in the range {starttime} to {endtime}:")
                for f in deleted_files:
                    print(f"- {f}")
            else:
                print(f"\nNo files found to delete for sensor '{sensor}' in the range {starttime} to {endtime}.")

    except FileNotFoundError:
        print(f"Error: The directory '{path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    # Test for delete_fft
    from datetime import timedelta
    import shutil
    
    # Create a test directory and some dummy files
    test_dir = "test_files"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    sensor_1 = "sensorX"
    sensor_2 = "sensorY"
    
    base_dt = datetime(2025, 6, 1, 0, 1, 2)
    for i in range(10):
        file_start = base_dt + timedelta(days=i)
        file_end = file_start + timedelta(days=2)
        
        # Files for sensorX
        filename_1 = f"{sensor_1}_{file_start.strftime('%Y-%m-%dT%H-%M-%SZ')}_{file_end.strftime('%Y-%m-%dT%H-%M-%SZ')}.xyz"
        with open(os.path.join(test_dir, filename_1), 'w') as f:
            f.write("dummy content")
        
        # Files for sensorY
        filename_2 = f"{sensor_2}_{file_start.strftime('%Y-%m-%dT%H-%M-%SZ')}_{file_end.strftime('%Y-%m-%dT%H-%M-%SZ')}.xyz"
        with open(os.path.join(test_dir, filename_2), 'w') as f:
            f.write("dummy content")
    
    print(f"Files created in '{test_dir}':")
    for f in os.listdir(test_dir):
        print(f"- {f}")
    print("-" * 30)
    
    #--- Call the function ---
    #This will delete 'sensorX' files overlapping with 2025-06-05 to 2025-06-07
    delete_fft(
        path="jobs/test_files",
        sensor="sensorX",
        starttime="2025-06-05 00:00:00",
        endtime="2025-06-08 00:01:02",
        verbose=True
    )
    
    print("\nRemaining files in directory after execution:")
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            print(f"- {f}")
    else:
        print("Test directory deleted or does not exist.")
    
    # Clean up the test directory if needed
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"\nTest directory '{test_dir}' removed.")