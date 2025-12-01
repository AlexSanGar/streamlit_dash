import streamlit as st
import modulo as dm  

# ---------------------------------------------------------
# CONFIG STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Small Caps Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# CACHING (aceleración extrema)
# ---------------------------------------------------------
@st.cache_data
def get_static_fig(fig_function):
    return fig_function()

@st.cache_resource
def get_intradia():
    return dm.grafico_intradia()

@st.cache_resource
def get_premarket():
    return dm.grafico_premarket()

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.markdown("<h1 style='text-align: center;'>Estadísticas Small Caps</h1>", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------------------------------------
# MÉTRICAS PRINCIPALES
# ---------------------------------------------------------
col1, col2 = st.columns([1.4, 1])

with col1:
    st.plotly_chart(dm.fig_3, use_container_width=True)

with col2:
    st.plotly_chart(dm.fig_2, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# GAPS / MES + RETURN — Selector funcional
# ---------------------------------------------------------

col_left, col_right = st.columns([1.2, 2])

with col_left:
    st.plotly_chart(dm.fig_4, use_container_width=True)

with col_right:

    s_left, s_right = st.columns([0.15, 0.85])

    opciones = {
        "Gaps": "stocks",
        "Volumen": "volume",
        "Gap Value": "gap",
        "High Spike": "highspike",
        "Low Spike": "lowspike",
        "Range": "range",
        "Close Red": "closered",
        "RTH Fade": "rth_fade_close",
    }

    with s_left:
        metric_label = st.selectbox(
            "",
            list(opciones.keys()),
            key="selector_mes"
        )
        metric = opciones[metric_label]

    with s_right:

        if metric == "stocks":
            fig_mes = dm.grafico_gappers()
        elif metric == "volume":
            fig_mes = dm.grafico_volumen()
        elif metric == "gap":
            fig_mes = dm.grafico_gap()
        elif metric == "highspike":
            fig_mes = dm.grafico_highspike()
        elif metric == "lowspike":
            fig_mes = dm.grafico_lowspike()
        elif metric == "range":
            fig_mes = dm.grafico_range()
        elif metric == "closered":
            fig_mes = dm.grafico_closered()
        elif metric == "rth_fade_close":
            fig_mes = dm.grafico_rth_fade_to_close_mes()
        else:
            fig_mes = dm.grafico_gappers()

        st.plotly_chart(fig_mes, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# DISTRIBUCIONES
# ---------------------------------------------------------

c1, c2, c3 = st.columns(3)

with c1:
    tipo = st.selectbox("Distribución Spike:", ["High Spike", "Low Spike"])
    fig = dm.grafico_highspike_distribution() if tipo == "High Spike" else dm.grafico_lowspike_distribution()
    st.plotly_chart(fig, use_container_width=True)

with c2:
    tipo = st.selectbox("Distribución Horaria:", ["LOD Time", "HOD Time"])
    fig = dm.grafico_lod_distribution() if tipo == "LOD Time" else dm.grafico_hod_distribution()
    st.plotly_chart(fig, use_container_width=True)

with c3:
    tipo = st.selectbox("Return/Gap/Fade Distribución:", ["Return", "Gap Size", "Fade"])
    if tipo == "Return":
        fig = dm.grafico_return_distribution()
    elif tipo == "Gap Size":
        fig = dm.grafico_gap_size_distribution()
    else:
        fig = dm.grafico_fade_distribution()
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# INTRADÍA
# ---------------------------------------------------------
st.plotly_chart(get_intradia(), use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# MULTIFRAME
# ---------------------------------------------------------

c1, c2, c3 = st.columns(3)

with c1:
    opt = st.selectbox("Multi-Timeframe:", ["Returns", "High Spike", "Low Spike"])
    if opt == "Returns":
        fig = dm.grafico_multiframe_returns()
    elif opt == "High Spike":
        fig = dm.grafico_multiframe_highspike()
    else:
        fig = dm.grafico_multiframe_lowspike()
    st.plotly_chart(fig, use_container_width=True)

with c2:
    opt = st.selectbox("Price range/Gaps by year:", ["Price Range", "Gaps by Year"])
    fig = dm.grafico_price_range_distribution() if opt == "Price Range" else dm.grafico_gaps_por_ano()
    st.plotly_chart(fig, use_container_width=True)

with c3:
    opt = st.selectbox("Return from TF to close/VWAP Distance:", ["Return from TF to close", "VWAP Distance"])
    fig = dm.grafico_multiframe_return_to_close() if opt == "Return from TF to close" else dm.grafico_multiframe_vwap_distance()
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# PREMARKET
# ---------------------------------------------------------
st.markdown("<h3 style='text-align: center;'>Análsis Pre-Market</h3>", unsafe_allow_html=True)
st.markdown("---")

c1, c2 = st.columns([1, 2])

with c1:
    tipo = st.selectbox("Distribución Pre-Market:", ["PM High Time", "PMH Gap", "PMH Fade"])
    if tipo == "PM High Time":
        fig = dm.grafico_pm_high_distribution(dm.stocks_filtrados)
    elif tipo == "PMH Gap":
        fig = dm.grafico_pmh_gap_distribution()
    else:
        fig = dm.grafico_pmh_fade_distribution()
    st.plotly_chart(fig, use_container_width=True)

with c2:
    tipo = st.selectbox("Métricas Pre-Market:", ["PMH Gap Value", "Fade %", "Volume", "Fade PM >15%"])
    if tipo == "PMH Gap Value":
        fig = dm.grafico_pmh_gap_value()
    elif tipo == "Fade %":
        fig = dm.grafico_pmh_fade_value()
    elif tipo == "Volume":
        fig = dm.grafico_pmh_volume_mes()
    else:
        fig = dm.crear_grafico_retornos_stack()
    st.plotly_chart(fig, use_container_width=True)


st.plotly_chart(get_premarket(), use_container_width=True, key="premarket_chart")