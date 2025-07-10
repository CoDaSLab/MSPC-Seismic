from numpy._typing._array_like import NDArray
from monitoring.NOC import NOC
import numpy as np
import pytest

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

    noc.save(f"tests/nocs/{noc.name}.mat")
    noc.write_csv('tests/nocs/noc_list.csv')

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