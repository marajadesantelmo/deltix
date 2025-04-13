from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import sys
import json

# Add the deltix directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import deltix functions
from deltix_funciones import *
from llm_connector import get_llm_response, create_conversation

# Import tokens
try:
    from tokens import account_sid, auth_token, twilio_phone_number
except ImportError:
    # For deployment, use environment variables
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Initialize Flask app
app = Flask(__name__)

# Dictionary to store user conversations
user_conversations = {}

@app.route('/', methods=['GET'])
def home():
    return "Deltix webhook server is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    # Get incoming message data
    incoming_msg = request.values.get('Body', '').strip()
    sender_number = request.values.get('From', '')
    
    # Create a TwiML response
    resp = MessagingResponse()
    
    # Log incoming message
    print(f"Received message: '{incoming_msg}' from {sender_number}")
    
    # Get or create a conversation ID for this user
    if sender_number not in user_conversations:
        user_conversations[sender_number] = create_conversation()
    conversation_id = user_conversations[sender_number]
    
    # Create a TwiML response (still needed for the webhook to respond to Twilio)
    resp = MessagingResponse()
    
    try:
        # Process commands first
        if incoming_msg.lower().startswith('/start') or incoming_msg.lower() == 'hola':
            # Send welcome message
            welcome_msg = "Hola! Soy Deltix, el bot del humedal 🦫\n\n"
            welcome_msg += "Puedo ayudarte con información sobre el Delta del Paraná.\n\n"
            welcome_msg += "Algunos comandos que puedes usar:\n"
            welcome_msg += "• *mareas* - Pronóstico de mareas\n"
            welcome_msg += "• *windguru* - Pronóstico meteorológico\n"
            welcome_msg += "• *colectivas* - Horarios de lanchas\n"
            welcome_msg += "• *memes* - Memes isleños\n"
            client.messages.create(
                body=welcome_msg,
                from_=twilio_phone_number,
                to=sender_number
            )
        
        elif incoming_msg.lower() == 'mareas' or '/mareas' in incoming_msg.lower():
            # Send marea image
            client.messages.create(
                body="Acá tenés el informe de mareas:",
                from_=twilio_phone_number,
                to=sender_number,
                media_url=['https://raw.githubusercontent.com/marajadesantelmo/deltix/main/marea.png']
            )
            
        elif incoming_msg.lower() == 'windguru' or '/windguru' in incoming_msg.lower():
            # Send windguru image
            client.messages.create(
                body="Acá tenés el pronóstico de Windguru:",
                from_=twilio_phone_number,
                to=sender_number,
                media_url=['https://raw.githubusercontent.com/marajadesantelmo/deltix/main/windguru.png']
            )
        
        elif incoming_msg.lower() == 'hidrografia' or '/hidrografia' in incoming_msg.lower():
            # Read data from table_data.txt from GitHub raw URL
            import requests
            response = requests.get('https://raw.githubusercontent.com/marajadesantelmo/deltix/main/table_data.txt')
            if response.status_code == 200:
                lines = response.text.splitlines()
                formatted_message = "📊 PRONÓSTICO DE MAREAS - HIDROGRAFÍA NAVAL\n\n"
                
                if len(lines) > 0:
                    port_name = lines[0].strip()
                    formatted_message += f"🚢 {port_name}\n\n"
                
                if len(lines) > 2:
                    for line in lines[2:]:
                        data = line.strip().split('\t')
                        if len(data) >= 4:
                            tide_type = data[0]
                            time = data[1]
                            height = data[2]
                            date = data[3]
                            emoji = "🌊" if tide_type == "PLEAMAR" else "⬇️"
                            formatted_message += f"{emoji} {tide_type}: {time} hs - {height} m ({date})\n"
                
                client.messages.create(
                    body=formatted_message,
                    from_=twilio_phone_number,
                    to=sender_number
                )
            else:
                client.messages.create(
                    body="Lo siento, no pude obtener los datos de mareas de hidrografía en este momento.",
                    from_=twilio_phone_number,
                    to=sender_number
                )
                
        elif incoming_msg.lower() == 'memes' or '/memes' in incoming_msg.lower():
            import random
            # Get a random meme number between 1 and 56
            meme_number = random.randint(1, 56)
            meme_url = f"https://raw.githubusercontent.com/marajadesantelmo/deltix/main/memes/{meme_number}.png"
            
            client.messages.create(
                body="Me encantan los memes islenials 😂 Te mando uno.",
                from_=twilio_phone_number,
                to=sender_number,
                media_url=[meme_url]
            )
        
        # Handle other inputs with LLM
        else:
            # Get response from LLM
            llm_response = get_llm_response(incoming_msg, conversation_id)
            
            # Send the LLM response back to the user
            client.messages.create(
                body=llm_response,
                from_=twilio_phone_number,
                to=sender_number
            )
    
    except Exception as e:
        error_msg = f"Ocurrió un error: {str(e)}"
        print(error_msg)
        client.messages.create(
            body="Ups, algo salió mal. Por favor, intenta nuevamente más tarde.",
            from_=twilio_phone_number,
            to=sender_number
        )
    
    return str(resp)

@app.route('/status', methods=['POST'])
def status_callback():
    """Handle message status callback from Twilio"""
    message_sid = request.values.get('MessageSid', '')
    message_status = request.values.get('MessageStatus', '')
    
    print(f"Message {message_sid} status: {message_status}")
    
    return jsonify({"status": "received"})

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # This is the code that will be used by PythonAnywhere
    application = app