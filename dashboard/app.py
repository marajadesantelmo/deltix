"""
app.py — Dashboard de métricas del Bot Deltix.

Uso:
    streamlit run dashboard/app.py
    (desde la raíz del proyecto deltix/)
"""

import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta, date

# ── Configuración de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Deltix — Métricas",
    page_icon="🦫",
    layout="wide",
)

# ── Paleta y estilos ──────────────────────────────────────────────────────────

# Colores distintos para cada funcionalidad
FEATURE_COLORS = {
    "🚢 Colectivas":    "#5a9e47",
    "⚡ Clima/Mareas":  "#3b9dc4",
    "📅 Agenda":        "#e0a020",
    "😂 Memes":         "#c45a8a",
    "🤖 LLM":           "#9b5fc0",
    "🛒 Almaceneras":   "#3bbdaa",
    "💬 Social":        "#6b9e6b",
    "⚠️ LLM bloqueado": "#e07a30",
    "❌ LLM error":     "#c44040",
}

# Transparente para charts en dark mode
TRANSP = "rgba(0,0,0,0)"
GRID   = "rgba(255,255,255,0.07)"
TEXT   = "#c8e6c0"

st.markdown("""
<style>
/* KPI cards */
.kpi-card {
    background: linear-gradient(135deg, #2a4a2a 0%, #2f5230 100%);
    border: 1px solid #3e6e3e;
    border-radius: 12px;
    padding: 1.1rem 1rem 0.9rem;
    text-align: center;
}
.kpi-label  { font-size: 0.7rem; color: #7ab87a; font-weight: 700;
              text-transform: uppercase; letter-spacing: .08em; }
.kpi-value  { font-size: 2.1rem; font-weight: 800; color: #e8f5e2;
              line-height: 1.1; margin: 2px 0; }
.kpi-sub    { font-size: 0.72rem; color: #7ab87a; }
.kpi-trend-up   { color: #5fbf5f; font-size: 0.78rem; font-weight: 600; }
.kpi-trend-down { color: #bf5f5f; font-size: 0.78rem; font-weight: 600; }
.kpi-trend-neu  { color: #aaa;    font-size: 0.78rem; }

/* Section headers */
h2 { border-bottom: 2px solid #2e4e2e; padding-bottom: .3rem; }

/* Sidebar cleanup */
section[data-testid="stSidebar"] { background: #162a16; }

/* Expander */
details summary { font-weight: 600; }

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Rutas ─────────────────────────────────────────────────────────────────────

ROOT           = Path(__file__).parent.parent
CSV_PATH       = ROOT / "web_interactions.csv"
TIMESTAMP_FILE = Path(__file__).parent / ".last_sync"
SYNC_LOG       = Path(__file__).parent / "sync.log"

# ── Carga de datos ────────────────────────────────────────────────────────────

IS_CLOUD = not CSV_PATH.exists()

@st.cache_data(ttl=3600)
def load_data(pa_token: str = "", pa_user: str = "facundol") -> pd.DataFrame:
    """Carga datos. Puro: no llama a st.* para compatibilidad con st.cache_data."""
    if pa_token:   # cloud: descarga desde PythonAnywhere API
        url = (
            f"https://www.pythonanywhere.com/api/v0/user/{pa_user}"
            f"/files/path/home/{pa_user}/deltix/web_interactions.csv"
        )
        resp = requests.get(url, headers={"Authorization": f"Token {pa_token}"}, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), parse_dates=["timestamp"])
    else:          # local: lee desde disco
        df = pd.read_csv(str(CSV_PATH), parse_dates=["timestamp"])
    df["date"]    = df["timestamp"].dt.date
    df["hour"]    = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.day_name()
    return df

# Validar secretos y cargar datos (st.error/st.stop van FUERA de @st.cache_data)
if IS_CLOUD:
    _pa_token = st.secrets.get("PA_API_TOKEN", "")
    _pa_user  = st.secrets.get("PA_USERNAME", "facundol")
    if not _pa_token:
        st.error("⚠️ Configurá `PA_API_TOKEN` en Streamlit Secrets (Settings → Secrets).")
        st.stop()
    df_full = load_data(_pa_token, _pa_user)
else:
    df_full = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

if (ROOT / "bot_icon.png").exists():
    st.sidebar.image(str(ROOT / "bot_icon.png"), width=80)
st.sidebar.title("Deltix Dashboard")
st.sidebar.markdown("---")

min_date = df_full["date"].min()
max_date = df_full["date"].max()

date_range = st.sidebar.date_input(
    "Período de análisis",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

st.sidebar.markdown("---")

# Sync status
if IS_CLOUD:
    st.sidebar.markdown("☁️ **Fuente:** PythonAnywhere API")
    if st.sidebar.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
else:
    if TIMESTAMP_FILE.exists():
        last_sync = TIMESTAMP_FILE.read_text(encoding="utf-8").strip()
        st.sidebar.markdown(f"🔄 **Último sync**  \n`{last_sync}`")
    else:
        st.sidebar.markdown("🔄 Datos locales (sin sync)")

    if st.sidebar.button("🔄 Sincronizar ahora", use_container_width=True):
        sync_script = Path(__file__).parent / "sync_csv.py"
        with st.spinner("Descargando desde PythonAnywhere..."):
            ret = os.system(f'"{sync_script}" 2>&1')
        st.cache_data.clear()
        st.rerun()

    # Log viewer (colapsado)
    if SYNC_LOG.exists():
        with st.sidebar.expander("Log de sync"):
            lines = SYNC_LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            st.code("\n".join(lines[-15:]), language=None)

# ── Filtrar datos ─────────────────────────────────────────────────────────────

if len(date_range) == 2:
    start, end = date_range
    df = df_full[(df_full["date"] >= start) & (df_full["date"] <= end)].copy()
else:
    df = df_full.copy()
    start, end = min_date, max_date

# Período anterior (misma duración, para tendencias)
n_days = max((end - start).days, 1)
prev_end   = start - timedelta(days=1)
prev_start = prev_end - timedelta(days=n_days - 1)
df_prev = df_full[
    (df_full["date"] >= prev_start) & (df_full["date"] <= prev_end)
].copy()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Bot Deltix — Dashboard de Métricas")
period_str = f"{start} → {end}" if not df.empty else "sin datos"
st.caption(f"Período: **{period_str}** &nbsp;•&nbsp; Fuente: `web_interactions.csv`")

# ── Helpers trend ─────────────────────────────────────────────────────────────

def trend_html(current, previous, fmt=".0f", suffix=""):
    if previous == 0:
        return '<span class="kpi-trend-neu">— sin ref.</span>'
    delta = current - previous
    pct   = delta / previous * 100
    arrow = "▲" if delta > 0 else "▼"
    cls   = "kpi-trend-up" if delta >= 0 else "kpi-trend-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}% vs período anterior</span>'

def kpi(col, label, value_str, sub="", trend_html_str=""):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value_str}</div>
        <div class="kpi-sub">{sub}</div>
        <div style="margin-top:4px">{trend_html_str}</div>
    </div>""", unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────

total     = len(df)
prev_total = len(df_prev)
n_sess    = df["session_id"].nunique()
prev_sess = df_prev["session_id"].nunique()

type_counts = df["response_type"].value_counts()
llm_ok      = int(type_counts.get("llm", 0))
llm_blocked = int(type_counts.get("llm_blocked", 0))
llm_error   = int(type_counts.get("llm_error", 0))
total_llm   = llm_ok + llm_blocked + llm_error
pct_llm     = total_llm / total * 100 if total else 0
error_rate  = (llm_blocked + llm_error) / total * 100 if total else 0

sess_lens    = df.groupby("session_id").size()
avg_len      = sess_lens.mean() if len(sess_lens) else 0
power_users  = int((sess_lens >= 10).sum())
bounces      = int((sess_lens == 1).sum())

prev_pct_llm = (df_prev["response_type"].isin(["llm","llm_blocked","llm_error"]).sum()
                / len(df_prev) * 100) if len(df_prev) else 0

# ── KPI row ───────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "Interacciones",
    f"{total:,}".replace(",", "."),
    f"{n_sess} sesiones",
    trend_html(total, prev_total))
