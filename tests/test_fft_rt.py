from preprocessing.fft_rt import delete_fft, calculate_fft_rt
import os
from datetime import datetime, timedelta
import shutil
import numpy as np

def test_calculate_fft():
    features = calculate_fft_rt('2025-06-17 12:00:00', '2025-06-17 12:05:00', 'C7', 'PPMA', channels=['HHE', 'HHN', 'HHZ'], 
                    window_size=10, window_shift=None, detrend=False, fft_points='auto', 
                    merge_method=0, merge_fill_value = None, data_path="tests/data/mseed",
                    cpus=1, verbose=False, save=True, save_path="tests/data/features")

    assert features['ffts'].shape == (30, 1500)
    assert len(features['obs_labels']) == 30, "Number of labels does not match number of rows."
    assert features['obs_labels'][0] == "2025-06-17T12:00:10Z"
    assert features['obs_labels'][1] == "2025-06-17T12:00:20Z"
    assert features['obs_labels'][-1] == "2025-06-17T12:05:00Z"
    
    
def test_calculate_fft_with_overlap():
    features = calculate_fft_rt('2025-06-17 12:00:00', '2025-06-17 12:02:30', 'C7', 'PSAB', channels=['HHE', 'HHN', 'HHZ'], 
                    window_size=10, window_shift=5, detrend=False, fft_points='auto', 
                    merge_method=1, merge_fill_value = None, data_path="tests/data/mseed",
                    cpus=2, verbose=False, save=True, save_path="tests/data/features")

    assert features['ffts'].shape == (29, 1500)
    assert len(features['obs_labels']) == 29, "Number of labels does not match number of rows."
    assert features['obs_labels'][0] == "2025-06-17T12:00:10Z"
    assert features['obs_labels'][1] == "2025-06-17T12:00:15Z"
    assert features['obs_labels'][-1] == "2025-06-17T12:02:30Z"


def test_calculate_fft_gap():
    features = calculate_fft_rt('2021-09-10 22:30:00', '2021-09-10 23:00:00', 'C7', 'PPMA', channels=['HHE'], 
                    window_size=10, window_shift=None, detrend=False, fft_points='auto', 
                    merge_method=0, merge_fill_value = None, pad_fill_value = 0, data_path="tests/data/mseed",
                    cpus=1, verbose=False, save=True, save_path="tests/data/features")

    assert features['ffts'].shape == (180, 500)
    assert len(features['obs_labels']) == 180, "Number of labels does not match number of rows."
    assert features['obs_labels'][0] == "2021-09-10T22:30:10Z"
    assert features['obs_labels'][1] == "2021-09-10T22:30:20Z"
    assert features['obs_labels'][-1] == "2021-09-10T23:00:00Z"
    assert features['missing_rates'][0] < 1
    assert features['missing_rates'][-1] == 1
    assert not np.all(features['ffts'][0,:] == 0)
    assert np.all(features['ffts'][-1,:] == 0)
    

def test_calculate_fft_no_signal():
    features = calculate_fft_rt('2021-09-10 22:55:00', '2021-09-10 23:00:00', 'C7', 'PPMA', channels=['HHE'], 
                    window_size=10, window_shift=None, detrend=False, fft_points='auto', 
                    merge_method=0, merge_fill_value = None, pad_fill_value = 0, data_path="tests/data/mseed",
                    cpus=1, verbose=False, save=True, save_path="tests/data/features")

    assert features['ffts'].shape == (30, 500)
    assert len(features['obs_labels']) == 30, "Number of labels does not match number of rows."
    assert features['obs_labels'][0] == "2021-09-10T22:55:10Z"
    assert features['obs_labels'][1] == "2021-09-10T22:55:20Z"
    assert features['obs_labels'][-1] == "2021-09-10T23:00:00Z"
    assert np.all(features['missing_rates']) == 1
    assert np.all(features['ffts'] == 0)


def test_delete_fft():    
    # Create a test directory and some dummy files
    test_dir = "tests/test_files"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    station_1 = "stationX"
    station_2 = "stationY"
    
    base_dt = datetime(2025, 6, 1, 0, 1, 2)
    for i in range(10):
        file_start = base_dt + timedelta(days=i)
        file_end = file_start + timedelta(days=2)
        
        # Files for stationX
        filename_1 = f"{station_1}_{file_start.strftime('%Y-%m-%dT%H-%M-%SZ')}_{file_end.strftime('%Y-%m-%dT%H-%M-%SZ')}.xyz"
        with open(os.path.join(test_dir, filename_1), 'w') as f:
            f.write("dummy content")
        
        # Files for stationY
        filename_2 = f"{station_2}_{file_start.strftime('%Y-%m-%dT%H-%M-%SZ')}_{file_end.strftime('%Y-%m-%dT%H-%M-%SZ')}.xyz"
        with open(os.path.join(test_dir, filename_2), 'w') as f:
            f.write("dummy content")
    
    all_files = os.listdir(test_dir)

    delete_fft(
        path=test_dir,
        station="stationX",
        starttime="2025-06-05 00:00:00",
        endtime="2025-06-08 00:01:02",
        verbose=True
    )

    remaining_files = os.listdir(test_dir)
    
    assert all_files != remaining_files, "Some files should have been removed, but they were not."
    
    expected_files = ["stationX_2025-06-01T00-01-02Z_2025-06-03T00-01-02Z.xyz",
                        "stationX_2025-06-02T00-01-02Z_2025-06-04T00-01-02Z.xyz",
                        "stationX_2025-06-03T00-01-02Z_2025-06-05T00-01-02Z.xyz",
                        "stationX_2025-06-04T00-01-02Z_2025-06-06T00-01-02Z.xyz",
                        "stationX_2025-06-07T00-01-02Z_2025-06-09T00-01-02Z.xyz",
                        "stationX_2025-06-08T00-01-02Z_2025-06-10T00-01-02Z.xyz",
                        "stationX_2025-06-09T00-01-02Z_2025-06-11T00-01-02Z.xyz",
                        "stationX_2025-06-10T00-01-02Z_2025-06-12T00-01-02Z.xyz",
                        "stationY_2025-06-01T00-01-02Z_2025-06-03T00-01-02Z.xyz",
                        "stationY_2025-06-02T00-01-02Z_2025-06-04T00-01-02Z.xyz",
                        "stationY_2025-06-03T00-01-02Z_2025-06-05T00-01-02Z.xyz",
                        "stationY_2025-06-04T00-01-02Z_2025-06-06T00-01-02Z.xyz",
                        "stationY_2025-06-05T00-01-02Z_2025-06-07T00-01-02Z.xyz",
                        "stationY_2025-06-06T00-01-02Z_2025-06-08T00-01-02Z.xyz",
                        "stationY_2025-06-07T00-01-02Z_2025-06-09T00-01-02Z.xyz",
                        "stationY_2025-06-08T00-01-02Z_2025-06-10T00-01-02Z.xyz",
                        "stationY_2025-06-09T00-01-02Z_2025-06-11T00-01-02Z.xyz",
                        "stationY_2025-06-10T00-01-02Z_2025-06-12T00-01-02Z.xyz"]
    
    assert remaining_files == expected_files, "The remaining files are not the expected ones."
    
    # Clean up the test directory if needed
    if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
