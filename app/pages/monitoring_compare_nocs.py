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
group = st.session_state.group

col1 = st.columns(2)

with col1[0]:
    # Select NOCs to compare
    st.write("##### Select first NOC:")
    _, noc1 = forms.select_noc("noc_selector_comparison1", group["stations"])
    other.noc_summary(noc1)
    st.write("##### Select second NOC:")
    _, noc2 = forms.select_noc("noc_selector_comparison2", group["stations"])
    other.noc_summary(noc2)
    
    with st.form(key="pca_selector_comparison"):
        st.write("##### PCA parameters:")
        subcol = st.columns(2)
        with subcol[0]:
            preprocessing = forms.select_preprocessing("prep_selector_noc_comparison")
        with subcol[1]:
            n_components = st.number_input("Number of principal components", min_value=1, value='min')

        submit = st.form_submit_button("Plot oMEDA comparison", type='primary', use_container_width=True)
    
    with st.form("dq_noc_selector_comparison"):
        st.write("##### Plot T-scores for both NOCs:")
        col2 = st.columns(2)
        with col2[0]:
            logscale = st.checkbox("Log scale", value=False, key="logscale_noc_dq_monitoring",
                                            help="Display Y-axis using a logarithmic scale.")
            weight = st.slider("T-score weight", 0.0, 1.0, step=0.05)
        with col2[1]:
            submit_dq = st.form_submit_button("Plot T-scores", use_container_width=True)

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
            plots.plot_tscore_noc(noc1, T_weight=weight, nocs_path=config["paths"]["nocs"], logscale=logscale)
    
    with col3[1]:
        with st.spinner("Plotting results.."):
            plots.plot_tscore_noc(noc2, T_weight=weight, nocs_path=config["paths"]["nocs"], logscale=logscale)
