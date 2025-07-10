import pytest
from scipy.io import loadmat
from monitoring.NOC import NOC
from monitoring.mspc_rt import mspc
import pandas as pd
import time
import ast

@pytest.fixture
def psab_data():
    features = loadmat('tests/data/features/PSAB_2025-06-17T12-00-00Z_2025-06-17T12-30-00Z', squeeze_me=True)
    
    # Introduce anomaly
    features['ffts'][335:340, :] = 2 * features['ffts'][5:10, :]
    return features

@pytest.fixture
def ppma_data():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T13-00-00Z', squeeze_me=True)
    
    # Introduce anomalies
    features['ffts'][335:340, :] = 2 * features['ffts'][5:10, :]
    features['ffts'][345:350, :] = 2 * features['ffts'][20:25, :]
    return features

@pytest.fixture
def ppma_data2():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T13-00-00Z', squeeze_me=True)
    
    return features

@pytest.fixture
def noc_psab(psab_data):
    noc = NOC('psab_NOC1', psab_data['ffts'][:330, :], obs_labels=psab_data['obs_labels'][:330], network='C7', station='PSAB', 
              type='dynamic', preprocessing=1, n_components=2, alpha=0.01, percentile_threshold=True, 
              q_method='Jackson', csv_path='tests/metadata/noc_list.csv')
    return noc

@pytest.fixture
def noc_ppma(ppma_data):
    noc = NOC('ppma_NOC1', ppma_data['ffts'][:330, :], obs_labels=ppma_data['obs_labels'][:330], network='C7', station='PPMA', 
              type='dynamic', preprocessing=1, n_components=3, alpha=0.01, percentile_threshold=True, 
              q_method='Jackson', csv_path='tests/metadata/noc_list.csv')
    return noc

    
def test_mspc_with_overlap(noc_psab, psab_data):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    last_noc_update = noc_psab.last_update_time
    assert noc_psab.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:27:35Z']

    time.sleep(1)  # so the last update time is not the same
    mspc([noc_psab], psab_data['ffts'][330:, :], '2025-06-17 12:27:30', '2025-06-17 12:30:00',
         window_size=10, window_shift=5, anomaly_log_path="tests/metadata/anomaly_log.csv",
         noc_log_path = "tests/metadata/noc_list.csv", nocs_path = "tests/data/nocs/", plot=True)
    
    # Check updated NOC
    noc_log = pd.read_csv("tests/metadata/noc_list.csv")
    noc_row_new = noc_log[noc_log['name'] == noc_psab.name]
    
    time_range_new = ast.literal_eval(noc_row_new['time_range'].iloc[0]) 
    assert noc_row_new['last_update_time'].iloc[0] == last_noc_update, "The NOC was updated but there were anomalies."
    assert len(noc_psab.obs_labels) == noc_psab.features.shape[0], "Number of labels does not match number of rows."
    assert time_range_new == ['2025-06-17T12:00:10Z', '2025-06-17T12:27:35Z'], "The time range was not updated correctly."

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_psab.name]
    assert len(new_anomalies) == 5
    
    
def test_mspc_without_overlap(noc_ppma, ppma_data):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    last_noc_update = noc_ppma.last_update_time
    assert noc_ppma.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:55:00Z']

    time.sleep(1)
    mspc([noc_ppma], ppma_data['ffts'][330:, :], '2025-06-17 12:55:00', '2025-06-17 13:00:00',
         window_size=10, window_shift=None, anomaly_log_path="tests/metadata/anomaly_log.csv",
         noc_log_path = "tests/metadata/noc_list.csv", nocs_path = "tests/data/nocs/", plot=True)
    
    # Check updated NOC
    noc_log = pd.read_csv("tests/metadata/noc_list.csv")
    noc_row_new = noc_log[noc_log['name'] == noc_ppma.name]
    
    time_range_new = ast.literal_eval(noc_row_new['time_range'].iloc[0]) 
    assert noc_row_new['last_update_time'].iloc[0] == last_noc_update, "The NOC was updated but there were anomalies."
    assert len(noc_ppma.obs_labels) == noc_ppma.features.shape[0], "Number of labels does not match number of rows."
    assert time_range_new == ['2025-06-17T12:00:10Z', '2025-06-17T12:55:00Z'], "The time range was not updated correctly."

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_ppma.name]
    assert len(new_anomalies) == 10


def test_mspc_no_anomalies(noc_ppma, ppma_data2):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    last_noc_update = noc_ppma.last_update_time
    assert noc_ppma.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:55:00Z']

    time.sleep(1)
    mspc([noc_ppma], ppma_data2['ffts'][330:, :], '2025-06-17 12:55:00', '2025-06-17 13:00:00',
         window_size=10, window_shift=None, anomaly_log_path="tests/metadata/anomaly_log.csv",
         noc_log_path = "tests/metadata/noc_list.csv", nocs_path = "tests/data/nocs/", plot=True)
    
     # Check updated NOC
    last_noc_update_new = noc_ppma.last_update_time
    noc_log = pd.read_csv("tests/metadata/noc_list.csv")
    noc_row_new = noc_log[noc_log['name'] == noc_ppma.name]
    
    time_range_new = ast.literal_eval(noc_row_new['time_range'].iloc[0]) 
    assert last_noc_update_new != last_noc_update, "The NOC was not updated."
    assert len(noc_ppma.obs_labels) == noc_ppma.features.shape[0], "Number of labels does not match number of rows."
    assert time_range_new == ['2025-06-17T12:05:10Z', '2025-06-17T13:00:00Z'], "The time range was not updated correctly."

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_ppma.name]
    assert len(new_anomalies) == 0