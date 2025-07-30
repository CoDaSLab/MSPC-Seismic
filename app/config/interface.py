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
        st.page_link("./pages/database_dashboard.py", label = "Database", icon='🖥️')
    with col[3]:
        st.page_link("./pages/signal_processing_dashboard.py", label="SISMO Visualization", icon='📉')
    with col[4]:
        st.page_link("./pages/feature_extraction_dashboard.py", label="Feature extraction", icon="⛏️")
    with col[5]:
        st.page_link("./pages/real_time_monitoring.py", label="Real-time monitoring", icon="📡")
