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


def test_NOC_save(features):
    labels = np.arange(50)

    noc = NOC('test_NOC', features, obs_labels=labels, preprocessing=1, n_components=2)

    noc.save(f"tests/data/nocs/{noc.name}")
    noc.write_csv('tests/metadata/noc_list.csv')


def test_NOC_load():
    noc = NOC.load("tests/data/nocs/test_NOC")
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
    noc1.save(f"tests/data/nocs/{noc1.name}")
    noc2 = NOC('test_NOC2', new_features, preprocessing=1, n_components=2)
    noc2.save(f"tests/data/nocs/{noc2.name}")

    omeda_vec, fig, ax = compare_nocs(noc2, noc1, "tests/data/nocs/")

    assert len(omeda_vec) == features.shape[1]
    assert omeda_vec[3] > 0

    ax.set_ylabel("Changed label", loc="top")
    plt.tight_layout()
    plt.show()


def test_NOC_calculate_T():
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
    D_test, Q_test = noc.calculate_DQ_test(test_data, test_labels, store_dq=True)
    T_train, T_test = noc.calculate_T_test(weight=0)
    D_train, Q_train = np.array(noc.D), np.array(noc.Q)
    
    assert np.allclose(noc.Q_test, Q_test)
    assert np.allclose(T_train, np.array(Q_train) / np.median(Q_train))
    assert np.allclose(T_test, np.array(Q_test) / np.median(Q_train))
    assert noc.test_labels[0] == '2025-01-01T00:04:10Z'
    assert len(T_test) == test_data.shape[0]

    # Plot D and Q test values
    noc.plot_T_test(T_train, T_test, start, end, plot_train = False)
    plt.tight_layout()
    plt.show()

    noc.plot_T_test(T_train, T_test, start, end, plot_train = True)
    plt.tight_layout()
    plt.show()


def test_NOC_n_components(features):
    # Create a NOC instance without specifying n_components
    noc = NOC("test_NOC", features, preprocessing=1)
    
    fig, ax = noc.calculate_n_components(plot=True)

    # Find the knee label
    _, labels = ax.get_legend_handles_labels()
    knee_labels = [lbl for lbl in labels if lbl.lower().startswith("knee at")]

    assert knee_labels, "There should be a legend entry for the knee line"
    # Extract the number from the label
    knee_value = float(knee_labels[0].split(" ")[-1].strip()[:-1])

    # Compare with the computed n_components
    if knee_value >= 0.5:
        assert round(knee_value) == noc.n_components
    else:
        assert noc.n_components == 1

    plt.tight_layout()
    plt.show()
