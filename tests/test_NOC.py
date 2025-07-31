from numpy._typing._array_like import NDArray
from monitoring.NOC import NOC
import numpy as np
import pytest
import pandas as pd
from datetime import datetime, timezone
import matplotlib.pyplot as plt

@pytest.fixture
def features():
    return np.random.randn(50, 10)

@pytest.fixture
def new_features(features: NDArray[np.float64]):
    _, ncols = features.shape
    return np.random.randn(5, ncols)


def test_NOC_init_without_labels(features, new_features):
    noc = NOC('test_NOC', features, preprocessing=1, n_components=2)

    # Update NOC
    new_labels = ["a", "e", "i", "o", "u"]
    noc.update(new_features, new_labels)
    noc.summary()


def test_NOC_init_with_labels(features, new_features):
    labels = np.arange(50)

    noc = NOC('test_NOC', features, obs_labels=labels, preprocessing=1, n_components=2)

    # Update NOC
    new_labels = ["a", "e", "i", "o", "u"]
    noc.update(new_features, new_labels)
    noc.summary()


def test_NOC_update_no_deleting(features, new_features):
    labels = np.arange(50)

    noc = NOC('test_NOC', features, obs_labels=labels, preprocessing=1, n_components=2)
    # Does not delete old rows
    noc.update(new_features, delete_old=False)
    noc.summary()


def test_NOC_recalculate(features):
    labels = np.arange(50)

    noc = NOC('test_NOC', features, obs_labels=labels, preprocessing=1, n_components=2)
    # Only recalculates PCA and D and Q statistics
    noc.update()
    noc.summary()


def test_NOC_save(features, new_features):
    labels = np.arange(50)

    noc = NOC('test_NOC', features, obs_labels=labels, preprocessing=1, n_components=2)
    new_labels = ["a", "e", "i", "o", "u"]
    noc.update(new_features, new_labels)

    noc.save(f"tests/data/nocs/{noc.name}.mat")
    noc.write_csv('tests/metadata/noc_list.csv')


def test_NOC_time_labels():
    data = np.random.randn(7, 4)
    new_data = np.random.randn(4, 4)

    labels = [
        "2023-01-01 12:00:00",
        "2023-01-01 13:00:00",  # +1 hour
        "2023-01-01 14:00:00",  # +1 hour
        "2023-01-01 15:30:00",  # +1.5 hours (interval change)
        "2023-01-01 17:00:00",  # +1.5 hours
        "2023-01-01 18:30:00",  # +1.5 hours
        "2023-01-01 19:30:00"   # +1 hour (interval change)
    ]

    noc = NOC('test_NOC', data, obs_labels=labels, preprocessing=1, n_components=2)

    expected_time_range = [
        ["2023-01-01T12:00:00Z", "2023-01-01T14:00:00Z"],
        ["2023-01-01T15:30:00Z", "2023-01-01T18:30:00Z"],
        ["2023-01-01T19:30:00Z", "2023-01-01T19:30:00Z"]

    ]
    assert noc.time_range == expected_time_range, "Time range calculation failed."
    
    new_labels = [
        "2023-01-01 20:30:00",  # +1 hour
        "2023-01-01 22:30:00",  # +2 hours (interval change)
        "2023-01-02 00:30:00",  # +2 hours
        "2023-01-02 02:30:00",  # +2 hours
    ]
    noc.update(new_data, new_labels)

    expected_updated_time_range = [
        ["2023-01-01T17:00:00Z", "2023-01-01T17:00:00Z"],
        ["2023-01-01T18:30:00Z", "2023-01-01T20:30:00Z"],
        ["2023-01-01T22:30:00Z", "2023-01-02T02:30:00Z"]
    ]
    assert noc.time_range == expected_updated_time_range, "Updated time range calculation failed."

    noc.plot_DQ()  # plot mspc
    noc.save(f"tests/data/nocs/{noc.name}.mat", "mat")
    noc.save(f"tests/data/nocs/{noc.name}")
    noc.write_csv('tests/metadata/noc_list.csv')


def test_NOC_load():
    noc = NOC.load("tests/data/nocs/test_NOC")
    noc.update()
    noc.summary()


