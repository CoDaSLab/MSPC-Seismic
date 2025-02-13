import streamlit as st
from config.init import init_page
from utils.utils import init_session_state
from utils.widgets import select_time

# --- Application start ---
init_page("Digivolcan Database")
init_session_state()
# ------------------------

import pandas as pd
from datetime import datetime


from preprocessing.functions.data_check import check_sensors

# Cargar los archivos CSV
csv_files = {
    "Available Files":      "data/metadata/Available_files.csv",
    "Available Time":       "data/metadata/Available_times.csv",
    "Available Events":     "data/metadata/ivc_available_data.csv",
    "Feature Log":          "data/metadata/feature_log.csv",
}
names = list(csv_files.keys())


# Función para cargar datos de un archivo CSV
def load_data(csv_file):
    return pd.read_csv(csv_file)

# Función para aplicar filtros a los datos
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


def show_table(name):
    st.header(name)
    data = load_data(csv_files[name])

                                
    data = data.loc[:, ~data.columns.str.contains('\*')] # Remove '*' columns
    columns = data.columns.to_list()


    # Crear checkboxes para cada columna en una fila
    selected_columns = []
    st.subheader("Select columns to show:")
    cols = st.columns(len(columns))

    for col, column in zip(cols, columns):
        if col.checkbox(column, value=True, key=f"{name}_{column}"):
            selected_columns.append(column)
    # selected_columns = columns

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





st.title('Digivolcan database dashboard')

names.append('Check data availability')
tabs = st.tabs(names)

for id, tab in enumerate(tabs[:-1]):
    with tab:
        show_table(names[id])


# Check data availability
with tabs[-1 ]:

    COL = st.columns(2)
    with COL[0]:
        start, end = select_time('check_availability')

    tol = COL[1].number_input('Tolerance (s)', min_value = 0.0, value=0.0)

    result = check_sensors(start, end, tol = tol, pathfile=csv_files["Available Time"],
                           filenames_path=csv_files["Available Files"])
    df = pd.DataFrame(result)

    st.dataframe(df, use_container_width = True)
    # st.write(result["files"])
    # st.dataframe(df.drop(columns=['files', 'missing_data_periods']) )
    
    # st.write(result)
    pass