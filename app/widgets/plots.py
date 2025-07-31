import streamlit as st

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
    from monitoring.mspc_rt import plot_anomalies
    from monitoring.NOC import NOC
    import os
    from datetime import datetime, timezone
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))
    test_start = datetime.strptime(noc.test_labels[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    test_end = datetime.strptime(noc.test_labels[-1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    if test_start <= starttime and endtime <= test_end:
        fig, _ = plot_anomalies(noc, starttime, endtime, logscale=logscale, plot_train=plot_train,
                                criterion = criterion, n_consecutive = n_consecutive, save=False, show=False)

        if interactive:
            import mpld3
            import streamlit.components.v1 as components
            fig_html = mpld3.fig_to_html(fig)
            components.html(fig_html, height=600)
        else:
            st.pyplot(fig)
    else:
        st.error("No calculation available for the given time range.")


def plot_dq_rt(noc_name, time_range=None, logscale=False, plot_train=False, criterion = 'consecutive', 
               n_consecutive = 3, nocs_path="data/involcan/nocs", interactive=False):
    from monitoring.mspc_rt import plot_anomalies
    from monitoring.NOC import NOC
    import os
    from datetime import datetime, timedelta, timezone

    if time_range is None:
        time_range = timedelta(hours=st.session_state.config["num_hours_plot"])
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    endtime = datetime.now(timezone.utc)
    starttime = endtime - time_range
    
    try:
        fig, ax = plot_anomalies(noc, starttime, endtime, logscale=logscale, plot_train=plot_train,
                                criterion = criterion, n_consecutive = n_consecutive, save=False, show=False)
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


def plot_noc_omeda(noc1_name, noc2_name, preprocessing=1, n_components=None, var_labels=None, 
                   var_classes=None, nocs_path="data/involcan/nocs", 
                   interactive=False):
    from monitoring.NOC import compare_nocs, NOC
    import os

    noc1 = NOC.load(os.path.join(nocs_path, noc1_name).replace('\\', '/'))
    noc2 = NOC.load(os.path.join(nocs_path, noc2_name).replace('\\', '/'))

    _, fig, _ = compare_nocs(noc1, noc2, preprocessing=preprocessing, n_components=n_components,
                             var_labels=var_labels, var_classes=var_classes)

    if interactive:
        import mpld3
        import streamlit.components.v1 as components
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_var_pca(data, max_components=None, preprocessing=1, interactive=False):
    from mspc_pca.plot import var_pca

    if max_components is None:
        max_components = min(data.shape[0], data.shape[1], 20)

    fig, _ = var_pca(data, max_components, with_ckf=True, 
                    with_std=True if preprocessing == 2 else False)

    if interactive:
        import mpld3
        import streamlit.components.v1 as components
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)