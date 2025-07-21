"""
Last update: 21/07/2025

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
from mspc_pca.mspc import DQ, DQ_tt, plot_DQ, plot_DQ_tt
from scipy.io import savemat
import csv
from datetime import datetime, timezone
import pickle
import matplotlib.dates as mdates


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
        
        # Attributes for test data
        self.D_test = []
        self.Q_test = []
        self.test_labels = []
        self.test_missing_rates = []

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

        # Update D and Q statistics
        self.calculate_DQ()

        self.last_update_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


    def pca(self, n_components=None):
        """
        Computes a PCA model from the features matrix.
        """

        if n_components is None:
            n_components = self.n_components
            
        if self.preprocessing == 2:
            scaler = StandardScaler(with_std=True)
            X = scaler.fit_transform(self.features)
        else:
            X = self.features

        pca_model = PCA(n_components=self.n_components)
        scores = pca_model.fit_transform(X)
        loadings = pca_model.components_.T

        return scores, loadings, pca_model


    def calculate_DQ(self):
        """
        Computes the D and Q-statistics and control limits for MSPC-PCA.
        """
        self.D, self.Q, self.D_threshold, self.Q_threshold = DQ(self.features, n_components=self.n_components, 
                                                                 preprocessing=self.preprocessing, alpha=self.alpha, 
                                                                 percentile_threshold=self.percentile_threshold, 
                                                                 type_q=self.q_method, plot=False)
        if len(self.D_threshold) == 1:
            self.D_threshold = self.D_threshold[0]
        
        if len(self.Q_threshold) == 1:
            self.Q_threshold = self.Q_threshold[0]

    
    def calculate_DQ_test(self, test, test_labels, missing_rates=None, store_dq=False):
        """
        Computes the D and Q-statistic for test data using NOC features as training.

        Parameters
        ----------
        test (numpy array)
            Features to be used as test for D and Q calculation.
        test_labels (list)
            Labels (UTC times) for all observations in test data.
        missing_rates (list or None)
            Rate of missing values for each observation in test data. Defaults to
            no missing values (None).
        store_dq (bool)
            If True, stores results as attributes. If False, returns results (default: False).

        Returns
        -------
        D_test (list)
            D-statistic values for test data.
        Q_test (list)
            Q-statistic values for test data.
        """
        # Ensure missing_rates is a list of appropriate length if None
        if missing_rates is None:
            missing_rates = [0.0] * len(test_labels)

        # Calculate D and Q
        _, _, D_test, Q_test, _, _ = DQ_tt(self.features, test, n_components=self.n_components,
                                            preprocessing=self.preprocessing, alpha=self.alpha,
                                            percentile_threshold=self.percentile_threshold,
                                            type_q=self.q_method, plot=False)

        if store_dq:
            # Load existing test data into a map
            combined_data_map = {}
            for i, label in enumerate(self.test_labels):
                combined_data_map[label] = (self.D_test[i], self.Q_test[i], self.test_missing_rates[i])

            # Add new values. Rewrite existing values if the label already exists
            for i, label in enumerate(test_labels):
                combined_data_map[label] = (D_test[i], Q_test[i], missing_rates[i])

            # Convert the map to a list of tuples for easier manipulation
            # (label, D_value, Q_value, missing_rate)
            combined_data_list = [(label, *values) for label, values in combined_data_map.items()]

            # Order chronologically
            combined_data_list.sort(key=lambda x: x[0])

            # Clear existing attributes and update with ordered values
            self.D_test.clear()
            self.Q_test.clear()
            self.test_labels.clear()
            self.test_missing_rates.clear()

            for label, d_val, q_val, mr_val in combined_data_list:
                self.test_labels.append(label)
                self.D_test.append(d_val)
                self.Q_test.append(q_val)
                self.test_missing_rates.append(mr_val)
        else:
            return D_test, Q_test
    

    def delete_DQ_test(self, stop_date = None):
        """
        Deletes D and Q values from previous calculations with test data.

        Parameters
        ----------
        stop_date (str or datetime)
            UTC date from when to keep values. Values corresponding to previous dates will be deleted.
            Default is None (delete all values).
        """
        if self.D_test and self.Q_test and self.test_labels:
            if stop_date is None:
                self.D_test = []
                self.Q_test = []
                self.test_labels = []
                self.test_missing_rates = []
            else:
                if isinstance(stop_date, str):
                    stop_date = datetime.strptime(stop_date, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

                time_labels = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in self.test_labels]
                self.D_test = [value for value, date in zip(self.D_test, time_labels) if date > stop_date]
                self.Q_test = [value for value, date in zip(self.Q_test, time_labels) if date > stop_date]
                self.test_labels = [label for label, date in zip(self.test_labels, time_labels) if date > stop_date]
                self.test_missing_rates = [rate for rate, date in zip(self.test_missing_rates, time_labels) if date > stop_date]


    def plot_DQ(self, logscale=False, event_index=None, opacity=None, ax=None):
        """
        Plots D and Q-statistics and control limits.

        Parameters
        ----------
        logscale (bool) 
            If True, plots the statistics on a logarithmic scale (default: False).
        event_index (list)
            List of indices of observations to highlight in the graph (default: None).
        opacity (list)
            Opacity values for each bar in the plot (default: None).
        ax (tuple of Axis)
            Axes in which to plot (optional, default: None).

        Returns
        -------
        fig
            Matplotlib figure.
        axes
            Tuple of two Axes objects, corresponding to the D and Q plots, respectively.
        """
        fig, axes = plot_DQ(self.D, self.Q, self.D_threshold, self.Q_threshold, labels = self.obs_labels,
                            logscale=logscale, event_index=event_index, opacity=opacity, ax=ax)
        
        if len(self.time_range) > 0:
            # Format labels
            for ax in axes:
                ax.set_xlabel("UTC Time")

                locator = mdates.AutoDateLocator()
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            fig.autofmt_xdate()
        
        return fig, axes


    def plot_DQ_test(self, starttime, endtime, logscale=False, event_index=None, opacity=None,
                     plot_train=False, ax=None):
        """
        Plots D and Q-statistics and control limits for train and test.

        Parameters
        ----------
        starttime (str or datetime)
            Start of the time range (UTC) depicted in the plot.
        endtime (str or datetime)
            End of the time range (UTC) depicted in the plot.
        logscale (bool) 
            If True, plots the statistics on a logarithmic scale (default: False)
        event_index (list)
            List of indices of observations to highlight in the graph (default: None).
        opacity (list)
            Opacity values for each bar in the plot. Defaults to using missing rates 
            as opacity values.
        plot_train (bool)
            If True, plots both training and test D and Q values. If False,  only plots
            tests values (default: False)
        ax (tuple of Axis)
            Axes in which to plot (optional, default: None).

        Returns
        -------
        fig
            Matplotlib figure.
        axes
            Tuple of two Axes objects, corresponding to the D and Q plots, respectively.
        """
        # Convert start and end to datetime if they are strings
        if isinstance(starttime, str):
            starttime = datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if isinstance(endtime, str):
            endtime = datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

        time_labels = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in self.test_labels]
        # Assumes that labels refer to the end time of the window
        label_indices = [i for i, date in enumerate(time_labels) if starttime < date <= endtime]

        # D and Q values, and labels to plot
        D_plot = [self.D_test[i] for i in label_indices]
        Q_plot = [self.Q_test[i] for i in label_indices]
        plot_labels = [self.test_labels[i] for i in label_indices]

        if opacity is None:
            opacity = [1 - self.test_missing_rates[i] for i in label_indices]

        if plot_train:
            plot_labels = self.obs_labels + plot_labels
            if opacity is not None:
                opacity = [1] * len(self.obs_labels) + opacity

        # Plot
        fig, axes = plot_DQ_tt(self.D, self.Q, D_plot, Q_plot, self.D_threshold, self.Q_threshold, 
                               labels = plot_labels, logscale=logscale, plot_train=plot_train,
                               event_index=event_index, opacity=opacity, ax=ax)

        # Format x-axis labels
        xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').time() for label in plot_labels]
        xlabels = []
        xticks = []
        tick_step = 30 if len(xtimes) > 100 else 6 
        for i in range(len(xtimes)):
            if i % tick_step == (tick_step-1):
                xticks.append(i + 0.5)
                xlabels.append(xtimes[i])

        day = datetime.strptime(plot_labels[-1], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        for ax in axes:
            ax.set_xlabel(str(day) + " (UTC Time)", loc='right')
            ax.set_xticks(xticks)  # Center the ticks on the bars
            ax.set_xticks(np.arange(len(plot_labels))+0.5, minor=True)  # Center the ticks on the bars
            ax.set_xticklabels(xlabels, rotation=45, ha='right') # Rotate for better visibility

        return fig, axes


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
        print(f"    Updated on: {self.last_update_time}")
        
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
            
            starttime = ""
            endtime = ""
            if len(self.time_range) > 0 and isinstance(self.time_range[0], str):
                starttime = self.time_range[0]
                endtime = self.time_range[1]
                    
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
                'start_time': starttime,
                'end_time': endtime,
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
