import streamlit as st
import pandas as pd


def show_table(data):
    data = data.loc[:, ~data.columns.str.contains('\*')] # Remove '*' columns
    columns = data.columns.to_list()

    selected_columns = st.multiselect('Columns to show:', columns, columns)

    # Read 'start' and 'end' as datetime
    for column in selected_columns:
        if column == 'start' or column=='end':
            data[column] = pd.to_datetime(data[column])

    if 'year' in data.columns:
        data = data.sort_values(by=[data.columns[0], data.columns[1], data.columns[2],
                                    data.columns[3], data.columns[4], data.columns[5], 
                                    ]) .reset_index(drop=True) 
    # Mostrar los datos seleccionados
    if selected_columns:
        st.dataframe(data[selected_columns], use_container_width = True)
        with st.expander('Stats'):
            st.dataframe(data[selected_columns].describe(), use_container_width=True)
    else:
        st.write("No se ha seleccionado ninguna columna.")

def check_availability(av_file_path, av_time_path):
    from widgets.forms import select_time
    from preprocessing.functions.data_check import check_sensors
    COL = st.columns(2)
    with COL[0]:
        start, end = select_time('check_availability')

    tol = COL[1].number_input('Tolerance (s)', min_value = 0.0, value=0.0)

    result = check_sensors(start, end, tol = tol, pathfile=av_time_path,
                           filenames_path=av_file_path)
    df = pd.DataFrame(result)

    st.dataframe(df, use_container_width = True)
    return


def available_sensors():
    # Load sensor location data
    sensors = pd.read_csv("data/stations_lp.dat", sep='\s+')
    sensors.columns = ["sensor", "latitude", "longitude", "altitude (m)"]
    sensors['available'] = False
    sensors.loc[sensors['sensor'].isin(['PPMA', 'PLPI']), 'available'] = True
    sensors = sensors.sort_values('available', ignore_index=True, ascending=False)

    st.dataframe(sensors, use_container_width = True)
    st.write("Source: INVOLCÁN")

    return sensors



def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    )

    with st.expander("Apply filters"):

        df = df.copy()

        # Try to convert datetimes into a standard format (datetime, no timezone)
        for col in df.columns:
            if is_object_dtype(df[col]):
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception:
                    pass

            if is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

        modification_container = st.container()

        with modification_container:
            to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
            for column in to_filter_columns:
                left, right = st.columns((1, 20))
                left.write("↳")
                # Treat columns with < 10 unique values as categorical
                if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                    user_cat_input = right.multiselect(
                        f"Values for {column}",
                        df[column].unique(),
                        default=list(df[column].unique()),
                    )
                    df = df[df[column].isin(user_cat_input)]
                elif is_numeric_dtype(df[column]):
                    _min = float(df[column].min())
                    _max = float(df[column].max())
                    step = (_max - _min) / 100
                    user_num_input = right.slider(
                        f"Values for {column}",
                        _min,
                        _max,
                        (_min, _max),
                        step=step,
                    )
                    df = df[df[column].between(*user_num_input)]
                elif is_datetime64_any_dtype(df[column]):
                    user_date_input = right.date_input(
                        f"Values for {column}",
                        value=(
                            df[column].min(),
                            df[column].max(),
                        ),
                    )
                    if len(user_date_input) == 2:
                        user_date_input = tuple(map(pd.to_datetime, user_date_input))
                        start_date, end_date = user_date_input
                        df = df.loc[df[column].between(start_date, end_date)]
                else:
                    user_text_input = right.text_input(
                        f"Substring or regex in {column}",
                    )
                    if user_text_input:
                        df = df[df[column].str.contains(user_text_input)]

    return df