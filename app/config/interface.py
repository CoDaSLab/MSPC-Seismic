import streamlit as st

def logo():
    st.logo("app/resources/logo.png",)

@st.cache_data
def header():
    # All buttons in one row
    col = st.columns(5)

    with col[0]:
        st.page_link("home.py", label="Home", icon="🏠")
    with col[1]:
        st.page_link("./pages/monitoring.py", label="Monitoring", icon="🖥️")
    with col[2]:
        st.page_link("./pages/rtmonitoring.py", label="Real-Time Monitoring", icon="📡")
    with col[3]:
        st.page_link("./pages/download_data.py", label="Download data", icon='⬇️')
    with col[4]:
        st.page_link("./pages/configuration.py", label="Configuration", icon="⚙️")


@st.cache_data
def header_monitoring():
    col = st.columns(3)

    with col[0]:
        st.page_link("pages/monitoring.py", label="On-demand monitoring")
    with col[1]:
        st.page_link("pages/monitoring_compare_nocs.py", label="Compare NOCs")
    with col[2]:
        st.page_link("pages/monitoring_create_nocs.py", label = "Create NOCs")

# @st.cache_data
# def header_rtmonitoring():
#     col = st.columns(2)

#     with col[0]:
#         st.page_link("pages/rtmonitoring.py", label="Visualization")
#     with col[1]:
#         st.page_link("pages/rtmonitoring_config.py", label="Configuration")

@st.cache_data
def header_eda():
    col = st.columns(4)

    with col[0]:
        st.page_link("pages/eda_mapping.py", label="Map")
    with col[1]:
        st.page_link("pages/eda_database.py", label="Database")
    with col[2]:
        st.page_link("pages/eda_signal_processing.py", label="Signal visualization")
    with col[3]:
        st.page_link("pages/eda_feature_extraction.py", label="Feature extraction")