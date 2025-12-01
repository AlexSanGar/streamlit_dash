# dashboard_module.py
# Módulo limpio y optimizado (mantiene la lógica original, renombra lo necesario)

# -------------------------------------------------------------
# IMPORTS
# -------------------------------------------------------------
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# -------------------------------------------------------------
# CARGA DE DATOS (una sola vez)
# -------------------------------------------------------------
# Datos principales
stocks = pd.read_csv(
    "https://raw.githubusercontent.com/AlexSanGar/dash/refs/heads/main/data_completa.csv"
)
# Evita un caso erróneo puntual
stocks = stocks[~((stocks["Date"] == "2022-02-18") & (stocks["Ticker"] == "QNGY"))]

# Normaliza columna Date
stocks["Date"] = pd.to_datetime(stocks["Date"], errors="coerce")
stocks_v1 = stocks.copy()

stocks_v1["Period"] = stocks_v1["Date"].dt.year
stocks_v1["Month"] = stocks_v1["Date"].dt.month
# Watch out: .isocalendar().week returns Series with dtype UInt... cast to int
stocks_v1["Week"] = stocks_v1["Date"].dt.isocalendar().week.astype("Int64")

# Intraday (15min) -- cargar una sola vez para acelerar
try:
    intraday_df = pd.read_csv(
        "https://raw.githubusercontent.com/AlexSanGar/dash/refs/heads/main/data_15min.csv"
    )
except Exception:
    intraday_df = pd.DataFrame()  # si no carga, evitamos romper el módulo

# -------------------------------------------------------------
# FUNCIÓN DE FILTRADO
# -------------------------------------------------------------
def filtrar_smallcaps(df): 
    start = pd.to_datetime("2022-01-01") 
    end = pd.to_datetime("2025-11-30") 
    filtro_tiempo = (df["Date"] >= start) & (df["Date"] <= end) 

    filtro_no_buyouts = pd.to_numeric(df.get("RTH Range %", 0), errors="coerce") > 0.1 
    filtro_smallcaps = pd.to_numeric(df.get("Open Price", 0), errors="coerce") < 12 
    filtro_liquidez = pd.to_numeric(df.get("Premarket Volume", 0), errors="coerce") > 1_000_000 
    filtro_gap = (pd.to_numeric(df.get("Open Gap %", 0), errors="coerce") > 0.5) & ( pd.to_numeric(df.get("Open Gap %", 0), errors="coerce") < 8 ) 
    filtro_previous_day = pd.to_numeric(df.get("Previous Day Close Price", 0), errors="coerce") > 0.1 

    #filtro_premarket = pd.to_numeric(df.get("PMH Gap %", 0), errors="coerce") > 0.5
    #filtro_return = pd.to_numeric(df.get("Day Return %", 0), errors="coerce") < 0
    #pm_time = pd.to_datetime(df.get("PM High Time"), format="%H:%M", errors="coerce") 
    #filtro_hora = (pm_time >= pd.to_datetime("07:00")) & (pm_time <= pd.to_datetime("09:00"))

    filtros = (
        filtro_tiempo & 
        filtro_no_buyouts & 
        filtro_smallcaps & 
        filtro_liquidez & 
        filtro_gap & 
        #filtro_premarket &
        #filtro_return &
        #filtro_hora &
        filtro_previous_day
        )
    
    return df.loc[filtros].copy()


stocks_filtrados = filtrar_smallcaps(stocks_v1)

# -------------------------------------------------------------
# MÉTRICAS BASE (precomputadas para rendimiento)
# -------------------------------------------------------------

def _to_yearmonth(df, year_col="Period", month_col="Month"):
    return df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)

# GAPS
monthly_counts = (
    stocks_filtrados.groupby(["Period","Month"])
    .size()
    .reset_index(name="Stocks")
)
monthly_counts["YearMonth"] = _to_yearmonth(monthly_counts)
monthly_counts["SMA_6"] = monthly_counts["Stocks"].rolling(6, min_periods=1).mean()

# VOLUME
monthly_volume = (
    stocks_filtrados.groupby(["Period","Month"])["EOD Volume"]
    .sum()
    .reset_index()
)
monthly_volume["YearMonth"] = _to_yearmonth(monthly_volume)
monthly_volume["SMA_6"] = monthly_volume["EOD Volume"].rolling(6, min_periods=1).mean()

# GAP VALUE
monthly_gap_open = (
    stocks_filtrados.groupby(["Period","Month"])["Open Gap %"]
    .mean()
    .reset_index()
)
monthly_gap_open["YearMonth"] = _to_yearmonth(monthly_gap_open)
monthly_gap_open["Gap (%)"] = (monthly_gap_open["Open Gap %"] * 100).round(2)
monthly_gap_open["SMA_6"] = monthly_gap_open["Gap (%)"].rolling(6, min_periods=1).mean()

# HIGH SPIKE
monthly_highspike = (
    stocks_filtrados.groupby(["Period","Month"])["High Spike %"]
    .mean()
    .reset_index()
)
monthly_highspike["YearMonth"] = _to_yearmonth(monthly_highspike)
monthly_highspike["High Spike (%)"] = (monthly_highspike["High Spike %"] * 100).round(2)
monthly_highspike["SMA_6"] = monthly_highspike["High Spike (%)"].rolling(6, min_periods=1).mean()

# LOW SPIKE
monthly_lowspike = (
    stocks_filtrados.groupby(["Period","Month"])["Low Spike %"]
    .mean()
    .reset_index()
)
monthly_lowspike["YearMonth"] = _to_yearmonth(monthly_lowspike)
monthly_lowspike["Low Spike (%)"] = (monthly_lowspike["Low Spike %"] * 100).round(2)
monthly_lowspike["SMA_6"] = monthly_lowspike["Low Spike (%)"].rolling(6, min_periods=1).mean()

# RANGE
monthly_range = (
    stocks_filtrados.groupby(["Period","Month"])["RTH Range %"]
    .mean()
    .reset_index()
)
monthly_range["YearMonth"] = _to_yearmonth(monthly_range)
monthly_range["Range (%)"] = (monthly_range["RTH Range %"] * 100).round(2)
monthly_range["SMA_6"] = monthly_range["Range (%)"].rolling(6, min_periods=1).mean()

