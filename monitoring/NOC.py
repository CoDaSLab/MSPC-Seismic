"""
Last update: 19/09/2025

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
from mspc_pca import mspc, plot
from scipy.io import savemat
import csv
from datetime import datetime, timezone
import pickle


class NOC:
    def __init__(self, name:str, features:np.ndarray, obs_labels:list = None, 
                 network:str = "", station:str = "", type:str = "", preprocessing:int = 1, 
                 n_components:int = 1, quantile_threshold:float = 0.99, 
                 csv_path:str = None):
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
            Station code or list of station codes.
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
            'auto' for automatic calculation of the number of components.
            Default is `min(features.shape)`.
        quantile_threshold (float)
            Quantile of the D and Q values used as threshold. Default is 0.99.
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
        self.features_shape = features.shape
        if obs_labels is not None:
            self.obs_labels = list(obs_labels)
        else:
            self.obs_labels = [""] * self.features_shape[0]
            
        # Features metadata
        self.metadata = {}
        self.time_range = []

        self.preprocessing = preprocessing
        if n_components:
            self.n_components = n_components
        else: 
            self.n_components = np.min(features.shape)
        self.quantile_threshold = quantile_threshold
        self.csv_path = csv_path

        # Find number of components
        if n_components == 'var':
            self.calculate_n_components(method='var')
        elif n_components == 'ckf':
            self.calculate_n_components(method='ckf')

        self.D = []
        self.Q = []
        
        # Attributes for test data
        self.D_test = []
        self.Q_test = []
        self.test_labels = []
        self.test_missing_rates = []

        # Calculate D and Q statistics
        self.calculate_DQ()

        self.last_update_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def recalculate(self, nocs_path):
        """
        Recalculate D and Q-statistic values.
        """
        # Delete stored D and Q values
        self.delete_DQ_test()

        # Load features
        self.features = self.load_features(nocs_path)

        # Calculate D and Q again
        self.calculate_DQ()
        self.last_update_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    def set_metadata(self, starttime, endtime, window_size, window_shift=None, 
                     detrend=None, windowing=False, fft_points='auto', 
                     merge_method=0, merge_fill_value=None, pad_fill_value=0):
        """
        Create a `metadata` attribute containing information related to the training features.
        """
        if isinstance(starttime, datetime):
            starttime = starttime.strftime('%Y-%m-%dT%H:%M:%SZ')
            endtime = endtime.strftime('%Y-%m-%dT%H:%M:%SZ')
            
        self.metadata["start_time"] = starttime
        self.metadata["end_time"] = endtime
        self.metadata["window_size"] = window_size
        if window_shift is None:
            self.metadata["window_shift"] = window_size
        else: self.metadata["window_shift"] = window_shift
        self.metadata["detrend"] = detrend
        self.metadata["windowing"] = windowing
        self.metadata["fft_points"] = fft_points
        self.metadata["merge_method"] = merge_method
        self.metadata["merge_fill_value"] = merge_fill_value
        self.metadata["pad_fill_value"] = pad_fill_value

        self.time_range = [starttime, endtime]
    
    
    def calculate_n_components(self, max_components=None, method='var', plot=False, ax=None):
        """
        Automatically determines the number of principal components for MSPC-PCA by finding
        a knee in the CKF function (method='ckf') or the residual variance (method='var')
        """
        from kneefinder import KneeFinder
        from mspc_pca.ckf import ckf
        
        if self.preprocessing == 2:
            scaler = StandardScaler(with_std=True)
            X = scaler.fit_transform(self.features)
        else:
            X = self.features.copy()

        pca = PCA(n_components=max_components)
        X_fit = pca.fit_transform(X)

        scores = X_fit
        loadings = pca.components_
        data_x = np.arange(len(pca.explained_variance_ratio_) + 1)

        if method == 'ckf':
            ckf_cumpress = ckf(X, scores, loadings.T, plot=False)
            data_y = ckf_cumpress / ckf_cumpress[0]  # Normalize CKF
        elif method == 'var':
            res_var = np.array(1 - np.cumsum(pca.explained_variance_ratio_))  # residual variance
            data_y = np.insert(res_var, 0, 1)
        
        # Find knee
        kf = KneeFinder(data_x=data_x, data_y=data_y)
        knee_x, _ = kf.find_knee()

        self.n_components = max(1, round(knee_x))

        if plot:
            import matplotlib.pyplot as plt
             # --- Plotting ---
            if ax is None:
                fig, ax = plt.subplots(figsize=(6, 4))
            
            ax.plot(data_x, data_y, label="Residual Variance" if method=='var' else "ckf", color='red', marker='o')
            ax.axvline(x=knee_x, color="black", linestyle="--", label=f"Knee at $x = {knee_x}$")
            ax.set_xlabel("Number of Principal Components")
            ax.legend()

            return fig, ax


    def calculate_DQ(self):
        """
        Computes the D and Q-statistics and control limits for MSPC-PCA.
        """
        if len(self.D) > 0 and len(self.Q) > 0:
            return
        
        # Preprocessing
        self.mean = np.mean(self.features, axis=0)
        self.std = np.std(self.features, axis=0, ddof=1) # Bessel's correction, shouldn't affect results but is mathematically correct
        if self.preprocessing == 1:
            X_norm = self.features - self.mean
        elif self.preprocessing == 2:
            X_norm = (self.features - self.mean) / self.std

        # PCA
        pca = PCA(n_components=self.n_components)
        scores = pca.fit_transform(X_norm)
        self.pca = pca

        self.score_mean = np.mean(scores, axis=0)
        self.score_std = np.std(scores, axis=0, ddof=1)
        self.D = np.sum(((scores - self.score_mean) / self.score_std) ** 2, axis=1)

        X_norm_reconstructed = pca.inverse_transform(scores)
        residuals = X_norm - X_norm_reconstructed
        self.Q = np.sum(residuals ** 2, axis=1)

        # Thresholds
        quantile_threshold = self.quantile_threshold
        if np.isscalar(quantile_threshold):
            self.D_threshold = np.percentile(self.D, 100 * (1 - quantile_threshold))
            self.Q_threshold = np.percentile(self.Q, 100 * (1 - quantile_threshold))
        else:
            self.D_threshold = []
            self.Q_threshold = []
            for a in quantile_threshold:
                self.D_threshold.append(np.percentile(self.D, 100 * (1 - a)))
                self.Q_threshold.append(np.percentile(self.Q, 100 * (1 - a)))


    def calculate_T(self, weight=None, norm_quantile=0.5):
        """
        Computes the T-scores for MSPC-PCA.
        T = weight * D / UCL_D + (1 - weight) * Q / UCL_Q
        UCL_D and UCL_Q are calculated as the norm_quantile quantile and of the D and Q values, respectively
        Original paper: Computers & Security 87 (2019) 101603

        Parameters
        ----------
        weight: float 
            Weighting factor (between 0 and 1) for T-score. Default is the ratio between
              number of principal components and the number of variables of the features matrix.
        norm_quantile: float
            Quantile used for normalization in the T-score formula. Default is 0.5 (median).
        
        Returns
        -------
        list: 
            T-score values.
        """
        if weight is None:
            weight = self.n_components / self.features_shape[1]

        T = mspc.tscore((self.D, self.Q), weight=weight, norm_quantile=norm_quantile)
        return T

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

        # Preprocessing
        if self.preprocessing == 1:
            X_test_norm = test - self.mean
        elif self.preprocessing == 2:
            X_test_norm = (test - self.mean) / self.std
        
        scores_test = self.pca.transform(X_test_norm)
        
        # Calculate D and Q
        D_test = np.sum(((scores_test - self.score_mean) / self.score_std) ** 2, axis=1)
        X_test_norm_reconstructed = self.pca.inverse_transform(scores_test)
        residuals_test = X_test_norm - X_test_norm_reconstructed
        Q_test = np.sum(residuals_test ** 2, axis=1)

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
        
        return D_test, Q_test
    
    def calculate_T_test(self, weight=None, norm_quantile=0.5):
        """
        Computes T-scores of test data.
        T = weight * D / UCL_D + (1 - weight) * Q / UCL_Q
        UCL_D and UCL_Q are calculated as the norm_quantile quantile and of the 
        training D and Q values, respectively.

        Parameters
        ----------
        weight: float 
            Weighting factor (between 0 and 1) for T-score. Default is the ratio between
              number of principal components and the number of variables of the features matrix.
        norm_quantile: float
            Quantile used for normalization in the T-score formula. Default is 0.5 (median).
        
        Returns
        -------
        (T_train, T_test): 
            Train and test T-score values.
        """
        if weight is None:
            weight = self.n_components / self.features_shape[1]

        T_train, T_test = mspc.tscore_tt((self.D, self.Q), (self.D_test, self.Q_test), weight=weight, norm_quantile=norm_quantile)
        return T_train, T_test

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
        fig, axes = plot.plot_DQ(self.D, self.Q, self.D_threshold, self.Q_threshold, labels = self.obs_labels,
                            logscale=logscale, event_index=event_index, opacity=opacity, ax=ax)
        
        # Format x-axis labels
        start_day = datetime.strptime(self.obs_labels[0], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        end_day = datetime.strptime(self.obs_labels[-1], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        if start_day == end_day:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').time() for label in self.obs_labels]
        else:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').strftime('%m-%d %H:%M:%S') for label in self.obs_labels]
        xlabels = []
        xticks = []
        if len(xtimes) < 100:
            tick_step = 6
        else:
            n = np.floor(np.log10(len(xtimes) / 100))
            tick_step = 6 * (5 ** (n + 1))

        for i in range(len(xtimes)):
            if i % tick_step == (tick_step-1):
                xticks.append(i + 0.5)
                xlabels.append(xtimes[i])

        for ax in axes:
            if start_day == end_day:
                ax.set_xlabel(str(end_day) + " (UTC Time)", loc='right')
            else:
                ax.set_xlabel("UTC Time", loc='right')
            ax.set_xticks(xticks)  # Center the ticks on the bars
            ax.set_xticks(np.arange(len(self.obs_labels))+0.5, minor=True)  # Center the ticks on the bars
            ax.set_xticklabels(xlabels, rotation=45, ha='right') # Rotate for better visibility
            ax.set_xlim(-1, len(xtimes))

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
        fig, axes = plot.plot_DQ_tt(self.D, self.Q, D_plot, Q_plot, self.D_threshold, self.Q_threshold, 
                               labels = plot_labels, logscale=logscale, plot_train=plot_train,
                               event_index=event_index, opacity=opacity, ax=ax)

        # Format x-axis labels
        start_day = datetime.strptime(plot_labels[0], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        end_day = datetime.strptime(plot_labels[-1], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        if start_day == end_day:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').time() for label in plot_labels]
        else:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').strftime('%m-%d %H:%M:%S') for label in plot_labels]
        xlabels = []
        xticks = []
        if len(xtimes) < 100:
            tick_step = 6
        else:
            n = np.floor(np.log10(len(xtimes) / 100))
            tick_step = 6 * (5 ** (n + 1))

        for i in range(len(xtimes)):
            if i % tick_step == (tick_step-1):
                xticks.append(i + 0.5)
                xlabels.append(xtimes[i])

        for ax in axes:
            if start_day == end_day:
                ax.set_xlabel(str(end_day) + " (UTC Time)", loc='right')
            else:
                ax.set_xlabel("UTC Time", loc='right')
            ax.set_xticks(xticks)  # Center the ticks on the bars
            ax.set_xticks(np.arange(len(plot_labels))+0.5, minor=True)  # Center the ticks on the bars
            ax.set_xticklabels(xlabels, rotation=45, ha='right') # Rotate for better visibility
            ax.set_xlim(-1, len(xtimes))

        return fig, axes

    
    def plot_T(self, T, threshold_quantiles=None, logscale=False, event_index=None, opacity=None, ax=None):
        """
        Plots T-score and control limits.

        Parameters
        ----------
        T (list)
            T-score values.
        threshold_quantiles (float)
            Quantile of the T-values used as threshold. Default is `1 - self.quantile_threshold`.
        logscale (bool) 
            If True, plots the statistics on a logarithmic scale (default: False).
        event_index (list)
            List of indices of observations to highlight in the graph (default: None).
        opacity (list)
            Opacity values for each bar in the plot (default: None).
        ax (Axis)
            Axes in which to plot (optional, default: None).

        Returns
        -------
        fig
            Matplotlib figure.
        ax
            Axes object.
        """
        if threshold_quantiles is None:
            threshold_quantiles = 1 - self.quantile_threshold
        fig, ax = plot.plot_tscore(T, threshold_quantiles, labels = self.obs_labels,
                                    logscale=logscale, event_index=event_index, opacity=opacity, ax=ax)
        
        # Format x-axis labels
        start_day = datetime.strptime(self.obs_labels[0], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        end_day = datetime.strptime(self.obs_labels[-1], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        if start_day == end_day:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').time() for label in self.obs_labels]
        else:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').strftime('%m-%d %H:%M:%S') for label in self.obs_labels]
        xlabels = []
        xticks = []
        if len(xtimes) < 100:
            tick_step = 6
        else:
            n = np.floor(np.log10(len(xtimes) / 100))
            tick_step = 6 * (5 ** (n + 1))

        for i in range(len(xtimes)):
            if i % tick_step == (tick_step-1):
                xticks.append(i + 0.5)
                xlabels.append(xtimes[i])

        if start_day == end_day:
            ax.set_xlabel(str(end_day) + " (UTC Time)", loc='right')
        else:
            ax.set_xlabel("UTC Time", loc='right')
        ax.set_xticks(xticks)  # Center the ticks on the bars
        ax.set_xticks(np.arange(len(self.obs_labels))+0.5, minor=True)  # Center the ticks on the bars
        ax.set_xticklabels(xlabels, rotation=45, ha='right') # Rotate for better visibility
        ax.set_xlim(-1, len(xtimes))

        return fig, ax


    def plot_T_test(self, T_train, T_test, starttime, endtime, threshold_quantiles=None, logscale=False, event_index=None, opacity=None,
                     plot_train=False, ax=None):
        """
        Plots T-scores and control limits for train and test.

        Parameters
        ----------
        T_train (list)
            Training T-scores.
        T_test (list)
            Test T-scores.
        starttime (str or datetime)
            Start of the time range (UTC) depicted in the plot.
        endtime (str or datetime)
            End of the time range (UTC) depicted in the plot.
        threshold_quantiles (float)
            Quantile of the T-values used as threshold. Default is `1 - self.quantile_threshold`.
        logscale (bool) 
            If True, plots the statistics on a logarithmic scale (default: False)
        event_index (list)
            List of indices of observations to highlight in the graph (default: None).
        opacity (list)
            Opacity values for each bar in the plot. Defaults to using missing rates 
            as opacity values.
        plot_train (bool)
            If True, plots both training and test T values. If False,  only plots
            tests values (default: False)
        ax (Axis)
            Ax in which to plot (optional, default: None).

        Returns
        -------
        fig
            Matplotlib figure.
        ax
            Axes object.
        """
        # Convert start and end to datetime if they are strings
        if isinstance(starttime, str):
            starttime = datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if isinstance(endtime, str):
            endtime = datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

        time_labels = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for label in self.test_labels]
        # Assumes that labels refer to the end time of the window
        label_indices = [i for i, date in enumerate(time_labels) if starttime < date <= endtime]

        # T values, and labels to plot
        T_plot = [T_test[i] for i in label_indices]
        plot_labels = [self.test_labels[i] for i in label_indices]

        if opacity is None:
            opacity = [1 - self.test_missing_rates[i] for i in label_indices]

        if plot_train:
            plot_labels = self.obs_labels + plot_labels
            if opacity is not None:
                opacity = [1] * len(self.obs_labels) + opacity

        # Plot
        if threshold_quantiles is None:
            threshold_quantiles = 1 - self.quantile_threshold
        fig, ax = plot.plot_tscore_tt(T_train, T_plot, threshold_quantiles, labels = plot_labels, 
                                        logscale=logscale, plot_train=plot_train,
                                        event_index=event_index, opacity=opacity, ax=ax)

        # Format x-axis labels
        start_day = datetime.strptime(plot_labels[0], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        end_day = datetime.strptime(plot_labels[-1], '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')
        if start_day == end_day:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').time() for label in plot_labels]
        else:
            xtimes = [datetime.strptime(label, '%Y-%m-%dT%H:%M:%SZ').strftime('%m-%d %H:%M:%S') for label in plot_labels]
        xlabels = []
        xticks = []
        if len(xtimes) < 100:
            tick_step = 6
        else:
            n = np.floor(np.log10(len(xtimes) / 100))
            tick_step = 6 * (5 ** (n + 1))

        for i in range(len(xtimes)):
            if i % tick_step == (tick_step-1):
                xticks.append(i + 0.5)
                xlabels.append(xtimes[i])

        if start_day == end_day:
            ax.set_xlabel(str(end_day) + " (UTC Time)", loc='right')
        else:
            ax.set_xlabel("UTC Time", loc='right')
        ax.set_xticks(xticks)  # Center the ticks on the bars
        ax.set_xticks(np.arange(len(plot_labels))+0.5, minor=True)  # Center the ticks on the bars
        ax.set_xticklabels(xlabels, rotation=45, ha='right') # Rotate for better visibility
        ax.set_xlim(-1, len(xtimes))

        return fig, ax


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
        if isinstance(self.station, list):
            print(f"    Stations: {self.station}")
        else:
            print(f"    Station: {self.station}")
        print(f"    NOC type: {self.type}")
        print(f"    Updated on: {self.last_update_time}")
        
        print("Parameters:")
        print(f"    Features shape: {self.features_shape}")
        print(f"    Preprocessing: {self.preprocessing} ({'centering' if self.preprocessing == 1 else 'centering + scaling'})")
        print(f"    Number of principal components: {self.n_components}")
        print(f"    Percentile: {self.quantile_threshold * 100}")

        print("Control limits:")
        print(f"    D threshold: {self.D_threshold:.4f}")
        print(f"    Q threshold: {self.Q_threshold:.4f}")
        print("=============================")

    
    def save(self, filepath:str, filetype:str='pickle'):
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

        if self.features is None:
            self.features = np.array([])

        # Save features
        if isinstance(self.features, np.ndarray) and self.features.size > 0:
            features = {'name': self.name, 'features': self.features, 'obs_labels': self.obs_labels}
            feat_filepath = os.path.join(os.path.dirname(filepath), f'features_{self.name}')
            if filetype == 'mat':
                savemat(feat_filepath, features)
            else:
                features["config"] = self.metadata
                with open(feat_filepath, 'wb') as f:
                    pickle.dump(features, f)

            # Remove features from NOC instance
            self.features = np.array([])

        # Save dictionary with all NOC attributes (no features)
        if filetype == 'mat':
            data = self.__dict__
            del data['csv_path']
            del data["metadata"]
            del data["pca"]
            
            savemat(filepath, data)
        else:
            with open(filepath, 'wb') as f:
                pickle.dump(self, f)


    @staticmethod
    def load(filepath, include_dq=True) -> "NOC":
        """
        Load a NOC from a pickle file.

        Parameters
        ----------
        filepath (str)
            Path to the input file.
        include_dq (bool)
            Whether to include the D and Q statistic values in the output.
        
        Returns
        -------
        NOC
            An instance of the NOC class
        """
        with open(filepath, 'rb') as f:
            noc = pickle.load(f)
        
        if not include_dq:
            del noc.D, noc.Q, noc.D_threshold, noc.Q_threshold
            del noc.D_test, noc.Q_test, noc.test.missing_rates, noc.test_labels
        
        return noc
    
    def load_features(self, nocs_path='data/involcan/nocs/'):
        path = os.path.join(nocs_path, f"features_{self.name}").replace('\\', '/')
        with open(path, 'rb') as f:
            feat = pickle.load(f)
        return feat["features"]
        

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
            
            if self.metadata:
                starttime = self.metadata["start_time"]
                endtime = self.metadata["end_time"]
            elif len(self.time_range) > 0:
                if isinstance(self.time_range[0], str):
                    starttime = self.time_range[0]
                    endtime = self.time_range[1]
                else:
                    starttime = self.time_range[0][0]
                    endtime = self.time_range[-1][1]
            else:
                starttime = ""
                endtime = ""
            
            # Create new row
            row = {
                'name': self.name,
                'network': self.network,
                'station': self.station,
                'type': self.type,
                'n_windows': self.features_shape[0],
                'n_variables': self.features_shape[1],
                'preprocessing': self.preprocessing,
                'n_components': self.n_components,
                'quantile_threshold': self.quantile_threshold,
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
        return f"NOC: {self.name}"


# Additional functions
from mspc_pca.omeda import omeda

def compare_nocs(noc1:NOC, noc2:NOC, nocs_path, preprocessing=1, n_components=None, var_labels=None, var_classes=None, ax=None):
    """
    Compares two NOCs using oMEDA.

    Parameters
    ----------
    noc1 (NOC)
        First NOC.
    noc2 (NOC)
        Second NOC.
    nocs_path (str)
        Path to the directory where NOCs are saved.
    preprocessing (int)
        Preprocessing for NOC features:
        - 1: mean-centering (default)
        - 2: autoscaling
    n_components (int)
        Number of principal components (PCs). By default, all PCs are used.
    var_labels (list)
        Labels for the variables (x-axis).
    var_classes (list)
        Classes for coloring
    ax (Axis)
        Axis where the oMEDA vector will be plotted (optional, default: None).

    Returns
    -------
    omeda_vec (array)
        oMEDA results.
    fig (Figure)
        Plot figure.
    ax (Axis)
        Axis with plotted oMEDA vector.
    """
    # Check that the NOCs are comparable
    assert noc1.features_shape[1] == noc2.features_shape[1], f"Error: NOCs should have the same number of columns ({noc1.features_shape[1]} != {noc2.features_shape[1]})."
    
    noc1_features = noc1.load_features(nocs_path)
    noc2_features = noc2.load_features(nocs_path)
    features_all = np.vstack((noc1_features, noc2_features))

    # Dummy variable for omeda
    dummy = np.ones(len(features_all))
    dummy[len(noc1_features):] = -1
    
    if preprocessing == 1:
        scaler = StandardScaler(with_std=False)
    elif preprocessing == 2:
        scaler = StandardScaler(with_std=True)
    
    features_all = scaler.fit_transform(features_all)

    pca_model = PCA(n_components=n_components)
    scores = pca_model.fit_transform(features_all)
    loadings = pca_model.components_.T

    omeda_vec, fig, ax = omeda(features_all, dummy=dummy, R=loadings, plot=True, var_labels=var_labels, var_classes=var_classes,
                                title=f"{noc1.name} (+) vs. {noc2.name} (-)")
    
    return omeda_vec, fig, ax


def fuse_nocs(noc_names, new_name=None, new_type='dynamic', n_components=1, nocs_path='data/involcan/nocs', 
              log_path='data/involcan/metadata/noc_list.csv', verbose=False):
    """
    Combine the features of different NOCs along the columns and creates a new NOC. 

    Parameters
    ----------
    noc_names (list)
        List of NOC names.
    new_name (str)
        Name of the new NOC.
    new_type (str)
        Type of the new NOC. One of 'dynamic', 'static' or 'inactive'.
    n_components (int)
        Number of principal components. Default is 1.
    nocs_path (str)
        Path to the directory where NOCs are saved.
    log_path (str)
        Path to the CSV file containing information about the NOCs.
    """
    noc_names = sorted(noc_names)
    feat_all = []
    stations = []
    for i, name in enumerate(noc_names):
        # Load NOC and features
        filepath = os.path.join(nocs_path, name)
        noc = NOC.load(filepath)
        feat = noc.load_features(nocs_path)
        feat_param = noc.metadata
        feat_shape = feat.shape

        match = True
        if i == 0:
            # Reference values
            ref_param = feat_param
            ref_shape = feat_shape

            # Other parameters
            obs_labels = noc.obs_labels
            network = noc.network
            prep = noc.preprocessing
            qt = noc.quantile_threshold
            time_range = noc.time_range
        else:
            # Check parameters used for feature extraction
            if np.any(feat_shape != ref_shape):
                match = False
                if verbose:
                    print(f"Shape of NOC {noc.name} should be {ref_shape} but is {feat_shape}. This NOC will not be part of the combined NOC.")
            for key in ref_param.keys():
                if feat_param[key] != ref_param[key]:
                    match = False
                    if verbose:
                        print(f"Parameter {key} of NOC {noc.name} should be {ref_param[key]} but is {feat_param[key]}. This NOC will not be part of the combined NOC.")
        
        if match:
            feat_all.append(feat)
            stations.append(noc.station)
    
    if len(feat_all) < 2:
        raise Exception("No NOCs to fuse")

    # Create new NOC
    features = np.hstack(feat_all)
    if new_name is None:
        new_name = "-".join(stations) + "_" + new_type[0] + "_" + datetime.strptime(time_range[1], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
    new_noc = NOC(new_name, features, obs_labels, network, stations, new_type, 
                  preprocessing=prep, n_components=n_components, quantile_threshold=qt, csv_path=log_path)
    new_path = os.path.join(nocs_path, new_name)
    new_noc.metadata = ref_param
    new_noc.time_range = time_range
    new_noc.save(new_path)
    new_noc.write_csv(log_path)

    print(f"NOCs for stations {stations} fused.")
    
    return new_noc