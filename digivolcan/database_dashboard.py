import streamlit as st
import pandas as pd
from datetime import datetime

from functions.data_check import check_sensors

# Cargar los archivos CSV
csv_files = {
    "Available Files":      "database/Available_files.csv",
    "Available Time":       "database/Available_times.csv",
    "Available Events":     "database/ivc_available_data.csv",
    "Feature Log":          "database/feature_log.csv",
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


# --- Application start ---
st.set_page_config(
    page_title= "Digivolcan Database",
    layout='wide',
    page_icon='🖥',
    )
st.title('Digivolcan database dashboard')

names.append('Check availability')
tabs = st.tabs(names)

for id, tab in enumerate(tabs[:-1]):
    with tab:
        show_table(names[id])



with tabs[-1 ]:

    COL = st.columns(2)
    COL[0].subheader("start")
    col = COL[0].columns(2)
    fecha = col[0].date_input("Select a date", key='start_date', value=datetime(2021, 11, 26))
    hora = col[1].time_input("Select a time", key='start_time')
    start = datetime.combine(fecha, hora)

    tol = col[0].number_input('Tolerance (s)', min_value = 0.0, value=0.0)

    COL[1].subheader("end")
    col = COL[1].columns(2)
    fecha = col[0].date_input("Select a date", key='end_date', value = datetime(2021, 11, 27))
    hora = col[1].time_input("Select a time", key='end_time')
    end = datetime.combine(fecha, hora)


    result = check_sensors(start, end, tol = tol, pathfile=csv_files["Available Time"],
                           filenames_path=csv_files["Available Files"])
    df = pd.DataFrame(result)

    st.dataframe(df, use_container_width = True)
    # st.write(result["files"])
    # st.dataframe(df.drop(columns=['files', 'missing_data_periods']) )
    
    # st.write(result)
    pass