# CLOSE RED
monthly_closered = (
    stocks_filtrados.assign(close_red=stocks_filtrados["Day Return %"] < 0)
    .groupby(["Period","Month"])["close_red"]
    .mean()
    .reset_index()
)
monthly_closered["YearMonth"] = _to_yearmonth(monthly_closered)
monthly_closered["Close Red (%)"] = (monthly_closered["close_red"] * 100).round(2)
monthly_closered["SMA_6"] = monthly_closered["Close Red (%)"].rolling(6, min_periods=1).mean()

# RTH FADE
monthly_rth_fade = (
    stocks_filtrados.assign(RTH_Fade = pd.to_numeric(stocks_filtrados["RTH Fade to Close %"], errors="coerce"))
    .groupby(["Period","Month"])["RTH_Fade"]
    .mean()
    .reset_index()
)
monthly_rth_fade["YearMonth"] = _to_yearmonth(monthly_rth_fade)
monthly_rth_fade["Fade (%)"] = (monthly_rth_fade["RTH_Fade"] * 100).round(2)
monthly_rth_fade["SMA_6"] = monthly_rth_fade["Fade (%)"].rolling(6, min_periods=1).mean()

# fig_2 metrics (negativos vs positivos)
total = len(stocks_filtrados)
neg_count = (stocks_filtrados["Day Return %"] < 0).sum()
pos_count = total - neg_count
neg_pct = round(neg_count / total * 100, 2) if total > 0 else 0
pos_pct = round(100 - neg_pct, 2) if total > 0 else 0

# PM Fade > 15% metrics
total_1 = len(stocks_filtrados)
neg_count_1 = (stocks_filtrados["PMH Fade to Open %"] < -0.15).sum()
pos_count_1 = total_1 - neg_count_1
neg_pct_1 = round(neg_count_1 / total_1 * 100, 2) if total_1 > 0 else 0
pos_pct_1 = round(100 - neg_pct_1, 2) if total_1 > 0 else 0

# Para fig_3 (avg / median)
stocks_filtrados_1 = filtrar_smallcaps(stocks)  # mantiene la semántica original

# Cálculos de medias y medianas
avg_return = round(stocks_filtrados_1["Day Return %"].mean() * 100, 2)
avg_open_gap = round(stocks_filtrados_1["Open Gap %"].mean() * 100, 2)
avg_high_spike = round(stocks_filtrados_1["High Spike %"].mean() * 100, 2)
avg_low_spike = round(stocks_filtrados_1["Low Spike %"].mean() * 100, 2)
avg_range = round(stocks_filtrados_1["RTH Range %"].mean() * 100, 2)

# convierte HOD/LOD, calcula medias/medianas (respetando errores)
stocks_filtrados_1["HOD Time"] = pd.to_datetime(stocks_filtrados_1["HOD Time"], format="%H:%M", errors="coerce")
stocks_filtrados_1["HOD_horario"] = (
    stocks_filtrados_1["HOD Time"].dt.hour * 3600 + stocks_filtrados_1["HOD Time"].dt.minute * 60
)
mean_seconds = stocks_filtrados_1["HOD_horario"].mean()
if pd.isna(mean_seconds):
    avg_hod_time = "NA"
else:
    avg_hod_time = f"{int(mean_seconds // 3600):02d}:{int((mean_seconds % 3600) // 60):02d}"

stocks_filtrados_1["LOD Time"] = pd.to_datetime(stocks_filtrados_1["LOD Time"], format="%H:%M", errors="coerce")
stocks_filtrados_1["LOD_horario"] = (
    stocks_filtrados_1["LOD Time"].dt.hour * 3600 + stocks_filtrados_1["LOD Time"].dt.minute * 60
)
mean_seconds = stocks_filtrados_1["LOD_horario"].mean()
if pd.isna(mean_seconds):
    avg_lod_time = "NA"
else:
    avg_lod_time = f"{int(mean_seconds // 3600):02d}:{int((mean_seconds % 3600) // 60):02d}"

median_return = round(stocks_filtrados_1["Day Return %"].median() * 100, 2)
median_open_gap = round(stocks_filtrados_1["Open Gap %"].median() * 100, 2)
median_high_spike = round(stocks_filtrados_1["High Spike %"].median() * 100, 2)
median_low_spike = round(stocks_filtrados_1["Low Spike %"].median() * 100, 2)
median_range = round(stocks_filtrados_1["RTH Range %"].median() * 100, 2)

# median times
hod_median_seconds = stocks_filtrados_1["HOD_horario"].median()
if pd.isna(hod_median_seconds):
    median_hod_time = "NA"
else:
    median_hod_time = f"{int(hod_median_seconds // 3600):02d}:{int((hod_median_seconds % 3600) // 60):02d}"

lod_median_seconds = stocks_filtrados_1["LOD_horario"].median()
if pd.isna(lod_median_seconds):
    median_lod_time = "NA"
else:
    median_lod_time = f"{int(lod_median_seconds // 3600):02d}:{int((lod_median_seconds % 3600) // 60):02d}"

def format_value(v):
    """Formatea valores para la tabla (mantiene tu HTML original)."""
    if isinstance(v, str) and ":" in v:
        return v
    try:
        v_num = float(v)
    except Exception:
        return str(v)
    return f"<span style='color:#00cc96'>{v}%</span>" if v_num >= 0 else f"<span style='color:#ef553b'>{v}%</span>"

metrics = ["High Spike", "Low Spike", "Return", "Gap at open", "RTH Range", "HOD Time", "LOD Time"]
avg_values = [
    format_value(avg_high_spike),
    format_value(avg_low_spike),
    format_value(avg_return),
    format_value(avg_open_gap),
    format_value(avg_range),
    avg_hod_time,
    avg_lod_time,
]
median_values = [
    format_value(median_high_spike),
    format_value(median_low_spike),
    format_value(median_return),
    format_value(median_open_gap),
    format_value(median_range),
    median_hod_time,
    median_lod_time,
]

# -------------------------------------------------------------
# PMH / PM metrics (renombradas para evitar sobreescrituras)
# -------------------------------------------------------------
# monthly_pmh_gap : PMH Gap % por mes (renombrado)
if "PMH Gap %" not in stocks_filtrados.columns:
    # Mantener comportamiento original: lanzar error para que se detecte en dev
    raise KeyError("La columna 'PMH Gap %' no existe en stocks_filtrados")

