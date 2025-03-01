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

# Sidebar for project management
st.sidebar.title("Projects")
projects = st.sidebar.selectbox("Select a project", options=["Project 1", "Project 2", "Add new project..."])

if projects == "Add new project...":
    new_project_name = st.sidebar.text_input("Enter new project name")
    if st.sidebar.button("Add Project"):
        # Add new project logic
        st.sidebar.success(f"Project '{new_project_name}' added!")

if st.sidebar.button("Delete Project"):
    # Delete project logic
    st.sidebar.warning(f"Project '{projects}' deleted!")

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

def make_api_call(user_input, project, documents):
    try:
        context = "\n".join([doc["content"] for doc in documents])
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model="deepseek/deepseek-chat:free",
            messages=[
                {
                    "role": "user",
                    "content": f"[{project}] {user_input}\n\nContext:\n{context}"
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise e

if user_input:
    if "marea" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("marea.png"):
            st.image("marea.png")
        else:
            st.error("Error: No se encontró el archivo de mareas.")

    elif "windguru" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("windguru.png"):
            st.image("windguru.png")
        else:
            st.error("Error: No se encontró el archivo de Windguru.")

    elif "memes" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Aquí tienes algunos memes divertidos...")
        if os.path.exists("memes/1.png"):
            st.image("memes/1.png")
        else:
            st.error("Error: No se encontró el archivo de memes.")

    else:
        try:
            documents = retrieve_documents(user_input)
            bot_reply = make_api_call(user_input, projects, documents)
            st.chat_message("user").write(user_input)
            st.chat_message("assistant", avatar="bot_icon.png").write(bot_reply)
        except Exception as e:
            st.error(f"Error: {e}")