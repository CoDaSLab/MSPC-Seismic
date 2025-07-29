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
    import mpld3
    import streamlit.components.v1 as components
    from monitoring.mspc_rt import plot_anomalies
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))
    fig, _ = plot_anomalies(noc, starttime, endtime, logscale=logscale, plot_train=plot_train,
                            criterion = criterion, n_consecutive = n_consecutive, save=False, show=False)

    if interactive:
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)

def plot_noc_omeda(noc1_name, noc2_name, preprocessing=1, n_components=None, var_labels=None, 
                   var_classes=None, nocs_path="data/involcan/nocs", interactive=False):
    import mpld3
    import streamlit.components.v1 as components
    from monitoring.NOC import compare_nocs, NOC
    import os

    noc1 = NOC.load(os.path.join(nocs_path, noc1_name).replace('\\', '/'))
    noc2 = NOC.load(os.path.join(nocs_path, noc2_name).replace('\\', '/'))

    _, fig, _ = compare_nocs(noc1, noc2, preprocessing=preprocessing, n_components=n_components,
                             var_labels=var_labels, var_classes=var_classes)

    if interactive:
        fig_html = mpld3.fig_to_html(fig)
        components.html(fig_html, height=600)
    else:
        st.pyplot(fig)