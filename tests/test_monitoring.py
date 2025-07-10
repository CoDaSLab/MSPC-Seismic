import pytest
from scipy.io import loadmat
import pandas as pd
from datetime import datetime, timedelta, timezone
import json

from monitoring.NOC import NOC
from monitoring.main import monitoring

@pytest.fixture
def ppma_data():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T13-00-00Z', squeeze_me=True)
    
    # Introduce anomalies
    features['ffts'][335:340, :] = 2 * features['ffts'][5:10, :]
    features['ffts'][345:350, :] = 2 * features['ffts'][20:25, :]
    return features

@pytest.fixture
def noc_ppma1(ppma_data):
    noc = NOC('ppma1', ppma_data['ffts'][:270, :], obs_labels=ppma_data['obs_labels'][:270], network='C7', station='PPMA', 
              type='dynamic', preprocessing=1, n_components=2, alpha=0.01, percentile_threshold=True, 
              csv_path='tests/metadata/noc_list.csv')
    return noc

@pytest.fixture
def noc_ppma2(ppma_data):
    noc = NOC('ppma2', ppma_data['ffts'][:270, :], obs_labels=ppma_data['obs_labels'][:270], network='C7', station='PPMA', 
              type='static', preprocessing=1, n_components=3, alpha=0.05, percentile_threshold=True, 
              csv_path='tests/metadata/noc_list.csv')
    return noc

def empty_csv(path):
    file = pd.read_csv(path, nrows=0)
    file.to_csv(path, index=False)

def test_monitoring_2nocs(noc_ppma1, noc_ppma2):
    config_path = "tests/config.json"
    
    # Empty logs
    empty_csv("tests/metadata/anomaly_log.csv")
    empty_csv("tests/metadata/noc_list.csv")

    # Save NOCs to files
    noc_ppma1.save(f"tests/data/nocs/{noc_ppma1.name}")
    noc_ppma2.save(f"tests/data/nocs/{noc_ppma2.name}")
    noc_ppma1.write_csv()
    noc_ppma2.write_csv()

    update_time1 = noc_ppma1.last_update_time
    update_time2 = noc_ppma2.last_update_time

    # Edit available stations file to make PPMA and PSAB available
    latest_pulls = pd.read_csv("tests/metadata/latest_pulls.csv")
    filtered_pulls = latest_pulls[latest_pulls['sensor'].isin(["PPMA", "PSAB"])]
    filtered_pulls["latest_pull_time"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    filtered_pulls.to_csv("tests/metadata/latest_pulls.csv")

    # Set starttime and endtime in config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        config["starttime"] = '2025-06-17T12:45:00Z'
        config["endtime"] = '2025-06-17T12:50:00Z'
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    # Run monitoring
    monitoring(config_path)

    # Check NOCs
    noc1 = NOC.load(f"tests/data/nocs/{noc_ppma1.name}")
    noc2 = NOC.load(f"tests/data/nocs/{noc_ppma2.name}")
    update_time_new1 = noc1.last_update_time
    update_time_new2 = noc2.last_update_time
    assert update_time1 != update_time_new1, "First run failed: dynamic NOC was not updated."
    assert update_time2 == update_time_new2, "First run failed: static NOC was updated."

    # Update starttime and endtime in config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        config["starttime"] = '2025-06-17T12:50:00Z'
        config["endtime"] = '2025-06-17T12:55:00Z'
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    # Run monitoring again
    monitoring(config_path)

    # Check NOCs
    noc1 = NOC.load(f"tests/data/nocs/{noc_ppma1.name}")
    noc2 = NOC.load(f"tests/data/nocs/{noc_ppma2.name}")
    assert update_time_new1 != noc1.last_update_time, "Second run failed: dynamic NOC was not updated when there were no anomalies."
    assert update_time_new2 == noc2.last_update_time, "Second run failed: static NOC was updated."