monthly_pmh_gap = (
    stocks_filtrados.assign(**{"PMH Gap %": pd.to_numeric(stocks_filtrados["PMH Gap %"], errors="coerce")})
    .groupby(["Period", "Month"], as_index=False)
    .agg(PMH_Gap_Mean=("PMH Gap %", "mean"))
)
monthly_pmh_gap["YearMonth_dt"] = pd.to_datetime(
    monthly_pmh_gap["Period"].astype(str) + "-" + monthly_pmh_gap["Month"].astype(str).str.zfill(2) + "-01",
    format="%Y-%m-%d",
    errors="coerce",
)
monthly_pmh_gap = monthly_pmh_gap.sort_values("YearMonth_dt").reset_index(drop=True)
monthly_pmh_gap["Gap (%)"] = monthly_pmh_gap["PMH_Gap_Mean"] * 100
monthly_pmh_gap["SMA_6"] = monthly_pmh_gap["Gap (%)"].rolling(window=6, min_periods=1).mean()
monthly_pmh_gap["Gap (%)"] = monthly_pmh_gap["Gap (%)"].round(2)
monthly_pmh_gap["SMA_6"] = monthly_pmh_gap["SMA_6"].round(2)
monthly_pmh_gap["YearMonth"] = monthly_pmh_gap["YearMonth_dt"].dt.strftime("%Y-%m")

# monthly_fade (PMH Fade to Open %)
if "PMH Fade to Open %" not in stocks_filtrados.columns:
    raise KeyError("La columna 'PMH Fade to Open %' no existe en stocks_filtrados")

tmp_df = stocks_filtrados.copy()
tmp_df["PMH Fade to Open %"] = (
    tmp_df["PMH Fade to Open %"].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
)
tmp_df["PMH Fade to Open %"] = pd.to_numeric(tmp_df["PMH Fade to Open %"], errors="coerce")
monthly_fade = (
    tmp_df.groupby(["Period", "Month"], as_index=False)
    .agg(PMH_Fade_Mean=("PMH Fade to Open %", "mean"))
)
monthly_fade["YearMonth_dt"] = pd.to_datetime(
    monthly_fade["Period"].astype(str) + "-" + monthly_fade["Month"].astype(str).str.zfill(2) + "-01",
    format="%Y-%m-%d",
    errors="coerce",
)
monthly_fade = monthly_fade.sort_values("YearMonth_dt").reset_index(drop=True)
monthly_fade["Fade (%)"] = monthly_fade["PMH_Fade_Mean"] * 100
monthly_fade["SMA_6"] = monthly_fade["Fade (%)"].rolling(window=6, min_periods=1).mean()
monthly_fade["Fade (%)"] = monthly_fade["Fade (%)"].round(2)
monthly_fade["SMA_6"] = monthly_fade["SMA_6"].round(2)
monthly_fade["YearMonth"] = monthly_fade["YearMonth_dt"].dt.strftime("%Y-%m")

# monthly_pmv (Premarket Volume)
if "Premarket Volume" not in stocks_filtrados.columns:
    raise KeyError("La columna 'Premarket Volume' no existe en stocks_filtrados")

tmp_df2 = stocks_filtrados.copy()
tmp_df2["Premarket Volume"] = tmp_df2["Premarket Volume"].astype(str).str.replace(",", "", regex=False).str.strip()
tmp_df2["Premarket Volume"] = pd.to_numeric(tmp_df2["Premarket Volume"], errors="coerce")
monthly_pmv = (
    tmp_df2.groupby(["Period", "Month"], as_index=False)
    .agg(PMH_Volume_Total=("Premarket Volume", "sum"))
)
monthly_pmv["YearMonth_dt"] = pd.to_datetime(
    monthly_pmv["Period"].astype(str) + "-" + monthly_pmv["Month"].astype(str).str.zfill(2) + "-01",
    format="%Y-%m-%d",
    errors="coerce",
)
monthly_pmv = monthly_pmv.sort_values("YearMonth_dt").reset_index(drop=True)
monthly_pmv["SMA_6"] = monthly_pmv["PMH_Volume_Total"].rolling(window=6, min_periods=1).mean()
monthly_pmv["PMH_Volume_Total"] = monthly_pmv["PMH_Volume_Total"].round(2)
monthly_pmv["SMA_6"] = monthly_pmv["SMA_6"].round(2)
monthly_pmv["YearMonth"] = monthly_pmv["YearMonth_dt"].dt.strftime("%Y-%m")

# monthly_rth_fade
if "RTH Fade to Close %" not in stocks_filtrados.columns:
    raise KeyError("La columna 'RTH Fade to Close %' no existe en stocks_filtrados")

tmp_df3 = stocks_filtrados.copy()
tmp_df3["RTH Fade to Close %"] = tmp_df3["RTH Fade to Close %"].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
tmp_df3["RTH Fade to Close %"] = pd.to_numeric(tmp_df3["RTH Fade to Close %"], errors="coerce")
monthly_rth_fade = (
    tmp_df3.groupby(["Period", "Month"], as_index=False)
    .agg(RTH_Fade_Mean=("RTH Fade to Close %", "mean"))
)
monthly_rth_fade["YearMonth_dt"] = pd.to_datetime(
    monthly_rth_fade["Period"].astype(str) + "-" + monthly_rth_fade["Month"].astype(str).str.zfill(2) + "-01",
    format="%Y-%m-%d",
    errors="coerce",
)
monthly_rth_fade = monthly_rth_fade.sort_values("YearMonth_dt").reset_index(drop=True)
monthly_rth_fade["Fade (%)"] = monthly_rth_fade["RTH_Fade_Mean"] * 100
monthly_rth_fade["SMA_6"] = monthly_rth_fade["Fade (%)"].rolling(window=6, min_periods=1).mean()
monthly_rth_fade["Fade (%)"] = monthly_rth_fade["Fade (%)"].round(2)
monthly_rth_fade["SMA_6"] = monthly_rth_fade["SMA_6"].round(2)
monthly_rth_fade["YearMonth"] = monthly_rth_fade["YearMonth_dt"].dt.strftime("%Y-%m")

# -------------------------------------------------------------
# FIGURAS (funciones)
# -------------------------------------------------------------

