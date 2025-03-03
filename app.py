from supabase import create_client
import streamlit as st
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import re
import requests
import time
import random

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

supabase = create_client(supabase_url, supabase_key)

openrouter_key = os.getenv('OPENROUTER_API_KEY')
if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

class EventHandler(AssistantEventHandler):
    @override    
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
    @override     
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        
def on_tool_call_created(self, tool_call):
  print(f"\nassistant > {tool_call.type}\n", flush=True)

def on_tool_call_delta(self, delta, snapshot):
  if delta.type == 'code_interpreter':
    if delta.code_interpreter.input:
      print(delta.code_interpreter.input, end="", flush=True)
    if delta.code_interpreter.outputs:
      print(f"\n\noutput >", flush=True)
      for output in delta.code_interpreter.outputs:
        if output.type == "logs":
          print(f"\n{output.logs}", flush=True)

col_title, col_logo = st.columns([5, 1])
with col_title:
  st.title("Deltix")
  st.write("El bot del humedal...")
with col_logo:
  st.image('bot_icon.png')

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def get_help_message():
    return ("Ingresando algunas de estas palabras podes obtener información útil:\n"
        "- **mareas**: _obtener el pronóstico de mareas_\n"
        "- **windguru**: _pronóstico meteorológico de windgurú_\n"
        "- **colectivas**: _horarios de lanchas colectivas_\n"
        "- **memes**: _ver los memes más divertidos de la isla_\n"
    )

def retrieve_documents(query):
    response = supabase.from_("documents").select("*").ilike("content", f"%{query}%").execute()
    return response.data

def make_api_call(user_input, project_id, documents, retries=3, delay=2):
    try:
        #context_supabase = "\n".join([doc["content"] for doc in documents])
        context = []
        if any(keyword in user_input.lower() for keyword in ['seguridad', 'policia', 'emergencia', 'telefono']):
            with open("rag/policia.txt", "r") as file:
                context.append(file.read())
        previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"])
        
        for attempt in range(retries):
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                    "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
                },
                extra_body={},
                model="deepseek/deepseek-chat:free",
                messages=[
                    {
                        "role": "system",
                        "content": "Vos sos Deltix, el bot del humedal. Eres argentino y amable. Ingresando algunas de estas palabras el usuario puede obtener información útil: mareas: obtener el pronóstico de mareas, windguru: pronóstico meteorológico de windgurú, Colectivas: horarios de lanchas colectivas, memes: ver los memes más divertidos de la isla"
                    },
                    {
                        "role": "user",
                        "content": f"{user_input}\n\nMensajes anteriores:\n{previous_messages_content}\n\nContexto:\n{context}"
                    }
                ]
            )
            response_content = completion.choices[0].message.content
            if response_content.strip():
                return response_content
            time.sleep(delay)
        raise ValueError("Received empty response from OpenRouter API after multiple attempts")
    except Exception as e:
        raise e

def store_chat_message(project_id, role, content):
    supabase.from_("chat_history").insert({"project_id": project_id, "role": role, "content": content}).execute()

def create_project():
    response = supabase.from_("projects").insert({"name": "Nueva conversacion"}).execute()
    return response.data[0]["id"]

def get_random_meme():
    meme_files = [f"memes/{file}" for file in os.listdir("memes") if file.endswith(".png")]
    return random.choice(meme_files) if meme_files else None

# Store project_id in session state to persist across conversation
if "project_id" not in st.session_state:
    st.session_state.project_id = create_project()

project_id = st.session_state.project_id

# Show initial bot messages only once per session
if "initial_messages_shown" not in st.session_state:
    st.session_state.initial_messages_shown = False

if not st.session_state.initial_messages_shown:
    st.chat_message("assistant", avatar="bot_icon.png").write("Hola! Soy Deltix. En qué te puedo ayudar? 🐱")
    st.chat_message("assistant", avatar="bot_icon.png").write(get_help_message())
    st.session_state.initial_messages_shown = True

user_input = st.chat_input("Ingresa tu mensaje...")

