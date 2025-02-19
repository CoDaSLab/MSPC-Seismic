"""
Last update: 10/09/2024

file name: data_check.py

Description:
This file contains functions that go through the raw data files in order to register data availability.
Things like wether or not there is an interruption in the information, see what sensors have or don't have data,
as well as get the names of the files that cointain a certain subset of data.
"""


import pandas as pd
from datetime import datetime, timedelta


"""
function: get_interruptions(df_time, query)
Find the interruptions in the available data in a period of time determined by the start time and end time specified in a query.

Inputs
df_time:    pandas dataframe. Contains the information on the available times ( Available_times.csv )
query:      2x1 tuple (start, end). "starts" is the datetime starting time of the period you want to check. "end" is the datetime ending time of the period. 


Outputs
n_interruptions:        int. Number of interruptions in the data along the query period. -1 if( q0_exists  == Falseor q1_exists == False)
missing_data_periods:   list. Contains the starting and ending time of the time portions along the query period where no data is available. -1 if( q0_exists  == Falseor q1_exists == False)
q0_exists:              bool. True if there is information for the start query period. 
q1_exists:              bool. True if there is information for the end query period.

"""
def get_interruptions(df_time, query):
    assert query[1] > query[0], "endtime should be greater than starttime."

    q1_exists, q0_exists = (True, True)
    if len(df_time[df_time['start'] <= query[0]]) == 0:
        q0_exists = False
    if len(df_time[df_time['end'] >= query[1]]) == 0:
        q1_exists = False

    if (not q0_exists) or (not q1_exists): return -1, -1, q0_exists, q1_exists

    q0 = df_time[df_time['start'] <= query[0]].sort_values(
        by='start', ascending=False).reset_index(drop=False).iloc[0]['index']

    q1 = df_time[df_time['end'] >= query[1]].sort_values(
        by='end', ascending=True).reset_index(drop=False).iloc[0]['index']
    

    interruptions = df_time.loc[q0: q1]
    n_interruptions = len(interruptions) - 1 

    end_dates = pd.to_datetime(interruptions['end'][:-1])
    start_dates = pd.to_datetime(interruptions['start'][1:])
    missing_data_periods = list(zip(end_dates, start_dates))


    return  n_interruptions, missing_data_periods, q0_exists, q1_exists

"""
function: get_filenames(start, end, sensor, channel, path = "data/metadata/Available_files.csv")
Find the names of the files that include the data that the user desires.

Inputs
start:      datetime. Start of the time period of the data the user wants
end:        datetime. End of the time period of the data the user wants
sensor:     string. Name of the sensor whose data the user wants (DAS, PLPI, PPMA)
channel:    string. Channel of the data the user wants (None, HHE, HHN, HHZ)
path:       string. Path to Available_files.csv, the table containing the information on availability of file availability


Outputs
filepaths:  list of strings containing all of the filepaths (paths+filenames) 
filenames:  list of strings containing all of the file names
paths:      list of strings containing all of the file paths 

"""

def get_filenames(start, end, sensor, channel, path = "data/metadata/Available_files.csv"):
    data_files = pd.read_csv(path)
    data_files['channel'] = data_files['channel'].fillna('')
    
    data_files['datetime'] = pd.to_datetime(data_files[['year', 'month', 'day', 'hour', 'minute', 'second']])
    data_files = data_files.sort_values(by='datetime')

    diff = 0
    if sensor == "DAS":                     diff = timedelta(minutes = 1)
    if "PLPI" in sensor or "PPMA" in sensor: diff = timedelta(days = 1)

    subset = data_files[
        (data_files["sensor"]== sensor) &
        (data_files["channel"]== channel) &

        (data_files["datetime"] >= start - diff) &
        (data_files["datetime"] <= end) 
        ]

    filenames, paths = subset.filename.to_list(), subset.path.to_list()
    filepaths = [item[0] +"/"+ item[1] for item in zip(paths, filenames)]

    return filepaths, filenames, paths
    
