from supabase import create_client
import streamlit as st
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import random

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables")

supabase = create_client(supabase_url, supabase_key)

openrouter_key = os.getenv('OPENROUTER_API_KEY')
if not openrouter_key:
    raise ValueError("OpenRouter API Key must be set in environment variables")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def get_help_message():
    return (
        "- **mareas**: _obtener el pronóstico de mareas_\n"
        "- **windguru**: _pronóstico meteorológico de windgurú_\n"
        "- **colectivas**: _horarios de lanchas colectivas_\n"
        "- **memes**: _ver los memes más divertidos de la isla_\n"
    )

def retrieve_documents(query):
    response = supabase.from_("documents").select("*").ilike("content", f"%{query}%").execute()
    return response.data

def make_api_call(user_input, project_id, documents):
    try:
        context = "\n".join([doc["content"] for doc in documents])
        previous_messages = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data
        previous_messages_content = "\n".join([msg["content"] for msg in previous_messages if msg["role"] == "user"])
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
                    "content": "Vos sos Deltix, el bot del humedal. Eres argentino, simpático, informal y amable."
                },
                {
                    "role": "user",
                    "content": f"{user_input}\n\nMensajes anteriores:\n{previous_messages_content}\n\nContexto:\n{context}"
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
    st.write("Hola! Soy Deltix. En qué te puedo ayudar? 🐱")
    st.write(get_help_message())
    st.session_state.initial_messages_shown = True

user_input = st.text_input("Ingresa tu mensaje...")

if user_input:
    store_chat_message(project_id, "user", user_input)
    if "marea" in user_input.lower():
        st.write("Sí, ahora te mando...")
        if os.path.exists("marea.png"):
            st.image("marea.png")
        else:
            st.error("Error: No se encontró el archivo de mareas.")
        store_chat_message(project_id, "assistant", "Sí, ahora te mando...")

    elif "windguru" in user_input.lower():
        st.write("Sí, ahora te mando...")
        if os.path.exists("windguru.png"):
            st.image("windguru.png")
        else:
            st.error("Error: No se encontró el archivo de Windguru.")
        store_chat_message(project_id, "assistant", "Sí, ahora te mando...")

    elif "memes" in user_input.lower() or st.session_state.get("wants_more_memes", False):
        st.write("Ya te mando un meme")
        store_chat_message(project_id, "assistant", "Ya te mando un meme")
        if "memes" in user_input.lower():
            st.session_state.wants_more_memes = True
        if user_input.lower() == "no":
            st.session_state.wants_more_memes = False
            st.write("¡Espero que hayas disfrutado los memes!")
            store_chat_message(project_id, "assistant", "¡Espero que hayas disfrutado los memes!")
        elif user_input.lower() == "si" or st.session_state.wants_more_memes:
            meme_file = get_random_meme()
            if meme_file:
                st.image(meme_file)
                store_chat_message(project_id, "meme", f"{meme_file}")
                if "meme_message_shown" not in st.session_state:
                    st.write("Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes")
                    store_chat_message(project_id, "assistant", "Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes")
                    st.session_state.meme_message_shown = True
                st.write("¿Queres ver más memes? (Si/No)")
                store_chat_message(project_id, "assistant", "¿Queres ver más memes? (Si/No)")
            else:
                st.error("Error: No se encontraron archivos de memes.")
                st.session_state.wants_more_memes = False
        else:
            st.session_state.wants_more_memes = False
            try:
                documents = retrieve_documents(user_input)
                bot_reply = make_api_call(user_input, project_id, documents)
                st.write(user_input)
                st.write(bot_reply)
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        try:
            documents = retrieve_documents(user_input)
            bot_reply = make_api_call(user_input, project_id, documents)
            st.write(user_input)
            st.write(bot_reply)
            store_chat_message(project_id, "assistant", bot_reply)
        except Exception as e:
            st.error(f"Error: {e}")

# Display chat history
chat_history = supabase.from_("chat_history").select("*").eq("project_id", project_id).execute().data

for message in chat_history:
    if message["role"] == "user":
        st.write(message["content"])
    elif message["role"] == "meme":
        st.image(message["content"])
    else:
        st.write(message["content"])