def colectivas():
    st.chat_message("assistant", avatar="bot_icon.png").write("Elegí la empresa de lancha colectiva:\n- **Jilguero**: va por el Carapachay-Angostura\n- **Interisleña**: Sarmiento, San Antonio y muchos más\n- **LineasDelta**: Caraguatá, Canal Arias, Paraná Miní")
    st.session_state.colectivas_step = "select_company"
    def handle_colectivas_input(user_input):
        if st.session_state.colectivas_step == "select_company":
            if "jilguero" in user_input.lower():
                st.session_state.colectivas_company = "Jilguero"
                st.chat_message("assistant", avatar="bot_icon.png").write("En qué sentido querés viajar? Ida a la isla o vuelta a Tigre?")
                st.session_state.colectivas_step = "select_direction"
            elif "interisleña" in user_input.lower():
                st.session_state.colectivas_company = "Interisleña"
                st.chat_message("assistant", avatar="bot_icon.png").write("Querés los horarios de verano o de invierno?")
                st.session_state.colectivas_step = "select_season"
            elif "lineasdelta" in user_input.lower():
                st.session_state.colectivas_company = "LineasDelta"
                st.chat_message("assistant", avatar="bot_icon.png").write("Qué recorrido necesitás? Ida a la isla o vuelta a Tigre?")
                st.session_state.colectivas_step = "select_direction"
            else:
                st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí una empresa de lancha colectiva: Jilguero, Interisleña, LineasDelta")
                st.session_state.colectivas_step = None

        elif st.session_state.colectivas_step == "select_direction":
            if st.session_state.colectivas_company == "Jilguero":
                if "ida" in user_input.lower():
                    st.image("colectivas/jilguero_ida.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla de Jilguero.")
                elif "vuelta" in user_input.lower():
                    st.image("colectivas/jilguero_vuelta.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre de Jilguero.")
                else:
                    st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Ida a la isla' o 'Vuelta a Tigre'.")
                    st.session_state.colectivas_step = None
            elif st.session_state.colectivas_company == "LineasDelta":
                st.session_state.colectivas_direction = user_input.lower()
                st.chat_message("assistant", avatar="bot_icon.png").write("En época escolar o no escolar?")
                st.session_state.colectivas_step = "select_schedule"

        elif st.session_state.colectivas_step == "select_season":
            if "verano" in user_input.lower():
                st.image("colectivas/interislena_ida_verano.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de verano de Interisleña.")
            elif "invierno" in user_input.lower():
                st.image("colectivas/interislena_ida_invierno.png")
                st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de invierno de Interisleña.")
            else:
                st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Verano' o 'Invierno'.")
                st.session_state.colectivas_step = None

        elif st.session_state.colectivas_step == "select_schedule":
            if "escolar" in user_input.lower():
                if "ida" in st.session_state.colectivas_direction:
                    st.image("colectivas/lineas_delta_ida_escolar.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla en época escolar de LineasDelta.")
                elif "vuelta" in st.session_state.colectivas_direction:
                    st.image("colectivas/lineas_delta_vuelta_escolar.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre en época escolar de LineasDelta.")
            elif "no escolar" in user_input.lower():
                if "ida" in st.session_state.colectivas_direction:
                    st.image("colectivas/lineas_delta_ida_no_escolar.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de ida a la isla en época no escolar de LineasDelta.")
                elif "vuelta" in st.session_state.colectivas_direction:
                    st.image("colectivas/lineas_delta_vuelta_no_escolar.png")
                    st.chat_message("assistant", avatar="bot_icon.png").write("Estos son los horarios de vuelta a Tigre en época no escolar de LineasDelta.")
            else:
                st.chat_message("assistant", avatar="bot_icon.png").write("No entendí. Por favor, elegí 'Escolar' o 'No escolar'.")
                st.session_state.colectivas_step = None

        if st.session_state.colectivas_step is None:
            st.session_state.colectivas_step = "select_company"

if user_input:
    store_chat_message(project_id, "user", user_input)
    if "marea" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("marea.png"):
            st.image("marea.png")
        else:
            st.error("Error: No se encontró el archivo de mareas.")
        store_chat_message(project_id, "assistant", "Sí, ahora te mando...")

    elif "windguru" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("windguru.png"):
            st.image("windguru.png")
        else:
            st.error("Error: No se encontró el archivo de Windguru.")
        store_chat_message(project_id, "assistant", "Sí, ahora te mando...")

    elif "memes" in user_input.lower() or st.session_state.get("wants_more_memes", False):
        st.chat_message("assistant", avatar="bot_icon.png").write("Ya te mando un meme")
        store_chat_message(project_id, "assistant", "Ya te mando un meme")
        if "memes" in user_input.lower():
            st.session_state.wants_more_memes = True
        if user_input.lower() == "no":
            st.session_state.wants_more_memes = False
            st.chat_message("assistant", avatar="bot_icon.png").write("¡Espero que hayas disfrutado los memes!")
            store_chat_message(project_id, "assistant", "¡Espero que hayas disfrutado los memes!")
        elif user_input.lower() == "si" or st.session_state.wants_more_memes:
            meme_file = get_random_meme()
            if meme_file:
                st.image(meme_file)
                store_chat_message(project_id, "meme", f"{meme_file}")
                if "meme_message_shown" not in st.session_state:
                    st.chat_message("assistant", avatar="bot_icon.png").write("Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes")
                    store_chat_message(project_id, "assistant", "Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes")
                    st.session_state.meme_message_shown = True
                st.chat_message("assistant", avatar="bot_icon.png").write("¿Queres ver más memes? (Si/No)")
                time.sleep(1)
                store_chat_message(project_id, "assistant", "¿Queres ver más memes? (Si/No)")
            else:
                st.error("Error: No se encontraron archivos de memes.")
                st.session_state.wants_more_memes = False
        else:
            st.session_state.wants_more_memes = False
            try:
                documents = retrieve_documents(user_input)
                bot_reply = make_api_call(user_input, project_id, documents)
                st.chat_message("user").write(user_input)
                st.chat_message("assistant", avatar="bot_icon.png").write(bot_reply)
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                st.error(f"Error: {e}")

    elif "colectivas" in user_input.lower():
        colectivas()
    elif st.session_state.get("colectivas_step"):
        handle_colectivas_input(user_input)
    else:
        try:
            documents = retrieve_documents(user_input)
            bot_reply = make_api_call(user_input, project_id, documents)
            st.chat_message("user").write(user_input)
            st.chat_message("assistant", avatar="bot_icon.png").write(bot_reply)
            store_chat_message(project_id, "assistant", bot_reply)
        except Exception as e:
            st.error(f"Error: {e}")
