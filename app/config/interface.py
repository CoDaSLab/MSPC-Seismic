import streamlit as st

def logo():
    st.logo("app/resources/logo.png",)

@st.cache_data
def header():
    # Crear una fila de botones en el encabezado
    col = st.columns(6)

    with col[0]:
        st.page_link("home.py", label="Home", icon="🏠")
    with col[1]:
        st.page_link("./pages/mapping.py", label = "Map", icon='🗺️')
    with col[2]:
        st.page_link("./pages/database_dashboard.py", label = "Database", icon='📚')
    with col[3]:
        st.page_link("./pages/monitoring.py", label="Monitoring", icon="🖥️")
    with col[4]:
        st.page_link("./pages/rtmonitoring.py", label="Real-Time Monitoring", icon="📡")
    with col[5]:
        st.page_link("./pages/eda.py", label="Exploratory Data Analysis", icon='📉')



@st.cache_data
def header_monitoring():
    col = st.columns(3)

    with col[0]:
        st.page_link("pages/monitoring.py", label="On-demand monitoring")
    with col[1]:
        st.page_link("pages/monitoring_compare_nocs.py", label="Compare NOCs")
    with col[2]:
        st.page_link("pages/monitoring_create_nocs.py", label = "Create NOCs")

@st.cache_data
def header_rtmonitoring():
    col = st.columns(2)

    with col[0]:
        st.page_link("pages/rtmonitoring.py", label="Visualization")
    with col[1]:
        st.page_link("pages/rtmonitoring_config.py", label="Configuration")

@st.cache_data
def header_eda():
    col = st.columns(2)

    with col[0]:
        st.page_link("pages/eda.py", label="Signal visualization")
    with col[1]:
        st.page_link("pages/eda_feature_extraction.py", label="Feature extraction")