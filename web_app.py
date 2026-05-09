import os
import json
from flask import Flask, request, jsonify, render_template, session
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

KEYWORDS = {
    "weather":     ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'tormenta', 'calor', 'frio', 'nublado'],
    "tides":       ['mareas', 'marea', 'pleamar', 'bajamar', 'agua', 'altura'],
    "almacen":     ['almacen', 'almacén', 'almacenera', 'almaceneras'],
    "jilguero":    ['jilguero', 'carapachay', 'angostura'],
    "interislena": ['interisleña', 'interislena', 'sarmiento', 'san antonio'],
    "lineasdelta": ['lineasdelta', 'caraguatá', 'caraguata', 'canal arias', 'lineas delta'],
    "activities":  ['actividades', 'emprendimientos', 'hacer', 'visitar', 'kayak', 'alfareria', 'hospedaje', 'paseos'],
}

SYSTEM_PROMPT = (
    "Vos sos Deltix, el bot del humedal. Sos un carpincho digital que ayuda a habitantes y visitantes "
    "del Delta del Paraná en Tigre. Respondé de forma concisa y útil. No saludes ni repitas 'hola'. "
    "No inventes información ni alucines datos. Tu postura es anticapitalista y ambientalista. "
    "Si no podés responder algo, sugerí palabras clave: clima, mareas, colectivas, almaceneras, actividades."
)


def load_rag_file(filename):
    try:
        path = os.path.join(BASE_DIR, "rag", filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def load_weather_data():
    try:
        path = os.path.join(BASE_DIR, "rag", "weather_data.json")
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def load_tides_data():
    try:
        path = os.path.join(BASE_DIR, "table_data.txt")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def build_context(user_input):
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
            location = current.get('name', 'Tigre')
            context.append(
                f"Clima actual en {location}: {temp}°C (sensación {feels}°C), {desc}, "
                f"humedad {humidity}%, viento {wind} m/s"
            )

    if any(k in text for k in KEYWORDS["tides"]):
        tides = load_tides_data()
        if tides:
            context.append(f"Datos de mareas:\n{tides}")

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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    if 'history' not in session:
        session['history'] = []

    context = build_context(user_message)

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

        return jsonify({'reply': reply})
    except Exception as e:
        print(f"LLM error: {e}")
        return jsonify({'reply': 'Tuve un problema técnico. Intentá de nuevo en un momento.'})


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


@app.route('/api/mareas')
def api_mareas():
    return jsonify({'data': load_tides_data()})


if __name__ == '__main__':
    app.run(debug=True)
