import pytest
from scipy.io import loadmat
import pandas as pd
from datetime import datetime, timezone
import json
import os
import shutil
import tempfile

from monitoring.NOC import NOC
from monitoring.main import monitoring

@pytest.fixture
def ppma_data():
    features = loadmat('tests/data/features/PPMA_2025-06-17T12-00-00Z_2025-06-17T12-05-00Z', squeeze_me=True)
    
    # Introduce anomalies
    features['ffts'][23, :] = 2 * features['ffts'][5, :]
    features['ffts'][25:29, :] = 2 * features['ffts'][16:20, :]
    return features

@pytest.fixture
def noc_ppma1(ppma_data):
    noc = NOC('ppma1', ppma_data['ffts'][:20, :], obs_labels=ppma_data['obs_labels'][:20], network='C7', station='PPMA', 
              type='dynamic', preprocessing=1, n_components=2, alpha=0.01, percentile_threshold=True, 
              csv_path='tests/metadata/noc_list.csv')
    return noc

@pytest.fixture
def noc_ppma2(ppma_data):
    noc = NOC('ppma2', ppma_data['ffts'][:20, :], obs_labels=ppma_data['obs_labels'][:20], network='C7', station='PPMA', 
              type='static', preprocessing=1, n_components=3, alpha=0.05, percentile_threshold=True, 
              csv_path='tests/metadata/noc_list.csv')
    return noc

@pytest.fixture
def temp_dir_with_files():
    test_dir = tempfile.mkdtemp()

    files = [
        "report_2024-01-01.txt",     # Should be deleted
        "summary_2025-01-01.log",    # Should not be deleted
        "data_2023-12-31.txt",       # Should be deleted
        "notes_2025-07-16.txt",      # Same as cutoff
        "badfile_2025-13-01.txt",    # Invalid date
        "otherfile.txt"              # No date
    ]

    for filename in files:
        with open(os.path.join(test_dir, filename), 'w') as f:
            f.write("Test content")

    yield test_dir

    shutil.rmtree(test_dir)

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

    # Edit available stations file to make PPMA and PSAB available
    latest_pulls = pd.read_csv("tests/metadata/latest_pulls.csv")
    filtered_pulls = latest_pulls[latest_pulls['sensor'].isin(["PPMA", "PSAB"])]
    filtered_pulls["latest_pull_time"] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    filtered_pulls.to_csv("tests/metadata/latest_pulls.csv", index=False)

    # Set starttime and endtime in config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        config["starttime"] = '2025-06-17T12:03:20Z'
        config["endtime"] = '2025-06-17T12:04:10Z'
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    # Run monitoring
    monitoring(config_path)

    # Check NOCs
    noc_ppma1 = NOC.load(f"tests/data/nocs/{noc_ppma1.name}")
    noc_ppma2 = NOC.load(f"tests/data/nocs/{noc_ppma2.name}")
    assert len(noc_ppma1.D_test) == 5
    assert len(noc_ppma1.Q_test) == 5
    assert len(noc_ppma2.D_test) == 5
    assert len(noc_ppma2.Q_test) == 5

    # Update starttime and endtime in config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        config["starttime"] = '2025-06-17T12:04:10Z'
        config["endtime"] = '2025-06-17T12:05:00Z'
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    # Run monitoring again
    monitoring(config_path)

    # Check NOCs
    noc_ppma1 = NOC.load(f"tests/data/nocs/{noc_ppma1.name}")
    noc_ppma2 = NOC.load(f"tests/data/nocs/{noc_ppma2.name}")
    assert len(noc_ppma1.D_test) == 10
    assert len(noc_ppma1.Q_test) == 10
    assert len(noc_ppma2.D_test) == 10
    assert len(noc_ppma2.Q_test) == 10


def test_delete_old_files(temp_dir_with_files):
    from monitoring.main import delete_old_files

    delete_old_files(temp_dir_with_files, "%Y-%m-%d", "2025-07-16")

    remaining = set(os.listdir(temp_dir_with_files))
    expected = {
        "notes_2025-07-16.txt",
        "badfile_2025-13-01.txt",
        "otherfile.txt"
    }

    assert remaining == expected