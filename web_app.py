import os
import csv
import json
import uuid
import random
import smtplib
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
    "No inventes información ni alucines datos. Tu postura es anticapitalista y ambientalista. "
    "Si no podés responder algo, sugerí palabras clave: clima, mareas, hidrografia, windguru, "
    "colectivas, almaceneras, actividades."
)

KEYWORDS = {
    "weather":     ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'tormenta', 'calor', 'frio', 'nublado'],
    "tides":       ['mareas', 'marea', 'pleamar', 'bajamar'],
    "hidrografia": ['hidrografia', 'hidrografía', 'naval'],
    "agenda":      ['agenda', 'actividades', 'emprendimientos', 'agenda del rio', 'agenda del río'],
    "windguru":    ['windguru', 'viento', 'wind'],
    "jilguero":    ['jilguero', 'carapachay', 'angostura'],
    "interislena": ['interisleña', 'interislena', 'sarmiento', 'san antonio'],
    "lineasdelta": ['lineasdelta', 'lineas delta', 'caraguata', 'canal arias'],
    "colectivas":  ['colectivas', 'horarios', 'lancha', 'lanchas'],
    "almacen":     ['almacen', 'almacén', 'almacenera', 'almaceneras'],
    "activities":  ['actividades', 'emprendimientos', 'hacer', 'visitar', 'paseos', 'experiencias'],
    "amanita":     ['amanita', 'canoa'],
    "alfareria":   ['alfareria', 'alfarería', 'barro', 'arcilla', 'kutral'],
    "labusqueda":  ['labusqueda', 'busqueda', 'hostal', 'ceremonias'],
    "kayaks":      ['kayak', 'kayaks', 'canaveral', 'cañaveral'],
    "masajes":     ['masaje', 'masajes', 'charco', 'thai'],
    "familia":     ['familia islena', 'familia isleña', 'dietetica', 'alimentos'],
    "frutales":    ['frutales', 'citricos', 'cítricos', 'limonero', 'naranjas', 'mandarina', 'planta frutal'],
    "dulceras":    ['dulceras', 'dulcera', 'dulceras del rio', 'reposteria', 'repostería'],
    "vivero":      ['vivero', 'tierra fertil', 'tierra fértil', 'compost', 'igarape', 'igarapé', 'huerta'],
    "nahuel":      ['nahuel', 'poda', 'carpinteria', 'carpintería', 'zanja', 'mantenimiento isla'],
    "aguariba":    ['aguariba', 'agroecologico', 'agroecológico', 'verduras', 'bolson', 'bolsón'],
    "lena":        ['leña', 'lena', 'quebracho', 'salamandra', 'ligustro'],
    "memes":       ['meme', 'memes'],
}

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
    text = user_input.lower()
    context = []
    if any(k in text for k in KEYWORDS["weather"]):
        w = load_weather_data()
        if w:
            current = w.get('current_weather', {})
            temp = current.get('main', {}).get('temp', 'N/A')
            feels = current.get('main', {}).get('feels_like', 'N/A')
            humidity = current.get('main', {}).get('humidity', 'N/A')
            desc = current.get('weather', [{}])[0].get('description', 'N/A')
            wind = current.get('wind', {}).get('speed', 'N/A')
            context.append(f"Clima en Tigre: {temp}°C (sensación {feels}°C), {desc}, humedad {humidity}%, viento {wind} m/s")
    if any(k in text for k in KEYWORDS["tides"] + KEYWORDS["hidrografia"]):
        context.append(load_tides_text())
    if any(k in text for k in KEYWORDS["almacen"]):
        context.append(load_rag_file("almaceneras.txt"))
    if any(k in text for k in KEYWORDS["jilguero"]):
        context.append(load_rag_file("jilguero.txt"))
    if any(k in text for k in KEYWORDS["interislena"]):
        context.append(load_rag_file("interislena.txt"))
    if any(k in text for k in KEYWORDS["lineasdelta"]):
        context.append(load_rag_file("lineasdelta.txt"))
    if any(k in text for k in KEYWORDS["activities"] +
           KEYWORDS["amanita"] + KEYWORDS["alfareria"] + KEYWORDS["labusqueda"] +
           KEYWORDS["kayaks"] + KEYWORDS["masajes"] + KEYWORDS["familia"] +
           KEYWORDS["frutales"] + KEYWORDS["dulceras"] + KEYWORDS["vivero"] +
           KEYWORDS["nahuel"] + KEYWORDS["aguariba"] + KEYWORDS["lena"]):
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
    "Nélida G":        "🛒 *Nélida G* — José Olivera\nLUN, MIÉ, VIE, SÁB: Arroyo Caraguatá / Cruz Colorada / Canal Arias / Río Luján\n📞 155644466",
    "Raquel N":        "🛒 *Raquel N* — Roberto Baraldo\nLUNES y SÁBADO: Río Sarmiento / Capitán / Arroyo La Horca\nMARTES y MIÉRCOLES: Río Paraná hasta Carabelas / Canal 5\n📞 1544981064",
    "Stella Maris":    "🛒 *Stella Maris* — Manuel Compagnucci\nVIERNES: Escobar / Paraná / Paycaraby / Estudiantes / Las Cañas\nSÁBADOS: Puerto Escobar / La Serna / Arroyo Chana / Felicaria\n📞 1562771474",
}