def test_NOC_DQ_test():
    # Create training data
    data = np.random.randn(24, 4)
    start = datetime(2025,1,1,0,0,0, tzinfo=timezone.utc)
    end = datetime(2025,1,1,0,4,0, tzinfo=timezone.utc)
    labels = list(pd.date_range(start, end, data.shape[0]+1).strftime('%Y-%m-%dT%H:%M:%SZ'))[1:]  # Exclude the first label

    assert data.shape[0] == len(labels)

    noc = NOC('test_NOC', data, obs_labels=labels, preprocessing=1, n_components=2)

    # Create test data
    test_data = np.random.rand(6, 4)
    start = datetime(2025,1,1,0,4,0, tzinfo=timezone.utc)
    end = datetime(2025,1,1,0,5,0, tzinfo=timezone.utc)
    test_labels = pd.date_range(start, end, test_data.shape[0]+1).strftime('%Y-%m-%dT%H:%M:%SZ')[1:]  # Exclude the first label

    assert test_data.shape[0] == len(test_labels)

    # Calculate D and Q test values
    _, _ = noc.calculate_DQ_test(test_data, test_labels, store_dq=True)
    
    assert noc.test_labels[0] == '2025-01-01T00:04:10Z'
    assert len(noc.D_test) == test_data.shape[0]
    assert len(noc.Q_test) == test_data.shape[0]

    # Plot D and Q test values
    noc.plot_DQ_test(start, end, plot_train = False)
    plt.tight_layout()
    plt.show()

    noc.plot_DQ_test(start, end, plot_train = True)
    plt.tight_layout()
    plt.show()

    # Delete test data from NOC
    noc.delete_DQ_test()

    assert len(noc.D_test) == 0
    assert len(noc.Q_test) == 0


def test_NOC_DQ_test_unordered_labels():
    # Create training data
    data = np.random.randn(24, 4)
    start = datetime(2025,1,1,0,0,0, tzinfo=timezone.utc)
    end = datetime(2025,1,1,0,4,0, tzinfo=timezone.utc)
    labels = list(pd.date_range(start, end, data.shape[0]+1).strftime('%Y-%m-%dT%H:%M:%SZ'))[1:]  # Exclude the first label

    assert data.shape[0] == len(labels)

    noc = NOC('test_NOC', data, obs_labels=labels, preprocessing=1, n_components=2)

    # Create test data
    test_data = np.random.rand(6, 4)
    start = datetime(2025,1,1,0,4,0, tzinfo=timezone.utc)
    end = datetime(2025,1,1,0,5,0, tzinfo=timezone.utc)
    test_labels = pd.date_range(start, end, test_data.shape[0]+1).strftime('%Y-%m-%dT%H:%M:%SZ')[1:]  # Exclude the first label

    assert test_data.shape[0] == len(test_labels)

    # Calculate D and Q test values
    _, _ = noc.calculate_DQ_test(test_data, test_labels, store_dq=True)
    D1 = noc.D_test.copy()
    Q1 = noc.Q_test.copy()
    
    assert noc.test_labels[0] == '2025-01-01T00:04:10Z'
    assert len(D1) == test_data.shape[0]
    assert len(Q1) == test_data.shape[0]

    # Test data part 2
    test_data2 = 2 * np.random.rand(7, 4)
    start2 = datetime(2024,12,31,23,50,0, tzinfo=timezone.utc)
    end2 = datetime(2024,12,31,23,51,0, tzinfo=timezone.utc)
    test_labels2 = list(pd.date_range(start2, end2, test_data2.shape[0]).strftime('%Y-%m-%dT%H:%M:%SZ')[1:])  # Exclude the first label
    test_labels2.append('2025-01-01T00:05:00Z')  # Add a duplicate label

    # Calculate D and Q test values
    _, _ = noc.calculate_DQ_test(test_data2, test_labels2, store_dq=True)
    
    assert noc.test_labels[0] == test_labels2[0]
    assert noc.test_labels[-1] == test_labels2[-1]
    assert len(noc.D_test) == len(test_data) + len(test_data2) - 1  # sum of lengths minus the duplicate
    assert len(noc.Q_test) == len(test_data) + len(test_data2) - 1
    assert noc.D_test[-2] == D1[-2]
    assert noc.D_test[-1] != D1[-1]  # Ensure the duplicate value was replaced


def test_compare_NOCs(features, new_features):
    from monitoring.NOC import compare_nocs
    
    new_features[:, 3] = 1.5 * np.abs(features[:len(new_features), 3]) + 1

    noc1 = NOC('test_NOC', features, preprocessing=1, n_components=2)
    noc2 = NOC('test_NOC2', new_features, preprocessing=1, n_components=2)

    omeda_vec, fig, ax = compare_nocs(noc2, noc1)

    assert len(omeda_vec) == features.shape[1]
    assert omeda_vec[3] > 0

    ax.set_ylabel("Changed label", loc="top")
    plt.tight_layout()
    plt.show()