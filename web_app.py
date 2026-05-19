import os
import re
import csv
import unicodedata
import json
import uuid
import random
import smtplib
import time
from collections import defaultdict
from email.message import EmailMessage
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI

try:
    from tokens import openrouter_key, telegram_token, gmail_token
except ImportError:
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    telegram_token = os.getenv('TELEGRAM_TOKEN', 'fallback-secret')
    gmail_token = os.getenv('GMAIL_TOKEN', '')

app = Flask(__name__)
app.secret_key = telegram_token[:32]

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# Manual rate limiter — only applied to LLM calls
_llm_hits = defaultdict(list)

def _llm_rate_ok(ip, per_minute=3, per_hour=10, per_day=15):
    """Returns True if the IP is within LLM rate limits, False otherwise."""
    now = time.time()
    hits = [t for t in _llm_hits[ip] if now - t < 86400]
    _llm_hits[ip] = hits
    if sum(1 for t in hits if now - t < 60) >= per_minute:
        return False
    if sum(1 for t in hits if now - t < 3600) >= per_hour:
        return False
    if len(hits) >= per_day:
        return False
    _llm_hits[ip].append(now)
    return True

openai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEB_LOG_PATH = os.path.join(BASE_DIR, "web_interactions.csv")
WEB_LOG_HEADERS = ["timestamp", "session_id", "user_message", "bot_reply", "response_type", "images", "quick_replies"]

def _ensure_log():
    if not os.path.exists(WEB_LOG_PATH):
        with open(WEB_LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WEB_LOG_HEADERS)

def log_interaction(user_message, bot_reply, response_type, images=None, quick_replies=None):
    try:
        _ensure_log()
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())[:8]
            session.modified = True
        with open(WEB_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session.get('session_id', '?'),
                user_message[:300],
                (bot_reply or '')[:300],
                response_type,
                ",".join(images) if images else "",
                ",".join(quick_replies) if quick_replies else "",
            ])
    except Exception as e:
        print(f"Log error: {e}")

SYSTEM_PROMPT = (
    "Vos sos Deltix, el bot del humedal. Sos un carpincho digital que ayuda a habitantes y visitantes "
    "del Delta del Paraná en Tigre. Respondé de forma concisa y útil. No saludes ni repitas 'hola'. "
    "Fuiste creado por Facundo como proyecto comunitario del Delta del Paraná. "
    "Si te preguntan sobre tu historia u origen, decí que sos un bot que desde el 2023 está disponible en Telegram "
    "y desde el 2026 en formato web, y que buscás crear un espacio digital comunitario, anticapitalista "
    "y en defensa de los humedales — no inventes más detalles. "
    "NUNCA inventes información: no alucines nombres de lanchas, cooperativas, almaceneras, horarios, "
    "precios ni datos de contacto que no estén en el contexto provisto. "
    "Si no tenés el dato, decí que no lo tenés y sugerí las palabras clave disponibles: "
    "clima, mareas, hidrografia, windguru, colectivas, almaceneras, actividades. "
    "Sobre datos de contacto: si el usuario pide explícitamente el contacto, teléfono o WhatsApp "
    "de un emprendimiento, dalo siempre de forma directa y completa — nunca digas que está oculto "
    "ni que no podés compartirlo. Si el usuario solo pregunta qué servicios hay o qué hace un emprendimiento, "
    "no incluyas el número a menos que sea imprescindible; en ese caso podés mencionar que tiene contacto disponible."
)

KEYWORDS = {
    # 'tiempo' y 'viento' removidos — demasiado ambiguos; viento sólo en windguru
    "weather":     ['clima', 'temperatura', 'pronostico', 'pronóstico', 'lluvia', 'tormenta',
                    'calor', 'frio', 'frío', 'nublado', 'el tiempo', 'qué tiempo', 'que tiempo'],
    # crecida/inundación agregados
    "tides":       ['mareas', 'marea', 'pleamar', 'bajamar',
                    'crecida', 'inundacion', 'inundación', 'nivel del rio', 'nivel del río',
                    'subio el rio', 'subió el río', 'bajo el rio', 'bajó el río'],
    # 'naval' removido — demasiado genérico
    "hidrografia": ['hidrografia', 'hidrografía'],
    "agenda":      ['agenda', 'actividades', 'emprendimientos', 'agenda del rio', 'agenda del río'],
    # 'viento' mantenido aquí (único lugar), 'wind' removido — inglés innecesario
    "windguru":    ['windguru', 'viento'],
    "jilguero":    ['jilguero', 'carapachay', 'angostura'],
    "interislena": ['interisleña', 'interislena', 'sarmiento', 'san antonio', 'capitan', 'capitán',
                    'paso del toro', 'rama negra', 'antequera', 'cruz colorada', 'felicaria',
                    'arroyo toro', 'abra vieja', 'fredes', 'estudiantes', 'puy carabi', 'canal 5'],
    "lineasdelta": ['lineasdelta', 'lineas delta', 'caraguata', 'canal arias'],
    # 'horarios' removido — demasiado genérico, activa flujo colectivas para cualquier negocio
    "colectivas":  ['colectivas', 'lancha', 'lanchas', 'horario de lancha', 'horarios de lancha',
                    'horario del barco', 'barco colectivo'],
    # delivery/provisiones agregados
    "almacen":     ['almacen', 'almacén', 'almacenera', 'almaceneras',
                    'delivery', 'provisiones', 'mercaderia', 'mercadería', 'abastecimiento'],
    "activities":  ['actividades', 'emprendimientos', 'qué hacer', 'que hacer', 'qué visitar',
                    'que visitar', 'paseos', 'experiencias', 'turismo', 'recorrido'],
    # 'canoa' sola removida — demasiado genérica
    "amanita":     ['amanita', 'paseo en canoa', 'excursion canoa', 'excursión canoa', 'canoa isleña'],
    # 'barro' removido — muy común en contexto del delta (barro/lodo)
    "alfareria":   ['alfareria', 'alfarería', 'arcilla', 'kutral', 'taller de barro'],
    # 'busqueda' y 'busqueda' solas removidas; 'alimentos' removido
    "labusqueda":  ['labusqueda', 'la busqueda', 'la búsqueda', 'hostal', 'hostal delta', 'ceremonias'],
    "kayaks":      ['kayak', 'kayaks', 'canaveral', 'cañaveral'],
    "masajes":     ['masaje', 'masajes', 'charco', 'thai'],
    # 'alimentos' removido — demasiado genérico
    "familia":     ['familia islena', 'familia isleña', 'dietetica', 'dietética', 'piojo isleno'],
    "frutales":    ['frutales', 'citricos', 'cítricos', 'limonero', 'naranjas', 'mandarina', 'planta frutal'],
    "dulceras":    ['dulceras', 'dulcera', 'dulceras del rio', 'reposteria', 'repostería'],
    "vivero":      ['vivero', 'tierra fertil', 'tierra fértil', 'compost', 'igarape', 'igarapé', 'huerta'],
    "nahuel":      ['nahuel servicios', 'poda de arboles', 'poda en altura', 'carpinteria isla',
                    'carpintería isla', 'zanja', 'mantenimiento isla', 'nahuel delta'],
    "aguariba":    ['aguariba', 'agroecologico', 'agroecológico', 'verduras delta', 'bolson agroecologico',
                    'bolsón agroecológico'],
    # calefacción/estufa agregados
    "lena":        ['leña', 'lena', 'quebracho', 'salamandra', 'ligustro', 'calefaccion',
                    'calefacción', 'estufa a leña', 'estufa a lena'],
    "memes":       ['meme', 'memes'],
    "sublinor":    ['sublinor', 'imprenta'],
    "yoga":        ['yoga', 'iyengar'],
    # 'igarape delta' (2 palabras) se chequea ANTES que 'vivero' para evitar
    # que 'igarape' solo matchee al vivero cuando el usuario busca las excursiones
    "igarapedelta": ['igarape delta', 'delta salvaje', 'guia naturalista', 'senderismo delta'],
    # Lanchas taxis y fletes — subcategorías específicas primero, luego el menú general
    "fletesmareaexpress": ['fletes marea express', 'marea express'],
    "viajesvita":         ['viajes vita', 'vita delta', 'fletes vita'],
    "oscart":             ['oscar t', 'oscar traslados', 'arroyo espera viajes'],
    "taxifletes":         ['taxifletes', 'taxi fletes', 'lancha taxi', 'traslado isla', 'flete isla'],
}