AGENDA_OPTIONS = {
    "Amanita Canoa":       "amanita canoa",
    "Kutral Alfarería":    "alfareria kutral",
    "La Búsqueda":         "labusqueda",
    "Cañaveral Kayaks":    "canaveral kayaks",
    "Masaje Thai":         "charco masajes",
    "Familia Isleña":      "familia islena",
    "Planta Frutales":     "planta frutales",
    "Dulceras del Río":    "dulceras del rio",
    "Vivero Isleño":       "vivero isleno",
    "Nahuel Servicios":    "nahuel servicios",
    "Aguariba Anfibia":    "aguariba",
    "Leña a tu Muelle":    "leña muelle",
}


def handle_almaceneras_flow(user_input):
    text = user_input.strip()
    text_lower = text.lower()
    alm = session.get('alm_flow')

    if alm and alm.get('step') == 'select':
        # Buscar coincidencia con nombre de almacenera
        for name, info in ALMACENERAS.items():
            if name.lower() in text_lower or text_lower in name.lower():
                session.pop('alm_flow', None)
                session.modified = True
                return {"reply": info, "images": [], "quick_replies": []}
        # Sin coincidencia — repetir menú
        return {"reply": "Elegí una almacenera de la lista 👇",
                "images": [], "quick_replies": list(ALMACENERAS.keys())}

    if any(k in text_lower for k in KEYWORDS["almacen"]):
        session['alm_flow'] = {'step': 'select'}
        session.modified = True
        return {"reply": "¿Cuál almacenera querés consultar? 🛒",
                "images": [], "quick_replies": list(ALMACENERAS.keys())}

    return None


def handle_agenda_flow(user_input):
    text = user_input.strip()
    text_lower = text.lower()
    agenda = session.get('agenda_flow')

    if agenda and agenda.get('step') == 'select':
        for label, query in AGENDA_OPTIONS.items():
            if any(w in text_lower for w in query.split()):
                session.pop('agenda_flow', None)
                session.modified = True
                return detect_quick_response(query)
        return {"reply": "Elegí una actividad 👇",
                "images": [], "quick_replies": list(AGENDA_OPTIONS.keys())}

    if any(k in text_lower for k in KEYWORDS["agenda"]):
        session['agenda_flow'] = {'step': 'select'}
        session.modified = True
        return {"reply": "¿Qué actividad te interesa? 🌿",
                "images": [], "quick_replies": list(AGENDA_OPTIONS.keys()) + ["➕ Sumá tu emprendimiento", "✏️ Cambiar o dar de baja mis datos"]}

    return None


