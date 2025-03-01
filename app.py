from supabase import create_client
import streamlit as st
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import re
import requests

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

# Remove options to avoid passing unexpected arguments
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

# Initialize OpenAI client with OpenRouter base URL
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

# Initial bot message
st.chat_message("assistant", avatar="bot_icon.png").write("Hola! Soy Deltix. En qué te puedo ayudar? 🐱")

def get_help_message():
    return (
        "- **/mareas**: _obtener el pronóstico de mareas_\n"
        "- **/windguru**: _pronóstico meteorológico de windgurú_\n"
        "- **/colectivas**: _horarios de lanchas colectivas_\n"
        "- **/memes**: _ver los memes más divertidos de la isla_\n"
    )

st.chat_message("assistant", avatar="bot_icon.png").write(get_help_message())

user_input = st.chat_input("Ingresa tu mensaje...")

def retrieve_documents(query):
    response = supabase.from_("documents").select("*").ilike("content", f"%{query}%").execute()
    return response.data

def make_api_call(user_input, project_id, documents):
    try:
        context = "\n".join([doc["content"] for doc in documents])
        previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"])
        context = f"{previous_messages_content}\n{context}"
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model="deepseek/deepseek-chat:free",
            messages=[
                {   "role": "system",
                    "content": "Sos Deltix, el bot del humedal. Eres argentino, simpático, informal y amable. Tu objetivo es ayudar a quienes habitan y visitan el delta inferior del Paraná. Fui diseñado para proporcionar información y servicios útiles a las personas que habitan o visitan la hermosa región del Delta del Tigre, en Buenos Aires. Por ahora mis principales funcionalidades son enviar pronósticos meteorológico y de maraes, horarios de lanchas colectivas y mandar los Memes Islenials más divertidos de la isla :P En el futuro te voy a poder ayudar también cuando estés buscando recomendaciones locales, información sobre actividades en el delta o simplemente quieras mantenerte al tanto de las novedades de la zona.",
                    "role": "user",
                    "content": f"{user_input}\n\nContexto:\n{context}"
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise e

def store_chat_message(project_id, role, content):
    supabase.from_("chat_history").insert({"project_id": project_id, "role": role, "content": content}).execute()

def create_project():
    response = supabase.from_("projects").insert({"name": "Nueva conversacion"}).execute()
    return response.data[0]["id"]

# Store project_id in session state to persist across conversation
if "project_id" not in st.session_state:
    st.session_state.project_id = create_project()

project_id = st.session_state.project_id

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

    elif "memes" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Aquí tienes algunos memes divertidos...")
        if os.path.exists("memes/1.png"):
            st.image("memes/1.png")
        else:
            st.error("Error: No se encontró el archivo de memes.")
        store_chat_message(project_id, "assistant", "Aquí tienes algunos memes divertidos...")

    else:
        try:
            documents = retrieve_documents(user_input)
            bot_reply = make_api_call(user_input, project_id, documents)
            st.chat_message("user").write(user_input)
            st.chat_message("assistant", avatar="bot_icon.png").write(bot_reply)
            store_chat_message(project_id, "assistant", bot_reply)
        except Exception as e:
            st.error(f"Error: {e}")