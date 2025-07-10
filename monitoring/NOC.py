"""
Last update: 04/07/2025

file name: NOC.py

Description:
This file contains the code for the NOC class.
This class is used to store all information associated with Normal Operation Conditions (NOC) for 
real-time monitoring using MSPC-PCA.
"""

import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from mspc_pca.mspc import DyQ, plot_DyQ
from scipy.io import savemat
import csv
from datetime import datetime, timezone
import pickle


class NOC:
    def __init__(self, name:str, features:np.ndarray, obs_labels:list = None, 
                 network:str = "", station:str = "", type:str = "", preprocessing:int = 1, 
                 n_components:int = None, alpha:float = 0.01, percentile_threshold:bool = True, 
                 q_method:str = 'Jackson', csv_path:str = None):
        """
        Stores and updates information associated with the Normal Operation Conditions (NOC) for
        real-time monitoring using Principal Component Analysis-based Multivariate Statistical 
        Process Control (MSPC-PCA).

        Parameters
        ----------
        name (str)
            NOC name.
        network (str)
            Network code.
        station (str)
            Station code.
        type (str)
            Type of NOC (static or dynamic).
        features (numpy array)
            2D matrix of features used as training data for MSPC-PCA.
        obs_labels (list of string)
            Labels for the observations (rows) of the feature matrix.
        preprocessing (int)
            Type of preprocessing to apply to features:
                1: centering (default)
                2: centering and scaling
        n_components (int)
            Number of principal components to compute and used for MSPC.
            Default is `min(features.shape)`.
        alpha (float)
            Significance level. Used for percentile calculation if `percentile_threshold == True`.
            Default ia 0.01.
        percentile_threshold (bool)
            If True, computes the control limits as the `(1 - alpha) * 100` percentile of the 
            D and Q values for the training data. If False, uses methods by Tracy et al. (1992)
            for D, and Box (1954) or Jackson and Mudholkar (1979) for Q. Default is True.
        q_method (str)
            Method for Q control limit. Only used if percentile_threshold = False.
                - 'Box' for Box (1954)
                - 'Jackson' for Jackson and Mudholkar (1979) (default)
        csv_path (str)
            Path to a CSV file for writing NOC information.

        """
        # Parameter check
        if not isinstance(features, np.ndarray):
            raise TypeError("features must be a numpy ndarray")

        if features.ndim != 2:
            raise ValueError(f"features must be a 2D matrix, but got shape {features.shape}")

        # Initialization
        self.name = name
        self.network = network
        self.station = station
        self.type = type
        self.features = features
        if obs_labels is not None:
            self.obs_labels = list(obs_labels)
        else:
            self.obs_labels = [""] * self.features.shape[0]
        self.get_time_range()

        self.preprocessing = preprocessing
        if n_components:
            self.n_components = n_components
        else: 
            self.n_components = np.min(features.shape)
        self.alpha = alpha
        self.percentile_threshold = percentile_threshold
        self.q_method = q_method
        self.csv_path = csv_path

        # Calculate PCA
        self.pca()

        # Calculate D and Q statistics
        self.calculate_DQ()

        self.last_update_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


    def update(self, new_features=None, new_obs_labels=[], delete_old=True):
        """
        Updates the NOC's features, and recalculates the PCA model and D and Q statistics. If new features are provided, 
        they are appended to the previously existing features matrix.

        Parameters
        ----------
        new_features (numpy array)
            2D matrix containing new features to append to the previously existing feature matrix.
            Default is None.
        new_obs_labels (list)
            Observation (row) labels for `new_features`.
        delete_old (bool)
            If True, the first rows of the previous feature matrix will be replaced, so the
            updated features matrix will have the same shape as the previously existing one.
            Default is True.
        """
        # Check new features and labels
        num_rows, num_cols = self.features.shape
        if new_features is None:
            new_features = np.empty((0, num_cols))

        num_new_rows, num_new_cols = new_features.shape
        assert num_new_cols == num_cols, f"New features matrix has {num_new_cols} columns but should have {num_cols} columns."

        if len(new_obs_labels) > 0:
            assert len(new_obs_labels) == num_new_rows, f"Parameter new_obs_labels has length {len(new_obs_labels)}, but should have length {num_new_rows}."

        # Delete old features 
        if delete_old and num_new_rows <= num_rows:
            self.features = np.delete(self.features, np.arange(num_new_rows), axis=0)
            self.obs_labels = self.obs_labels[num_new_rows:]

        # Add new features
        self.features = np.vstack((self.features, new_features))
        if len(new_obs_labels) > 0:
            self.obs_labels.extend(new_obs_labels)
        else:
            self.obs_labels.extend([""] * num_new_rows)
        self.get_time_range()
        
        # Update PCA model
        self.pca()

        # Update D and Q statistics
        self.calculate_DQ()

        self.last_update_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


    def pca(self):
        """
        Computes a PCA model from the features matrix.
        """
        if self.preprocessing == 2:
            scaler = StandardScaler(with_std=True)
            X = scaler.fit_transform(self.features)
        else:
            X = self.features

        self.pca_model = PCA(n_components=self.n_components)
        self.scores = self.pca_model.fit_transform(X)
        self.loadings = self.pca_model.components_.T


    def calculate_DQ(self):
        """
        Computes the D and Q-statistics and control limits for MSPC-PCA.
        """
        self.D, self.Q, self.D_threshold, self.Q_threshold = DyQ(self.features, n_components=self.n_components, 
                                                                 preprocessing=self.preprocessing, alpha=self.alpha, 
                                                                 percentile_threshold=self.percentile_threshold, 
                                                                 type_q=self.q_method, plot=False)
        if len(self.D_threshold) == 1:
            self.D_threshold = self.D_threshold[0]
        
        if len(self.Q_threshold) == 1:
            self.Q_threshold = self.Q_threshold[0]
    

    def plot_DQ(self, logscale=False):
        """
        Plots D and Q-statistics and control limits.

        Parameters
        ----------
        logscale (bool) 
            If True, plots the statistics on a logarithmic scale (default: False)
        """
        plot_DyQ(self.D, self.Q, self.D_threshold, self.Q_threshold, logscale=logscale)


    def get_time_range(self):
        """
        Obtains the data time range from the observation labels as a list of pairs 
        [first window time, last window time].
        """
        self.time_range = []

        if len(self.obs_labels) > 1:
            dates = self.obs_labels[:]

            # Parse dates in in observation labels
            for i, date in enumerate(self.obs_labels):
                if isinstance(date, str):
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                        try:
                            dates[i] = datetime.strptime(date, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        print(f"Could not parse '{date}' as date.")
                        return
                else:
                    return

            # Calculate differences
            diffs = [dates[i+1] - dates[i] for i in range(len(dates)-1)]
            if all([diff == diffs[0] for diff in diffs]):
                first_window_time = datetime.strftime(dates[0], "%Y-%m-%dT%H:%M:%SZ")
                last_window_time = datetime.strftime(dates[-1], "%Y-%m-%dT%H:%M:%SZ")
                self.time_range.extend([first_window_time, last_window_time])
            else:
                # Group by time interval between consecutive observations
                current_group = [dates[0]]
                for i in range(1, len(dates)-1):
                    if diffs[i-1] == diffs[i]:
                        current_group.append(dates[i])
                    else:
                        if len(current_group) > 1:
                            current_group.append(dates[i])
                        # Obtain time range
                        first_window_time = datetime.strftime(current_group[0], "%Y-%m-%dT%H:%M:%SZ")
                        last_window_time = datetime.strftime(current_group[-1], "%Y-%m-%dT%H:%M:%SZ")
                        self.time_range.append([first_window_time, last_window_time])
                        current_group = [dates[i+1]] if len(current_group) > 1 else [dates[i]]
                else:
                    first_window_time = datetime.strftime(current_group[0], "%Y-%m-%dT%H:%M:%SZ")
                    last_window_time = datetime.strftime(dates[-1], "%Y-%m-%dT%H:%M:%SZ")
                    self.time_range.append([first_window_time, last_window_time])

    
    def summary(self):
        """
        Prints a summary of the NOC.
        """
        print("======== NOC Summary ========")
        print("Information:")
        print(f"    Name: {self.name}")
        print(f"    Network: {self.network}")
        print(f"    Station: {self.station}")
        print(f"    NOC type: {self.type}")
        
        print("Parameters:")
        print(f"    Features shape: {self.features.shape}")
        print(f"    Preprocessing: {self.preprocessing} ({'centering' if self.preprocessing == 1 else 'centering + scaling'})")
        print(f"    Number of principal components: {self.n_components}")

        print(f"    Use percentile as threshold: {self.percentile_threshold}")
        if self.percentile_threshold == True:
            print(f"    Percentile: {(1 - self.alpha) * 100}")
        else:
            print(f"    Significance level: {self.alpha}")
            print(f"    Q threshold method: {self.q_method}")

        print("Control limits:")
        print(f"    D threshold: {self.D_threshold:.4f}")
        print(f"    Q threshold: {self.Q_threshold:.4f}")
        print("=============================")

    
    def save(self, filepath, filetype='pickle'):
        """
        Saves NOC data in a file.

        Parameters
        ----------
        filepath (str)
            Path to the output file.
        filetype (str)
            'mat' for .mat file, 'pickle' for using pickle (default: 'pickle')
        """
        # Create directory if it does not exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if filetype == 'mat':
            data = self.__dict__
            del data['pca_model']
            del data['csv_path']

            # Save dictionary with all NOC attributes
            savemat(filepath, data)
        else:
            with open(filepath, 'wb') as f:
                pickle.dump(self, f)
    

    @staticmethod
    def load(filepath):
        """
        Load a NOC from a pickle file.

        Parameters
        ----------
        filepath (str)
            Path to the input file.
        """
        with open(filepath, 'rb') as f:
            return pickle.load(f)
        

    def write_csv(self, path=None):
        """
        Write NOC information as a row in a CSV file.

        Parameters
        ----------
        path (str)
            Path to the CSV file.
        """
        csv_path = self.csv_path if path is None else path

        if csv_path is not None:
            # Create directory if it does not exist
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Create new row
            row = {
                'name': self.name,
                'network': self.network,
                'station': self.station,
                'type': self.type,
                'n_windows': self.features.shape[0],
                'n_variables': self.features.shape[1],
                'n_components': self.n_components,
                'D_threshold': np.round(self.D_threshold, 4),
                'Q_threshold': np.round(self.Q_threshold, 4),
                'time_range': self.time_range,
                'last_update_time': self.last_update_time
            }

            updated = False
            rows = []
            if os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0:
                with open(csv_path, mode="r", newline='', encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for existing_row in reader:
                        if existing_row['name'] == row['name']:
                            rows.append(row)  # Replace the row with the same 'name'
                            updated = True
                        else:
                            rows.append(existing_row)

            if not updated:
                rows.append(row)  # Add new row if no existing match was found

            # Write all rows back
            with open(csv_path, mode="w", newline='', encoding="utf-8") as file:
                fields = row.keys()
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

    def __str__(self):
        return f"NOC class. Name: {self.name}."


if __name__ == '__main__':
    from scipy.io import loadmat

    # data = loadmat("data/involcan/features/PPMA_2025-06-18T01-00-00Z_2025-06-18T09-00-00Z", 
    #                 squeeze_me=True)
    # features = data['ffts']

    features = np.random.randn(50, 5)
    labels = np.arange(50)
    n_cols = features.shape[1]

    noc = NOC('test_NOC', features, preprocessing=1, n_components=2)
    # noc.plot_DQ()
    noc.summary()

    # Update NOC
    new_features = np.random.randn(5, n_cols)
    new_labels = ["a", "e", "i", "o", "u"]
    noc.update(new_features, new_labels)
    noc.summary()

    noc.update(new_features, delete_old=False)
    noc.summary()

    noc.update()
    noc.save("jobs/nocs/nocnoc")
    noc.write_csv('jobs/nocs/noc_list.csv')
    print(noc.time_range)