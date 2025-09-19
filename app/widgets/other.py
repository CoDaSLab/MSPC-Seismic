import streamlit as st

def noc_summary(noc_name, nocs_path="data/involcan/nocs"):
    """
    Displays a NOC's relevant attributes.
    """
    import os
    from monitoring.NOC import NOC
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    starttime = ""
    endtime = ""
    if len(noc.time_range) > 0:
        if isinstance(noc.time_range[0], str):
            starttime = noc.time_range[0]
            endtime = noc.time_range[1]
        else:
            starttime = noc.time_range[0][0]
            endtime = noc.time_range[-1][1]

    with st.expander("NOC details"):
        st.markdown("##### :orange[**Information**]")
        st.markdown(f"**Name:** {noc.name}")
        st.markdown(f"**Network:** {noc.network}")
        st.markdown(f"**Station:** {noc.station}")
        st.markdown(f"**NOC type:** {noc.type}")
        st.markdown(f"**Start time:** {starttime}")
        st.markdown(f"**End time:** {endtime}")
        st.markdown(f"**Last updated:** {noc.last_update_time}")
        
        st.markdown("##### :orange[**Parameters**]")
        st.markdown(f"**Features shape:** {noc.features_shape}")
        st.markdown(f"**Preprocessing:** {'mean-centering' if noc.preprocessing == 1 else 'autoscaling'}")
        st.markdown(f"**Number of principal components:** {noc.n_components}")
        st.markdown(f"**Percentile:** {noc.quantile_threshold * 100}")

        st.markdown("##### :orange[**Control limits**]")
        st.markdown(f"**D threshold:** {noc.D_threshold:.4f}")
        st.markdown(f"**Q threshold:** {noc.Q_threshold:.4f}")


def monitoring_status():
    rt = st.session_state.config["monitoring"]["auto_monitoring"]
    
    if rt:
        msg = "Real-time monitoring active"
        color = "green"
    else:
        msg = "Real-time monitoring inactive"
        color = "red"

    st.markdown(
        f"""
        <div style="padding:10px; border-radius:10px; background-color:{color}; color:white; text-align:center">
            {msg}
        </div>
        """,
        unsafe_allow_html=True
    )
