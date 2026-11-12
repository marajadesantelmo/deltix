"""
app.py — Dashboard de métricas y revisión de conversaciones de Tincho (UNDelta).

Uso (desde esta carpeta, para que tome .streamlit/config.toml con el tema UNDelta):
    cd tincho/dashboard
    python sync_db.py            # baja el histórico desde PythonAnywhere
    streamlit run app.py

Contraseña: variable de entorno TINCHO_DASH_PASSWORD o st.secrets["TINCHO_DASH_PASSWORD"].
Sin contraseña configurada el dashboard NO abre (falla cerrado).
"""
import hmac
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import sync_db

st.set_page_config(page_title="Tincho — Métricas", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ── Control de acceso ─────────────────────────────────────────────────────────


def _password_configurada():
    """Variable de entorno primero; st.secrets solo si existe el archivo (si no, Streamlit muestra un error en pantalla)."""
    if os.environ.get("TINCHO_DASH_PASSWORD"):
        return os.environ["TINCHO_DASH_PASSWORD"]
    for carpeta in (Path(__file__).parent / ".streamlit", Path.home() / ".streamlit"):
        if (carpeta / "secrets.toml").exists():
            return st.secrets.get("TINCHO_DASH_PASSWORD", "")
    return ""


if not st.session_state.get("authenticated"):
    pw = _password_configurada()
    if not pw:
        st.error("Falta configurar TINCHO_DASH_PASSWORD (variable de entorno o secrets). El dashboard no se abre sin contraseña.")
        st.stop()
    with st.form("login_form"):
        _pwd = st.text_input("🔒 Código de acceso", type="password")
        _entrar = st.form_submit_button("Acceder", type="primary", use_container_width=True)
    if _entrar:
        if hmac.compare_digest(_pwd.encode(), pw.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Código incorrecto.")
    st.stop()

# ── Estilos (paleta UNDelta) ──────────────────────────────────────────────────

LIMA, VERDE, DORADO, NAVY_MID = "#B5CC7C", "#99BB64", "#BB9B56", "#1D4763"
PALETA = {"opcion": "#B5CC7C", "comando": "#6FB5A3", "rag": "#BB9B56", "rag_sin_dato": "#C75C5C",
          "siu_consulta": "#5FA8D3", "calendario": "#D9B3E6", "siu_verificacion": "#3B7CA6", "jailbreak": "#E07A30",
          "limite": "#9B5FC0", "clave": "#8AA0AB", "inicio": "#4A5A63", "sistema": "#6C7C85"}
ETIQUETAS = {"opcion": "Botón / menú", "comando": "Palabra clave", "rag": "Pregunta libre (respondida)",
             "rag_sin_dato": "Pregunta libre (sin respuesta)", "calendario": "Calendario (datos fijos)", "siu_consulta": "Consulta SIU",
             "siu_verificacion": "Verificación SIU", "jailbreak": "Intento de jailbreak",
             "limite": "Límite de uso", "clave": "Clave de inicio", "inicio": "Carga de página", "sistema": "Sistema"}

st.markdown("""
<style>
.kpi-card { background: linear-gradient(160deg,#153549 0%,#1D4763 100%); border: 1px solid rgba(181,204,124,.2);
  border-top: 3px solid var(--accent,#B5CC7C); border-radius: 14px; padding: .85rem .75rem; text-align: center;
  box-shadow: 0 3px 10px rgba(0,0,0,.35); }
.kpi-label { font-size: .62rem; color: #B5CC7C; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; }
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #F8F6EF; line-height: 1.15; margin: 4px 0 2px; }
.kpi-sub { font-size: .68rem; color: #8AA0AB; min-height: 1em; }
h2, h3 { border-bottom: 2px solid #1D4763; padding-bottom: .3rem; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

def md(texto):
    """El bot usa *negrita* estilo WhatsApp; Streamlit (Markdown) necesita **negrita**."""
    return re.sub(r"\*([^*\n]+)\*", r"**\1**", texto or "")


# ── Datos ─────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=600, show_spinner=False)
def cargar(mtime: float) -> pd.DataFrame:
    """`mtime` solo sirve para invalidar la caché cuando cambia el archivo local."""
    con = sqlite3.connect(f"file:{sync_db.LOCAL_DB}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query("SELECT * FROM mensajes ORDER BY id", con)
    finally:
        con.close()
    df["ts"] = pd.to_datetime(df["ts"])  # ya está en hora argentina
    df["fecha"] = df["ts"].dt.date
    df["hora"] = df["ts"].dt.hour
    df["dia_semana"] = df["ts"].dt.day_name()
    df["tipo_desc"] = df["tipo"].map(ETIQUETAS).fillna(df["tipo"])
    return df


with st.sidebar:
    st.markdown("### 🎓 Tincho")
    st.caption("Métricas y revisión de conversaciones · UNDelta")
    if st.button("🔄 Sincronizar ahora", use_container_width=True):
        with st.spinner("Descargando desde PythonAnywhere…"):
            ok = sync_db.download_all()
        cargar.clear()
        (st.success if ok else st.error)("Sincronizado." if ok else "No se pudo sincronizar (mirá la consola).")
    if sync_db.TIMESTAMP_FILE.exists():
        st.caption(f"Última sincronización: {sync_db.TIMESTAMP_FILE.read_text(encoding='utf-8')}")

if not sync_db.LOCAL_DB.exists():
    st.warning("Todavía no hay datos locales. Corré `python sync_db.py` o tocá «Sincronizar ahora».")
    st.stop()

df_all = cargar(sync_db.LOCAL_DB.stat().st_mtime)
if df_all.empty:
    st.info("La base existe pero todavía no tiene mensajes.")
    st.stop()

with st.sidebar:
    f_min, f_max = df_all["fecha"].min(), df_all["fecha"].max()
    rango = st.date_input("Período", value=(f_min, f_max), min_value=f_min, max_value=f_max)
    if isinstance(rango, tuple) and len(rango) == 2:
        desde, hasta = rango
    else:
        desde = hasta = rango[0] if isinstance(rango, tuple) else rango
    with st.expander("Tipos de respuesta"):
        tipos_sel = st.multiselect("Mostrar", list(ETIQUETAS), default=list(ETIQUETAS),
                                   format_func=lambda t: ETIQUETAS[t], label_visibility="collapsed")

df = df_all[(df_all["fecha"] >= desde) & (df_all["fecha"] <= hasta) & (df_all["tipo"].isin(tipos_sel))]
if df.empty:
    st.info("No hay mensajes con esos filtros.")
    st.stop()

# ── Encabezado y KPIs ─────────────────────────────────────────────────────────

st.markdown("## 🎓 Tincho — asistente virtual de la UNDelta")
st.caption(f"{desde:%d/%m/%Y} → {hasta:%d/%m/%Y} · hora de Argentina")


def kpi(col, label, value, sub="", accent=LIMA):
    col.markdown(f"<div class='kpi-card' style='--accent:{accent}'><div class='kpi-label'>{label}</div>"
                 f"<div class='kpi-value'>{value}</div><div class='kpi-sub'>{sub}</div></div>", unsafe_allow_html=True)


conv = df[df["tipo"] != "inicio"]
libres = df[df["tipo"].isin(["rag", "rag_sin_dato"])]
sin_resp = int((libres["tipo"] == "rag_sin_dato").sum())
pct_sin = f"{100 * sin_resp / len(libres):.0f}%" if len(libres) else "—"

c = st.columns(6)
kpi(c[0], "Sesiones", df["sesion"].nunique(), "personas distintas (anónimas)")
kpi(c[1], "Mensajes", len(conv), f"{len(df) - len(conv)} cargas de página", VERDE)
kpi(c[2], "Preguntas libres", len(libres), f"{len(libres) - sin_resp} respondidas", DORADO)
kpi(c[3], "Sin respuesta", pct_sin, f"{sin_resp} de {len(libres)} preguntas libres", "#C75C5C")
kpi(c[4], "Consultas SIU", int((df["tipo"] == "siu_consulta").sum()),
    f"{int((df['tipo'] == 'siu_verificacion').sum())} pasos de verificación", "#5FA8D3")
kpi(c[5], "Alertas", int(df["tipo"].isin(["jailbreak", "limite"]).sum()), "jailbreak + límites de uso", "#E07A30")
st.write("")

tab_act, tab_nav, tab_libres, tab_rev, tab_ses = st.tabs(
    ["📈 Actividad", "🧭 Navegación", "💬 Preguntas libres", "🔍 Revisión de respuestas", "🗂️ Sesiones"])

LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#E9F0E4",
              margin=dict(l=10, r=10, t=40, b=10))

# ── Actividad ─────────────────────────────────────────────────────────────────
with tab_act:
    por_dia = df.groupby(["fecha", "tipo_desc", "tipo"]).size().reset_index(name="n")
    fig = px.bar(por_dia, x="fecha", y="n", color="tipo_desc", title="Mensajes por día",
                 color_discrete_map={ETIQUETAS[k]: v for k, v in PALETA.items()},
                 labels={"n": "Mensajes", "fecha": "", "tipo_desc": "Tipo"})
    fig.update_layout(**LAYOUT, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
    a, b = st.columns(2)
    por_hora = conv.groupby("hora").size().reindex(range(24), fill_value=0).reset_index(name="n")
    f1 = px.bar(por_hora, x="hora", y="n", title="Mensajes por hora del día", color_discrete_sequence=[LIMA])
    f1.update_layout(**LAYOUT, xaxis=dict(dtick=2), yaxis_title="", xaxis_title="")
    a.plotly_chart(f1, use_container_width=True)
    orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    por_sem = conv.groupby("dia_semana").size().reindex(orden, fill_value=0)
    f2 = px.bar(x=nombres, y=por_sem.values, title="Mensajes por día de la semana", color_discrete_sequence=[DORADO])
    f2.update_layout(**LAYOUT, yaxis_title="", xaxis_title="")
    b.plotly_chart(f2, use_container_width=True)
    mix = df.groupby("tipo_desc").size().reset_index(name="n")
    f3 = px.pie(mix, names="tipo_desc", values="n", hole=.5, title="Qué tipo de respuesta recibió la gente",
                color="tipo_desc", color_discrete_map={ETIQUETAS[k]: v for k, v in PALETA.items()})
    f3.update_layout(**LAYOUT)
    st.plotly_chart(f3, use_container_width=True)

# ── Navegación ────────────────────────────────────────────────────────────────
with tab_nav:
    botones = df[df["usuario"].str.startswith("[botón] ", na=False)].copy()
    botones["opcion_id"] = botones["usuario"].str.replace("[botón] ", "", regex=False)
    a, b = st.columns(2)
    top = botones["opcion_id"].value_counts().head(20).reset_index()
    top.columns = ["Opción", "Veces"]
    a.markdown("#### Botones más tocados")
    a.dataframe(top, use_container_width=True, hide_index=True)
    cmds = df[df["tipo"] == "comando"]["usuario"].str.lower().str.strip().value_counts().head(20).reset_index()
    cmds.columns = ["Palabra clave", "Veces"]
    b.markdown("#### Palabras clave escritas")
    b.dataframe(cmds, use_container_width=True, hide_index=True)
    st.caption("Los pasos de verificación y las respuestas del SIU no se guardan (privacidad): solo se cuentan.")

# ── Preguntas libres ──────────────────────────────────────────────────────────
with tab_libres:
    st.markdown("#### Preguntas sin respuesta — candidatas para ampliar la base")
    sr = df[df["tipo"] == "rag_sin_dato"]
    if sr.empty:
        st.success("No hubo preguntas sin respuesta en el período. 🎉")
    else:
        rep = sr["usuario"].str.lower().str.strip().value_counts().reset_index()
        rep.columns = ["Pregunta", "Veces"]
        st.dataframe(rep, use_container_width=True, hide_index=True)
    st.markdown("#### Todas las preguntas libres")
    tabla = libres[["ts", "tipo_desc", "usuario", "bot", "fuentes"]].rename(
        columns={"ts": "Fecha", "tipo_desc": "Tipo", "usuario": "Pregunta", "bot": "Respuesta", "fuentes": "Fuentes"})
    st.dataframe(tabla.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Descargar CSV", tabla.to_csv(index=False).encode("utf-8-sig"),
                       "tincho_preguntas_libres.csv", "text/csv")

# ── Revisión ──────────────────────────────────────────────────────────────────
with tab_rev:
    st.markdown("#### Respuestas generadas con IA, para control de calidad")
    st.caption("Leelas contra la fuente citada. Si una respuesta es incorrecta, corregí el dato en "
               "`tincho/data/institucional/` y regenerá la base (`build_kb.py`).")
    rag = libres[libres["tipo"] == "rag"].sort_values("ts", ascending=False)
    if rag.empty:
        st.info("No hay respuestas generadas en el período.")
    for _, fila in rag.head(50).iterrows():
        with st.expander(f"{fila['ts']:%d/%m %H:%M} · {fila['usuario'][:90]}"):
            st.markdown(f"**Pregunta:** {fila['usuario']}")
            st.markdown(f"**Respuesta de Tincho:**\n\n{md(fila['bot'])}")
            if fila["fuentes"]:
                st.markdown("**Fuentes consultadas:**\n\n" + "\n".join(f"- {u}" for u in fila["fuentes"].split("\n")))
    if len(rag) > 50:
        st.caption(f"Se muestran las 50 más recientes de {len(rag)}. Descargá el CSV desde «Preguntas libres» para ver todas.")

# ── Sesiones ──────────────────────────────────────────────────────────────────
with tab_ses:
    resumen = (df_all.groupby("sesion").agg(inicio=("ts", "min"), mensajes=("id", "count"))
               .sort_values("inicio", ascending=False).reset_index())
    elegida = st.selectbox("Sesión (identificador anónimo)", resumen["sesion"],
                           format_func=lambda s: f"{s} · {resumen.loc[resumen.sesion == s, 'inicio'].iloc[0]:%d/%m %H:%M} · "
                                                 f"{resumen.loc[resumen.sesion == s, 'mensajes'].iloc[0]} msj")
    for _, m in df_all[df_all["sesion"] == elegida].iterrows():
        if m["usuario"]:
            st.chat_message("user").write(f"{m['usuario']}")
        st.chat_message("assistant").write(md(m["bot"]) or "—")
        st.caption(f"{m['ts']:%H:%M:%S} · {ETIQUETAS.get(m['tipo'], m['tipo'])}")
