import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, send_from_directory
from openai import OpenAI

try:
    from tokens import openrouter_key, telegram_token
except ImportError:
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    telegram_token = os.getenv('TELEGRAM_TOKEN', 'fallback-secret')

app = Flask(__name__)
app.secret_key = telegram_token[:32]

openai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    if any(k in text for k in KEYWORDS["activities"]):
        context.append(load_rag_file("actividades.txt"))
    return "\n\n".join(c for c in context if c)


def detect_quick_response(user_input):
    """
    Detecta si el mensaje coincide con un comando específico y devuelve
    texto + imágenes sin necesidad de llamar al LLM.
    Retorna None si no hay coincidencia directa.
    """
    text = user_input.lower()

    if any(k in text for k in KEYWORDS["hidrografia"]):
        return {
            "reply": format_hidrografia(),
            "images": []
        }

    if any(k in text for k in KEYWORDS["tides"]):
        return {
            "reply": "Acá tenés el pronóstico de mareas del INA 🌊",
            "images": ["/img/marea.png"]
        }

    if any(k in text for k in KEYWORDS["windguru"]):
        return {
            "reply": "Pronóstico de WindGurú para las islas ☁️",
            "images": ["/img/windguru.png"]
        }

    if any(k in text for k in KEYWORDS["jilguero"]):
        return {
            "reply": "Horarios del Jilguero 🚢",
            "images": ["/img/colectivas/jilguero_ida.png", "/img/colectivas/jilguero_vuelta.png"]
        }

    if any(k in text for k in KEYWORDS["interislena"]):
        season = "invierno" if is_winter() else "verano"
        return {
            "reply": f"Horarios de Interisleña — temporada {season} ⛵",
            "images": [
                f"/img/colectivas/interislena_ida_{season}.png",
                f"/img/colectivas/interislena_vuelta_{season}.png"
            ]
        }

    if any(k in text for k in KEYWORDS["lineasdelta"]):
        return {
            "reply": "Horarios de Líneas Delta 🛥️",
            "images": [
                "/img/colectivas/lineas_delta_ida_escolar.png",
                "/img/colectivas/lineas_delta_ida_no_escolar.png",
                "/img/colectivas/lineas_delta_vuelta_escolar.png",
                "/img/colectivas/lineas_delta_vuelta_no_escolar.png"
            ]
        }

    if any(k in text for k in KEYWORDS["colectivas"]):
        return {
            "reply": "¿Qué colectiva querés consultar? 🚢\n\nElegí una:\n• Jilguero\n• Interisleña\n• Líneas Delta",
            "images": []
        }

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

    return None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<path:filename>')
def serve_image(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    if 'history' not in session:
        session['history'] = []

    # Try keyword-based quick response first
    quick = detect_quick_response(user_message)
    if quick:
        session['history'].append({"role": "user", "content": user_message})
        session['history'].append({"role": "assistant", "content": quick["reply"]})
        session.modified = True
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
        return jsonify({'reply': reply, 'images': []})
    except Exception as e:
        print(f"LLM error: {e}")
        return jsonify({'reply': 'Tuve un problema técnico. Intentá de nuevo en un momento.', 'images': []})


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


if __name__ == '__main__':
    app.run(debug=True)