"""
function: check_sensors(start, end, tol = 0, pathfile = "data/metadata/Available_times.csv",
                    sensors = ['DAS', 'PLPI_HHE', 'PLPI_HHN', 'PLPI_HHZ', 'PPMA_HHE', 'PPMA_HHN', 'PPMA_HHZ'])
Check the data availability and files containing the data of a time period of a sensor or set of sensors.

Inputs
start:  datetime. Start of the time period of the data the user wants
end:    datetime. End of the time period of the data the user wants
tol:    float. Set the tolerance for peridod of missing data. If the duration of the period of missing data is lower than tol, the period is not considered as an interruption

Outputs
result: Dictionary containing the elements:
        'available_starttime','available_endtime','sensor','n_interruptions','missing_data_periods','files'

"""
def check_sensors(start, end, tol = 0, pathfile = "data/metadata/Available_times.csv",
                  sensors = ['DAS', 'PLPI_HHE', 'PLPI_HHN', 'PLPI_HHZ', 'PPMA_HHE', 'PPMA_HHN', 'PPMA_HHZ'],
                  filenames_path = False):

    data_times = pd.read_csv(pathfile)
    data_times['start'] = pd.to_datetime(data_times['start'])
    data_times['end'] = pd.to_datetime(data_times['end'])
    query = [start, end]

    result = {
        'available_starttime': [],
        'available_endtime': [],
        'sensor': [],
        'n_interruptions': [],
        'missing_data_periods': [],
        'files': [],
    }

    for sensor in sensors:
        if sensor =='DAS':
            df_time = data_times[data_times['sensor']==sensor]
            channel = ''

        if sensor[:4] in ['PLPI', 'PPMA']:
            df_time = data_times[data_times['sensor']==sensor[:4]]
            df_time = df_time[df_time['channel'] == sensor[-3:]]
            channel=sensor[-3:]


        n_interruptions, missing_data_periods, q0, q1 = get_interruptions(df_time, query)

        if type(missing_data_periods)!=int:
            if len(missing_data_periods)>0:
                if missing_data_periods[0][1]- missing_data_periods[0][0] < timedelta(0, tol):
                    n_interruptions = 0
                    missing_data_periods = []

        result['sensor'].append(sensor)
        result['available_starttime'].append(q0)
        result['available_endtime'].append(q1)
        result['n_interruptions'].append(n_interruptions)
        result['missing_data_periods'].append(missing_data_periods)
        
        if filenames_path == False:
            _, files, _ = get_filenames(start, end, sensor, channel)
        else:
            _, files, _ = get_filenames(start, end, sensor, channel, path=filenames_path)
            
        result['files'].append(files)
        # try:
        #     if (q0) & (q1):
        #         files = get_filenames(start, end, sensor, channel)
        #         result['files'].append(files)
        #     else:
        #         result['files'].append([])
                
        # except: result['files'].append([])

    return result

    
"""
function: plot_availability(ax, limits, missing_data, axis = 'X', alpha = 0.3)
Plot the data availability of seismic sonsors PLPI and PPMA
"""

def plot_availability(ax, limits, missing_data, axis = 'X', alpha = 0.3):
    start, end = limits
    if axis =='X':
        # missing data
        for period in missing_data:
            ax.fill_between([period[0], period[1]], start, end, color='red', alpha = alpha)

        # available data
        if missing_data:
            ax.fill_between([ start, missing_data[0][0] ], start, end, color='green', alpha = alpha)
            for i, _  in enumerate(missing_data[:-1]):
                ax.fill_between([ missing_data[i][1], missing_data[i+1][0] ], start, end, color='green', alpha = alpha)
            ax.fill_between([ missing_data[len(missing_data)-1][0], end ], start, end, color='green', alpha = alpha)
        else:
            ax.fill_between([start, end], start, end, color="green", alpha = 0.3)
        
    if axis =='Y':
        # missing data
        for period in missing_data:
            ax.fill_between([start, end], period[0], period[1], color='red', alpha = alpha)

        # available data
        if missing_data:
            ax.fill_between([start, end], start, missing_data[0][0], color='green', alpha = alpha)
            for i, _  in enumerate(missing_data[:-1]):
                ax.fill_between([start, end], missing_data[i][1], missing_data[i+1][0], color='green', alpha = alpha)
            ax.fill_between([start, end], missing_data[len(missing_data)-1][0], end, color='green', alpha = alpha)
        else:
            ax.fill_between([start, end], start, end, color="green", alpha = 0.3)
    return 


