from preprocessing.fft_rt import *
import os
from datetime import datetime, timedelta
from unittest.mock import patch
import shutil
import numpy as np
import pytest
from scipy.io import loadmat

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


def test_calculate_fft_multiple_stations():
    features = calculate_fft_rt('2025-06-17 12:00:00', '2025-06-17 12:01:00', 'C7', ['PPMA','PSAB'], channels=['HHE', 'HHN'], 
                    window_size=10, window_shift=None, detrend=False, fft_points='auto', 
                    merge_method=0, merge_fill_value = None, data_path="tests/data/mseed",
                    cpus=1, verbose=False, save=True, save_path="tests/data/features")

    assert features['ffts'].shape == (6, 2000)
    assert len(features['obs_labels']) == 6, "Number of labels does not match number of rows."
    assert features['obs_labels'][0] == "2025-06-17T12:00:10Z"
    assert features['obs_labels'][1] == "2025-06-17T12:00:20Z"
    assert features['obs_labels'][-1] == "2025-06-17T12:01:00Z"
    assert len(features['var_labels']) == 2000
    assert len(features['var_classes']) == 2000
    assert features['var_classes'][500] == 'PPMA.HHN'
    assert np.unique(features['var_classes']).tolist() == ['PPMA.HHE', 'PPMA.HHN', 'PSAB.HHE', 'PSAB.HHN']
    
    
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



@pytest.fixture
def fake_feat():
    """Simulate a feature file loaded with loadmat"""
    return {
        "ffts": np.array([[1, 2], [3, 4], [5, 6]]),
        "var_labels": ["v1", "v2"],
        "var_classes": ["c1", "c2"],
        "obs_labels": ["2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z", "2023-01-01T02:00:00Z"],
        "missing_rates": [0.0, 0.05, 0.0],
        "config": {"param": "ok"},
    }


class TestFindFeatures:
    def test_invalid_date_range(self):
        """Should raise an error if starttime > endtime"""
        with pytest.raises(AssertionError):
            find_features(
                path="dummy",
                stations="STA",
                starttime="2023-01-02 00:00:00",
                endtime="2023-01-01 00:00:00",
                feature_types=["ffts"]
            )

    @patch("preprocessing.fft_rt.list_fft_files")
    @patch("preprocessing.fft_rt.loadmat")
    def test_no_files(self, mock_loadmat, mock_list_fft):
        """If no files are found, should return an empty dict"""
        mock_list_fft.return_value = []
        result = find_features(
            path="dummy",
            stations="STA",
            starttime="2023-01-01 00:00:00",
            endtime="2023-01-02 00:00:00",
            feature_types=["ffts"]
        )
        assert result == {}

    @patch("preprocessing.fft_rt.list_fft_files")
    @patch("preprocessing.fft_rt.loadmat")
    def test_single_station_features(self, mock_loadmat, mock_list_fft, fake_feat):
        """Process a single file for one station and return feature dictionary"""
        mock_list_fft.return_value = ["fake_file.mat"]
        mock_loadmat.return_value = fake_feat

        result = find_features(
            path="dummy",
            stations="STA",
            starttime="2023-01-01 00:00:00",
            endtime="2023-01-02 00:00:00",
            feature_types=["ffts"]
        )

        assert "ffts" in result
        assert "obs_labels" in result
        assert "missing_rates" in result
        assert "var_labels" in result
        assert "var_classes" in result
        assert result["ffts"].shape[1] == 2  # two variables

    @patch("preprocessing.fft_rt.list_fft_files")
    @patch("preprocessing.fft_rt.loadmat")
    def test_additional_matches_filters(self, mock_loadmat, mock_list_fft, fake_feat):
        """Should discard files if additional_matches does not match"""
        mock_list_fft.return_value = ["fake_file.mat"]
        fake_feat["config"]["param"] = "other"  # does not match required
        mock_loadmat.return_value = fake_feat

        result = find_features(
            path="dummy",
            stations="STA",
            starttime="2023-01-01 00:00:00",
            endtime="2023-01-02 00:00:00",
            feature_types=["ffts"],
            additional_matches={"param": "ok"}
        )
        assert result == {}

    @patch("preprocessing.fft_rt.list_fft_files")
    @patch("preprocessing.fft_rt.loadmat")
    def test_multiple_stations_combination(self, mock_loadmat, mock_list_fft, fake_feat):
        """Should combine features from multiple stations correctly"""
        mock_list_fft.side_effect = [
            ["file_sta1.mat"],  # files for STA1
            ["file_sta2.mat"],  # files for STA2
        ]

        feat_sta1 = fake_feat.copy()
        feat_sta1["ffts"] = np.array([[10, 20], [30, 40], [50, 60]])
        feat_sta1["missing_rates"] = [0.0, 0.0, 0.0]

        feat_sta2 = fake_feat.copy()
        feat_sta2["ffts"] = np.array([[4, 5], [6, 7], [8, 9]])
        feat_sta2["obs_labels"] = ["2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z", "2023-01-01T03:00:00Z"]
        feat_sta2["missing_rates"] = [0.0, 0.1, 0.05]

        mock_loadmat.side_effect = [feat_sta1, feat_sta2]

        result = find_features(
            path="dummy",
            stations=["STA1", "STA2"],
            starttime="2023-01-01 00:00:00",
            endtime="2023-01-02 00:00:00",
            feature_types=["ffts"]
        )

        all_obs = ["2023-01-01T01:00:00Z", "2023-01-01T02:00:00Z", "2023-01-01T03:00:00Z"]
        all_ffts = np.array([[30, 40, 6, 7], [50, 60, 0, 0], [0, 0, 8, 9]])
        assert np.all(result["obs_labels"] == np.array(all_obs))
        assert np.allclose(result["missing_rates"], np.array([0.05, 0.5, 0.525]))
        assert result["ffts"].shape == (3, 4)
        assert np.allclose(result["ffts"], all_ffts)
        assert np.all(result["var_classes"] == np.array(['STA1.c1', 'STA1.c2', 'STA2.c1', 'STA2.c2']))
