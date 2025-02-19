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
        st.subheader('Stats:')
        st.write(data[selected_columns].describe())
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



# WIP
def apply_filters(data, name, selected_columns):
    # Filtering
    st.subheader('Queries:')
    
    query_col, query_type, query_value = st.columns(3)

    with query_col:
        selected_column = st.selectbox("Select column", selected_columns, key=f"{name}_query_col")
    
    with query_type:
        condition = st.selectbox("Condition", ["Exact value", "Min value", "Max value"], key=f"{name}_query_type")

    with query_value:
        if condition == "Exact value":
            query_val = st.text_input("Value", key=f"{name}_query_val")
        else:
            query_val = st.number_input("Value", key=f"{name}_query_val", value=0)

    # Aplicar filtros
    if selected_column:
        if condition == "Exact value":
            return data[data[selected_column] == query_val]
        elif condition == "Min value":
            return data[data[selected_column] >= query_val]
        elif condition == "Max value":
            return data[data[selected_column] <= query_val]

    return data