if __name__=='__main__':
    start, end = (
        datetime(2021, 9, 12, 0, 0),
        datetime(2021, 9, 30, 0, 0)
    )

    # Function health check
    print(f"""
Checking data_check.py functions ...
starttime: {start}
endtime:   {end}
    """)

    # check_sensors health check
    result = check_sensors(start, end, tol=0.0)
    df = pd.DataFrame(result)
    print("check_sensors:")
    print(df)

    # quit()
    # get_filenames health check
    filenames = get_filenames(start, end, 'DAS', '')
    print("\nDAS Filenames:" )
    # print(filenames)
    
    # quit()
    # get_interruptions health check
    df_time = pd.read_csv("data/metadata/Available_times.csv")
    df_time['start'] = pd.to_datetime(df_time['start'])
    df_time['end'] = pd.to_datetime(df_time['end'])

    interruptions = get_interruptions(df_time, [start, end])
    print("interruptions:")
    # print(interruptions)



    plot = False
    if plot:
        # plot availability
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.ticker import MaxNLocator


        fig, ax = plt.subplots(figsize = (10,8))
        for id, row in df[['sensor', 'missing_data_periods']].iterrows():
            sensor = row['sensor'][:4]

            if sensor =='DAS' and type(row['missing_data_periods']) != int: 
                fig_DAS, ax_DAS = plt.subplots(figsize=(10,8))
                ax_DAS.set_xlabel('DAS', fontsize = 16)
                plot_availability(ax_DAS, (start, end), row['missing_data_periods'], axis ='X', alpha = 0.3)
                plt.savefig(f'Analysis/DAS_sensor_data_availability.png')
                plt.clf()
                fig, ax = plt.subplots(figsize = (10,8))

            if sensor == 'PLPI':
                ax.set_xlabel(sensor, fontsize = 16)
                plot_availability(ax, (start, end), row['missing_data_periods'], axis ='X', alpha = 0.1)

            if sensor == 'PPMA':
                ax.set_ylabel(sensor, fontsize = 16)
                plot_availability(ax, (start, end), row['missing_data_periods'], axis ='Y', alpha = 0.1)

        ax.set_xlim(start, end)
        ax.set_ylim(start, end)
        ax.xaxis.set_major_locator(mdates.MonthLocator())  # Locators para los meses
        ax.xaxis.set_minor_locator(mdates.DayLocator())    # Locators para los días
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # Formateador para el año-mes
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))     # Formateador para el día
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6))  # Máximo 6 ticks mayores
        ax.xaxis.set_minor_locator(MaxNLocator(nbins=30))  # Máximo 30 ticks menores
        plt.setp(ax.get_xticklabels(which='minor'), rotation=45, ha='right')
        plt.setp(ax.get_xticklabels(which='major'), rotation=45, ha='right')


        ax.yaxis.set_major_locator(mdates.MonthLocator())  # Locators para los meses
        ax.yaxis.set_minor_locator(mdates.DayLocator())    # Locators para los días
        ax.yaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # Formateador para el año-mes
        ax.yaxis.set_minor_formatter(mdates.DateFormatter('%d'))     # Formateador para el día
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))  # Máximo 6 ticks mayores
        ax.yaxis.set_minor_locator(MaxNLocator(nbins=30))  # Máximo 30 ticks menores
        plt.savefig(f'digivolcan/figures/seismic_sensor_data_availability.png')







