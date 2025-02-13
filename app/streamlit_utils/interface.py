import streamlit as st

def logo():
    st.logo("streamlit/resources/logo.png",)

@st.cache_data
def header():
    # Crear una fila de botones en el encabezado
    col = st.columns(5)

    with col[0]:
        st.page_link("./streamlit/app_digivolcan.py", label="Home", icon="🏠")
    with col[1]:
        st.page_link("./streamlit/pages/map.py", label = "Map", icon='🗺️')
    with col[2]:
        st.page_link("./streamlit/pages/database_dashboard.py", label = "Database", icon='🖥️')
    with col[3]:
        st.page_link("./streamlit/pages/signal_processing_dashboard.py", label="SISMO Visualization", icon='📉')
    with col[4]:
        st.page_link("./streamlit/pages/feature_extraction_dashboard.py", label="Feature extraction", icon="⛏️")

