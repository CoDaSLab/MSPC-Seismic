import pytest
from scipy.io import loadmat
from monitoring.NOC import NOC
from monitoring.mspc_rt import mspc
import pandas as pd
import time
import ast

@pytest.fixture
def psab_data():
    features = loadmat('tests/data/features/PSAB_2025-06-17T12-00-00Z_2025-06-17T12-02-30Z', squeeze_me=True)
    
    # Introduce anomaly
    features['ffts'][27:29, :] = 2 * features['ffts'][5:7, :]
    return features

@pytest.fixture
def ppma_data():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T12-05-00Z', squeeze_me=True)
    
    # Introduce anomalies
    features['ffts'][25, :] = 2 * features['ffts'][7, :]
    features['ffts'][28, :] = 2 * features['ffts'][22, :]
    return features

@pytest.fixture
def ppma_data2():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T12-05-00Z', squeeze_me=True)

    features['ffts'][25, :] = 0.5 * features['ffts'][7, :]
    features['ffts'][28, :] = 0.5 * features['ffts'][22, :]
    return features

@pytest.fixture
def noc_psab(psab_data):
    noc = NOC('psab_NOC1', psab_data['ffts'][:25, :], obs_labels=psab_data['obs_labels'][:25], network='C7', station='PSAB', 
              type='dynamic', preprocessing=1, n_components=2, alpha=0.01, percentile_threshold=True, 
              q_method='Jackson', csv_path='tests/metadata/noc_list.csv')
    return noc

@pytest.fixture
def noc_ppma(ppma_data):
    noc = NOC('ppma_NOC1', ppma_data['ffts'][:25, :], obs_labels=ppma_data['obs_labels'][:25], network='C7', station='PPMA', 
              type='dynamic', preprocessing=1, n_components=3, alpha=0.001, percentile_threshold=True, 
              q_method='Jackson', csv_path='tests/metadata/noc_list.csv')
    return noc

    
def test_mspc_with_overlap(noc_psab, psab_data):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    assert noc_psab.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:02:10Z']
    assert len(noc_psab.obs_labels) == noc_psab.features.shape[0]

    time.sleep(1)  # so the last update time is not the same
    # 29 windows: 25 training, 4 test
    mspc([noc_psab], psab_data['ffts'][25:, :], '2025-06-17 12:02:05', '2025-06-17 12:02:30',
         window_size=10, window_shift=5, anomaly_log_path="tests/metadata/anomaly_log.csv",
         nocs_path = "tests/data/nocs/", plot=True)
    
    assert len(noc_psab.D_test) == 4
    assert len(noc_psab.Q_test) == 4
    assert len(noc_psab.test_labels) == 4
    assert noc_psab.test_labels[0] == '2025-06-17T12:02:15Z'
    assert noc_psab.test_labels[-1] == '2025-06-17T12:02:30Z'

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_psab.name]
    assert len(new_anomalies) == 2
    
    
def test_mspc_without_overlap(noc_ppma, ppma_data):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    assert noc_ppma.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:04:10Z']
    assert len(noc_ppma.obs_labels) == noc_ppma.features.shape[0]

    time.sleep(1)
    # 30 windows: 25 training, 5 test
    mspc([noc_ppma], ppma_data['ffts'][25:, :], '2025-06-17 12:04:10', '2025-06-17 12:05:00',
         window_size=10, window_shift=None, anomaly_log_path="tests/metadata/anomaly_log.csv",
         nocs_path = "tests/data/nocs/", plot=True)
    
    assert len(noc_ppma.D_test) == 5
    assert len(noc_ppma.Q_test) == 5
    assert len(noc_ppma.test_labels) == 5
    assert noc_ppma.test_labels[0] == '2025-06-17T12:04:20Z'
    assert noc_ppma.test_labels[-1] == '2025-06-17T12:05:00Z'

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_ppma.name]
    assert len(new_anomalies) == 2


def test_mspc_no_anomalies(noc_ppma, ppma_data2):
    # Empty logs
    empty_noc_log = pd.read_csv("tests/metadata/noc_list.csv", nrows=0)
    empty_noc_log.to_csv("tests/metadata/noc_list.csv", index=False)
    empty_anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv", nrows=0)
    empty_anomaly_log.to_csv("tests/metadata/anomaly_log.csv", index=False)

    assert noc_ppma.time_range == ['2025-06-17T12:00:10Z', '2025-06-17T12:04:10Z']
    assert len(noc_ppma.obs_labels) == noc_ppma.features.shape[0]

    time.sleep(1)
    mspc([noc_ppma], ppma_data2['ffts'][25:, :], '2025-06-17 12:04:10', '2025-06-17 12:05:00',
         window_size=10, window_shift=None, anomaly_log_path="tests/metadata/anomaly_log.csv",
         nocs_path = "tests/data/nocs/", plot=True)
    
    assert len(noc_ppma.D_test) == 5
    assert len(noc_ppma.Q_test) == 5
    assert len(noc_ppma.test_labels) == 5
    assert noc_ppma.test_labels[0] == '2025-06-17T12:04:20Z'
    assert noc_ppma.test_labels[-1] == '2025-06-17T12:05:00Z'

    # Check updated anomaly log
    anomaly_log = pd.read_csv("tests/metadata/anomaly_log.csv")
    new_anomalies = anomaly_log[anomaly_log['NOC'] == noc_ppma.name]
    assert len(new_anomalies) == 0