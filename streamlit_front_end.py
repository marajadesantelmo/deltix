'''
Front-end in streamlit
'''

import streamlit as st
import os

# Initialize chat history in session state if it doesn't exist
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Store project_id in session state to persist across conversation
if "project_id" not in st.session_state:
    st.session_state.project_id = create_project()

project_id = st.session_state.project_id

# UI Layout
col_title, col_logo = st.columns([5, 1])
with col_title:
    st.title("Deltix")
    st.write("El bot del humedal...")
with col_logo:
    st.image('bot_icon.png')

# Show initial bot messages only once per session
if "initial_messages_shown" not in st.session_state:
    st.session_state.initial_messages_shown = False

if not st.session_state.initial_messages_shown:
    welcome_msg = "Hola! Soy Deltix. En qué te puedo ayudar? 🐱"
    help_msg = get_menu_message()
    
    # Add to session state chat messages
    st.session_state.chat_messages.append({"role": "assistant", "content": welcome_msg})
    st.session_state.chat_messages.append({"role": "assistant", "content": help_msg})
    
    # Store in database
    store_chat_message(project_id, "assistant", welcome_msg)
    store_chat_message(project_id, "assistant", help_msg)
    
    st.session_state.initial_messages_shown = True

# Display all messages from the session state
for message in st.session_state.chat_messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    elif message["role"] == "assistant":
        st.chat_message("assistant", avatar="bot_icon.png").write(message["content"])
    elif message["role"] == "image":
        # For images we stored previously
        st.image(message["content"])

# Chat input
user_input = st.chat_input("Ingresa tu mensaje...")

def colectivas():
    msg = "Elegí la empresa de lancha colectiva:\n- **Jilguero**: va por el Carapachay-Angostura\n- **Interisleña**: Sarmiento, San Antonio y muchos más\n- **LineasDelta**: Caraguatá, Canal Arias, Paraná Miní"
    st.session_state.chat_messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant", avatar="bot_icon.png").write(msg)
    store_chat_message(project_id, "assistant", msg)
    st.session_state.colectivas_step = "select_company"

if user_input:
    # Always add the user message to chat history and display immediately
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    store_chat_message(project_id, "user", user_input)
    
    if "marea" in user_input.lower() or "mareas" in user_input.lower():
        msg = "Sí, ahora te mando..."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if os.path.exists("marea.png"):
            # Update image in real-time by reading the file each time
            st.image("marea.png")
            st.session_state.chat_messages.append({"role": "image", "content": "marea.png"})
        else:
            error_msg = "Error: No se encontró el archivo de mareas."
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    elif "windguru" in user_input.lower():
        msg = "Sí, ahora te mando..."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if os.path.exists("windguru.png"):
            # Update image in real-time by reading the file each time
            st.image("windguru.png")
            st.session_state.chat_messages.append({"role": "image", "content": "windguru.png"})
        else:
            error_msg = "Error: No se encontró el archivo de Windguru."
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    elif "memes" in user_input.lower() or "meme" in user_input.lower() or st.session_state.get("wants_more_memes", False):
        msg = "Ya te mando un meme"
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if "memes" in user_input.lower() or "meme" in user_input.lower():
            st.session_state.wants_more_memes = True
        
        if user_input.lower() == "no":
            st.session_state.wants_more_memes = False
            msg = "¡Espero que hayas disfrutado los memes!"
            st.session_state.chat_messages.append({"role": "assistant", "content": msg})
            st.chat_message("assistant", avatar="bot_icon.png").write(msg)
            store_chat_message(project_id, "assistant", msg)
        elif user_input.lower() == "si" or st.session_state.wants_more_memes:
            meme_file = get_random_meme()
            if meme_file:
                st.image(meme_file)
                st.session_state.chat_messages.append({"role": "image", "content": meme_file})
                store_chat_message(project_id, "meme", f"{meme_file}")
                
                if "meme_message_shown" not in st.session_state:
                    msg = "Buenísimo, no? Son de la página Memes Islenials. Te recomiendo que la sigas en las redes"
                    st.session_state.chat_messages.append({"role": "assistant", "content": msg})
                    st.chat_message("assistant", avatar="bot_icon.png").write(msg)
                    store_chat_message(project_id, "assistant", msg)
                    st.session_state.meme_message_shown = True
                
                msg = "¿Queres ver más memes? (Si/No)"
                st.session_state.chat_messages.append({"role": "assistant", "content": msg})
                st.chat_message("assistant", avatar="bot_icon.png").write(msg)
                store_chat_message(project_id, "assistant", msg)
            else:
                error_msg = "Error: No se encontraron archivos de memes."
                st.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                st.session_state.wants_more_memes = False
        else:
            st.session_state.wants_more_memes = False

    elif "hidrografia" in user_input.lower():
        msg = "Aca va el pronostico de mareas de hidrografía naval..."
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant", avatar="bot_icon.png").write(msg)
        store_chat_message(project_id, "assistant", msg)
        
        if os.path.exists("hidrografia.png"):
            st.image("hidrografia.png")
            st.session_state.chat_messages.append({"role": "image", "content": "hidrografia.png"})
        else:
            error_msg = "Error: No se encontró el archivo de hidrografía."
            st.error(error_msg)
            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    elif "colectivas" in user_input.lower():
        colectivas()
    elif st.session_state.get("colectivas_step"):
        if not handle_colectivas_input(user_input):
            # Create a placeholder for the "thinking" message
            with st.chat_message("assistant", avatar="bot_icon.png"):
                thinking_placeholder = st.empty()
                thinking_placeholder.write("deltix pensando...")
                
                try:
                    documents = []
                    bot_reply = make_api_call(user_input, project_id, documents)
                    # Replace with actual response
                    thinking_placeholder.write(bot_reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                    store_chat_message(project_id, "assistant", bot_reply)
                except Exception as e:
                    error_msg = f"Error: {e}"
                    thinking_placeholder.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    elif contains_weather_keywords(user_input):
        # Create a placeholder for the "thinking" message
        with st.chat_message("assistant", avatar="bot_icon.png"):
            thinking_placeholder = st.empty()
            thinking_placeholder.write("deltix pensando...")
            
            try:
                documents = []
                bot_reply = make_api_call(user_input, project_id, documents)
                # Replace with actual response
                thinking_placeholder.write(bot_reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                error_msg = f"Error: {e}"
                thinking_placeholder.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    else:
        # Create a placeholder for the "thinking" message
        with st.chat_message("assistant", avatar="bot_icon.png"):
            thinking_placeholder = st.empty()
            thinking_placeholder.write("deltix pensando...")
            
            try:
                documents = []
                bot_reply = make_api_call(user_input, project_id, documents)
                # Replace with actual response
                thinking_placeholder.write(bot_reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})
                store_chat_message(project_id, "assistant", bot_reply)
            except Exception as e:
                error_msg = f"Error: {e}"
                thinking_placeholder.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})