kpi(c2, "Sesiones únicas",
    str(n_sess),
    f"{bounces} rebotes (1 msg)",
    trend_html(n_sess, prev_sess))
kpi(c3, "Prom. msgs / sesión",
    f"{avg_len:.1f}",
    f"{power_users} power users (10+)")
kpi(c4, "Ratio LLM",
    f"{pct_llm:.1f}%",
    "umbral saludable < 15%",
    trend_html(pct_llm, prev_pct_llm))
kpi(c5, "Tasa de error",
    f"{error_rate:.2f}%",
    f"{llm_blocked} blocked + {llm_error} errores")

st.markdown("<br>", unsafe_allow_html=True)

# ── Fila 1: barras + dona ─────────────────────────────────────────────────────

col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown("### Interacciones y sesiones por día")
    daily_msgs = df.groupby("date").size().reset_index(name="interacciones")
    daily_sess = df.groupby("date")["session_id"].nunique().reset_index(name="sesiones")
    daily = daily_msgs.merge(daily_sess, on="date")
    daily["date_str"] = daily["date"].astype(str)

    fig = go.Figure()

    # Barras — interacciones (eje izquierdo)
    fig.add_trace(go.Bar(
        x=daily["date_str"], y=daily["interacciones"],
        name="Interacciones",
        marker=dict(
            color=daily["interacciones"],
            colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
            line=dict(width=0),
        ),
        yaxis="y1",
        hovertemplate="<b>%{x}</b><br>%{y} interacciones<extra></extra>",
    ))

    # Línea — sesiones (eje derecho)
    fig.add_trace(go.Scatter(
        x=daily["date_str"], y=daily["sesiones"],
        name="Sesiones",
        mode="lines+markers",
        line=dict(color="#3b9dc4", width=2.5, shape="spline"),
        marker=dict(color="#3b9dc4", size=7, line=dict(color="#0e1a0e", width=1.5)),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>%{y} sesiones<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=50, t=10, b=0), height=270,
        xaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        yaxis=dict(
            title="Interacciones", title_font=dict(color="#7ed957", size=11),
            showgrid=True, gridcolor=GRID, color="#7ed957", zeroline=False,
        ),
        yaxis2=dict(
            title="Sesiones", title_font=dict(color="#3b9dc4", size=11),
            overlaying="y", side="right",
            color="#3b9dc4", zeroline=False, showgrid=False,
        ),
        legend=dict(
            orientation="h", x=0, y=1.08,
            font=dict(color=TEXT, size=11),
            bgcolor=TRANSP,
        ),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.markdown("### Funcionalidades usadas")
    type_map = {
        "colectivas":   "🚢 Colectivas",
        "quick":        "⚡ Clima/Mareas",
        "agenda":       "📅 Agenda",
        "memes":        "😂 Memes",
        "llm":          "🤖 LLM",
        "almaceneras":  "🛒 Almaceneras",
        "social":       "💬 Social",
        "llm_blocked":  "⚠️ LLM bloqueado",
        "llm_error":    "❌ LLM error",
    }
    tc = (type_counts
          .rename(index=type_map)
          .loc[lambda s: s.index.isin(type_map.values())]
          .reset_index())
    tc.columns = ["label", "count"]
    colors = [FEATURE_COLORS.get(l, "#888") for l in tc["label"]]

    fig2 = go.Figure(go.Pie(
        labels=tc["label"], values=tc["count"],
        marker=dict(colors=colors, line=dict(color="#0e1a0e", width=2)),
        hole=0.45,
        textinfo="percent",
        textfont=dict(size=12, color="white"),
        hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
    ))
    fig2.update_layout(
        paper_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=260,
        legend=dict(font=dict(size=11, color=TEXT), bgcolor=TRANSP,
                    orientation="v", x=1, y=0.5),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Fila 2: actividad horaria + top mensajes ─────────────────────────────────

col_h, col_top = st.columns([3, 2])

with col_h:
    st.markdown("### Actividad por hora del día")
    hourly = df.groupby("hour").size().reindex(range(24), fill_value=0).reset_index()
    hourly.columns = ["hour", "count"]
    peak_h = int(hourly.loc[hourly["count"].idxmax(), "hour"])

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=hourly["hour"], y=hourly["count"],
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(90,158,71,0.18)",
        line=dict(color="#7ed957", width=2.5, shape="spline"),
        marker=dict(
            color=["#e07a30" if h == peak_h else "#5a9e47" for h in hourly["hour"]],
            size=[10 if h == peak_h else 5 for h in hourly["hour"]],
        ),
        hovertemplate="<b>%{x}h</b>: %{y} msgs<extra></extra>",
    ))
    fig3.add_annotation(
        x=peak_h, y=int(hourly.loc[hourly["hour"]==peak_h, "count"].values[0]),
        text=f"Pico: {peak_h}h",
        showarrow=True, arrowhead=2,
        font=dict(color="#e07a30", size=12),
        arrowcolor="#e07a30",
        bgcolor="#1a2e1a", bordercolor="#e07a30",
        ay=-30,
    )
    fig3.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=280,
        xaxis=dict(showgrid=False, color=TEXT, tickmode="linear",
                   tick0=0, dtick=1),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        hoverlabel=dict(bgcolor="#1a2e1a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_top:
    st.markdown("### Top 10 mensajes de usuario")
    top_msgs = (
        df["user_message"].str.strip().str.lower()
        .value_counts().head(10)
        .reset_index()
    )
    top_msgs.columns = ["Mensaje", "Veces"]

    fig5 = go.Figure(go.Bar(
        x=top_msgs["Veces"][::-1],
        y=top_msgs["Mensaje"][::-1],
        orientation="h",
        marker=dict(
            color=top_msgs["Veces"][::-1],
            colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
            line=dict(width=0),
        ),
        text=top_msgs["Veces"][::-1],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{y}: %{x} veces<extra></extra>",
    ))
    fig5.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=40, t=10, b=0), height=280,
        xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
        yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig5, use_container_width=True)

