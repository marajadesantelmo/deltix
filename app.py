import streamlit as st
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
import os
import re

openai_key = os.getenv('OPENAI_API_KEY')

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
    api_key=openai_key)

# Initial bot message
st.chat_message("assistant", avatar="bot_icon.png").write("Hola! Soy Deltix. En qué te puedo ayudar? 🐱")

def get_help_message():
    return ("- <b>/mareas </b>   <i> obtener el pronóstico de mareas &#9875</i>\n"
            "- <b>/windguru </b>   <i> pronóstico meteorológico de windgurú</i>\n"
            "- <b>/colectivas </b>   <i> horarios de lanchas colectivas &#128337</i>\n"
            "- <b>/memes </b>   <i> ver los memes más divertidos de la isla &#129315 </i>\n")

st.chat_message("assistant", avatar="bot_icon.png").write(get_help_message())

user_input = st.chat_input("Ingresa tu mensaje...")

if user_input:
    if "marea" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("marea.png"):
            st.image("marea.png")
        else:
            st.error("Error: No se encontró el archivo de mareas.")

    if "windguru" in user_input.lower():
        st.chat_message("assistant", avatar="bot_icon.png").write("Sí, ahora te mando...")
        if os.path.exists("windguru.png"):
            st.image("windguru.png")
        else:
            st.error("Error: No se encontró el archivo de Windguru.")



    else:
        try:
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )
            with client.beta.threads.runs.stream(
                thread_id=thread.id,
                assistant_id='asst_nnDTLYK0nrjuIBJCdscnA6vb',
                event_handler=EventHandler()) as stream:
                    stream.until_done()
                    bot_response = stream.get_final_messages()
                    bot_reply = bot_response[0].content[0].text.value
                    bot_reply = re.sub(r"【.*?】", "", bot_reply)
            st.chat_message("user").write(user_input)
            st.chat_message("assistant", avatar="bot_icon.png").write(bot_reply)
        except Exception as e:
            st.error(f"Error: {e}")