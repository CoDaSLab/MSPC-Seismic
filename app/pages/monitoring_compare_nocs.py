import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_monitoring

from widgets import *

# --- Application start ---
init_page("Monitoring - NOC comparison")
init_session_state()
st.title("Monitoring")
header_monitoring()
# ------------------------

st.subheader("NOC comparison")

config = st.session_state.config

col1 = st.columns(2)

with col1[0]:
    # Select NOCs to compare
    st.write("##### Select first NOC:")
    _, noc1 = forms.select_noc("noc_selector_comparison1", config["data"]["stations"], config["paths"]["noc_log"])
    tables.noc_summary(noc1, config["paths"]["nocs"])
    st.write("##### Select second NOC:")
    _, noc2 = forms.select_noc("noc_selector_comparison2", config["data"]["stations"], config["paths"]["noc_log"])
    tables.noc_summary(noc2, config["paths"]["nocs"])
    
    with st.form(key="pca_selector_comparison"):
        st.write("##### PCA parameters:")
        subcol = st.columns(2)
        with subcol[0]:
            preprocessing = forms.select_preprocessing("prep_selector_noc_comparison")
        with subcol[1]:
            n_components = st.number_input("Number of principal components", min_value=1, value='min')

        submit = st.form_submit_button("Plot oMEDA comparison", type='primary', use_container_width=True)
    
    with st.form("dq_noc_selector_comparison"):
        st.write("##### Plot D and Q statistics for both NOCs:")
        col2 = st.columns(2)
        with col2[0]:
            logscale = st.checkbox("Log scale", value=False, key="logscale_noc_dq_monitoring",
                                            help="Display Y-axis using a logarithmic scale.")
        with col2[1]:
            submit_dq = st.form_submit_button("Plot D and Q statistics", use_container_width=True)

with col1[1]:
    if submit:
        # Plot oMEDA
        with st.spinner("Calculating oMEDA..."):
            plots.plot_noc_omeda(noc1, noc2, preprocessing=preprocessing, n_components=n_components, 
                                nocs_path=config["paths"]["nocs"])

if submit_dq:
    col3 = st.columns(2)
    with col3[0]:
        with st.spinner("Plotting results..."):
            plots.plot_dq_noc(noc1, nocs_path=config["paths"]["nocs"], logscale=logscale)
    
    with col3[1]:
        with st.spinner("Plotting results.."):
            plots.plot_dq_noc(noc2, nocs_path=config["paths"]["nocs"], logscale=logscale)