# ── Fila 3: engagement ────────────────────────────────────────────────────────

col3, _ = st.columns([2, 3])

with col3:
    st.markdown("### Engagement por sesión")
    ranges_labels = ["1-2 msgs", "3-5 msgs", "6-10 msgs", "10+ msgs"]
    ranges_vals   = [0, 0, 0, 0]
    for l in sess_lens:
        if l <= 2:    ranges_vals[0] += 1
        elif l <= 5:  ranges_vals[1] += 1
        elif l <= 10: ranges_vals[2] += 1
        else:         ranges_vals[3] += 1
    fig4 = go.Figure(go.Bar(
        x=ranges_vals, y=ranges_labels,
        orientation="h",
        marker=dict(
            color=["#3b6e2e","#4a9e30","#6abf50","#7ed957"],
            line=dict(width=0),
        ),
        text=[f"{v}  ({v/n_sess*100:.0f}%)" for v in ranges_vals],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{y}: %{x} sesiones<extra></extra>",
    ))
    fig4.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=60, t=10, b=0), height=220,
        xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
        yaxis=dict(showgrid=False, color=TEXT),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Expanders de detalle ──────────────────────────────────────────────────────

def detail_table(response_type: str, col_name: str):
    sub = df[df["response_type"] == response_type]
    if sub.empty:
        st.info("Sin datos en el período seleccionado.")
        return
    msgs = (sub["user_message"].str.strip().str.lower()
            .value_counts().head(15).reset_index())
    msgs.columns = [col_name, "Veces"]
    st.dataframe(msgs, use_container_width=True, hide_index=True)