def handle_memes_flow(user_input):
    text = user_input.lower().strip()
    meme = session.get('meme_flow')

    if meme:
        step = meme.get('step')

        if step == 'more':
            if any(s in text for s in ['si', 'sí', 'dale', 'otro', 'mas', 'más', 'meme']):
                session['meme_flow'] = {'step': 'more2'}
                session.modified = True
                n = random.randint(1, 56)
                return {"reply": None,
                        "images": [f"/img/memes/{n}.png"],
                        "footer_text": "Uno más? 😄",
                        "quick_replies": ["Sí, otro 😄", "No gracias"]}
            if any(s in text for s in ['no', 'gracias', 'listo']):
                session.pop('meme_flow', None)
                session.modified = True
                return {"reply": "Bueno... si querés podés seguir explorando el delta con Deltix 🦫",
                        "images": [], "quick_replies": []}

        if step == 'more2':
            if any(s in text for s in ['si', 'sí', 'dale', 'otro', 'mas', 'más', 'meme']):
                session['meme_flow'] = {'step': 'more'}
                session.modified = True
                n = random.randint(1, 56)
                return {"reply": None,
                        "images": [f"/img/memes/{n}.png"],
                        "footer_text": "Te mando otro? 😄",
                        "quick_replies": ["Sí, otro 😄", "No gracias"]}
            if any(s in text for s in ['no', 'gracias', 'listo']):
                session.pop('meme_flow', None)
                session.modified = True
                return {"reply": "Bueno... si querés podés seguir explorando el delta con Deltix 🦫",
                        "images": [], "quick_replies": []}

        return None

    if any(k in text for k in KEYWORDS["memes"]):
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
    """
    text = user_input.lower().strip()
    col = session.get('col')

    # ── Estamos dentro de un flujo activo ──
    if col:
        step = col.get('step')

        if step == 'linea':
            if any(k in text for k in KEYWORDS["jilguero"]):
                session['col'] = {'step': 'direccion', 'linea': 'jilguero'}
                session.modified = True
                return {"reply": "Jilguero 🚢 ¿Ida o vuelta?", "images": [],
                        "quick_replies": ["Ida", "Vuelta"]}
            if any(k in text for k in KEYWORDS["interislena"]):
                session['col'] = {'step': 'temporada', 'linea': 'interislena'}
                session.modified = True
                return {"reply": "Interisleña ⛵ ¿Qué temporada?", "images": [],
                        "quick_replies": ["Invierno", "Verano"]}
            if any(k in text for k in KEYWORDS["lineasdelta"]):
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

            if linea == 'jilguero':
                return {
                    "reply": f"Jilguero — {direccion.capitalize()} 🚢",
                    "images": [f"/img/colectivas/jilguero_{direccion}.png"],
                    "quick_replies": []
                }
            if linea == 'interislena':
                temporada = col.get('temporada', 'invierno')
                return {
                    "reply": f"Interisleña — {direccion.capitalize()} — {temporada.capitalize()} ⛵",
                    "images": [f"/img/colectivas/interislena_{direccion}_{temporada}.png"],
                    "quick_replies": []
                }
            if linea == 'lineasdelta':
                periodo = col.get('periodo', 'escolar')
                label = periodo.replace('_', ' ')
                return {
                    "reply": f"Líneas Delta — {direccion.capitalize()} — {label.capitalize()} 🛥️",
                    "images": [f"/img/colectivas/lineas_delta_{direccion}_{periodo}.png"],
                    "quick_replies": []
                }

    # ── Inicio del flujo desde cero ──
    if any(k in text for k in KEYWORDS["colectivas"]):
        session['col'] = {'step': 'linea'}
        session.modified = True
        return {"reply": "¿Qué línea de colectiva querés consultar? 🚢", "images": [],
                "quick_replies": ["Jilguero", "Interisleña", "Líneas Delta"]}

    if any(k in text for k in KEYWORDS["jilguero"]):
        session['col'] = {'step': 'direccion', 'linea': 'jilguero'}
        session.modified = True
        return {"reply": "Jilguero 🚢 ¿Ida o vuelta?", "images": [],
                "quick_replies": ["Ida", "Vuelta"]}

    if any(k in text for k in KEYWORDS["interislena"]):
        session['col'] = {'step': 'temporada', 'linea': 'interislena'}
        session.modified = True
        return {"reply": "Interisleña ⛵ ¿Qué temporada?", "images": [],
                "quick_replies": ["Invierno", "Verano"]}

    if any(k in text for k in KEYWORDS["lineasdelta"]):
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
    text = user_input.lower()

    if any(k in text for k in KEYWORDS["hidrografia"]):
        return {"reply": format_hidrografia(), "images": [], "quick_replies": []}

    if any(k in text for k in KEYWORDS["tides"]):
        return {"reply": "Acá tenés el pronóstico de mareas del INA 🌊",
                "images": ["/img/marea.png"], "quick_replies": []}

    if any(k in text for k in KEYWORDS["windguru"]):
        return {"reply": "Pronóstico de WindGurú para las islas ☁️",
                "images": ["/img/windguru.png"], "quick_replies": []}

    if any(k in text for k in KEYWORDS["amanita"]):
        return {
            "reply": "🛶 **Experiencias en Canoa Isleña**\n\nPaseos por el Delta del Paraná\nCon guía bilingüe (opcional)\nServicio puerta a puerta (opcional)\n\nInstagram: amanitaturismodelta\nContacto: 1169959272",
            "images": ["/img/actividades_productos/amanita.png"]
        }

    if any(k in text for k in KEYWORDS["alfareria"]):
        return {
            "reply": "🏺 **Kutral Alfarería**\n\nEncuentros con el barro\nTalleres de alfarería\nExperimentación y creación con arcilla\n\nInstagram: kutralalfareria",
            "images": ["/img/actividades_productos/alfareria.png"]
        }

    if any(k in text for k in KEYWORDS["labusqueda"]):
        return {
            "reply": "🌿 **La Búsqueda**\n\nEspacio para encuentros y ceremonias\nHostal en el Delta\nConexión con la naturaleza\n\nInstagram: labusqueda_cabanadelta\nContacto: 1150459556",
            "images": ["/img/actividades_productos/labusqueda.png"]
        }

    if any(k in text for k in KEYWORDS["kayaks"]):
        return {
            "reply": "🚣 **Cañaveral Kayaks**\n\nExcursiones en kayak\nPaseos con guía\nRemadas nocturnas\n\nlinktr.ee/canaveralkayaks\nContacto: 1126961274",
            "images": ["/img/actividades_productos/canaveralkayaks.png"]
        }

    if any(k in text for k in KEYWORDS["masajes"]):
        return {
            "reply": "💆 **Masaje Thai**\n\nen el Tres Bocas\n@estecharco\nContacto: 1122541171",
            "images": ["/img/actividades_productos/charco_masajes.png"]
        }

    if any(k in text for k in KEYWORDS["familia"]):
        return {
            "reply": "🌾 **La Familia Isleña**\n\nAlimentos dietéticos, nutritivos y a buen precio\nHarinas, arroces, lentejas, porotos, frutos secos y más\nRepartos a tu muelle con envíos gratis todas las semanas\n\nPedidos al WhatsApp de Jorge (Piojo): 11 3046-6301",
            "images": ["/img/actividades_productos/familia_islena_flyer.jpg"]
        }

    if any(k in text for k in KEYWORDS["frutales"]):
        return {
            "reply": "🍋 **Planta Frutales**\n\nVenta de plantas cítricas para islas y amarras\nLimoneros, Mandarinas, Naranjas, Kinotos, Pomelos y más\n\nPrecios (macetas 6 lts): $26.000 c/u · $25.000 x5 · $24.000 x10\nEntrega en CABA, Zona Norte, Islas y Amarras\n\nContacto: 116 369 0177",
            "images": ["/img/actividades_productos/frutales.png"]
        }

    if any(k in text for k in KEYWORDS["dulceras"]):
        return {
            "reply": "🍯 **Dulceras del Río**\n\nProductos dulces y repostería artesanal\nEntregas los jueves en Amarras Hugo del Carril\nPuntos de entrega: Amarra Hugo Carril · Muelle La Anacahuita Río Carpachay\nReutilizamos frascos de vidrio 🫙\n\nInstagram: @dulcerasdelrio\nContacto: 11 5525 3829",
            "images": ["/img/actividades_productos/dulceras1.jpeg", "/img/actividades_productos/dulceras2.jpeg"]
        }

    if any(k in text for k in KEYWORDS["vivero"]):
        return {
            "reply": "🌱 **Vivero Isleño — Cooperativa Igarapé Delta**\n\n\"Hacer huerta es terapia\"\n\nTierra Fértil: $9.200 (bolsas 40 lts)\nCompost Orgánico: $11.500\n10% descuento pidiendo 30 bolsas o más\n\nEntrega en tu muelle · Zona Correa y San Antonio\nContacto: 1159233663",
            "images": ["/img/actividades_productos/vivero_isleno.jpeg"]
        }

    if any(k in text for k in KEYWORDS["nahuel"]):
        return {
            "reply": "🔨 **Nahuel Servicios**\n\nTrabajos para tu hogar y terreno en el Delta\n· Poda en altura (corte y mantenimiento de árboles)\n· Movimiento de tierra y zanjas\n· Carpintería: decks, torres de agua, estructuras en madera\n· Limpieza de terrenos y mantenimiento general\n\nContacto: Nahuel — 11 5349 2653",
            "images": ["/img/actividades_productos/nahuel.jpeg"]
        }

    if any(k in text for k in KEYWORDS["aguariba"]):
        return {
            "reply": "🥬 **Aguariba Anfibia**\n\nProducción agroecológica del Delta\nPedidos para entrega el miércoles\n(cargar hasta el lunes a las 22hs)\n40% de reintegro con CUENTA DNI 💳\n\nWeb: aguaribayanfibia.com.ar\nInstagram: @aguaribayanfibia",
            "images": ["/img/actividades_productos/aguariba.png"]
        }

    if any(k in text for k in KEYWORDS["lena"]):
        return {
            "reply": "🪵 **Leña a tu Muelle — Gabriel**\n\nBolsas tamaño salamandra (10-12 kg)\n· Quebracho Colorado: $8.500\n· Ligustro: $7.500\n· Sauce: $6.500\n· Maderitas para prender: $3.000\n\nCompra mínima: 5 bolsas\nContacto: Gabriel — 1564584445",
            "images": ["/img/actividades_productos/gabi_lena.jpeg"]
        }

    return None


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
@limiter.limit("3 per minute; 10 per hour; 15 per day")
def chat():
    data = request.get_json()
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    if 'history' not in session:
        session['history'] = []

    # Multi-step flows (order matters)
    for flow_fn, flow_type in [
        (handle_memes_flow,       "memes"),
        (handle_almaceneras_flow, "almaceneras"),
        (handle_agenda_flow,      "agenda"),
        (handle_colectivas_flow,  "colectivas"),
    ]:
        resp = flow_fn(user_message)
        if resp:
            session['history'].append({"role": "user", "content": user_message})
            session['history'].append({"role": "assistant", "content": resp["reply"]})
            session.modified = True
            log_interaction(user_message, resp["reply"], flow_type,
                            resp.get("images"), resp.get("quick_replies"))
            return jsonify(resp)

    # Keyword-based quick responses (single-step)
    quick = detect_quick_response(user_message)
    if quick:
        session['history'].append({"role": "user", "content": user_message})
        session['history'].append({"role": "assistant", "content": quick["reply"]})
        session.modified = True
        log_interaction(user_message, quick["reply"], "quick",
                        quick.get("images"), quick.get("quick_replies"))
        return jsonify(quick)

    # Fall back to LLM
    context = build_llm_context(user_message)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in session['history'][-10:]:
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
        session['history'].append({"role": "user", "content": user_message})
        session['history'].append({"role": "assistant", "content": reply})
        session.modified = True
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