def _norm(s):
    """Lowercase + strip accents for accent-insensitive keyword matching."""
    return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('ascii')

# Pre-normalized keyword lists (computed once at startup)
KEYWORDS_NORM = {k: [_norm(kw) for kw in v] for k, v in KEYWORDS.items()}

def is_winter():
    return datetime.now().month in [4, 5, 6, 7, 8, 9]


def load_rag_file(filename):
    try:
        with open(os.path.join(BASE_DIR, "rag", filename), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def load_weather_data():
    try:
        with open(os.path.join(BASE_DIR, "rag", "weather_data.json"), 'r') as f:
            return json.load(f)
    except Exception:
        return None


def load_tides_text():
    try:
        with open(os.path.join(BASE_DIR, "table_data.txt"), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def format_hidrografia():
    try:
        with open(os.path.join(BASE_DIR, "table_data.txt"), 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not lines:
            return "No hay datos de hidrografía en este momento."
        msg = "📊 PRONÓSTICO DE MAREAS — HIDROGRAFÍA NAVAL\n\n"
        if lines:
            msg += f"🚢 {lines[0].strip()}\n\n"
        for line in lines[2:]:
            data = line.strip().split('\t')
            if len(data) >= 4:
                tide_type, time_, height, date = data[0], data[1], data[2], data[3]
                emoji = "🌊" if tide_type.upper() == "PLEAMAR" else "⬇️"
                msg += f"{emoji} {tide_type}: {time_} hs — {height} m ({date})\n"
        return msg
    except Exception:
        return "No se pudo cargar la información de hidrografía."


def build_llm_context(user_input):
    text = _norm(user_input)
    context = []
    if any(k in text for k in KEYWORDS_NORM["weather"]):
        w = load_weather_data()
        if w:
            current = w.get('current_weather', {})
            temp = current.get('main', {}).get('temp', 'N/A')
            feels = current.get('main', {}).get('feels_like', 'N/A')
            humidity = current.get('main', {}).get('humidity', 'N/A')
            desc = current.get('weather', [{}])[0].get('description', 'N/A')
            wind = current.get('wind', {}).get('speed', 'N/A')
            context.append(f"Clima en Tigre: {temp}°C (sensación {feels}°C), {desc}, humedad {humidity}%, viento {wind} m/s")
    if any(k in text for k in KEYWORDS_NORM["tides"] + KEYWORDS_NORM["hidrografia"]):
        context.append(load_tides_text())
    if any(k in text for k in KEYWORDS_NORM["almacen"]):
        context.append(load_rag_file("almaceneras.txt"))
    if any(k in text for k in KEYWORDS_NORM["jilguero"]):
        context.append(load_rag_file("jilguero.txt"))
    if any(k in text for k in KEYWORDS_NORM["interislena"]):
        context.append(load_rag_file("interislena.txt"))
    if any(k in text for k in KEYWORDS_NORM["lineasdelta"]):
        context.append(load_rag_file("lineasdelta.txt"))
    _base_act_kws = (KEYWORDS_NORM["activities"] + KEYWORDS_NORM["amanita"] + KEYWORDS_NORM["alfareria"] +
                     KEYWORDS_NORM["labusqueda"] + KEYWORDS_NORM["kayaks"] + KEYWORDS_NORM["masajes"] +
                     KEYWORDS_NORM["familia"] + KEYWORDS_NORM["frutales"] + KEYWORDS_NORM["dulceras"] +
                     KEYWORDS_NORM["vivero"] + KEYWORDS_NORM["nahuel"] + KEYWORDS_NORM["aguariba"] +
                     KEYWORDS_NORM["sublinor"] + KEYWORDS_NORM["yoga"] + KEYWORDS_NORM["igarapedelta"] +
                     KEYWORDS_NORM["taxifletes"] + KEYWORDS_NORM["fletesmareaexpress"] +
                     KEYWORDS_NORM["viajesvita"] + KEYWORDS_NORM["oscart"])
    _lena_ok = (any(k in text for k in KEYWORDS_NORM["lena"]) and
                not any(k in text for k in KEYWORDS_NORM["interislena"]))
    if any(k in text for k in _base_act_kws) or _lena_ok:
        context.append(load_rag_file("actividades.txt"))
    return "\n\n".join(c for c in context if c)


# ── Almaceneras data ──────────────────────────────────────────────────────────

ALMACENERAS = {
    "Nilda Alicia":    "🛒 *Nilda Alicia* (Anita) — Miguel Machado\nMARTES, VIERNES: Río Sarmiento / Río San Antonio\nMIÉRCOLES, SÁBADO: Río Capitán / Rama Negra / Arroyo Toro\n📞 1557490961",
    "Cachito":         "🛒 *Cachito* — Aníbal Isea\nLUN, MIÉ, VIE, SÁB: Río Carapachay hasta el 500\nDOMINGO: Río Carapachay hasta Angostura\n📞 11 6572-1030",
    "Elsa María":      "🛒 *Elsa María* — Mayorista\n📞 1565548280",
    "Sta. Teresita A": "🛒 *Santa Teresita* (ex Negrita) — Ángel Ojeda\nMARTES y SÁBADO: Río Carapachay hasta Río Paraná\nMIÉRCOLES y VIERNES: Arroyo Espera hasta Cruz Colorada\n📞 1532661770",
    "Juan y Juan":     "🛒 *Juan y Juan* — Tito Hendenreich — Mayorista\n📞 15 5095771 / 15 31905299",
    "Sta. Teresita R": "🛒 *Santa Teresita* — Ricardo Ojeda\nMARTES, JUEVES, SÁBADO y DOMINGO\nRío Luján / Canal Arias hasta el Paraná",
    "Adriana":         "🛒 *Adriana* — Leo Rinaldi\nMIÉRCOLES, DOMINGO: Arroyo Abra Vieja\nJUEVES, SÁBADO: Toro / Antequera / Arroyo Banco / Andresito\n📞 1569789983",
    "Buena Vida":      "🛒 *Buena Vida* — Cristian Lara\nLUNES: Arroyo Dorado / Sábalos / Arroyon / Boraso\nVIERNES: Arroyo Tiburón / Canal del Este y Aguajes\n📞 1553395931",
    "Esperanza R":     "🛒 *Esperanza R* — Oscar Suárez\nMARTES, JUEVES y SÁBADO\nRío Carapachay hasta Sienará / Río Luján / Arroyo Caraguatá hasta el 400\n📞 1565098174",
    "Gardenia":        "🛒 *Gardenia* — Mayorista\n📞 1540554422 / 1531882922",
    "Gloria I":        "🛒 *Gloria I* — Jorge Rinaldi\nMIÉRCOLES: Río San Antonio / Canal Honda / Aguaje del Durazno\nJUEVES: Chaná / Paraná Mini / Tuyú Paré\nVIERNES: Arroyo Correntoso / La Barca / La Barquita\n📞 1531298913",
    "Ignacio Franco":  "🛒 *Ignacio Franco* — Familia Bettiga\nMIÉRCOLES: Río Sarmiento / Capitán hasta Club Imos / Fredes\nJUEVES: Río Capitán / Arroyo Fredes\nVIERNES: Arroyo Estudiante / Felicaria / Paraná Mini\nSÁBADO: Arroyo Fredes / Paraná Miní / Tuyú Paré / Chaná\n📞 1562828206",
    "Madreselva":      "🛒 *Madreselva* — Familia Bettiga\nMIÉRCOLES: Capitán arriba / Estudiante / Paicarabí\nJUEVES: Río Sarmiento / Espera / Cruz Colorada\nVIERNES: Paicarabí / Canal La Serna / Canal 4\n📞 1554709382",
    "Raquel N":        "🛒 *Raquel N* — Roberto Baraldo\nLUNES y SÁBADO: Río Sarmiento / Capitán / Arroyo La Horca\nMARTES y MIÉRCOLES: Río Paraná hasta Carabelas / Canal 5\n📞 1544981064",
    "Stella Maris":    "🛒 *Stella Maris* — Manuel Compagnucci\nVIERNES: Escobar / Paraná / Paycaraby / Estudiantes / Las Cañas\nSÁBADOS: Puerto Escobar / La Serna / Arroyo Chana / Felicaria\n📞 1562771474",
}

AGENDA_OPTIONS = {
    "Amanita Canoa":       "amanita canoa",
    "Kutral Alfarería":    "alfareria kutral",
    "La Búsqueda":         "la busqueda",
    "Cañaveral Kayaks":    "canaveral kayaks",
    "Masaje Thai":         "masaje thai",
    "Familia Isleña":      "familia islena",
    "Planta Frutales":     "planta frutales",
    "Dulceras del Río":    "dulceras del rio",
    "Vivero Isleño":       "vivero isleno",
    "Nahuel Servicios":    "nahuel servicios",
    "Aguariba Anfibia":    "aguariba",
    "Leña a tu Muelle":    "leña muelle",
    "Sublinor Gráfica 🖨️":    "sublinor imprenta",
    "Yoga con Lau 🧘":        "yoga lau",
    "Igarapé Delta 🌿":       "igarape delta senderismo",
    "Lanchas Taxis y Fletes 🚤": "taxifletes traslado lancha",
}


SOCIAL_GREETINGS = ['hola', 'buenas', 'buen dia', 'buen día', 'buenos dias', 'buenos días',
                    'buenas tardes', 'buenas noches', 'hey']
SOCIAL_THANKS    = ['gracias', 'muchas gracias', 'mil gracias', 'grax']
SOCIAL_BYE       = ['chau', 'adios', 'adiós', 'hasta luego', 'nos vemos']

def _social_match(text, keywords):
    """Coincidencia con word boundary para evitar falsos positivos en substrings.
    Normaliza tanto el texto como las keywords para matching sin tildes."""
    text_n = _norm(text)
    return any(re.search(r'\b' + re.escape(_norm(k)) + r'\b', text_n) for k in keywords)

GREETING_REPLIES = [
    "¡Hola! Soy Deltix, el bot del humedal 🦦 ¿En qué te puedo ayudar?\n\nPreguntame sobre clima, mareas, colectivas, almaceneras o actividades del Delta.",
    "¡Buenas! Soy Deltix 🌿 Estoy acá para ayudarte con info del Delta del Paraná.\n\nPreguntame sobre clima, mareas, horarios de lanchas, almaceneras o actividades.",
    "¡Hola! 🦦 ¿Qué necesitás saber del Delta?",
]
THANKS_REPLIES = [
    "¡De nada! Es un placer ayudar a lxs humanos que visitan el humedal 🦦",
    "¡De nada! Siempre a disposición 🌿",
    "¡Con gusto! Para eso estoy 🦦",
]
BYE_REPLIES = [
    "¡Hasta luego! Que disfrutes el humedal 🌿",
    "¡Chau! Volvé cuando quieras 🦦",
    "¡Hasta la próxima! Que estés bien 🌿",
]

GREETING_CHIPS = ["🌤️ Clima", "🌊 Mareas", "⛵ Colectivas", "🛒 Almaceneras", "🗓️ Agenda del Río"]


def handle_social_flow(user_input):
    """
    Responde a saludos, agradecimientos y despedidas sin llamar al LLM.
    - Solo actúa sobre mensajes cortos (≤ 6 palabras).
    - No interrumpe flows activos (almaceneras, colectivas, agenda).
    - Usa word boundaries para evitar falsos positivos en substrings.
    """
    # No interrumpir si hay un flow multi-paso activo
    if session.get('alm_flow') or session.get('col') or session.get('agenda_flow'):
        return None

    text = user_input.strip()
    if len(text.split()) > 6:
        return None

    if _social_match(text, SOCIAL_THANKS):
        return {"reply": random.choice(THANKS_REPLIES), "images": [], "quick_replies": []}

    if _social_match(text, SOCIAL_BYE):
        return {"reply": random.choice(BYE_REPLIES), "images": [], "quick_replies": []}

    if _social_match(text, SOCIAL_GREETINGS):
        return {"reply": random.choice(GREETING_REPLIES), "images": [], "quick_replies": GREETING_CHIPS}

    return None


def _is_different_topic(text):
    """Devuelve True si el texto claramente corresponde a otro dominio."""
    text = _norm(text)
    other_kws = (
        KEYWORDS_NORM["weather"] + KEYWORDS_NORM["tides"] + KEYWORDS_NORM["hidrografia"] +
        KEYWORDS_NORM["agenda"] + KEYWORDS_NORM["windguru"] + KEYWORDS_NORM["jilguero"] +
        KEYWORDS_NORM["interislena"] + KEYWORDS_NORM["lineasdelta"] + KEYWORDS_NORM["colectivas"] +
        KEYWORDS_NORM["memes"]
    )
    return any(k in text for k in other_kws)


def handle_almaceneras_flow(user_input):
    text = user_input.strip()
    text_lower = _norm(text)
    alm = session.get('alm_flow')

    _alm_note = "La comunidad Deltix se fortalece por el aporte de habitantes de la isla 🌿"

    if alm and alm.get('step') == 'select':
        # Buscar coincidencia con nombre de almacenera
        for name, info in ALMACENERAS.items():
            if _norm(name) in text_lower or text_lower in _norm(name):
                session.pop('alm_flow', None)
                session.modified = True
                return {"reply": info, "images": [], "quick_replies": ["✏️ Sugerí una modificación"], "note": _alm_note}
        # Sin coincidencia — si es otro tema, liberar el flow
        if _is_different_topic(text_lower):
            session.pop('alm_flow', None)
            session.modified = True
            return None
        # Mismo tema pero input inválido — repetir menú
        return {"reply": "Elegí una almacenera de la lista 👇",
                "images": [], "quick_replies": list(ALMACENERAS.keys())}

    if any(k in text_lower for k in KEYWORDS_NORM["almacen"]):
        session['alm_flow'] = {'step': 'select'}
        session.modified = True
        return {"reply": "¿Cuál almacenera querés consultar? 🛒",
                "images": [], "quick_replies": list(ALMACENERAS.keys())}

    return None


def handle_agenda_flow(user_input):
    text = user_input.strip()
    text_lower = _norm(text)
    agenda = session.get('agenda_flow')

    if agenda and agenda.get('step') == 'select':
        for label, query in AGENDA_OPTIONS.items():
            # Ignorar palabras de 3 letras o menos (ej. "del", "rio", "lau")
            # para evitar falsos positivos por substring (ej. "del" dentro de "delta")
            words = [w for w in query.split() if len(w) >= 4]
            if words and any(w in text_lower for w in words):
                session.pop('agenda_flow', None)
                session.modified = True
                return detect_quick_response(query)
        # Sin coincidencia — si es otro tema, liberar el flow
        if _is_different_topic(text_lower):
            session.pop('agenda_flow', None)
            session.modified = True
            return None
        return {"reply": "Elegí una actividad 👇",
                "images": [], "quick_replies": list(AGENDA_OPTIONS.keys())}

    if any(k in text_lower for k in KEYWORDS_NORM["agenda"]):
        session['agenda_flow'] = {'step': 'select'}
        session.modified = True
        return {"reply": "¿Qué actividad te interesa? 🌿",
                "images": [], "quick_replies": list(AGENDA_OPTIONS.keys()) + ["➕ Sumá tu emprendimiento", "✏️ Cambiar o dar de baja mis datos"]}

    return None


def handle_memes_flow(user_input):
    text = _norm(user_input).strip()
    meme = session.get('meme_flow')

    if meme:
        step = meme.get('step')

        # Word boundaries para evitar falsos positivos: "no" en "invierno", "si" en substrings, etc.
        def _mw(keywords, t):
            return any(re.search(r'\b' + re.escape(k) + r'\b', t) for k in keywords)

        if step == 'more':
            if _mw(['si', 'sí', 'dale', 'otro', 'mas', 'más', 'meme'], text):
                session['meme_flow'] = {'step': 'more2'}
                session.modified = True
                n = random.randint(1, 56)
                return {"reply": None,
                        "images": [f"/img/memes/{n}.png"],
                        "footer_text": "Uno más? 😄",
                        "quick_replies": ["Sí, otro 😄", "No gracias"]}
            if _mw(['no', 'gracias', 'listo'], text):
                session.pop('meme_flow', None)
                session.modified = True
                return {"reply": "Bueno... si querés podés seguir explorando el delta con Deltix 🦫",
                        "images": [], "quick_replies": []}

        if step == 'more2':
            if _mw(['si', 'sí', 'dale', 'otro', 'mas', 'más', 'meme'], text):
                session['meme_flow'] = {'step': 'more'}
                session.modified = True
                n = random.randint(1, 56)
                return {"reply": None,
                        "images": [f"/img/memes/{n}.png"],
                        "footer_text": "Te mando otro? 😄",
                        "quick_replies": ["Sí, otro 😄", "No gracias"]}
            if _mw(['no', 'gracias', 'listo'], text):
                session.pop('meme_flow', None)
                session.modified = True
                return {"reply": "Bueno... si querés podés seguir explorando el delta con Deltix 🦫",
                        "images": [], "quick_replies": []}

        return None

    if any(k in text for k in KEYWORDS_NORM["memes"]):
        session['meme_flow'] = {'step': 'more'}
        session.modified = True
        n = random.randint(1, 56)
        return {
            "reply": "...me encantan los memes islenials 😄 Te mando uno:",
            "images": [f"/img/memes/{n}.png"],
            "footer_text": "Buenísimo, no? Son de la página **Memes Islenials**. Te recomiendo que la sigas en las redes 🏝️",
            "quick_replies": ["Otro meme 😄", "No gracias"]
        }

    return None


def handle_colectivas_flow(user_input):
    """
    Maneja el flujo conversacional de colectivas paso a paso.
    Guarda el estado en session['col']. Retorna dict o None.
    Preguntas específicas (con '?', 'cuándo', etc.) van al LLM con RAG.
    """
    text = _norm(user_input).strip()
    col = session.get('col')

    # Preguntas específicas de horario → LLM con RAG (no flujo guiado)
    if not col:
        specific_patterns = ['?', 'cuando', 'a que hora', 'que hora',
                             'ultim', 'primer', 'sale desde', 'llega a', 'demora',
                             'tarda', 'horario de', 'cuantos', 'hay servicio']
        if any(p in text for p in specific_patterns):
            return None

    # ── Estamos dentro de un flujo activo ──
    if col:
        step = col.get('step')

        if step == 'linea':
            if any(k in text for k in KEYWORDS_NORM["jilguero"]):
                session['col'] = {'step': 'direccion', 'linea': 'jilguero'}
                session.modified = True
                return {"reply": "Jilguero 🚢 ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}
            if any(k in text for k in KEYWORDS_NORM["interislena"]):
                session['col'] = {'step': 'temporada', 'linea': 'interislena'}
                session.modified = True
                return {"reply": "Interisleña ⛵ ¿Qué temporada?", "images": [],
                        "quick_replies": ["Invierno", "Verano"]}
            if any(k in text for k in KEYWORDS_NORM["lineasdelta"]):
                session['col'] = {'step': 'periodo', 'linea': 'lineasdelta'}
                session.modified = True
                return {"reply": "Líneas Delta 🛥️ ¿Período escolar o no escolar?", "images": [],
                        "quick_replies": ["Escolar", "No escolar"]}

        elif step == 'temporada':
            if 'invierno' in text:
                session['col'] = {**col, 'step': 'direccion', 'temporada': 'invierno'}
                session.modified = True
                return {"reply": "Temporada invierno ❄️ ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}
            if 'verano' in text:
                session['col'] = {**col, 'step': 'direccion', 'temporada': 'verano'}
                session.modified = True
                return {"reply": "Temporada verano ☀️ ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}

        elif step == 'periodo':
            if 'no' in text:
                session['col'] = {**col, 'step': 'direccion', 'periodo': 'no_escolar'}
                session.modified = True
                return {"reply": "Período no escolar 🏖️ ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}
            if 'escolar' in text:
                session['col'] = {**col, 'step': 'direccion', 'periodo': 'escolar'}
                session.modified = True
                return {"reply": "Período escolar 📚 ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}

        elif step == 'direccion':
            if 'ida' in text:
                direccion = 'ida'
            elif 'vuelta' in text:
                direccion = 'vuelta'
            else:
                # Respuesta inválida — recordamos las opciones
                return {"reply": "Por favor elegí una opción:", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}

            linea = col.get('linea')
            session.pop('col', None)
            session.modified = True

            _col_note = "La comunidad Deltix se fortalece por el aporte de habitantes de la isla 🌿"

            if linea == 'jilguero':
                return {
                    "reply": f"Jilguero — {direccion.capitalize()} 🚢",
                    "images": [f"/img/colectivas/jilguero_{direccion}.png"],
                    "quick_replies": ["✏️ Sugerí una modificación"],
                    "note": _col_note
                }
            if linea == 'interislena':
                temporada = col.get('temporada', 'invierno')
                temp_label = temporada.capitalize()
                if direccion == 'ida':
                    return {
                        "reply": f"Interisleña — Ida — {temp_label} ⛵\nSalidas desde Tigre hacia las islas:",
                        "images": [f"/img/colectivas/interislena_ida_{temporada}.png"],
                        "quick_replies": [
                            "¿Horarios de vuelta de Interisleña?",
                            "¿Horarios de un recorrido específico de Interisleña?",
                            "✏️ Sugerí una modificación"
                        ],
                        "note": _col_note
                    }
                else:  # vuelta — respuesta textual con recorridos completos del PDF
                    return {
                        "reply": (
                            f"Interisleña — Vuelta — {temp_label} ⛵\n"
                            "Salidas hacia Est. Fluvial Tigre, Muelle 2:\n\n"
                            "🚢 **Río Tigre, Luján, Sarmiento, Capitán hasta Paso del Toro**\n"
                            "L-V: 6:30 / 7:30 / 8:30 / 10:30 / 12:30 / 14:50 / 16:10 / 16:50 / 18:00 / 20:10\n"
                            "Sáb: 6:30 / 7:30 / 8:30 / 9:15 / 10:30 / 11:15 / 12:15 / 12:30 / 13:50 / 15:15 / 16:30 / 18:00 / 19:15 / 20:10\n"
                            "Dom: 7:30 / 9:15 / 10:30 / 11:15 / 12:15 / 12:30 / 13:50 / 15:15 / 16:30 / 18:00 / 19:15 / 20:10\n\n"
                            "🛥️ **Río Tigre, Luján, Sarmiento, Capitán, Paraná de las Palmas**\n"
                            "L-V: 6:30 / 8:30 / 10:30 / 12:30 / 15:00 / 16:50 / 18:00 / 20:00\n"
                            "Sáb: 6:30 / 8:30 / 10:30 / 12:00 / 16:30 / 17:30 / 18:00 / 19:20 / 20:00\n"
                            "Dom: 10:30 / 12:00 / 15:00 / 16:30 / 17:30 / 18:00 / 19:20 / 20:00\n\n"
                            "⛵ **Río Tigre, Luján, Sarmiento, Capitán, Arroyo Antequera**\n"
                            "L-V: 8:00 / 12:30 · Sáb: 8:00 / 11:30 / 18:30 · Dom: 18:00 / 19:30 / 20:00\n\n"
                            "🌿 **Río Tigre, Luján, Sarmiento, Espera hasta Cruz Colorada**\n"
                            "L-V: 7:00 / 12:00 / 18:00 · Sáb: 7:00 / 12:00 / 18:00 / 19:30 · Dom: 19:30\n\n"
                            "🌊 **Río Tigre, Luján, Sarmiento, Capitán, Arroyo Toro**\n"
                            "L-V: 7:30 / 18:00 · Sáb: 7:30 / 11:15 / 18:50 · Dom: 7:30 / 11:15\n\n"
                            "⬆️ **Río Tigre, Luján, Sarmiento, Capitán, Arroyo Rama Negra**\n"
                            "L-V: 7:30 / 18:00 · Sáb: 7:30 / 12:15 / 18:00 / 19:30 · Dom: 7:30 / 12:15 / 19:30\n\n"
                            "🛶 **Río Tigre, Luján, Sarmiento, Capitán, Paraná de las Palmas, Arroyo Felicaria**\n"
                            "L/Ma/V: 6:30 · L-V: 16:50 · Sáb: 6:30 / 12:00 / 16:30 / 20:00 · Dom: 12:00 / 16:30 / 20:00"
                        ),
                        "images": [],
                        "quick_replies": [
                            "¿Horarios completos desde Paso del Toro?",
                            "¿Horarios completos desde Antequera?",
                            "✏️ Sugerí una modificación"
                        ],
                        "note": _col_note
                    }
            if linea == 'lineasdelta':
                periodo = col.get('periodo', 'escolar')
                label = periodo.replace('_', ' ')
                return {
                    "reply": f"Líneas Delta — {direccion.capitalize()} — {label.capitalize()} 🛥️",
                    "images": [f"/img/colectivas/lineas_delta_{direccion}_{periodo}.png"],
                    "quick_replies": ["✏️ Sugerí una modificación"],
                    "note": _col_note
                }

    # ── Inicio del flujo desde cero ──
    if any(k in text for k in KEYWORDS_NORM["colectivas"]):
        session['col'] = {'step': 'linea'}
        session.modified = True
        return {"reply": "¿Qué línea de colectiva querés consultar? 🚢", "images": [],
                "quick_replies": ["Jilguero", "Interisleña", "Líneas Delta"]}

    if any(k in text for k in KEYWORDS_NORM["jilguero"]):
        session['col'] = {'step': 'direccion', 'linea': 'jilguero'}
        session.modified = True
        return {"reply": "Jilguero 🚢 ¿Ida o vuelta?", "images": [],
                "quick_replies": ["Ida", "Vuelta"]}

    if any(k in text for k in KEYWORDS_NORM["interislena"]):
        session['col'] = {'step': 'temporada', 'linea': 'interislena'}
        session.modified = True
        return {"reply": "Interisleña ⛵ ¿Qué temporada?", "images": [],
                "quick_replies": ["Invierno", "Verano"]}

    if any(k in text for k in KEYWORDS_NORM["lineasdelta"]):
        session['col'] = {'step': 'periodo', 'linea': 'lineasdelta'}
        session.modified = True
        return {"reply": "Líneas Delta 🛥️ ¿Período escolar o no escolar?", "images": [],
                "quick_replies": ["Escolar", "No escolar"]}

    return None


def detect_quick_response(user_input):
    """
    Detecta si el mensaje coincide con un comando específico y devuelve
    texto + imágenes sin necesidad de llamar al LLM.
    Retorna None si no hay coincidencia directa.
    """
    text = _norm(user_input)

    if any(k in text for k in KEYWORDS_NORM["hidrografia"]):
        return {"reply": format_hidrografia(), "images": [], "quick_replies": []}

    if any(k in text for k in KEYWORDS_NORM["tides"]) and not any(k in text for k in KEYWORDS_NORM["fletesmareaexpress"]):
        return {"reply": "Acá tenés el pronóstico de mareas del INA 🌊",
                "images": ["/img/marea.png"], "quick_replies": []}

    if any(k in text for k in KEYWORDS_NORM["windguru"]):
        return {"reply": "Pronóstico de WindGurú para las islas ☁️",
                "images": ["/img/windguru.png"], "quick_replies": []}

    if any(k in text for k in KEYWORDS_NORM["amanita"]):
        return {
            "reply": "🛶 **Experiencias en Canoa Isleña**\n\nPaseos por el Delta del Paraná\nCon guía bilingüe (opcional)\nServicio puerta a puerta (opcional)\n\nInstagram: amanitaturismodelta\nContacto: 1169959272",
            "images": ["/img/actividades_productos/amanita.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["alfareria"]):
        return {
            "reply": "🏺 **Kutral Alfarería**\n\nEncuentros con el barro\nTalleres de alfarería\nExperimentación y creación con arcilla\n\nInstagram: kutralalfareria",
            "images": ["/img/actividades_productos/alfareria.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["labusqueda"]):
        return {
            "reply": "🌿 **La Búsqueda**\n\nEspacio para encuentros y ceremonias\nHostal en el Delta\nConexión con la naturaleza\n\nInstagram: labusqueda_cabanadelta\nContacto: 1150459556",
            "images": ["/img/actividades_productos/labusqueda.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["kayaks"]):
        return {
            "reply": "🚣 **Cañaveral Kayaks**\n\nExcursiones en kayak\nPaseos con guía\nRemadas nocturnas\n\nlinktr.ee/canaveralkayaks\nContacto: 1126961274",
            "images": ["/img/actividades_productos/canaveralkayaks.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["masajes"]):
        return {
            "reply": "💆 **Masaje Thai**\n\nen el Tres Bocas\n@estecharco\nContacto: 1122541171",
            "images": ["/img/actividades_productos/charco_masajes.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["familia"]):
        return {
            "reply": "🌾 **La Familia Isleña**\n\nAlimentos dietéticos, nutritivos y a buen precio\nHarinas, arroces, lentejas, porotos, frutos secos y más\nRepartos a tu muelle con envíos gratis todas las semanas\n\nPedidos al WhatsApp de Jorge (Piojo): 11 3046-6301",
            "images": ["/img/actividades_productos/familia_islena_flyer.jpg"]
        }

    if any(k in text for k in KEYWORDS_NORM["frutales"]):
        return {
            "reply": "🍋 **Planta Frutales**\n\nVenta de plantas cítricas para islas y amarras\nLimoneros, Mandarinas, Naranjas, Kinotos, Pomelos y más\n\nPrecios (macetas 6 lts): $26.000 c/u · $25.000 x5 · $24.000 x10\nEntrega en CABA, Zona Norte, Islas y Amarras\n\nContacto: 116 369 0177",
            "images": ["/img/actividades_productos/frutales.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["dulceras"]):
        return {
            "reply": "🍯 **Dulceras del Río**\n\nProductos dulces y repostería artesanal\nEntregas los jueves en Amarras Hugo del Carril\nPuntos de entrega: Amarra Hugo Carril · Muelle La Anacahuita Río Carpachay\nReutilizamos frascos de vidrio 🫙\n\nInstagram: @dulcerasdelrio\nContacto: 11 5525 3829",
            "images": ["/img/actividades_productos/dulceras1.jpeg", "/img/actividades_productos/dulceras2.jpeg"]
        }

    # Igarapé Delta excursiones — chequeado ANTES de vivero porque 'igarape delta'
    # (2 palabras) es más específico que 'igarape' solo (que pertenece al vivero)
    if any(k in text for k in KEYWORDS_NORM["igarapedelta"]):
        return {
            "reply": "🌿 **Igarapé Delta**\n\nExcursiones de Navegación, Senderismo, Canotaje y Turismo Rural\nNaturaleza · Cultura · Aventura — Delta Salvaje\nGuía Local Isleño Naturalista\n\nInstagram: @igarapedelta\nContacto: 005491159233663",
            "images": []
        }

    if any(k in text for k in KEYWORDS_NORM["vivero"]):
        return {
            "reply": "🌱 **Vivero Isleño — Cooperativa Igarapé Delta**\n\n\"Hacer huerta es terapia\"\n\nTierra Fértil: $9.200 (bolsas 40 lts)\nCompost Orgánico: $11.500\n10% descuento pidiendo 30 bolsas o más\n\nEntrega en tu muelle · Zona Correa y San Antonio\nContacto: 1159233663",
            "images": ["/img/actividades_productos/vivero_isleno.jpeg"]
        }

    if any(k in text for k in KEYWORDS_NORM["nahuel"]):
        return {
            "reply": "🔨 **Nahuel Servicios**\n\nTrabajos para tu hogar y terreno en el Delta\n· Poda en altura (corte y mantenimiento de árboles)\n· Movimiento de tierra y zanjas\n· Carpintería: decks, torres de agua, estructuras en madera\n· Limpieza de terrenos y mantenimiento general\n\nContacto: Nahuel — 11 5349 2653",
            "images": ["/img/actividades_productos/nahuel.jpeg"]
        }

    if any(k in text for k in KEYWORDS_NORM["aguariba"]):
        return {
            "reply": "🥬 **Aguariba Anfibia**\n\nProducción agroecológica del Delta\nPedidos para entrega el miércoles\n(cargar hasta el lunes a las 22hs)\n40% de reintegro con CUENTA DNI 💳\n\nWeb: aguaribayanfibia.com.ar\nInstagram: @aguaribayanfibia",
            "images": ["/img/actividades_productos/aguariba.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["yoga"]):
        return {
            "reply": "🧘 **Yoga con Lau**\n\nClases de Yoga Iyengar en la isla para adultxs\nNo se necesita experiencia previa\n\n📅 Lunes 10 a 11:30hs\n📅 Jueves 16:30 a 18hs\n📍 Cabañas Mayuwausi — Arroyo Reyes\n\nInstagram: @lau_g_yoga\nContacto: 1130614215",
            "images": ["/img/actividades_productos/yoga_con_lau.png"]
        }

    if any(k in text for k in KEYWORDS_NORM["sublinor"]):
        return {
            "reply": "🖨️ **Sublinor Gráfica**\n\nImprenta gráfica en Acassuso y en el Delta del Tigre\nEspecializada en rompecabezas, posavasos, papelería para bares,\npapelería comercial, merchandising corporativo y más\n\nInstagram: @sublinorgrafica\nContacto: sublinorgrafica@gmail.com",
            "images": []
        }

    # Servicios individuales de transporte — chequeados ANTES del menú taxifletes
    if any(k in text for k in KEYWORDS_NORM["fletesmareaexpress"]):
        return {
            "reply": "🚢 **Fletes Marea Express**\n\nFletes en lancha, transporte seguro por agua\nCargas de todo tipo: materiales, herramientas, mercadería\nZonas rurales, islas y barrios ribereños\n\nContacto: 1168803724",
            "images": ["/img/actividades_productos/flete1.jpeg"]
        }

    if any(k in text for k in KEYWORDS_NORM["viajesvita"]):
        return {
            "reply": "🚤 **Viajes y Fletes Vita**\n\nViajes y fletes en lancha por el Delta\n\nContacto Claudio: 1162564547\nContacto Valeria: 1163044895",
            "images": ["/img/actividades_productos/viajes.jpeg"]
        }

    if any(k in text for k in KEYWORDS_NORM["oscart"]):
        return {
            "reply": "⛵ **Óscar T — Traslados y Paseos**\n\nViajes, traslados y paseos las 24 horas\nBase: Arroyo Espera, Delta del Paraná\nSu traslado de confianza, siempre.\n\nContacto: 1165012823 / 1131761412",
            "images": ["/img/actividades_productos/viajes2.jpeg"]
        }

    # Menú Lanchas Taxis y Fletes (submenu con sub-chips)
    if any(k in text for k in KEYWORDS_NORM["taxifletes"]):
        return {
            "reply": "🚤 **Lanchas Taxis y Fletes**\n\n¿Cuál servicio buscás?",
            "images": [],
            "quick_replies": ["Fletes Marea Express 🚢", "Viajes Vita 🚤", "Óscar T Traslados ⛵"]
        }

    if any(k in text for k in KEYWORDS_NORM["lena"]) and not any(k in text for k in KEYWORDS_NORM["interislena"]):
        return {
            "reply": "🪵 **Leña a tu Muelle — Gabriel**\n\nBolsas tamaño salamandra (10-12 kg)\n· Quebracho Colorado: $8.500\n· Ligustro: $7.500\n· Sauce: $6.500\n· Maderitas para prender: $3.000\n\nCompra mínima: 5 bolsas\nContacto: Gabriel — 1564584445",
            "images": ["/img/actividades_productos/gabi_lena.jpeg"]
        }

    return None


HISTORY_MAX_MSGS  = 6    # últimos 3 intercambios (user+assistant × 3)
HISTORY_MAX_CHARS = 250  # truncar cada mensaje para no reventar la cookie

def _history_add(user_msg, bot_reply):
    """Agrega un par user/assistant al historial, truncando y limitando el tamaño."""
    hist = session.setdefault('history', [])
    hist.append({"role": "user",      "content": (user_msg  or '')[:HISTORY_MAX_CHARS]})
    hist.append({"role": "assistant", "content": (bot_reply or '')[:HISTORY_MAX_CHARS]})
    session['history'] = hist[-HISTORY_MAX_MSGS:]
    session.modified = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<path:filename>')
def serve_image(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'manifest.json')


@app.route('/service-worker.js')
def service_worker():
    resp = send_from_directory(os.path.join(BASE_DIR, 'static'), 'service-worker.js')
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    if 'history' not in session:
        session['history'] = []

    # Multi-step flows (order matters)
    for flow_fn, flow_type in [
        (handle_social_flow,      "social"),
        (handle_memes_flow,       "memes"),
        (handle_almaceneras_flow, "almaceneras"),
        (handle_agenda_flow,      "agenda"),
        (handle_colectivas_flow,  "colectivas"),
    ]:
        resp = flow_fn(user_message)
        if resp:
            _history_add(user_message, resp["reply"])
            log_interaction(user_message, resp["reply"], flow_type,
                            resp.get("images"), resp.get("quick_replies"))
            return jsonify(resp)

    # Keyword-based quick responses (single-step)
    quick = detect_quick_response(user_message)
    if quick:
        _history_add(user_message, quick["reply"])
        log_interaction(user_message, quick["reply"], "quick",
                        quick.get("images"), quick.get("quick_replies"))
        return jsonify(quick)

    # Fall back to LLM — check rate limit first
    ip = get_remote_address()
    if not _llm_rate_ok(ip):
        log_interaction(user_message, "RATE_LIMITED", "llm_blocked")
        return jsonify({'reply': 'Enviaste demasiadas consultas seguidas. Esperá un momento y volvé a intentar 🌿', 'images': [], 'quick_replies': []})

    context = build_llm_context(user_message)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in session.get('history', []):
        messages.append(msg)

    content = user_message
    if context:
        content = f"{user_message}\n\n[Contexto:\n{context}]"
    messages.append({"role": "user", "content": content})

    try:
        response = openai_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=messages,
            max_tokens=600
        )
        reply = response.choices[0].message.content
        _history_add(user_message, reply)
        log_interaction(user_message, reply, "llm")
        return jsonify({'reply': reply, 'images': [], 'quick_replies': []})
    except Exception as e:
        print(f"LLM error: {e}")
        log_interaction(user_message, "ERROR", "llm_error")
        return jsonify({'reply': 'Tuve un problema técnico. Intentá de nuevo en un momento.', 'images': [], 'quick_replies': []})


@app.route('/api/clima')
def api_clima():
    w = load_weather_data()
    if not w:
        return jsonify({'error': 'Sin datos de clima'})
    current = w.get('current_weather', {})
    main = current.get('main', {})
    return jsonify({
        'location': current.get('name', 'Tigre'),
        'temp': main.get('temp'),
        'feels_like': main.get('feels_like'),
        'humidity': main.get('humidity'),
        'description': current.get('weather', [{}])[0].get('description', ''),
        'wind_speed': current.get('wind', {}).get('speed'),
    })


SUGGESTIONS_LOG_PATH = os.path.join(BASE_DIR, "suggestions.csv")
EMPRENDIMIENTOS_LOG_PATH = os.path.join(BASE_DIR, "emprendimientos.csv")
DATA_REQUESTS_LOG_PATH = os.path.join(BASE_DIR, "data_requests.csv")

def _save_suggestion(text):
    file_exists = os.path.isfile(SUGGESTIONS_LOG_PATH)
    with open(SUGGESTIONS_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "suggestion"])
        writer.writerow([datetime.now().isoformat(), text])

def _send_suggestion_email(text):
    msg = EmailMessage()
    msg['From'] = "marajadesantelmo@gmail.com"
    msg['To'] = "marajadesantelmo@gmail.com"
    msg['Subject'] = "💡 Nueva sugerencia en deltix.com.ar"
    msg.set_content(f"Un usuario envió la siguiente sugerencia desde la web:\n\n{text}")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("marajadesantelmo@gmail.com", gmail_token)
    server.send_message(msg)
    server.quit()


@app.route('/join', methods=['POST'])
@limiter.limit("5 per hour")
def join():
    data = request.get_json()
    nombre      = (data.get('nombre') or '').strip()
    descripcion = (data.get('descripcion') or '').strip()
    tipo        = (data.get('tipo') or '').strip()
    instagram   = (data.get('instagram') or '').strip()
    contacto    = (data.get('contacto') or '').strip()
    if not nombre:
        return jsonify({'ok': False, 'error': 'El nombre es obligatorio'}), 400

    # Guardar en CSV
    file_exists = os.path.isfile(EMPRENDIMIENTOS_LOG_PATH)
    with open(EMPRENDIMIENTOS_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "nombre", "descripcion", "tipo", "instagram", "contacto"])
        writer.writerow([datetime.now().isoformat(), nombre, descripcion, tipo, instagram, contacto])

    # Enviar email
    try:
        body = (f"Nuevo emprendimiento en deltix.com.ar:\n\n"
                f"Nombre: {nombre}\n"
                f"Descripción: {descripcion}\n"
                f"Tipo: {tipo}\n"
                f"Instagram: {instagram}\n"
                f"Contacto: {contacto}")
        msg = EmailMessage()
        msg['From'] = "marajadesantelmo@gmail.com"
        msg['To'] = "marajadesantelmo@gmail.com"
        msg['Subject'] = f"🌿 Nuevo emprendimiento: {nombre}"
        msg.set_content(body)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("marajadesantelmo@gmail.com", gmail_token)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email join error: {e}")

    return jsonify({'ok': True})


@app.route('/data-request', methods=['POST'])
@limiter.limit("3 per hour")
def data_request():
    data = request.get_json()
    nombre    = (data.get('nombre') or '').strip()
    solicitud = (data.get('solicitud') or '').strip()
    if not nombre:
        return jsonify({'ok': False, 'error': 'El nombre es obligatorio'}), 400

    # Guardar en CSV
    file_exists = os.path.isfile(DATA_REQUESTS_LOG_PATH)
    with open(DATA_REQUESTS_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "nombre", "solicitud"])
        writer.writerow([datetime.now().isoformat(), nombre, solicitud])

    # Enviar email
    try:
        body = (f"Solicitud de baja o cambio de datos en deltix.com.ar:\n\n"
                f"Nombre del emprendimiento: {nombre}\n"
                f"Solicitud: {solicitud}")
        msg = EmailMessage()
        msg['From'] = "marajadesantelmo@gmail.com"
        msg['To'] = "marajadesantelmo@gmail.com"
        msg['Subject'] = f"✏️ Solicitud de datos: {nombre}"
        msg.set_content(body)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("marajadesantelmo@gmail.com", gmail_token)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email data-request error: {e}")

    return jsonify({'ok': True})


@app.route('/suggest', methods=['POST'])
@limiter.limit("3 per hour")
def suggest():
    data = request.get_json()
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'Mensaje vacío'}), 400
    _save_suggestion(text)
    try:
        _send_suggestion_email(text)
    except Exception as e:
        print(f"Email error: {e}")
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True)
