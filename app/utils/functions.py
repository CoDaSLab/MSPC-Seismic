import pandas as pd

def load_data(filepath, sep=',', header='infer'):
    return pd.read_csv(filepath,sep=sep, header=header)

def load_events():
    # Load registered events data
    events = pd.read_csv("data/ivc.dat", header=None)
    # Name the columns
    events.columns =  ['year', 'month', 'day', 'hour', 'minute', 'second', 'magnitude', 'longitude', 'latitude','depth (km)','*1','*2']
    events = events.drop(["*1","*2"], axis = 1)

    time_col = ['year', 'month', 'day', 'hour', 'minute', 'second']
    events['datetime'] = pd.to_datetime(events[time_col])
    # Discard columns used for datetime
    events = events.drop(time_col, axis=1)
    # Sort by datetime
    events = events.sort_values(by='datetime').reset_index(drop=True)
    # Reorder columns
    events = events[[events.columns[-1]] + list(events.columns[:-1])]
    
    return events


