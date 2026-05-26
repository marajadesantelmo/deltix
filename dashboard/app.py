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
    initial_sidebar_state="collapsed",
)

# ── Control de acceso ─────────────────────────────────────────────────────────

_pwd = st.text_input("🔒 Código de acceso", type="password", key="pwd")
if _pwd != "nomellamescapibara":
    if _pwd:
        st.error("Código incorrecto.")
    st.stop()

# ── Paleta y estilos ──────────────────────────────────────────────────────────

# Colores distintos para cada funcionalidad
FEATURE_COLORS = {
    "🚢 Colectivas":    "#5a9e47",
    "🌤️ Clima":         "#3b9dc4",
    "🌊 Mareas":        "#1a6fa0",
    "📡 Hidrografía":   "#2eb8b8",
    "🌬️ WindGurú":      "#6baed6",
    "⚡ Clima/Mareas":  "#3b9dc4",   # histórico (tipo "quick" sin clasificar)
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
/* ── KPI cards ──────────────────────────────────────────────────────────── */
.kpi-card {
    background: linear-gradient(160deg, #1b381b 0%, #224022 100%);
    border: 1px solid rgba(90,158,71,0.2);
    border-top: 3px solid var(--kpi-accent, #5a9e47);
    border-radius: 12px;
    padding: 0.85rem 0.75rem 0.8rem;
    text-align: center;
    box-shadow: 0 3px 10px rgba(0,0,0,0.35);
}
.kpi-icon  { font-size: 1.25rem; line-height: 1.4; }
.kpi-label { font-size: 0.6rem; color: #7ab87a; font-weight: 700;
             text-transform: uppercase; letter-spacing: .11em; margin-top: 1px; }
.kpi-value { font-size: 1.95rem; font-weight: 800; color: #f0f8ed;
             line-height: 1.1; margin: 4px 0 2px; }
.kpi-sub   { font-size: 0.67rem; color: #5f9a5f; min-height: 1em; }
.kpi-sep   { height: 1px; background: rgba(90,158,71,0.15); margin: 6px 0 5px; }
.kpi-trend-up   { color: #5cc75c; font-size: 0.68rem; font-weight: 600; }
.kpi-trend-down { color: #c75c5c; font-size: 0.68rem; font-weight: 600; }
.kpi-trend-neu  { color: #777;    font-size: 0.68rem; }

/* ── Brand header ────────────────────────────────────────────────────────── */
.brand-title    { font-size: 1.2rem; font-weight: 800; color: #e8f5e2; line-height: 1.1; }
.brand-subtitle { font-size: 0.7rem; color: #7ab87a; font-weight: 500; letter-spacing: .05em; }

/* ── Section headers ─────────────────────────────────────────────────────── */
h2 { border-bottom: 2px solid #2e4e2e; padding-bottom: .3rem; }

/* Ocultar botón de colapso del sidebar */
button[kind="header"] { display: none; }

/* Expander */
details summary { font-weight: 600; }

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Rutas ─────────────────────────────────────────────────────────────────────

ROOT           = Path(__file__).parent.parent
CSV_PATH       = ROOT / "web_interactions.csv"
TG_CSV_PATH    = ROOT / "tg_interactions.csv"
TIMESTAMP_FILE = Path(__file__).parent / ".last_sync"
SYNC_LOG       = Path(__file__).parent / "sync.log"

# ── Carga de datos ────────────────────────────────────────────────────────────

IS_CLOUD = not CSV_PATH.exists()

@st.cache_data(ttl=3600)
def load_data(pa_token: str = "", pa_user: str = "facundol") -> pd.DataFrame:
    """Carga datos web. Puro: no llama a st.* para compatibilidad con st.cache_data."""
    if pa_token:
        url = (
            f"https://www.pythonanywhere.com/api/v0/user/{pa_user}"
            f"/files/path/home/{pa_user}/deltix/web_interactions.csv"
        )
        resp = requests.get(url, headers={"Authorization": f"Token {pa_token}"}, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), parse_dates=["timestamp"])
    else:
        df = pd.read_csv(str(CSV_PATH), parse_dates=["timestamp"])
    df["timestamp"] = df["timestamp"] - pd.Timedelta(hours=3)
    df["date"]    = df["timestamp"].dt.date
    df["hour"]    = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.day_name()
    df["source"]  = "web"
    return df

@st.cache_data(ttl=3600)
def load_tg_data(pa_token: str = "", pa_user: str = "facundol") -> pd.DataFrame:
    """Carga datos de Telegram. Devuelve DataFrame vacío si el archivo no existe aún."""
    try:
        if pa_token:
            url = (
                f"https://www.pythonanywhere.com/api/v0/user/{pa_user}"
                f"/files/path/home/{pa_user}/deltix/tg_interactions.csv"
            )
            resp = requests.get(url, headers={"Authorization": f"Token {pa_token}"}, timeout=30)
            if resp.status_code == 404:
                return pd.DataFrame(columns=["timestamp","user_id","user_message","response_type","bot_reply","date","hour","weekday","source"])
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text), parse_dates=["timestamp"])
        else:
            if not TG_CSV_PATH.exists():
                return pd.DataFrame(columns=["timestamp","user_id","user_message","response_type","bot_reply","date","hour","weekday","source"])
            df = pd.read_csv(str(TG_CSV_PATH), parse_dates=["timestamp"])
        df["timestamp"] = df["timestamp"] - pd.Timedelta(hours=3)
        df["date"]    = df["timestamp"].dt.date
        df["hour"]    = df["timestamp"].dt.hour
        df["weekday"] = df["timestamp"].dt.day_name()
        df["source"]  = "telegram"
        # Normalizar: renombrar user_id → session_id para compatibilidad
        if "user_id" in df.columns:
            df = df.rename(columns={"user_id": "session_id"})
        return df
    except Exception as e:
        print(f"TG data load error: {e}")
        return pd.DataFrame(columns=["timestamp","user_id","user_message","response_type","bot_reply","date","hour","weekday","source"])

# Validar secretos y cargar datos
if IS_CLOUD:
    _pa_token = st.secrets.get("PA_API_TOKEN", "")
    _pa_user  = st.secrets.get("PA_USERNAME", "facundol")
    if not _pa_token:
        st.error("⚠️ Configurá `PA_API_TOKEN` en Streamlit Secrets (Settings → Secrets).")
        st.stop()
    df_full    = load_data(_pa_token, _pa_user)
    df_tg_full = load_tg_data(_pa_token, _pa_user)
else:
    df_full    = load_data()
    df_tg_full = load_tg_data()

TG_AVAILABLE = len(df_tg_full) > 0

# ── Barra superior ────────────────────────────────────────────────────────────

min_date = df_full["date"].min()
max_date = df_full["date"].max()

_col_brand, _col_empty, _col_controls = st.columns([3, 5, 2])

with _col_brand:
    _sub_img, _sub_txt = st.columns([1, 3])
    with _sub_img:
        if (ROOT / "bot_icon.png").exists():
            st.image(str(ROOT / "bot_icon.png"), width=54)
    with _sub_txt:
        st.markdown("""
        <div style="padding-top:10px">
          <div class="brand-title">Bot Deltix</div>
          <div class="brand-subtitle">Dashboard de Métricas</div>
        </div>""", unsafe_allow_html=True)

with _col_controls:
    _sub_date, _sub_btn = st.columns([4, 1])
    with _sub_date:
        date_range = st.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
        )
    with _sub_btn:
        st.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
        if IS_CLOUD:
            if st.button("🔄", use_container_width=True, help="Actualizar datos"):
                st.cache_data.clear()
                st.rerun()
        else:
            if st.button("🔄", use_container_width=True, help="Sincronizar desde PythonAnywhere"):
                sync_script = Path(__file__).parent / "sync_csv.py"
                with st.spinner("Descargando..."):
                    ret = os.system(f'"{sync_script}" 2>&1')
                st.cache_data.clear()
                st.rerun()
            if SYNC_LOG.exists():
                with st.expander("Log"):
                    lines = SYNC_LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                    st.code("\n".join(lines[-15:]), language=None)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr style="border:none;border-top:1px solid #2e5030;margin:0.4rem 0 0.8rem">', unsafe_allow_html=True)

# ── Filtrar datos ─────────────────────────────────────────────────────────────

if len(date_range) == 2:
    start, end = date_range
    df = df_full[(df_full["date"] >= start) & (df_full["date"] <= end)].copy()
else:
    df = df_full.copy()
    start, end = min_date, max_date

# Filtro Telegram con el mismo período
if TG_AVAILABLE and len(df_tg_full):
    df_tg = df_tg_full[(df_tg_full["date"] >= start) & (df_tg_full["date"] <= end)].copy()
else:
    df_tg = df_tg_full.copy() if TG_AVAILABLE else pd.DataFrame()

# Período anterior (misma duración, para tendencias)
n_days = max((end - start).days, 1)
prev_end   = start - timedelta(days=1)
prev_start = prev_end - timedelta(days=n_days - 1)
df_prev = df_full[
    (df_full["date"] >= prev_start) & (df_full["date"] <= prev_end)
].copy()

# ── Período activo ────────────────────────────────────────────────────────────

period_str = f"{start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}" if not df.empty else "sin datos"

# ── Helpers trend ─────────────────────────────────────────────────────────────

def trend_html(current, previous, fmt=".0f", suffix=""):
    if previous == 0:
        return ""
    delta = current - previous
    pct   = delta / previous * 100
    arrow = "▲" if delta > 0 else "▼"
    cls   = "kpi-trend-up" if delta >= 0 else "kpi-trend-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}% vs período anterior</span>'

def kpi(col, label, value_str, sub="", trend_html_str="", icon="", accent="#5a9e47"):
    icon_html  = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    trend_html = (f'<div class="kpi-sep"></div><div style="min-height:1rem">{trend_html_str}</div>'
                  if trend_html_str else "")
    col.markdown(f"""
    <div class="kpi-card" style="--kpi-accent:{accent}">
        {icon_html}
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value_str}</div>
        <div class="kpi-sub">{sub}</div>
        {trend_html}
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
bounce_pct   = bounces / n_sess * 100 if n_sess else 0

# Usuarios activos únicos por día (session_id distintos por día)
dau          = df.groupby("date")["session_id"].nunique()  # Daily Active Users
avg_dau      = dau.mean() if len(dau) else 0
max_dau      = int(dau.max()) if len(dau) else 0
prev_dau     = df_prev.groupby("date")["session_id"].nunique().mean() if len(df_prev) else 0

prev_pct_llm = (df_prev["response_type"].isin(["llm","llm_blocked","llm_error"]).sum()
                / len(df_prev) * 100) if len(df_prev) else 0

# ── Métricas hoy / este mes (sobre df_full, independiente del filtro) ─────────
_today       = df_full["date"].max()          # fecha más reciente del dataset
_dau_full    = df_full.groupby("date")["session_id"].nunique()
_msgs_daily  = df_full.groupby("date").size()
users_today  = int(_dau_full.get(_today, 0))
msgs_today   = int(_msgs_daily.get(_today, 0))
avg_dau_full = _dau_full.mean() if len(_dau_full) else 0
avg_msgs_daily = _msgs_daily.mean() if len(_msgs_daily) else 0

_this_month  = _today.replace(day=1)
df_month     = df_full[df_full["date"] >= _this_month]
users_month  = int(df_month["session_id"].nunique())
msgs_month   = int(len(df_month))

# Promedio mensual histórico
_monthly = (
    df_full.assign(month=df_full["date"].apply(lambda d: d.replace(day=1)))
           .groupby("month")["session_id"].nunique()
)
avg_monthly  = _monthly.mean() if len(_monthly) else 0
_msgs_monthly = (
    df_full.assign(month=df_full["date"].apply(lambda d: d.replace(day=1)))
           .groupby("month").size()
)
avg_msgs_monthly = _msgs_monthly.mean() if len(_msgs_monthly) else 0

# ── Labels de los dos grupos de KPIs ─────────────────────────────────────────

_lbl_l, _lbl_r = st.columns([6, 5])
with _lbl_l:
    st.markdown(
        f'<p style="font-size:0.72rem;color:#5f9a5f;margin:-2px 0 4px">📅 {period_str}</p>',
        unsafe_allow_html=True,
    )
with _lbl_r:
    st.markdown(
        f'<p style="font-size:0.72rem;color:#7a9e9f;margin:-2px 0 4px">'
        f'📌 Datos fijos — '
        f'Hoy: <b>{_today.strftime("%d/%m/%Y")}</b> · '
        f'Mes: <b>{_today.strftime("%B %Y")}</b></p>',
        unsafe_allow_html=True,
    )

# ── KPI row única ─────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5, c6, _sep, k1, k2, k3, k4 = st.columns(
    [1, 1, 1, 1, 1, 1, 0.06, 1, 1, 1, 1]
)
# Separador visual
_sep.markdown(
    '<div style="border-left:1px solid rgba(90,158,71,0.25);height:100%;'
    'margin:0 auto;width:1px"></div>',
    unsafe_allow_html=True,
)

kpi(c1, "Interacciones",
    f"{total:,}".replace(",", "."),
    f"{n_sess} sesiones",
    trend_html(total, prev_total),
    icon="💬", accent="#5a9e47")
kpi(c2, "Sesiones únicas",
    str(n_sess),
    "conversaciones distintas",
    trend_html(n_sess, prev_sess),
    icon="🗂️", accent="#5a9e47")
kpi(c3, "Usuarios/día (DAU)",
    f"{avg_dau:.1f}",
    f"pico: {max_dau} usuarios",
    trend_html(avg_dau, prev_dau),
    icon="👥", accent="#3b9dc4")
kpi(c4, "Msgs / sesión",
    f"{avg_len:.1f}",
    f"{power_users} power users (10+)",
    icon="📈", accent="#5a9e47")
kpi(c5, "Ratio LLM",
    f"{pct_llm:.1f}%",
    "umbral saludable < 15%",
    trend_html(pct_llm, prev_pct_llm),
    icon="🤖", accent="#9b5fc0")
kpi(c6, "Tasa de error",
    f"{error_rate:.2f}%",
    f"{llm_blocked} blocked + {llm_error} err.",
    icon="⚠️", accent="#e07a30")
kpi(k1, "Usuarios hoy",
    str(users_today),
    f"prom. diario: {avg_dau_full:.1f}",
    icon="🟢", accent="#3b9dc4")
kpi(k2, "Mensajes hoy",
    str(msgs_today),
    f"prom. diario: {avg_msgs_daily:.0f}",
    icon="💬", accent="#3b9dc4")
kpi(k3, "Usuarios este mes",
    str(users_month),
    f"prom. mensual: {avg_monthly:.0f}",
    icon="📅", accent="#5a9e47")
kpi(k4, "Mensajes este mes",
    str(msgs_month),
    f"prom. mensual: {avg_msgs_monthly:.0f}",
    icon="📊", accent="#5a9e47")

st.markdown("<br>", unsafe_allow_html=True)

# ── Fila 1: barras + tablas ──────────────────────────────────────────────────

col_l, col_tabs = st.columns([3, 2])

with col_l:
    st.markdown("### Interacciones y usuarios únicos por día")
    daily_msgs = df.groupby("date").size().reset_index(name="interacciones")
    daily_dau  = dau.reset_index()
    daily_dau.columns = ["date", "usuarios"]
    daily = daily_msgs.merge(daily_dau, on="date", how="left")
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

    # Línea — usuarios únicos por día (eje derecho)
    fig.add_trace(go.Scatter(
        x=daily["date_str"], y=daily["usuarios"],
        name="Usuarios únicos",
        mode="lines+markers",
        line=dict(color="#e0a020", width=2.5, shape="spline"),
        marker=dict(color="#e0a020", size=7, line=dict(color="#0e1a0e", width=1.5)),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>%{y} usuarios únicos<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=50, t=10, b=0), height=430,
        xaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        yaxis=dict(
            title="Interacciones", title_font=dict(color="#7ed957", size=11),
            showgrid=True, gridcolor=GRID, color="#7ed957", zeroline=False,
        ),
        yaxis2=dict(
            title="Usuarios únicos", title_font=dict(color="#e0a020", size=11),
            overlaying="y", side="right",
            color="#e0a020", zeroline=False, showgrid=False,
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

with col_tabs:
    # ── Tabla: Últimas conversaciones ─────────────────────────────────────────
    st.markdown("### Últimas conversaciones")
    ultimas = (
        df.groupby("session_id")
          .agg(fecha=("timestamp", "min"), mensajes=("user_message", "count"))
          .sort_values("fecha", ascending=False)
          .head(15)
          .reset_index(drop=True)
    )
    ultimas["Fecha"] = ultimas["fecha"].dt.strftime("%d/%m %H:%M")
    ultimas = ultimas.rename(columns={"mensajes": "Msgs"})[["Fecha", "Msgs"]]
    st.dataframe(ultimas, use_container_width=True, hide_index=True, height=175)

    # ── Tabla: Interacciones diarias ──────────────────────────────────────────
    st.markdown("### Interacciones diarias")
    daily_tbl = (
        daily[["date", "interacciones", "usuarios"]]
        .sort_values("date", ascending=False)
        .copy()
    )
    daily_tbl["Fecha"] = daily_tbl["date"].apply(
        lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
    )
    daily_tbl = daily_tbl.rename(columns={
        "interacciones": "Msgs",
        "usuarios":      "Usuarios",
    })[["Fecha", "Msgs", "Usuarios"]]
    st.dataframe(daily_tbl, use_container_width=True, hide_index=True, height=175)

# ── Fila 2: actividad horaria + dona + top mensajes ──────────────────────────

col_h, col_pie, col_top = st.columns([3, 2, 2])

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

with col_pie:
    st.markdown("### Funcionalidades usadas · *por sesión*")

    _CLIMA_KW      = ['clima', 'temperatura', 'pronostico', 'pronóstico', 'lluvia',
                      'tormenta', 'calor', 'frio', 'frío', 'nublado', 'el tiempo',
                      'qué tiempo', 'que tiempo']
    _MAREAS_KW     = ['mareas', 'marea', 'pleamar', 'bajamar', 'crecida',
                      'inundacion', 'inundación', 'nivel del rio', 'nivel del río',
                      'subio el rio', 'subió el río', 'bajo el rio', 'bajó el río']
    _HIDRO_KW      = ['hidrografia', 'hidrografía']
    _WINDGURU_KW   = ['windguru', 'viento']

    def _reclassify_quick(row):
        if row["response_type"] != "quick":
            return row["response_type"]
        msg = str(row["user_message"]).lower()
        if any(k in msg for k in _HIDRO_KW):
            return "hidrografia"
        if any(k in msg for k in _MAREAS_KW):
            return "mareas"
        if any(k in msg for k in _CLIMA_KW):
            return "clima"
        if any(k in msg for k in _WINDGURU_KW):
            return "windguru"
        return "quick"

    df_pie = df.copy()
    df_pie["response_type"] = df_pie.apply(_reclassify_quick, axis=1)
    pie_counts = (
        df_pie.drop_duplicates(subset=["session_id", "response_type"])
              ["response_type"]
              .value_counts()
    )
    type_map = {
        "colectivas":   "🚢 Colectivas",
        "clima":        "🌤️ Clima",
        "mareas":       "🌊 Mareas",
        "hidrografia":  "📡 Hidrografía",
        "windguru":     "🌬️ WindGurú",
        "quick":        "⚡ Clima/Mareas",
        "agenda":       "📅 Agenda",
        "memes":        "😂 Memes",
        "llm":          "🤖 LLM",
        "almaceneras":  "🛒 Almaceneras",
        "social":       "💬 Social",
        "llm_blocked":  "⚠️ LLM bloqueado",
        "llm_error":    "❌ LLM error",
    }
    tc = (pie_counts
          .rename(index=type_map)
          .loc[lambda s: s.index.isin(type_map.values())]
          .reset_index())
    tc.columns = ["label", "count"]

    # Agrupar categorías con menos de 2.5% en "Otros"
    _total_pie = tc["count"].sum()
    if _total_pie > 0:
        _mask_otros = (tc["count"] / _total_pie * 100) < 2.5
        _otros_sum  = int(tc.loc[_mask_otros, "count"].sum())
        tc = tc.loc[~_mask_otros].copy()
        if _otros_sum > 0:
            tc = pd.concat(
                [tc, pd.DataFrame([{"label": "⬜ Otros", "count": _otros_sum}])],
                ignore_index=True,
            )

    colors = [FEATURE_COLORS.get(l, "#888888") for l in tc["label"]]

    fig2 = go.Figure(go.Pie(
        labels=tc["label"], values=tc["count"],
        marker=dict(colors=colors, line=dict(color="#0e1a0e", width=2)),
        hole=0.45,
        textinfo="percent",
        textfont=dict(size=12, color="white"),
        hovertemplate="<b>%{label}</b><br>%{value} sesiones (%{percent})<extra></extra>",
    ))
    fig2.update_layout(
        paper_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=280,
        legend=dict(font=dict(size=11, color=TEXT), bgcolor=TRANSP,
                    orientation="v", x=1, y=0.5),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig2, use_container_width=True)

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

# ── Fila 3: engagement + ratio LLM diario ────────────────────────────────────

col3, col_llmr = st.columns([2, 3])

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

with col_llmr:
    st.markdown("### Evolución del ratio LLM por día")
    _all_dates_llm = sorted(df["date"].unique())
    daily_llm = (
        df.groupby("date")
          .apply(lambda g: pd.Series({
              "total": len(g),
              "llm":   g["response_type"].isin(["llm", "llm_blocked", "llm_error"]).sum(),
          }))
          .reindex(_all_dates_llm)
          .fillna(0)
          .reset_index()
    )
    daily_llm["pct"] = (daily_llm["llm"] / daily_llm["total"].replace(0, pd.NA) * 100).round(1)
    daily_llm["date_str"] = daily_llm["date"].astype(str)

    fig_llmr = go.Figure()
    # Área rellena
    fig_llmr.add_trace(go.Scatter(
        x=daily_llm["date_str"], y=daily_llm["pct"],
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(155,95,192,0.15)",
        line=dict(color="#9b5fc0", width=2.5, shape="spline"),
        marker=dict(color="#9b5fc0", size=7, line=dict(color="#0e1a0e", width=1.5)),
        hovertemplate="<b>%{x}</b><br>%{y:.1f}% LLM<extra></extra>",
        name="Ratio LLM",
    ))
    # Línea de umbral saludable (15 %)
    fig_llmr.add_hline(
        y=15,
        line=dict(color="#e07a30", width=1.5, dash="dot"),
        annotation_text="umbral 15%",
        annotation_position="top right",
        annotation_font=dict(color="#e07a30", size=11),
    )
    fig_llmr.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=220,
        xaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        yaxis=dict(
            showgrid=True, gridcolor=GRID, color=TEXT,
            zeroline=False, ticksuffix="%",
        ),
        legend=dict(font=dict(color=TEXT, size=11), bgcolor=TRANSP),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_llmr, use_container_width=True)

# ── Patrones de uso ───────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## Patrones de uso")

col_wd, col_br, col_errt = st.columns(3)

with col_wd:
    st.markdown("### Actividad por día de semana")
    WEEKDAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    WEEKDAY_ES    = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
    wd = (df["weekday"].value_counts()
          .reindex(WEEKDAY_ORDER, fill_value=0)
          .reset_index())
    wd.columns = ["weekday", "count"]
    wd["label"] = WEEKDAY_ES
    fig_wd = go.Figure(go.Bar(
        x=wd["label"], y=wd["count"],
        marker=dict(
            color=wd["count"],
            colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
            line=dict(width=0),
        ),
        text=wd["count"],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="<b>%{x}</b>: %{y} msgs<extra></extra>",
    ))
    fig_wd.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=240,
        xaxis=dict(showgrid=False, color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_wd, use_container_width=True)

with col_br:
    st.markdown("### % de interacciones de un sólo mensaje")
    daily_bounces = (
        df.groupby(["date", "session_id"]).size()
          .reset_index(name="n")
          .assign(bounced=lambda x: (x["n"] == 1).astype(int))
          .groupby("date")
          .agg(total_sess=("session_id", "count"), bounced=("bounced", "sum"))
          .reset_index()
    )
    daily_bounces["bounce_pct"] = (
        daily_bounces["bounced"] / daily_bounces["total_sess"] * 100
    ).round(1)
    daily_bounces["date_str"] = daily_bounces["date"].astype(str)
    fig_br = go.Figure(go.Scatter(
        x=daily_bounces["date_str"], y=daily_bounces["bounce_pct"],
        mode="lines+markers",
        line=dict(color="#3b9dc4", width=2.5, shape="spline"),
        marker=dict(color="#3b9dc4", size=8, line=dict(color="#0e1a0e", width=1.5)),
        fill="tozeroy",
        fillcolor="rgba(59,157,196,0.12)",
        hovertemplate="<b>%{x}</b><br>%{y:.1f}% bounce<extra></extra>",
    ))
    fig_br.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=240,
        xaxis=dict(showgrid=False, color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT,
                   zeroline=False, ticksuffix="%"),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_br, use_container_width=True)

with col_errt:
    st.markdown("### Tendencia de errores diaria")
    _all_dates = sorted(df["date"].unique())
    daily_err = (
        df[df["response_type"].isin(["llm_blocked", "llm_error"])]
        .groupby("date").size()
        .reindex(_all_dates, fill_value=0)
        .reset_index()
    )
    daily_err.columns = ["date", "errors"]
    daily_err["date_str"] = daily_err["date"].astype(str)
    fig_errt = go.Figure(go.Scatter(
        x=daily_err["date_str"], y=daily_err["errors"],
        mode="lines+markers",
        line=dict(color="#c44040", width=2.5, shape="spline"),
        marker=dict(color="#c44040", size=8, line=dict(color="#0e1a0e", width=1.5)),
        fill="tozeroy",
        fillcolor="rgba(196,64,64,0.12)",
        hovertemplate="<b>%{x}</b><br>%{y} errores<extra></extra>",
    ))
    fig_errt.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=240,
        xaxis=dict(showgrid=False, color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_errt, use_container_width=True)

# ── Análisis de flujos ────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## Análisis de flujos")

col_col, col_div, col_comp = st.columns(3)

with col_col:
    st.markdown("### Desglose de colectivas")
    col_msgs = df[df["response_type"] == "colectivas"]["user_message"].str.lower()
    line_counts = pd.Series({
        "Jilguero":     int(col_msgs.str.contains("jilguero", na=False).sum()),
        "Interisleña":  int(col_msgs.str.contains("interisle", na=False).sum()),
        "Líneas Delta": int(col_msgs.str.contains(r"l.neas delta|lineas delta",
                                                   regex=True, na=False).sum()),
        "Ida":          int(col_msgs.str.contains(r"\bida\b", regex=True, na=False).sum()),
        "Vuelta":       int(col_msgs.str.contains(r"\bvuelta\b", regex=True, na=False).sum()),
        "Escolar":      int(col_msgs.str.contains("escolar", na=False).sum()),
    }).sort_values()
    lc_df = line_counts.reset_index()
    lc_df.columns = ["consulta", "count"]
    fig_col2 = go.Figure(go.Bar(
        x=lc_df["count"], y=lc_df["consulta"],
        orientation="h",
        marker=dict(
            color=lc_df["count"],
            colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
            line=dict(width=0),
        ),
        text=lc_df["count"],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{y}: %{x} consultas<extra></extra>",
    ))
    fig_col2.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=40, t=10, b=0), height=280,
        xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
        yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_col2, use_container_width=True)

with col_div:
    st.markdown("### Diversidad de features")
    feat_div = (df.groupby("session_id")["response_type"]
                  .nunique().reset_index(name="n_types"))
    feat_div["bucket"] = feat_div["n_types"].apply(
        lambda x: "1 tipo" if x == 1 else ("2 tipos" if x == 2 else "3+ tipos")
    )
    div_counts = (feat_div["bucket"].value_counts()
                  .reindex(["1 tipo", "2 tipos", "3+ tipos"], fill_value=0)
                  .reset_index())
    div_counts.columns = ["bucket", "count"]
    fig_div = go.Figure(go.Bar(
        x=div_counts["bucket"], y=div_counts["count"],
        marker=dict(
            color=["#3b6e2e", "#4a9e30", "#7ed957"],
            line=dict(width=0),
        ),
        text=[f"{v} ({v/n_sess*100:.0f}%)" if n_sess else str(v)
              for v in div_counts["count"]],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="<b>%{x}</b>: %{y} sesiones<extra></extra>",
    ))
    fig_div.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=30), height=280,
        xaxis=dict(showgrid=False, color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_div, use_container_width=True)

with col_comp:
    st.markdown("### Completitud de flujos")
    _flow_rows = []
    for ft in ["colectivas", "almaceneras", "agenda"]:
        s = df[df["response_type"] == ft].groupby("session_id").size()
        _flow_rows.append({
            "tipo": ft.capitalize(),
            "1 interacción": int((s == 1).sum()),
            "2+": int((s >= 2).sum()),
        })
    df_flow = pd.DataFrame(_flow_rows)
    fig_flow = go.Figure()
    fig_flow.add_trace(go.Bar(
        name="1 paso (inicio)",
        x=df_flow["tipo"], y=df_flow["1 interacción"],
        marker=dict(color="#3b6e2e", line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>1 paso: %{y}<extra></extra>",
    ))
    fig_flow.add_trace(go.Bar(
        name="2+ pasos (completado)",
        x=df_flow["tipo"], y=df_flow["2+"],
        marker=dict(color="#7ed957", line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>2+ pasos: %{y}<extra></extra>",
    ))
    fig_flow.update_layout(
        barmode="stack",
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=280,
        xaxis=dict(showgrid=False, color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        legend=dict(orientation="h", x=0, y=1.12,
                    font=dict(color=TEXT, size=10), bgcolor=TRANSP),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_flow, use_container_width=True)

# ── Análisis del LLM ──────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## Análisis del LLM")

col_words, col_rlen = st.columns(2)

with col_words:
    st.markdown("### Temas frecuentes en LLM")
    STOPWORDS_ES = frozenset([
        "de","la","el","en","y","a","que","los","las","un","una","con",
        "por","para","del","se","es","al","lo","le","más","su","como",
        "me","qué","no","si","hay","tiene","tenés","te","mi","pero",
        "o","e","ni","ya","yo","tu","él","también","sobre","cuando",
        "desde","hasta","todo","puede","esto","esta","eso","ese","esos",
        "estas","todos","todas","muy","bien","hola","gracias","favor",
        "necesito","quiero","sabe","saben","donde","cuándo","cuando",
        "cómo","como","cuál","cual","cuánto","cuanto",
    ])
    _word_freq: dict = {}
    for _msg in df[df["response_type"] == "llm"]["user_message"].dropna():
        for _w in _msg.lower().split():
            _w = _w.strip("¿?!.,;:()")
            if len(_w) > 2 and _w not in STOPWORDS_ES:
                _word_freq[_w] = _word_freq.get(_w, 0) + 1
    _top_words = sorted(_word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
    if _top_words:
        tw_df = pd.DataFrame(_top_words, columns=["palabra", "count"])
        tw_df = tw_df.sort_values("count")
        fig_tw = go.Figure(go.Bar(
            x=tw_df["count"], y=tw_df["palabra"],
            orientation="h",
            marker=dict(
                color=tw_df["count"],
                colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
                line=dict(width=0),
            ),
            text=tw_df["count"],
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            hovertemplate="%{y}: %{x} veces<extra></extra>",
        ))
        fig_tw.update_layout(
            paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
            margin=dict(l=0, r=40, t=10, b=0), height=340,
            xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
            yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
            hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
        )
        st.plotly_chart(fig_tw, use_container_width=True)
    else:
        st.info("Sin datos LLM en el período seleccionado.")

with col_rlen:
    st.markdown("### Longitud de respuesta por tipo")
    avg_rlen = (
        df.assign(reply_len=df["bot_reply"].str.len().fillna(0))
          .groupby("response_type")["reply_len"]
          .mean().round(0).astype(int)
          .sort_values()
          .reset_index()
    )
    avg_rlen.columns = ["tipo", "avg_len"]
    fig_rlen = go.Figure(go.Bar(
        x=avg_rlen["avg_len"], y=avg_rlen["tipo"],
        orientation="h",
        marker=dict(
            color=avg_rlen["avg_len"],
            colorscale=[[0, "#2a5c1e"], [0.5, "#4a9e30"], [1, "#7ed957"]],
            line=dict(width=0),
        ),
        text=avg_rlen["avg_len"].apply(lambda v: f"{v} chars"),
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="<b>%{y}</b>: prom. %{x} chars<extra></extra>",
    ))
    fig_rlen.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=80, t=10, b=0), height=340,
        xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
        yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_rlen, use_container_width=True)

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

# ── Explorador de sesiones ───────────────────────────────────────────────────

st.markdown("---")
st.markdown("## Explorador de sesiones")

sess_summary = (
    df.groupby("session_id")
      .agg(first_ts=("timestamp", "min"), n_msgs=("user_message", "count"))
      .sort_values("first_ts", ascending=False)
      .reset_index()
)
sess_summary["label"] = (
    sess_summary["first_ts"].dt.strftime("%d/%m %H:%M")
    + "  —  " + sess_summary["session_id"]
    + "  (" + sess_summary["n_msgs"].astype(str) + " msgs)"
)

selected_label = st.selectbox(
    "Seleccioná una sesión",
    options=sess_summary["label"].tolist(),
    index=0,
)
selected_sid = sess_summary.loc[
    sess_summary["label"] == selected_label, "session_id"
].values[0]

df_sess = (
    df[df["session_id"] == selected_sid]
    [["timestamp", "user_message", "bot_reply", "response_type"]]
    .sort_values("timestamp")
    .copy()
)
df_sess["timestamp"] = df_sess["timestamp"].dt.strftime("%H:%M:%S")
df_sess.columns = ["Hora", "Usuario", "Bot", "Tipo"]
st.dataframe(df_sess, use_container_width=True, hide_index=True)

# ── Telegram ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## 📱 Bot de Telegram")

if not TG_AVAILABLE:
    st.info("Aún no hay datos del bot de Telegram. Una vez que `tg_interactions.csv` se genere en PythonAnywhere, aparecerá aquí automáticamente.")
else:
    # ── KPIs Telegram ────────────────────────────────────────────────────────
    tg_total     = len(df_tg)
    tg_users     = df_tg["session_id"].nunique() if "session_id" in df_tg.columns else 0
    tg_dau_serie = df_tg.groupby("date")["session_id"].nunique() if tg_users else pd.Series(dtype=float)
    tg_avg_dau   = tg_dau_serie.mean() if len(tg_dau_serie) else 0
    tg_llm_pct   = (df_tg["response_type"].isin(["llm","llm_error"]).sum() / tg_total * 100) if tg_total else 0
    tg_sess_lens = df_tg.groupby("session_id").size() if tg_users else pd.Series(dtype=float)
    tg_avg_len   = tg_sess_lens.mean() if len(tg_sess_lens) else 0

    tk1, tk2, tk3, tk4, tk5 = st.columns(5)
    kpi(tk1, "Mensajes TG",     f"{tg_total:,}".replace(",","."),  f"{n_days} días",         icon="📨", accent="#2b9fc4")
    kpi(tk2, "Usuarios únicos", str(tg_users),                     "IDs distintos",          icon="👤", accent="#2b9fc4")
    kpi(tk3, "Usuarios/día",    f"{tg_avg_dau:.1f}",               "DAU promedio",            icon="📅", accent="#2b9fc4")
    kpi(tk4, "Msgs / usuario",  f"{tg_avg_len:.1f}",               "profundidad de sesión",  icon="💬", accent="#2b9fc4")
    kpi(tk5, "Ratio LLM",       f"{tg_llm_pct:.1f}%",             "consultas al LLM",       icon="🤖", accent="#9b5fc0")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Comparativa Web vs Telegram por día ──────────────────────────────────
    col_cmp, col_tgpie = st.columns([3, 2])

    with col_cmp:
        st.markdown("### Mensajes diarios: Web vs Telegram")
        web_daily = df.groupby("date").size().reset_index(name="Web")
        tg_daily  = df_tg.groupby("date").size().reset_index(name="Telegram")
        cmp_daily = pd.merge(web_daily, tg_daily, on="date", how="outer").fillna(0).sort_values("date")
        cmp_daily["date_str"] = cmp_daily["date"].astype(str)

        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Bar(
            x=cmp_daily["date_str"], y=cmp_daily["Web"],
            name="Web", marker=dict(color="#5a9e47", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Web: %{y}<extra></extra>",
        ))
        fig_cmp.add_trace(go.Bar(
            x=cmp_daily["date_str"], y=cmp_daily["Telegram"],
            name="Telegram", marker=dict(color="#2b9fc4", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Telegram: %{y}<extra></extra>",
        ))
        fig_cmp.update_layout(
            barmode="group",
            paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
            margin=dict(l=0, r=0, t=10, b=0), height=280,
            xaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
            legend=dict(orientation="h", x=0, y=1.12, font=dict(color=TEXT, size=11), bgcolor=TRANSP),
            hoverlabel=dict(bgcolor="#1a2e1a", font_color="#e8f5e2"),
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    with col_tgpie:
        st.markdown("### Funcionalidades TG · *por usuario*")
        tg_type_counts = (
            df_tg.drop_duplicates(subset=["session_id","response_type"])["response_type"]
            .value_counts()
        )
        tg_type_map = {
            "colectivas":  "🚢 Colectivas",
            "mareas":      "🌊 Mareas",
            "windguru":    "🌬️ WindGurú",
            "hidrografia": "📡 Hidrografía",
            "agenda":      "📅 Agenda",
            "memes":       "😂 Memes",
            "llm":         "🤖 LLM",
            "almaceneras": "🛒 Almaceneras",
            "social":      "💬 Social",
            "llm_error":   "❌ LLM error",
            "other":       "❓ Otro",
        }
        tg_tc = (
            tg_type_counts.rename(index=tg_type_map)
            .loc[lambda s: s.index.isin(tg_type_map.values())]
            .reset_index()
        )
        tg_tc.columns = ["label", "count"]

        # Agrupar < 2.5% en Otros
        _tg_total_pie = tg_tc["count"].sum()
        if _tg_total_pie > 0:
            _tg_mask = (tg_tc["count"] / _tg_total_pie * 100) < 2.5
            _tg_otros = int(tg_tc.loc[_tg_mask, "count"].sum())
            tg_tc = tg_tc.loc[~_tg_mask].copy()
            if _tg_otros > 0:
                tg_tc = pd.concat([tg_tc, pd.DataFrame([{"label": "⬜ Otros", "count": _tg_otros}])], ignore_index=True)

        tg_colors = [FEATURE_COLORS.get(l, "#888888") for l in tg_tc["label"]]
        fig_tgpie = go.Figure(go.Pie(
            labels=tg_tc["label"], values=tg_tc["count"],
            marker=dict(colors=tg_colors, line=dict(color="#0e1a0e", width=2)),
            hole=0.45,
            textinfo="percent",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value} usuarios (%{percent})<extra></extra>",
        ))
        fig_tgpie.update_layout(
            paper_bgcolor=TRANSP,
            margin=dict(l=0, r=0, t=10, b=0), height=280,
            legend=dict(font=dict(size=11, color=TEXT), bgcolor=TRANSP, orientation="v", x=1, y=0.5),
            hoverlabel=dict(bgcolor="#2a4a2a", font_color="#e8f5e2"),
        )
        st.plotly_chart(fig_tgpie, use_container_width=True)

    # ── Top mensajes Telegram + usuarios más activos ──────────────────────────
    col_tgtop, col_tgusers = st.columns(2)

    with col_tgtop:
        st.markdown("### Top 10 mensajes en Telegram")
        tg_top = (
            df_tg["user_message"].str.strip().str.lower()
            .value_counts().head(10).reset_index()
        )
        tg_top.columns = ["Mensaje", "Veces"]
        fig_tgtop = go.Figure(go.Bar(
            x=tg_top["Veces"][::-1], y=tg_top["Mensaje"][::-1],
            orientation="h",
            marker=dict(
                color=tg_top["Veces"][::-1],
                colorscale=[[0, "#1a4a5c"], [0.5, "#2b7fa0"], [1, "#4dc4e8"]],
                line=dict(width=0),
            ),
            text=tg_top["Veces"][::-1], textposition="outside",
            textfont=dict(color=TEXT, size=11),
            hovertemplate="%{y}: %{x} veces<extra></extra>",
        ))
        fig_tgtop.update_layout(
            paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
            margin=dict(l=0, r=40, t=10, b=0), height=300,
            xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
            yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
            hoverlabel=dict(bgcolor="#1a2e3a", font_color="#e8f5e2"),
        )
        st.plotly_chart(fig_tgtop, use_container_width=True)

    with col_tgusers:
        st.markdown("### Usuarios más activos en Telegram")
        tg_user_counts = (
            df_tg.groupby("session_id").size()
            .sort_values(ascending=False).head(10)
            .reset_index()
        )
        tg_user_counts.columns = ["user_id", "mensajes"]
        tg_user_counts["user_id"] = tg_user_counts["user_id"].astype(str).str[-6:]  # últimos 6 dígitos
        fig_tgusers = go.Figure(go.Bar(
            x=tg_user_counts["mensajes"][::-1],
            y=("···" + tg_user_counts["user_id"])[::-1],
            orientation="h",
            marker=dict(
                color=tg_user_counts["mensajes"][::-1],
                colorscale=[[0, "#1a4a5c"], [0.5, "#2b7fa0"], [1, "#4dc4e8"]],
                line=dict(width=0),
            ),
            text=tg_user_counts["mensajes"][::-1], textposition="outside",
            textfont=dict(color=TEXT, size=11),
            hovertemplate="Usuario %{y}: %{x} mensajes<extra></extra>",
        ))
        fig_tgusers.update_layout(
            paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
            margin=dict(l=0, r=40, t=10, b=0), height=300,
            xaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT),
            yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
            hoverlabel=dict(bgcolor="#1a2e3a", font_color="#e8f5e2"),
        )
        st.plotly_chart(fig_tgusers, use_container_width=True)

    # ── Actividad horaria Telegram ────────────────────────────────────────────
    st.markdown("### Actividad por hora — Telegram")
    tg_hourly = df_tg.groupby("hour").size().reindex(range(24), fill_value=0).reset_index()
    tg_hourly.columns = ["hour", "count"]
    tg_peak_h = int(tg_hourly.loc[tg_hourly["count"].idxmax(), "hour"]) if tg_total else 0
    fig_tgh = go.Figure()
    fig_tgh.add_trace(go.Scatter(
        x=tg_hourly["hour"], y=tg_hourly["count"],
        mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(43,159,196,0.15)",
        line=dict(color="#4dc4e8", width=2.5, shape="spline"),
        marker=dict(
            color=["#e07a30" if h == tg_peak_h else "#2b9fc4" for h in tg_hourly["hour"]],
            size=[10 if h == tg_peak_h else 5 for h in tg_hourly["hour"]],
        ),
        hovertemplate="<b>%{x}h</b>: %{y} msgs<extra></extra>",
    ))
    if tg_total:
        fig_tgh.add_annotation(
            x=tg_peak_h,
            y=int(tg_hourly.loc[tg_hourly["hour"] == tg_peak_h, "count"].values[0]),
            text=f"Pico: {tg_peak_h}h", showarrow=True, arrowhead=2,
            font=dict(color="#e07a30", size=12), arrowcolor="#e07a30",
            bgcolor="#1a2e1a", bordercolor="#e07a30", ay=-30,
        )
    fig_tgh.update_layout(
        paper_bgcolor=TRANSP, plot_bgcolor=TRANSP,
        margin=dict(l=0, r=0, t=10, b=0), height=220,
        xaxis=dict(showgrid=False, color=TEXT, tickmode="linear", tick0=0, dtick=1),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, zeroline=False),
        hoverlabel=dict(bgcolor="#1a2e3a", font_color="#e8f5e2"),
    )
    st.plotly_chart(fig_tgh, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    f"Deltix Dashboard &nbsp;•&nbsp; "
    f"datos: `{CSV_PATH.name}` &nbsp;•&nbsp; "
    f"generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
