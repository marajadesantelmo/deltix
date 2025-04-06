from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import random
import time
from datetime import datetime
from llm_connector import get_llm_response, create_conversation
import os

# Initialize Flask app
app = Flask(__name__)

# Paths and global variables
base_path = '/home/facundol/deltix/' if os.path.exists('/home/facundol/deltix/') else ''
user_experience_path = base_path + 'user_experience.csv'
subscribers_mareas_path = base_path + 'subscribers_mareas.csv'
subscribers_windguru_path = base_path + 'subscribers_windguru.csv'
subscribers_hidrografia_path = base_path + 'subscribers_hidrografia.csv'

# Load user experience data
try:
    user_experience = pd.read_csv(user_experience_path)
except Exception as e:
    user_experience = pd.DataFrame(columns=["User ID", "Username", "First Name", "Last Name", "first_interaction"])

# Initialize a dictionary to store project IDs for each user
user_projects = {}

def update_user_experience(user_id, option):
    global user_experience
    timestamp_col = f'timestamp_{option}'
    q_col = f'q_{option}'

    if user_id in user_experience['User ID'].values:
        user_experience.loc[user_experience['User ID'] == user_id, timestamp_col] = datetime.now().strftime('%d-%m-%Y %H:%M')
        user_experience.loc[user_experience['User ID'] == user_id, q_col] += 1
        user_experience.to_csv(user_experience_path, index=False)

def generate_main_menu():
    return ("- Mareas: Pronóstico de mareas\n"
            "- Windguru: Pronóstico del clima\n"
            "- Colectivas: Horarios de lanchas\n"
            "- Memes: Memes isleños\n"
            "- Suscribirme: Suscribirte a envíos\n")

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    response = MessagingResponse()
    msg = response.message()

    # Handle user input
    if 'mareas' in incoming_msg:
        msg.body("Aquí tienes el pronóstico de mareas:")
        # Add logic to send mareas data
    elif 'windguru' in incoming_msg:
        msg.body("Aquí tienes el pronóstico de Windguru:")
        # Add logic to send windguru data
    elif 'colectivas' in incoming_msg:
        msg.body("Aquí tienes los horarios de lanchas colectivas:")
        # Add logic to send colectivas data
    elif 'memes' in incoming_msg:
        msg.body("Aquí tienes un meme isleño:")
        # Add logic to send memes
    elif 'suscribirme' in incoming_msg:
        msg.body("¿A qué te gustaría suscribirte? Mareas, Windguru o Hidrografía?")
        # Add logic to handle subscriptions
    else:
        # Fallback to LLM
        if from_number not in user_projects:
            user_projects[from_number] = create_conversation()
        project_id = user_projects[from_number]
        llm_response = get_llm_response(incoming_msg, project_id)
        msg.body(llm_response)

    return str(response)

if __name__ == '__main__':
    app.run(port=5000)