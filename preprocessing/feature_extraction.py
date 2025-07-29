"""
Last update: 16/05/2025

file name: feature_extraction

Description:
Collection of functions used to extract the features from a DAS signal and SISMO signals. 
"""

import os
from datetime import datetime, timedelta
import scipy
import numpy as np
from preprocessing.HDAS import HDAS
from preprocessing.SISMO import SISMO
from data.scripts.data_check import *
from itertools import islice


def create_DAS_object(files, path ='./', cpus = 4, preprocess = True, verbose = False):
    """
    Create the DAS object for feature extraction

    Inputs
    files: Files to use to create the HDAS object
    path: Path to the files.
    preprocess: bool. Determines whether or not the DAS data is preprocessed after creating the object (removeTrend and removeCoherentNoise via fit)
    verbose: bool. Update the log on the status of the function's process.

    Outputs
    H: Created object of the HDAS class.
    """

    if verbose == True: print("Creating HDAS object")
    H = HDAS(path, files, verbose=verbose)

    if verbose == True:
        H.check()
        print('')

    if preprocess == True:
        H.removeTrend(cpus)
        H.removeCoherentNoise(method='fit')

    return H


def create_SISMO_object(filepaths, cpus, windowing, preprocess = False, verbose = False):
    """
    Create the DAS object for feature extraction

    Inputs
    filespaths: list of paths to the files to read to create the object.
    preprocess: bool. Determines wether or not the DAS data is preprocessed after creating the object (removeTrend and removeCoherentNoise via fit)
    verbose: bool. Update the log on the status of the function's process.

    Outputs
    S: Created object of the SISMO class.
    """

    if verbose == True: print("Creating SISMO object")
    S = SISMO(filepaths, windowing=windowing, cpus=cpus, verbose=verbose)

    if verbose == True:
        S.check()
        print('')

    if preprocess == True:
        S.removeTrend()

    return S


def select_sps(H, sp_min = 0, sp_max = None, verbose = False):
    """
    Reduce the number of spatial points of the DAS considered in the HDAS object

    Inputs
    H: HDAS object. Object where to perform the operation
    sp_min: lower limit of the spatial point range to be cut
    sp_max: upper limit of the spatial point range to be cut.
    verbose: bool. Update the log on the status of the function's process.

    Outputs
    H: HDAS object after the cut
    """
    if sp_max == None: sp_max = H.nsens
    assert sp_min < sp_max, "sp_min must be lower than sp_max"

    H.cutX(sp_min*H.dx, sp_max*H.dx)
    H.sps = (H.xpos / H.dx).astype(int)
    
    if verbose == True:
        print(f"Remaining SPs: {H.sps}")

    return H


