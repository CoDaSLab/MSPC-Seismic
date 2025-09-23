import streamlit as st
from datetime import datetime, timedelta, timezone
from config.init import init_session_state

init_session_state()
update_freq = st.session_state.config["monitoring"]["update_frequency"]
rt_plots_cache_time = 0.8 * timedelta(minutes = update_freq)

def set_yaxis(key):
    col = st.columns(2)
    set_yaxis = col[0].checkbox('Set Y axis', False, key=f"Y axis_{key}")
    col = st.columns(2)
    if set_yaxis:
        ylim_min = col[0].number_input('Y axis range:', value = -8e6)
        ylim_max = col[1].number_input('ymax', value = +8e6, label_visibility='hidden')
        ylim = [ylim_min, ylim_max]
    else: ylim = None

    return ylim

def plot_seismogram(S, ylim, interactive):
    import mpld3
    import streamlit.components.v1 as components
    fig = S.plot_seismogram('', ylim, save=False)

    if interactive:
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_fft(S, window_id, ylim, interactive):
    import mpld3
    import streamlit.components.v1 as components
    fig = S.plot_fft(window_id, '', ylim, save=False)

    if interactive:
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_signals():
    
    return

def plot_dq(noc_name, starttime, endtime, logscale=False, plot_train=False,
            criterion = 'consecutive', n_consecutive = 3, nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.mspc_rt import plot_anomalies_DQ
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))
    try:
        test_start = datetime.strptime(noc.test_labels[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        test_end = datetime.strptime(noc.test_labels[-1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except:
        st.error("No data available for the given time range.")
        return
    window_size = timedelta(seconds=noc.metadata["window_size"])

    if test_start - window_size <= starttime and endtime <= test_end + window_size:
        fig, _ = plot_anomalies_DQ(noc, starttime, endtime, logscale=logscale, plot_train=plot_train,
                                criterion = criterion, n_consecutive = n_consecutive, bar_width=1, save=False, show=False)

        if interactive:
            import mpld3
            import streamlit.components.v1 as components
            fig_html = mpld3.fig_to_html(fig)
            components.html(fig_html, height=600)
        else:
            st.pyplot(fig)
    else:
        st.error("No calculation available for the given time range.")

@st.cache_resource(ttl=rt_plots_cache_time, show_spinner=False)
def plot_dq_rt(noc_name, time_range=None, logscale=False, plot_train=False, criterion = 'consecutive', 
               n_consecutive = 3, nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.mspc_rt import plot_anomalies_DQ
    from monitoring.NOC import NOC
    import os

    if time_range is None:
        time_range = timedelta(hours=st.session_state.config["plots"]["num_hours"])
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    # x-axis limits
    update_freq = st.session_state.config["monitoring"]["update_frequency"]
    delay = st.session_state.config["monitoring"]["delay"]
    endtime = datetime.now(timezone.utc)
    minutes = (endtime.minute // update_freq) * update_freq
    endtime = endtime.replace(minute=minutes, second=0, microsecond=0) - timedelta(minutes=delay)
    starttime = endtime - time_range 
    
    try:
        fig, ax = plot_anomalies_DQ(noc, starttime, endtime, logscale=logscale, plot_train=plot_train,
                                criterion = criterion, n_consecutive = n_consecutive, bar_width=1, save=False, show=False)
        ax[0].set_title("")
        ax[1].set_title("")
        ax[0].set_ylabel("D-statistic")
        ax[1].set_ylabel("Q-statistic")
        fig.suptitle(noc.name)

        if interactive:
            import mpld3
            import streamlit.components.v1 as components
            fig_html = mpld3.fig_to_html(fig)
            components.html(fig_html, height=600)
        else:
            st.pyplot(fig)
    except AssertionError:
        st.error("No recent data available.")


def plot_tscore(noc_name, starttime, endtime, T_weight=None, T_norm_quantile=0.5, T_threshold_quantile=None,
                    logscale=False, plot_train=False,criterion = 'consecutive', n_consecutive = 3, 
                    nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.mspc_rt import plot_anomalies_T
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))
    try:
        test_start = datetime.strptime(noc.test_labels[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        test_end = datetime.strptime(noc.test_labels[-1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except:
        st.error("No data available for the given time range.")
        return
    window_size = timedelta(seconds=noc.metadata["window_size"])

    if test_start - window_size <= starttime and endtime <= test_end + window_size:
        fig, ax = plot_anomalies_T(noc, starttime, endtime, T_weight, T_norm_quantile, T_threshold_quantile,
                                  logscale=logscale, plot_train=plot_train, criterion = criterion, 
                                  n_consecutive = n_consecutive, bar_width=1, save=False, show=False)
        ax.set_title("")
        ax.set_ylabel(f"T-score ($\\alpha = {T_weight}$)")

        if interactive:
            import mpld3
            import streamlit.components.v1 as components
            fig_html = mpld3.fig_to_html(fig)
            components.html(fig_html, height=600)
        else:
            st.pyplot(fig)
    else:
        st.error("No calculation available for the given time range.")

# @st.cache_resource(ttl=rt_plots_cache_time, show_spinner=False)
def plot_tscore_rt(
    noc_name,
    time_range=None,
    T_weight=None,
    T_norm_quantile=0.5,
    T_threshold_quantile=None,
    logscale=False,
    plot_train=False,
    criterion="consecutive",
    n_consecutive=3,
    nocs_path="data/involcan/nocs",
):
    from monitoring.mspc_rt import plot_anomalies_T
    from monitoring.NOC import NOC
    import os
    from datetime import datetime, timezone

    # Cargar NOC
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace("\\", "/"))
    delay = st.session_state.config["monitoring"]["delay"]

    endtime = datetime.now(timezone.utc)
    minutes = (endtime.minute // update_freq) * update_freq
    endtime = endtime.replace(minute=minutes, second=0, microsecond=0) - timedelta(minutes=delay)
    starttime = endtime - time_range 

    try:
        # Ahora la función devuelve Plotly fig, df y threshold
        fig_plotly = plot_anomalies_T(
            noc,
            starttime,
            endtime,
            T_weight,
            T_norm_quantile,
            T_threshold_quantile,
            logscale=logscale,
            plot_train=plot_train,
            criterion=criterion,
            n_consecutive=n_consecutive,
            show=False,
        )
        
        selected_points = st.plotly_chart(fig_plotly, use_container_width=True, on_select = "rerun")

        # Devolver datos útiles para procesar después
        return selected_points

    except AssertionError:
        st.error("No recent data available.")
        return None, None



def plot_dq_noc(noc_name, logscale=False, nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    fig, ax = noc.plot_DQ(logscale=logscale)
    ax[0].set_title("")
    ax[1].set_title("")
    ax[0].set_ylabel("D-statistic")
    ax[1].set_ylabel("Q-statistic")
    fig.suptitle(noc.name)

    if interactive:
        import mpld3
        import streamlit.components.v1 as components

        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)


def plot_tscore_noc(noc_name, T_weight=None, T_norm_quantile=0.5, T_threshold_quantile=None,
                    logscale=False, nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))
    T = noc.calculate_T(T_weight, T_norm_quantile)

    fig, ax = noc.plot_T(T, T_threshold_quantile, logscale=logscale)
    ax.set_title("")
    fig.suptitle(noc.name)
    ax.set_ylabel(f"T-score ($\\alpha = {T_weight}$)")

    if interactive:
        import mpld3
        import streamlit.components.v1 as components

        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)


def plot_noc_omeda(noc1_name, noc2_name, preprocessing=1, n_components=None, var_labels=None, 
                   var_classes=None, nocs_path="data/involcan/nocs", 
                   interactive=False):
    from monitoring.NOC import compare_nocs, NOC
    import os

    noc1 = NOC.load(os.path.join(nocs_path, noc1_name).replace('\\', '/'))
    noc2 = NOC.load(os.path.join(nocs_path, noc2_name).replace('\\', '/'))

    _, fig, _ = compare_nocs(noc1, noc2, nocs_path, preprocessing=preprocessing, 
                             n_components=n_components, var_labels=var_labels, var_classes=var_classes)

    if interactive:
        import mpld3
        import streamlit.components.v1 as components
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_var_pca(data, max_components=20, preprocessing=1, interactive=False):
    from mspc_pca.plot import var_pca

    fig, _ = var_pca(data, max_components, with_ckf=True, 
                    with_std=True if preprocessing == 2 else False)

    if interactive:
        import mpld3
        import streamlit.components.v1 as components
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_omeda(omeda_vec, stations, channels, vars_label=None, colors=["#3B96FF", "#32A006", "#FF7B00"], nticks=5):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    unique_stations = np.unique(stations)
    unique_channels = np.unique(channels)
    n_stations = len(unique_stations)
    n_channels = len(unique_channels)

    n_vars = len(omeda_vec) // (n_channels * n_stations)
    vmin = np.min(omeda_vec)
    vmax = np.max(omeda_vec)

    # Crear figura con subplots
    fig = make_subplots(
        rows=n_channels,
        cols=n_stations,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=[f"{st}" for st in unique_stations] * n_channels # Only for first row
    )

    for j, st in enumerate(unique_stations):  # columnas: estaciones
        for i, ch in enumerate(unique_channels):  # filas: canales
            id_start = n_vars * (j * n_channels + i)
            id_end = n_vars * (j * n_channels + i + 1)
            vec = omeda_vec[id_start:id_end]

            x_vals = np.arange(len(vec))
            hovertext = None

            # Si se pasan labels
            if vars_label is not None:
                hovertext = [f"{vars_label[k]}: {vec[k]:.3e}" for k in range(len(vec))]
                tickvals = np.linspace(0, len(vec)-1, nticks, dtype=int)
                ticktext = [vars_label[k] for k in tickvals]
                fig.update_xaxes(tickvals=tickvals, ticktext=ticktext, row=i+1, col=j+1)

            fig.add_trace(
                go.Bar(
                    x=x_vals,
                    y=vec,
                    name=f"{ch}",
                    marker=dict(color=colors[i % len(colors)]),
                    showlegend=(j == 0),
                    hovertext=hovertext,
                    hoverinfo="text" if vars_label is not None else "y+x"
                ),
                row=i + 1,
                col=j + 1,
                )

    # Sincronizar zoom
    for i in range(n_channels):
        for j in range(n_stations):
            fig.update_xaxes(matches='x', row=i+1, col=j+1)
            fig.update_yaxes(matches='y', row=i+1, col=j+1)

    # Layout
    fig.update_yaxes(range=[vmin, vmax])
    fig.update_xaxes(title_text="Frequency", row=n_channels, col=(n_stations // 2) + 1)
    fig.update_yaxes(title_text='difference', row=(n_channels // 2) + 1, col=1)

    for ann in fig.layout.annotations:
        if ann.y != 1.0:  
            ann.text = ""

    return fig