def grafico_gappers():
    fig = px.bar(monthly_counts,x="YearMonth",y="Stocks",title="   Gaps / mes",
                 labels={"YearMonth":"Mes","Stocks":"Gaps"},template="plotly_dark")
    fig.add_scatter(x=monthly_counts["YearMonth"], y=monthly_counts["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_volumen():
    fig = px.bar(monthly_volume,x="YearMonth",y="EOD Volume",title="   Volumen total",
                 labels={"YearMonth":"Mes"},template="plotly_dark")
    fig.add_scatter(x=monthly_volume["YearMonth"], y=monthly_volume["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_gap():
    fig = px.bar(monthly_gap_open,x="YearMonth",y="Gap (%)",title="   Gap Value %",
                 labels={"YearMonth":"Mes","Gap (%)":"Gap (%)"},template="plotly_dark")
    fig.add_scatter(x=monthly_gap_open["YearMonth"], y=monthly_gap_open["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_highspike():
    fig = px.bar(monthly_highspike,x="YearMonth",y="High Spike (%)",title="   High Spike %",
                 labels={"YearMonth":"Mes"},template="plotly_dark")
    fig.add_scatter(x=monthly_highspike["YearMonth"], y=monthly_highspike["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_lowspike():
    fig = px.bar(monthly_lowspike,x="YearMonth",y="Low Spike (%)",title="   Low Spike %",
                 labels={"YearMonth":"Mes"},template="plotly_dark")
    fig.add_scatter(x=monthly_lowspike["YearMonth"], y=monthly_lowspike["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_range():
    fig = px.bar(monthly_range,x="YearMonth",y="Range (%)",title="   RTH Range %",
                 labels={"YearMonth":"Mes"},template="plotly_dark")
    fig.add_scatter(x=monthly_range["YearMonth"], y=monthly_range["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig

def grafico_closered():
    fig = px.bar(monthly_closered,x="YearMonth",y="Close Red (%)",title="   Close Red %",
                 labels={"YearMonth":"Mes"},template="plotly_dark")
    fig.add_scatter(x=monthly_closered["YearMonth"], y=monthly_closered["SMA_6"],
                    mode="lines", name="SMA", line=dict(width=3,color="#ff9933"))
    fig.update_layout(xaxis_tickangle=90,height=450)
    return fig


# FIGURA 2 – CLOSE RED (stack horizontal)
fig_2 = go.Figure()
fig_2.add_trace(
    go.Bar(
        x=[neg_pct],
        y=["Retorno"],
        width=0.48,
        orientation="h",
        marker=dict(color="#ef553b", line=dict(color="#aa3d2d", width=1.5)),
        name="Negativas",
        hovertemplate=("<b>Acciones negativas</b><br>" f"Cantidad: {neg_count}<br>" f"Porcentaje: {neg_pct}%" "<extra></extra>"),
    )
)
fig_2.add_trace(
    go.Bar(
        x=[pos_pct],
        y=["Retorno"],
        width=0.48,
        orientation="h",
        marker=dict(color="#00cc96", line=dict(color="#0f8a63", width=1.5)),
        name="Positivas",
        hovertemplate=("<b>Acciones positivas</b><br>" f"Cantidad: {pos_count}<br>" f"Porcentaje: {pos_pct}%" "<extra></extra>"),
    )
)
fig_2.update_layout(
    barmode="stack",
    template="plotly_dark",
    height=240,
    title=dict(text=f"Close Red — {neg_pct}%      |      Total Gaps Filtradas: {total}", x=0.5, xanchor="center", font=dict(size=18, color="white")),
    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=12)),
    margin=dict(t=60, l=20, r=20, b=60),
)
fig_2.update_xaxes(showticklabels=False, range=[0, 100])
fig_2.update_yaxes(showticklabels=False)


# FIGURA 2 – CLOSE RED PM (stack)
def crear_grafico_retornos_stack():
    fig_2_local = go.Figure()
    fig_2_local.add_trace(
        go.Bar(
            x=[neg_pct_1],
            y=["Retorno"],
            width=0.48,
            orientation="h",
            marker=dict(color="#ef553b", line=dict(color="#aa3d2d", width=1.5)),
            name="Negativas",
            hovertemplate=("<b>Acciones negativas</b><br>" f"Cantidad: {neg_count_1}<br>" f"Porcentaje: {neg_pct_1}%" "<extra></extra>"),
        )
    )
    fig_2_local.add_trace(
        go.Bar(
            x=[pos_pct_1],
            y=["Retorno"],
            width=0.48,
            orientation="h",
            marker=dict(color="#00cc96", line=dict(color="#0f8a63", width=1.5)),
            name="Positivas",
            hovertemplate=("<b>Acciones positivas</b><br>" f"Cantidad: {pos_count_1}<br>" f"Porcentaje: {pos_pct_1}%" "<extra></extra>"),
        )
    )
    fig_2_local.update_layout(
        barmode="stack",
        template="plotly_dark",
        height=450,
        title=dict(text=f"Fade PM > 15% — {neg_pct_1}%      |      Total Gaps Filtradas: {total_1}", x=0.5, xanchor="center", font=dict(size=18, color="white")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(t=60, l=20, r=20, b=60),
    )
    fig_2_local.update_xaxes(showticklabels=False, range=[0, 100])
    fig_2_local.update_yaxes(showticklabels=False)
    return fig_2_local


# FIGURA 3 – METRICA / MEDIA / MEDIANA (tabla)
fig_3 = go.Figure(
    data=[
        go.Table(
            header=dict(
                values=["<b>Métrica</b>", "<b>Media</b>", "<b>Mediana</b>"],
                fill_color="#1f1f2e",
                font=dict(color="white", size=14),
                align="left",
            ),
            cells=dict(
                values=[metrics, avg_values, median_values],
                fill_color="#11121A",
                align="left",
                font=dict(color="white", size=13),
                height=35,
            ),
        )
    ]
)
fig_3.update_layout(template="plotly_dark", height=350, margin=dict(t=20, b=20, l=20, r=20))


# FIGURA 4 – RETURN GAPPERS/MES
stocks_filtrados["Date"] = pd.to_datetime(stocks_filtrados["Date"])
stocks_filtrados["Year"] = stocks_filtrados["Date"].dt.year
stocks_filtrados["Month"] = stocks_filtrados["Date"].dt.month
monthly_return = stocks_filtrados.groupby(["Year", "Month"])["Day Return %"].mean().reset_index()
monthly_return["YearMonth"] = monthly_return["Year"].astype(str) + "-" + monthly_return["Month"].astype(str).str.zfill(2)
monthly_return["Return (%)"] = round(monthly_return["Day Return %"] * 100, 2)

fig_4 = px.bar(
    monthly_return,
    x="YearMonth",
    y="Return (%)",
    title="   Return gaps/mes",
    labels={"YearMonth": "Mes", "Return (%)": "Retorno promedio (%)"},
    template="plotly_dark",
)
fig_4.update_layout(xaxis_tickangle=90, height=450)


# -------------------------------------------------------------
# DISTRIBUTIONS / TIME / PM / RTH
# -------------------------------------------------------------
def grafico_highspike_distribution():
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 9999]
    labels = ["0% - 10% ", "10% - 20% ", "20% - 30% ", "30% - 40% ", "40% - 50% ", "50% - 60% ", "60% - 70% ", "70% - 80% ", "80% - 90% ", "90% - 100% ", ">100% "]

    df = stocks_filtrados.copy()
    df["HS_bin"] = pd.cut(df["High Spike %"] * 100, bins=bins, labels=labels, include_lowest=True)
    distrib = df["HS_bin"].value_counts().reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(
        distrib,
        x="Acciones",
        y="Rango",
        orientation="h",
        labels={"Acciones": "Gaps", "Rango": ""},
        template="plotly_dark",
        title="HIGH SPIKE DISTRIBUTION",
    )
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center", yanchor="top", pad=dict(t=10)), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_lowspike_distribution():
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 9999]
    labels = ["0% - 10% ", "10% - 20% ", "20% - 30% ", "30% - 40% ", "40% - 50% ", "50% - 60% ", "60% - 70% ", "70% - 80% ", "80% - 90% ", "90% - 100% ", "=100% "]

    df = stocks_filtrados.copy()
    df["LS_abs"] = (df["Low Spike %"] * -100).abs()
    df["LS_bin"] = pd.cut(df["LS_abs"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["LS_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", labels={"Acciones": "Gaps", "Rango": ""}, template="plotly_dark", title="LOW SPIKE DISTRIBUTION")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center", yanchor="top", pad=dict(t=12)), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_lod_distribution():
    df = stocks_filtrados.copy()
    df["LOD_dt"] = pd.to_datetime(df["LOD Time"], format="%H:%M", errors="coerce")
    df = df.dropna(subset=["LOD_dt"])
    df["minutos"] = (df["LOD_dt"].dt.hour * 60 + df["LOD_dt"].dt.minute) - (9 * 60 + 30)
    bins = list(range(0, 390 + 30, 30))
    labels = [
        "09:30-10:00 ",
        "10:00-10:30 ",
        "10:30-11:00 ",
        "11:00-11:30 ",
        "11:30-12:00 ",
        "12:00-12:30 ",
        "12:30-13:00 ",
        "13:00-13:30 ",
        "13:30-14:00 ",
        "14:00-14:30 ",
        "14:30-15:00 ",
        "15:00-15:30 ",
        "15:30-16:00 ",
    ]
    df["LOD_bin"] = pd.cut(df["minutos"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["LOD_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", title="LOD TIME DISTRIBUTION", labels={"Acciones": "Gaps", "Rango": ""}, template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_hod_distribution():
    df = stocks_filtrados.copy()
    df["HOD_dt"] = pd.to_datetime(df["HOD Time"], format="%H:%M", errors="coerce")
    df = df.dropna(subset=["HOD_dt"])
    df["minutos"] = (df["HOD_dt"].dt.hour * 60 + df["HOD_dt"].dt.minute) - (9 * 60 + 30)
    bins = list(range(0, 390 + 30, 30))
    labels = [
        "09:30-10:00 ",
        "10:00-10:30 ",
        "10:30-11:00 ",
        "11:00-11:30 ",
        "11:30-12:00 ",
        "12:00-12:30 ",
        "12:30-13:00 ",
        "13:00-13:30 ",
        "13:30-14:00 ",
        "14:00-14:30 ",
        "14:30-15:00 ",
        "15:00-15:30 ",
        "15:30-16:00 ",
    ]
    df["HOD_bin"] = pd.cut(df["minutos"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["HOD_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", title="HOD TIME DISTRIBUTION", labels={"Acciones": "Gaps", "Rango": ""}, template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_return_distribution():
    df = stocks_filtrados.copy()
    df["Return_pct"] = df["Day Return %"] * 100
    bins = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100, 9999]
    labels = ["-100% a -80%", "-80% a -60%", "-60% a -40%", "-40% a -20%", "-20% a 0%", "0% a 20%", "20% a 40%", "40% a 60%", "60% a 80%", "80% a 100%", ">100%"]
    df["Return_bin"] = pd.cut(df["Return_pct"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["Return_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", labels={"Acciones": "Gaps", "Rango": ""}, title="RETURN DISTRIBUTION", template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels))
    return fig


def grafico_gap_size_distribution():
    df = stocks_filtrados.copy()
    df["Gap_pct"] = df["Open Gap %"] * 100
    bins = [0, 40, 60, 80, 100, 150, 200, 250, 300, 400, 99999]
    labels = ["0% - 40%", "40% - 60%", "60% - 80%", "80% - 100%", "100% - 150%", "150% - 200%", "200% - 250%", "250% - 300%", "300% - 400%", ">400%"]
    df["Gap_bin"] = pd.cut(df["Gap_pct"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["Gap_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", labels={"Acciones": "Gaps", "Rango": ""}, title="GAP SIZE DISTRIBUTION", template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_fade_distribution():
    df = stocks_filtrados.copy()
    df["Fade_pct"] = df["RTH Fade to Close %"] * 100
    bins = [-100, -90, -80, -70, -60, -50, -40, -30, -20, -10, 0]
    labels = ["-100% a -90%", "-90% a -80%", "-80% a -70%", "-70% a -60%", "-60% a -50%", "-50% a -40%", "-40% a -30%", "-30% a -20%", "-20% a -10%", "-10% a 0%"]
    df["Fade_bin"] = pd.cut(df["Fade_pct"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["Fade_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", labels={"Acciones": "Gaps", "Rango": ""}, title="RTH FADE TO CLOSE DISTRIBUTION", template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels))
    return fig


# -------------------------------------------------------------
# AVG CHANGE FROM OPEN (INTRADÍA) - usa intraday_df cargado arriba
# -------------------------------------------------------------
def grafico_intradia():
    if intraday_df.empty:
        # Si no pudimos descargar el CSV, devolvemos una figura vacía informativa
        fig = go.Figure()
        fig.update_layout(title="Data 15min no disponible", template="plotly_dark", height=300)
        return fig

    # Trabaja con copia local para no mutar intraday_df global
    df = intraday_df.copy()

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce").dt.date

    # Normaliza bar_time_local
    try:
        times = pd.to_datetime(df["bar_time_local"], format="%H:%M:%S", errors="raise")
        df["bar_time_local"] = times.dt.strftime("%H:%M")
    except Exception:
        times = pd.to_datetime(df["bar_time_local"], format="%H:%M", errors="coerce")
        df["bar_time_local"] = times.dt.strftime("%H:%M")

    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")

    RTH = [
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
    ]
    df = df[df["bar_time_local"].isin(RTH)].copy()

    sf = stocks_filtrados.copy()
    if "Ticker" in sf.columns and "ticker" not in sf.columns:
        sf = sf.rename(columns={"Ticker": "ticker"})

    sf["Date"] = pd.to_datetime(sf["Date"]).dt.date
    allowed = set(zip(sf["ticker"].astype(str), sf["Date"]))

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df.apply(lambda r: (str(r["ticker"]), r["date"]) in allowed, axis=1)].copy()

    open0930 = df[df["bar_time_local"] == "09:30"][["ticker", "date", "open"]].rename(columns={"open": "open_0930"})
    df = df.merge(open0930, on=["ticker", "date"], how="left")
    df = df.dropna(subset=["open_0930"])

    df["chg_from_open_pct"] = (df["open"] - df["open_0930"]) / df["open_0930"] * 100
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["month"] = pd.to_datetime(df["date"]).dt.month

    grp = df.groupby(["year", "month", "bar_time_local"], as_index=False)["chg_from_open_pct"].mean()

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1,
        cols=12,
        subplot_titles=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        shared_yaxes=True,
        horizontal_spacing=0.0001,
    )

    years = sorted(grp["year"].unique())
    time_order = RTH

    palette = {2022: "#4C78A8", 2023: "#F6C85F", 2024: "#E45756", 2025: "#ff8000"}
    default_color = "#7FB3FF"

    col_width = 1.0 / 12

    for year in years:
        df_y = grp[grp["year"] == year]
        for col_idx in range(1, 13):
            m = col_idx
            df_m = df_y[df_y["month"] == m].copy()
            df_m = df_m.set_index("bar_time_local").reindex(time_order).reset_index()
            yvals = df_m["chg_from_open_pct"].values

            fig.add_trace(
                go.Scatter(
                    x=time_order,
                    y=yvals,
                    mode="lines+markers",
                    name=str(year),
                    marker=dict(size=2),
                    line=dict(width=2, color=palette.get(year, default_color)),
                    legendgroup=str(year),
                    showlegend=(col_idx == 1),
                ),
                row=1,
                col=col_idx,
            )

            fig.update_xaxes(row=1, col=col_idx, tickvals=time_order[::4], ticktext=time_order[::4], tickangle=45, showgrid=False)

            if col_idx < 12:
                line_pos = col_idx * col_width
                fig.add_shape(type="line", xref="paper", yref="paper", x0=line_pos, y0=0.0, x1=line_pos, y1=1.0, line=dict(color="white", width=0.1, dash="dot"))

    fig.update_layout(template="plotly_dark", title="     AVG CHANGE FROM OPEN", height=500, legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1), margin=dict(l=40, r=20, t=100, b=60))
    fig.update_yaxes(ticksuffix="%")
    return fig


# -------------------------------------------------------------
# MULTIFRAME & RELATED
# -------------------------------------------------------------
def grafico_multiframe_returns():
    df = stocks_filtrados.copy()
    columnas = ["M1 Return %", "M5 Return %", "M15 Return %", "M30 Return %", "M60 Return %", "M120 Return %", "M180 Return %", "Day Return %"]
    labels = ["1 min Return", "5 min Return", "15 min Return", "30 min Return", "60 min Return", "120 min Return", "180 min Return", "Return"]
    valores = [(df[col] * 100).mean() for col in columnas]
    valores = valores[::-1]
    labels = labels[::-1]
    colores = ["#ef553b" if v < 0 else "#00cc96" for v in valores]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=valores, y=labels, orientation="h", marker=dict(color=colores), textposition="outside"))
    fig.update_layout(template="plotly_dark", title="   Multi-Timeframe Return %", height=450, xaxis=dict(ticksuffix="%"), margin=dict(l=60, r=20, t=60, b=20))
    return fig


def grafico_multiframe_highspike():
    df = stocks_filtrados.copy()
    columnas = ["M1 High Spike %", "M5 High Spike %", "M15 High Spike %", "M30 High Spike %", "M60 High Spike %", "M120 High Spike %", "M180 High Spike %"]
    labels = ["1 min High Spike ", "5 min High Spike ", "15 min High Spike ", "30 min High Spike ", "60 min High Spike ", "120 min High Spike ", "180 min High Spike "]
    valores = [(df[col] * 100).mean() for col in columnas]
    valores = valores[::-1]
    labels = labels[::-1]
    colores = ["#ef553b" if v < 0 else "#00cc96" for v in valores]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=valores, y=labels, orientation="h", marker=dict(color=colores), textposition="outside"))
    fig.update_layout(template="plotly_dark", title="   Multi-Timeframe High Spike %", height=450, xaxis=dict(ticksuffix="%"), margin=dict(l=60, r=20, t=60, b=20))
    return fig


def grafico_multiframe_lowspike():
    df = stocks_filtrados.copy()
    columnas = ["M1 Low Spike %", "M5 Low Spike %", "M15 Low Spike %", "M30 Low Spike %", "M60 Low Spike %", "M120 Low Spike %", "M180 Low Spike %"]
    labels = ["1 min Low Spike ", "5 min Low Spike ", "15 min Low Spike ", "30 min Low Spike ", "60 min Low Spike ", "120 min Low Spike ", "180 min Low Spike "]
    valores = [(df[col] * 100).mean() for col in columnas]
    valores = valores[::-1]
    labels = labels[::-1]
    colores = ["#ef553b" if v < 0 else "#00cc96" for v in valores]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=valores, y=labels, orientation="h", marker=dict(color=colores), textposition="outside"))
    fig.update_layout(template="plotly_dark", title="   Multi-Timeframe Low Spike %", height=450, xaxis=dict(ticksuffix="%"), margin=dict(l=60, r=20, t=60, b=20))
    return fig


# PRICE RANGE
def grafico_price_range_distribution():
    df = stocks_filtrados.copy()
    bins = [0, 1, 3, 5, 10, 9999]
    labels = ["0 - 1 $ ", "1 - 3 $ ", "3 - 5 $ ", "5 - 10 $ ", "> 10 $ "]
    df["PriceBin"] = pd.cut(df["Open Price"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["PriceBin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", labels={"Acciones": "Gaps", "Rango": ""}, title="PRICE RANGE DISTRIBUTION", template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, margin=dict(l=80, r=30, t=70, b=40), title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_gaps_por_ano():
    df = stocks_filtrados.copy()
    df["Year"] = pd.to_datetime(df["Date"]).dt.year
    conteo = df.groupby("Year").size().reset_index(name="Gaps")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=conteo["Year"], y=conteo["Gaps"], marker=dict(color="#00cc96")))
    fig.update_layout(template="plotly_dark", title="   Number of Gaps by Year", height=450, margin=dict(l=40, r=20, t=60, b=40))
    return fig


def grafico_multiframe_return_to_close():
    df = stocks_filtrados.copy()
    columnas = ["Return % From M1 to Close", "Return % From M5 to Close", "Return % From M15 to Close", "Return % From M30 to Close", "Return % From M60 to Close", "Return % From M120 to Close", "Return % From M180 to Close"]
    labels = ["From M1 to close", "From M5 to close", "From M15 to close", "From M30 to close", "From M60 to close", "From M120 to close", "From M180 to close"]
    valores = [(df[col] * 100).mean() for col in columnas]
    valores = valores[::-1]
    labels = labels[::-1]
    colores = ["#ef553b" if v < 0 else "#00cc96" for v in valores]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=valores, y=labels, orientation="h", marker=dict(color=colores), textposition="outside"))
    fig.update_layout(template="plotly_dark", title="   Multi-Timeframe Return % to close", height=450, xaxis=dict(ticksuffix="%"), margin=dict(l=60, r=20, t=60, b=20))
    return fig


def grafico_multiframe_vwap_distance():
    df = stocks_filtrados.copy()
    vwap_cols = {"VWAP Open": "VWAP at Open", "VWAP 5m": "VWAP at M5", "VWAP 15m": "VWAP at M15", "VWAP 30m": "VWAP at M30", "VWAP 60m": "VWAP at M60", "VWAP 90m": "VWAP at M90", "VWAP 120m": "VWAP at M120", "VWAP 180m": "VWAP at M180"}
    price_cols = {"VWAP Open": "Open Price", "VWAP 5m": "M5 Price", "VWAP 15m": "M15 Price", "VWAP 30m": "M30 Price", "VWAP 60m": "M60 Price", "VWAP 90m": "M90 Price", "VWAP 120m": "M120 Price", "VWAP 180m": "M180 Price"}

    labels = list(vwap_cols.keys())
    distancias = []
    for label in labels:
        vwap_col = vwap_cols[label]
        price_col = price_cols[label]
        # calculo seguro por si hay NaNs
        dist = (pd.to_numeric(df.get(price_col, pd.Series(dtype=float)), errors="coerce") - pd.to_numeric(df.get(vwap_col, pd.Series(dtype=float)), errors="coerce")) / pd.to_numeric(df.get(vwap_col, pd.Series(dtype=float)), errors="coerce") * 100
        distancias.append(np.nanmean(dist.values))

    distancias = distancias[::-1]
    labels = labels[::-1]
    colores = ["#00cc96" if v >= 0 else "#ef553b" for v in distancias]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=distancias, y=labels, orientation="h", marker=dict(color=colores), textposition="outside"))
    fig.update_layout(template="plotly_dark", title="   Distance VWAP from Price %", height=450, xaxis=dict(title="", ticksuffix="%"), margin=dict(l=70, r=40, t=60, b=40))
    return fig


# PMH / PM functions
def grafico_pm_high_distribution(stocks_df=None):
    if stocks_df is None:
        df = stocks_filtrados.copy()
    else:
        df = stocks_df.copy()

    df["PM_High_dt"] = pd.to_datetime(df["PM High Time"], format="%H:%M", errors="coerce")
    df = df.dropna(subset=["PM_High_dt"])
    start_pm_minutes = 4 * 60
    df["minutos"] = (df["PM_High_dt"].dt.hour * 60 + df["PM_High_dt"].dt.minute) - start_pm_minutes
    max_pm_minutes = 330
    bins = list(range(0, max_pm_minutes + 30, 30))
    labels = ["04:00-04:30 ", "04:30-05:00 ", "05:00-05:30 ", "05:30-06:00 ", "06:00-06:30 ", "06:30-07:00 ", "07:00-07:30 ", "07:30-08:00 ", "08:00-08:30 ", "08:30-09:00 ", "09:00-09:30 "]
    df["PM_High_bin"] = pd.cut(df["minutos"], bins=bins, labels=labels, include_lowest=True, right=False)
    distrib = df["PM_High_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", title="PM HIGH TIME DISTRIBUTION", labels={"Acciones": "Gaps", "Rango": ""}, template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_pmh_gap_distribution():
    df = stocks_filtrados.copy()
    df["PMH_gap_pct"] = df["PMH Gap %"] * 100
    bins = [0, 40, 60, 80, 100, 150, 200, 250, 300, 400, 99999]
    labels = ["0% - 40%", "40% - 60%", "60% - 80%", "80% - 100%", "100% - 150%", "150% - 200%", "200% - 250%", "250% - 300%", "300% - 400%", ">400%"]
    df["PMH_gap_bin"] = pd.cut(df["PMH_gap_pct"], bins=bins, labels=labels, include_lowest=True)
    distrib = df["PMH_gap_bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango", "Acciones"]
    distrib = distrib.iloc[::-1]

    fig = px.bar(distrib, x="Acciones", y="Rango", orientation="h", title="PMH GAP DISTRIBUTION", labels={"Acciones": "Gaps", "Rango": ""}, template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_pmh_fade_distribution():
    df = stocks_filtrados.copy()
    df["PMH_Fade_Pct_Scaled"] = df["PMH Fade to Open %"] * 100
    df = df.dropna(subset=["PMH_Fade_Pct_Scaled"])
    bins = [-100, -60, -50, -40, -30, -25, -20, -15, -10, -5, 0]
    labels = ["-100% a -60% ", "-60% a -50% ", "-50% a -40% ", "-40% a -30% ", "-30% a -25% ", "-25% a -20% ", "-20% a -15% ", "-15% a -10% ", "-10% a -5% ", "-5% a 0% "]
    df["PMH_Fade_Bin"] = pd.cut(df["PMH_Fade_Pct_Scaled"], bins=bins, labels=labels, include_lowest=True, right=False)
    distrib = df["PMH_Fade_Bin"].value_counts().reindex(labels).reset_index()
    distrib.columns = ["Rango (%)", "Acciones"]

    fig = px.bar(distrib, x="Acciones", y="Rango (%)", orientation="h", title="PMH FADE TO OPEN DISTRIBUTION ", labels={"Acciones": "Gaps", "Rango (%)": ""}, template="plotly_dark")
    fig.update_traces(marker_color="#69b3ff")
    fig.update_layout(height=450, title=dict(x=0.5, xanchor="center"), yaxis=dict(categoryorder="array", categoryarray=labels[::-1]))
    return fig


def grafico_pmh_gap_value():
    fig = px.bar(monthly_pmh_gap, x="YearMonth", y="Gap (%)", title="PMH Gap Value %", labels={"YearMonth": "Mes", "Gap (%)": "Gap medio (%)"}, template="plotly_dark")
    fig.add_scatter(x=monthly_pmh_gap["YearMonth"], y=monthly_pmh_gap["SMA_6"], mode="lines", name="SMA 6 meses", line=dict(color="#ff9933", width=3))
    fig.update_layout(xaxis_tickangle=90, height=450, coloraxis_showscale=False, title=dict(x=0.5, xanchor="center"))
    return fig


def grafico_pmh_fade_value():
    fig = px.bar(monthly_fade, x="YearMonth", y="Fade (%)", title="PMH Fade to Open %", labels={"YearMonth": "Mes", "Fade (%)": "Fade medio (%)"}, template="plotly_dark")
    fig.add_scatter(x=monthly_fade["YearMonth"], y=monthly_fade["SMA_6"], mode="lines", name="SMA 6M", line=dict(color="#ffaa00", width=3))
    fig.update_layout(xaxis_tickangle=90, height=450, margin=dict(l=40, r=20, t=60, b=50),title=dict(x=0.5, xanchor="center"))
    return fig


def grafico_pmh_volume_mes():
    fig = px.bar(monthly_pmv, x="YearMonth", y="PMH_Volume_Total", title="Total Premarket Volume", labels={"YearMonth": "Mes", "PMH_Volume_Total": ""}, template="plotly_dark")
    fig.add_scatter(x=monthly_pmv["YearMonth"], y=monthly_pmv["SMA_6"], mode="lines", name="SMA 6 meses", line=dict(color="#ff9933", width=3))
    fig.update_layout(height=450, xaxis_tickangle=90, margin=dict(l=40, r=20, t=60, b=40), title=dict(x=0.5, xanchor="center"))
    return fig


def grafico_rth_fade_to_close_mes():
    fig = px.bar(monthly_rth_fade, x="YearMonth", y="Fade (%)", title="   RTH Fade to Close", labels={"YearMonth": "Mes", "Fade (%)": "Fade medio (%)"}, template="plotly_dark")
    fig.add_scatter(x=monthly_rth_fade["YearMonth"], y=monthly_rth_fade["SMA_6"], mode="lines", name="SMA 6", line=dict(color="#ff9933", width=3))
    fig.update_layout(height=450, xaxis_tickangle=90, margin=dict(l=40, r=20, t=60, b=40))
    return fig

def grafico_premarket():
    if intraday_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Data 15min no disponible", template="plotly_dark", height=300)
        return fig

    df = intraday_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    try:
        times = pd.to_datetime(df["bar_time_local"], format="%H:%M:%S", errors="raise")
        df["bar_time_local"] = times.dt.strftime("%H:%M")
    except:
        times = pd.to_datetime(df["bar_time_local"], format="%H:%M", errors="coerce")
        df["bar_time_local"] = times.dt.strftime("%H:%M")

    df["open"] = pd.to_numeric(df["open"], errors="coerce")

    PM = [
        "04:00","04:15","04:30","04:45",
        "05:00","05:15","05:30","05:45",
        "06:00","06:15","06:30","06:45",
        "07:00","07:15","07:30","07:45",
        "08:00","08:15","08:30","08:45",
        "09:00","09:15","09:30"
    ]

    df = df[df["bar_time_local"].isin(PM)].copy()

    sf = stocks_filtrados.copy()
    if "Ticker" in sf.columns and "ticker" not in sf.columns:
        sf = sf.rename(columns={"Ticker": "ticker"})
    sf["Date"] = pd.to_datetime(sf["Date"]).dt.date

    allowed = set(zip(sf["ticker"].astype(str), sf["Date"]))
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df.apply(lambda r: (str(r["ticker"]), r["date"]) in allowed, axis=1)]

    open0930 = df[df["bar_time_local"] == "09:30"][["ticker","date","open"]].rename(columns={"open":"open_0930"})
    df = df.merge(open0930, on=["ticker","date"], how="left")
    df = df.dropna(subset=["open_0930"])

    df["chg_from_open_pct"] = (df["open"] - df["open_0930"]) / df["open_0930"] * 100
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["month"] = pd.to_datetime(df["date"]).dt.month

    grp = df.groupby(["year","month","bar_time_local"], as_index=False)["chg_from_open_pct"].mean()

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1, cols=12,
        subplot_titles=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        shared_yaxes=True,
        horizontal_spacing=0.0001
    )

    years = sorted(grp["year"].unique())
    time_order = PM

    palette = {2022:"#4C78A8", 2023:"#F6C85F", 2024:"#E45756", 2025:"#ff8000"}
    default_color = "#7FB3FF"
    col_width = 1/12

    for year in years:
        df_y = grp[grp["year"] == year]
        for col_idx in range(1,13):
            m = col_idx
            df_m = df_y[df_y["month"] == m].copy()
            df_m = df_m.set_index("bar_time_local").reindex(time_order).reset_index()
            yvals = df_m["chg_from_open_pct"].values

            fig.add_trace(
                go.Scatter(
                    x=time_order,
                    y=yvals,
                    mode="lines+markers",
                    marker=dict(size=2),
                    line=dict(width=2, color=palette.get(year, default_color)),
                    name=str(year),
                    legendgroup=str(year),
                    showlegend=(col_idx == 1)
                ),
                row=1, col=col_idx
            )

            fig.update_xaxes(
                row=1, col=col_idx,
                tickvals=time_order[::4],
                ticktext=time_order[::4],
                tickangle=45,
                showgrid=False
            )

            if col_idx < 12:
                fig.add_shape(
                    type="line",
                    xref="paper", yref="paper",
                    x0=col_idx*col_width, y0=0,
                    x1=col_idx*col_width, y1=1,
                    line=dict(color="white", width=0.1, dash="dot")
                )

    fig.update_layout(
        template="plotly_dark",
        title="     AVG CHANGE FROM OPEN — PRE-MARKET",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=100, b=60)
    )
    fig.update_yaxes(ticksuffix="%")
    return fig