def _calculate_features(H, verbose = False, timer = False):
    """
    Calculate a set of features from the signal of each of the spatial points in H.


    Inputs
    H: HDAS object. Object where to extract the features from
    window_size: float. duration of the window
    window_shift: float. duration of the window shift
    verbose: bool. Update the log on the status of the function's process.

    Outputs
    features_list: list of dictionaries. Each element contains a dictionary with the features calculated for every SP.
    """
    if verbose:
        time0 = datetime.now()
        print(f"[{time0}] Calculating features ...")

    # Calculate the features
    H.calculate_hjorth_parameters()
    if timer:
        print(f"Hjorth parameters calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    # H.approximate_entropy()
    # if timer:
    #     print(f"Approximate entropy calculated in {datetime.now() - time0}")
    #     time0 = datetime.now()

    H.spectral_entropy()
    if timer:
        print(f"Spectral entropy calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.scal_log_esp_power()
    if timer:
        print(f"Log spectral power calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.LFB()
    if timer:
        print(f"LFB parameters calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.lpc()
    if timer:
        print(f"LPC parameters calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.calculate_top_fft_amplitudes_and_frequencies()
    if timer:
        print(f"Top FFT amplitudes and frequencies calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.calculate_top_lpc_amplitudes_and_frequencies()
    if timer:
        print(f"Top LPC amplitudes and frequencies calculated in {datetime.now() - time0}")
        time0 = datetime.now()

    H.percentiles()
    if timer:
        print(f"Percentiles calculated in {datetime.now() - time0}")

    if verbose:
        print(f"[{datetime.now() - time0}] Calculated features ...")

    return {
        'Mobility': H.mobility_vals,
        'Mobility_delta_1': H.deltas_mob,
        'Mobility_delta_2': H.deltas_deltas_mob,
        'Complexity': H.complexity_vals,
        'Complexity_delta_1': H.deltas_com,
        'Complexity_delta_2': H.deltas_deltas_com,
        'Variance': H.variance_vals,
        'Variance_delta_1': H.deltas_var,
        'Variance_delta_2': H.deltas_deltas_var,
        # 'Approximate_entropy': H.approx_entropy_vals,
        # 'Approximate_entropy_delta_1': H.deltas_ent_app,
        # 'Approximate_entropy_delta_2': H.deltas_deltas_ent_app,
        'Spectral_entropy': H.entropy_vals,
        'Spectral_entropy_delta_1': H.deltas_ent,
        'Spectral_entropy_delta_2': H.deltas_deltas_ent,
        'Scal_log_esp_power': H.scal_log_esp_power_vals,
        'Scal_log_esp_power_delta_1': H.deltas_scal_log_esp_power,
        'Scal_log_esp_power_delta_2': H.deltas_deltas_scal_log_esp_power,
        'LFB': H.LFB_matrix_vals,
        'LFB_delta_1': H.deltas_LFB,
        'LFB_delta_2': H.deltas_deltas_LFB,
        'LPC': H.lpc_matrix,
        'LPC_delta_1': H.deltas_LPC,
        'LPC_delta_2': H.deltas_deltas_LPC,
        'Top_3_amplitudes_fft': H.top_fft_amplitudes_vals,
        'Top_3_amplitudes_fft_delta_1': H.deltas_fft_amp,
        'Top_3_amplitudes_fft_delta_2': H.deltas_deltas_fft_amp,
        'Top_3_frequencies_fft': H.top_fft_frequencies_vals,
        'Top_3_frequencies_fft_delta_1': H.deltas_fft_frec,
        'Top_3_frequencies_fft_delta_2': H.deltas_deltas_fft_frec,
        'Top_3_amplitudes_LPC': H.top_lpc_amplitudes_vals,
        'Top_3_amplitudes_LPC_delta_1': H.deltas_lpc_amp,
        'Top_3_amplitudes_LPC_delta_2': H.deltas_deltas_lpc_amp,
        'Top_3_frequencies_LPC': H.top_lpc_frequencies_vals,
        'Top_3_frequencies_LPC_delta_1': H.deltas_lpc_frec,
        'Top_3_frequencies_LPC_delta_2': H.deltas_deltas_lpc_frec,
        'Percentiles20_50_80': H.percentiles_matrix,
        'Percentiles20_50_80_delta_1': H.deltas_perc,
        'Percentiles20_50_80_delta_2': H.deltas_deltas_perc,
        # 'Existing_files': ''.join(existing_files)
        }


def _calculate_FFT_coefficients(H, fft_points = 256, verbose = False):
    """
    Calculate the FFT coefficients from the signal of each of the spatial points in H.

    Inputs
    H: HDAS object. Object where to extract the features from
    window_size: float. duration of the window
    window_shift: float. duration of the window shift
    verbose: bool. Update the log on the status of the function's process.

    Outputs
    FFTs_list: list of dictionaries. Each element contains a dictionary with FFT coefficients calculated for every SP.
    """

    if verbose:
        print(f"[{datetime.now()}] Calculating FFT coefficients ...")

    # Calculate the features
    H.fft_bin(fft_points)
    if verbose:
        print(f"[{datetime.now()}] Calculated FFT coefficients ...")
    return {
            'FFT_128_BIN': H.fft,
            'FFT_128_BIN_delta_1': H.deltas_fft,
            'FFT_128_BIN_delta_2': H.deltas_deltas_fft,
            # 'Existing_files': ''.join(existing_files)
        }


def _save_features(H, features, feature_type,
                  save_folder ="./data/involcan/features" ,
                  log_path = "./data/involcan/metadata/feature_log.csv",
                  split_by_rows=False, verbose = False):
    """
    Save the calculated features of the HDAS object H

    Inputs
    H: HDAS object. Object where to extract the features from
    features_list: list of dictionaries. Each element copntains a dictionary with the features calculated for every SP.
    save_folder: string. Path to the folder where the features will be saved.
    log_path: string. Path to the log document where we can check the id of every feature file.

    Outputs
    None
    """
    
    # Check log
    df_log = pd.read_csv(log_path)
    ids = pd.unique(df_log["file_id"]).tolist()
    if ids == []: ids = [0]
    last_id = int(max(ids))
    id = last_id + 1

    #######################################################
    """ Resampling of the FFTs """
    factor = getattr(H, "resampling_factor", 1)
    if factor > 1:
        resampled_features = {}
        for key, array in features.items():
            SP, W, F = array.shape
            if F % factor != 0:
                raise ValueError(f"The number of columns in '{key}' is not a multiple of {factor}.")
            
            # Aplicar el promedio en cada bloque de 100 columnas
            resampled_features[key] = array.reshape(SP, W, F // factor, factor).mean(axis=3)

        features = resampled_features
    #######################################################

    missing = H.get_missing_samples(rate = True)

    if split_by_rows:
        split_features = {}

        # Split the array in chunks of split_by_rows rows
        for key, array in features.items():
            SP, W, F = array.shape
            split_by_rows = 100  # CHANGE THIS
            if W > split_by_rows:
                # Split the array into smaller chunks
                n_chunks = (W // split_by_rows) + 1
                split_features[key] = []
                for i in range(n_chunks):
                    start = i * split_by_rows
                    end = (i + 1) * split_by_rows if i < n_chunks - 1 else W
                    array_chunk = array[:, start:end, :]
                    split_features[key].append(array_chunk)
        
        for i in range(n_chunks):
            feature_chunk = {}
            for key in features.keys():
                feature_chunk[key] = split_features[key][i]
            # Save the features in a .mat file
            filename = f"{id}_{i}.mat" if W > split_by_rows else f"{id}.mat"

            feature_chunk["missing_rates"] = missing
            scipy.io.savemat(f"{save_folder.rstrip('/')}/{filename}", feature_chunk)

    else:
        # Save the features in a .mat file
        filename = f"{id}.mat"
        features["missing_rates"] = missing
        scipy.io.savemat(f"{save_folder.rstrip('/')}/{filename}", features)

    n_variables = 0
    for key, feature in islice(features.items(), 3):
        feature = np.squeeze(feature)
        n_variables += feature.shape[1]

    if H.windowing: 
        window_name = H.windowing.__name__
    else:
        window_name = False

    # Fraction of missing data in the whole signal
    missing_mean = np.mean(missing).round(4)
    row = pd.DataFrame(
        [[id, H.network, H.station, H.channel, feature_type,
          H.stime.strftime("%Y-%m-%d %H:%M:%S.%f"), H.etime.strftime("%Y-%m-%d %H:%M:%S.%f"),
          H.window_size, H.window_size - H.window_shift, window_name,
          H.n_windows, n_variables,
          missing_mean,
          H.fmin, H.fmax,
          H.nsamp, H.srate,
          H.detrend, H.Coherent_noise_removed,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")]])
    # starttime, endtime
    for col_id in [5, 6, 19]:
       row[col_id] = row[col_id].str.slice(0, -4)

    row.to_csv(log_path, mode='a', sep=",", index=False, header=False, date_format="%Y-%m-%d %H:%M:%S.%f")

    if verbose == True: print(f"Features saved at {save_folder.rstrip('/')}/{id}.mat")
    
    return



def get_features(H, window, shift, fft_points = 256,
                types = ["FFT", "feature"],
                save_folder ="./data/involcan/features" ,
                log_path = "./data/involcan/metadata/feature_log.csv",
                split_by_rows=False, verbose = False, timer = False):
    """    
    Calculate the features and FFT coefficients of an HDAS object and save the results

    Inputs
    H: HDAS object. Object where to extrac the features from
    window: float. duration of the window.
    shift: float. duration of the window shift.
    fft_points: int. Number of FFT points to calculate.
    types: list of strings. Types of features to calculate. Options: "feature", "FFT"
    save_folder: string. Path to the folder where the features will be saved.
    log_path: string. Path to the log document where we can check the id of every feature file.
    split_by_rows: int or False. If it is an int, features will be split in different chunks of at most
        `split_by_rows` rows and saved in different files.
    verbose: bool. If True, prints information about the process.
    timer: bool. If True, prints the time taken to calculate the features.

    Outputs
    None
    """

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    H.set_windows(window, shift)

    # Features
    if "feature" in types:
        features = _calculate_features(H, verbose, timer)
        _save_features(H, features, "feature", save_folder, log_path, split_by_rows, verbose = verbose)   

    # FFT
    if "FFT" in types:
        features = _calculate_FFT_coefficients(H, fft_points, verbose)
        _save_features(H, features, "FFT", save_folder, log_path, split_by_rows, verbose = verbose)

    return

def check_log(query, log_path = "data/involcan/metadata/feature_log.csv"):
    log = pd.read_csv(log_path, parse_dates=["starttime", "endtime", "save_time"],
                      date_format='mixed')

    for key, value in query.items():
        log = log[log[key] == value]
    
    return log




if __name__ == '__main__':

    time0 = datetime.now()
    print(f"\nScript start at {time0}")
    starttime = datetime(2021, 9, 18, 0, 0)
    endtime   = datetime(2021, 9, 20, 0, 0)

    networks = ["C7"]
    stations = ["PPMA"]
    channels = ["HHE"]

    # window = 1.0*60*60 # 1 hour
    # window = 10 #s
    window = 1*60
    # window = 60*60/2
    overlap = 0 #window//2
    shift = window - overlap
    windowing = False # scipy.signal.windows.hamming

    decimation = 1
    detrend = False
    interpolate = False

    seconds = endtime - starttime
    seconds = seconds.seconds
    # n_FFTs = 2**10 # Número de coeficientes FFT (Se divide entre 2 por positivos y negativos)

    # SISMO extraction
    if True:
        for network in networks:
            for station in stations:
                for channel in channels:
                    print(f"""
                    Extracting SISMO features 
                        network: {network}, station: {station}, channel: {channel}
                        from {starttime}
                        to {endtime}
                        window: {window} s
                        overlap: {overlap} s
                        windowing: {windowing}
                        """)
                    print(f"\nRunning for {station} station and {channel} channel ...")

                    S = SISMO(network, station, channel, starttime, endtime,
                              detrend, windowing, cpus=10)
                    S.resampling_factor = 50
                    S.check()
                    
                    S.set_windows(window, shift)
                    get_features(S, window, shift, 'Auto',
                                types=['FFT'],
                                verbose = True, timer = True)
                
    # DAS extraction
    if False:

        starttime = datetime(2021, 11, 20, 0, 0)
        end = datetime(2021, 11, 28, 0, 0)
        delta = timedelta(hours=1)
        endtime = starttime + delta
        while endtime < end:

            print(f"""
            Extracting DAS features 
                from {starttime}
                to {endtime}
                window: {window} s
                overlap: {overlap} s
                windowing: {windowing.__name__}
                """)
            filepaths,  _, _ = get_filenames(starttime, endtime, 'DAS', '')
            assert len(filepaths) > 0, "No files available"
            H = create_DAS_object(filepaths, '.', cpus = 15, preprocess = True, verbose=True)
            # H.cutX(896*H.dx, 4992*H.dx)

            get_features(H, window, shift, verbose = True, timer = True)

            starttime += delta
            endtime += delta


    # SISMO extraction day by day.
    if False:
        etime = starttime
        t_delta = timedelta(days=1)
        while etime <= endtime:
            stime = etime
            etime = stime + t_delta

            for station in ["PLPI", "PPMA"][:]:
                for channel in ["HHN", "HHE", "HHZ"][:]:
                    print(f"""
                    Extracting SISMO features 
                        station: {station}, channel: {channel}
                        from {stime}
                        to {etime}
                        window: {window} s
                        overlap: {overlap} s
                        windowing: {windowing}
                        """)
                    print(f"\nRunning for {station} station and {channel} channel ...")
                    filepaths, _,_ = get_filenames(stime, etime, station, channel)

                    S = SISMO(station, channel, stime, etime,
                            detrend, decimation, windowing, interpolate)
                    S.check()

                    get_features(S, window, shift, 'Auto',
                                verbose = True, timer = True)
            

    print(f"Total runtime: {datetime.now() - time0}")