col_exp1, col_exp2, col_exp3 = st.columns(3)
with col_exp1:
    with st.expander("Detalle Colectivas"):
        detail_table("colectivas", "Consulta")
with col_exp2:
    with st.expander("Detalle Almaceneras"):
        detail_table("almaceneras", "Almacenera / Consulta")
with col_exp3:
    with st.expander("Detalle Agenda del Río"):
        detail_table("agenda", "Emprendimiento / Consulta")

# ── Conversaciones ────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## Conversaciones")

col_llm, col_err = st.columns(2)

with col_llm:
    st.markdown("### LLM")
    df_llm = (
        df[df["response_type"] == "llm"]
        [["timestamp", "user_message", "bot_reply"]]
        .sort_values("timestamp", ascending=False)
        .copy()
    )
    df_llm["timestamp"] = df_llm["timestamp"].dt.strftime("%d/%m %H:%M")
    df_llm.columns = ["Fecha", "Usuario", "Bot"]
    st.dataframe(df_llm, use_container_width=True, height=420, hide_index=True)

with col_err:
    st.markdown("### Errores")
    df_err = (
        df[df["response_type"].isin(["llm_blocked", "llm_error"])]
        [["timestamp", "user_message", "bot_reply", "response_type"]]
        .sort_values("timestamp", ascending=False)
        .copy()
    )
    if df_err.empty:
        st.success("Sin errores en el período seleccionado.")
    else:
        df_err["timestamp"] = df_err["timestamp"].dt.strftime("%d/%m %H:%M")
        df_err.columns = ["Fecha", "Usuario", "Bot", "Tipo"]
        st.dataframe(df_err, use_container_width=True, height=420, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    f"Deltix Dashboard &nbsp;•&nbsp; "
    f"datos: `{CSV_PATH.name}` &nbsp;•&nbsp; "
    f"generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
