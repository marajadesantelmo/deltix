import os
import json
import time
from supabase import create_client
from openai import OpenAI

# Load environment variables or tokens
try:
    from tokens import supabase_url, supabase_key, openrouter_key
except ImportError:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')

# Validate environment variables
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")
if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

# Initialize Supabase and OpenAI clients
supabase = create_client(supabase_url, supabase_key)
openai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

# Keywords for context generation
KEYWORDS = {
    "weather": ['clima', 'temperatura', 'pronostico', 'tiempo', 'lluvia', 'viento', 'llover', 'soleado', 'ventoso', 'humedad', 'tormenta', 'nublado', 'calor', 'frio'],
    "almacen": ['almacen', 'almacén', 'almacenera', 'almaceneras'],
    "jilguero": ['jilguero', 'carapachay', 'angostura'],
    "interislena": ['interisleña', 'interislena', 'sarmiento', 'san antonio', 'capitan', 'capitán'],
    "lineasdelta": ['lineasdelta', 'caraguatá', 'caraguata', 'canal arias', 'paraná miní', 'parana mini', 'lineas delta'],
    "activities": ['actividades', 'emprendimientos', 'hacer', 'visitar', 'conocer', 'experiencias', 'atracciones', 'paseos', 'canoa', 'kayak', 'arcilla', 'barro', 'alfareria', 'hospedaje']
}

class ContextManager:
    """Manages context generation based on user input."""
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def load_file(self, filename):
        """Load content from a file in the 'rag' directory."""
        try:
            file_path = os.path.join(self.base_dir, "rag", filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"File not found: {filename}")
            return ""
        except Exception as e:
            print(f"Error loading file {filename}: {e}")
            return ""

    def load_weather_data(self):
        """Load weather data from a JSON file."""
        try:
            weather_file = os.path.join(self.base_dir, "rag", "weather_data.json")
            with open(weather_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("Weather data file not found.")
            return None
        except Exception as e:
            print(f"Error loading weather data: {e}")
            return None

    def generate_context(self, user_input):
        """Generate context based on user input."""
        context = []

        # Add weather data if applicable
        if any(keyword in user_input.lower() for keyword in KEYWORDS["weather"]):
            weather_data = self.load_weather_data()
            if weather_data:
                context.append(self.format_weather_data(weather_data))
            else:
                context.append("No se pudo cargar la información del clima en este momento.")

        # Add other context files based on keywords
        if any(keyword in user_input.lower() for keyword in KEYWORDS["almacen"]):
            context.append(self.load_file("almaceneras.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["jilguero"]):
            context.append(self.load_file("jilguero.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["interislena"]):
            context.append(self.load_file("interislena.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["lineasdelta"]):
            context.append(self.load_file("lineasdelta.txt"))
        if any(keyword in user_input.lower() for keyword in KEYWORDS["activities"]):
            context.append(self.load_file("actividades.txt"))

        return "\n\n".join(context) if context else "No hay contexto disponible."

    def format_weather_data(self, weather_data):
        """Format weather data into a readable string."""
        try:
            current = weather_data.get('current_weather', {})
            location = current.get('name', 'Desconocido')
            temp = current.get('main', {}).get('temp', 'N/A')
            description = current.get('weather', [{}])[0].get('description', 'N/A')
            return f"Clima actual en {location}: {temp}°C, {description}"
        except Exception as e:
            print(f"Error formatting weather data: {e}")
            return "Información del clima no disponible."

class LLMClient:
    """Handles interactions with the LLM."""
    def __init__(self, client, retries=3, delay=2):
        self.client = client
        self.retries = retries
        self.delay = delay

    def get_response(self, user_input, context, conversation_id):
        """Get a response from the LLM."""
        system_prompt = (
            "Vos sos Deltix, el bot del humedal. Sos un carpincho digital que ayuda a habitantes y visitantes del Delta del Paraná en Tigre. "
            "Responde al último mensaje del usuario usando el contexto proporcionado. No inventes información ni alucines. Tu opinión es anticapitalista y ambientalista. "
            "Si no puedes responder, guía al usuario para que ingrese palabras clave como: clima, mareas, windguru, colectivas, almaceneras."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mensaje: {user_input}\n\nContexto:\n{context}"}
        ]

        for attempt in range(self.retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=messages
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retries - 1:
                    raise
                time.sleep(self.delay)

# Public API
def create_conversation():
    """Create a new conversation in Supabase."""
    response = supabase.from_("conversations").insert({"name": "Nueva conversacion"}).execute()
    return response.data[0]["id"]

def store_chat_message(conversation_id, role, content):
    """Store a chat message in Supabase."""
    supabase.from_("chat_history").insert({"conversation_id": conversation_id, "role": role, "content": content}).execute()

def get_llm_response(user_input, conversation_id):
    """Main function to get a response from the LLM."""
    context_manager = ContextManager()
    llm_client = LLMClient(openai_client)

    # Generate context
    context = context_manager.generate_context(user_input)

    # Get response from LLM
    response = llm_client.get_response(user_input, context, conversation_id)

    # Store messages in Supabase
    store_chat_message(conversation_id, "user", user_input)
    store_chat_message(conversation_id, "assistant", response)

    return response
