from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
from tokens import account_sid, auth_token
#Nueva versión
client = Client(account_sid, auth_token)

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Deltix webhook server is running!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        # Handle POST request (Twilio webhook)
        response = MessagingResponse()
        msg = response.message()
        
        # Always return the same message regardless of input
        msg.body("Hola, Soy deltix!")
        
        return str(response)
    else:
        # Handle GET request (browser access)
        return "Deltix webhook endpoint is active. Send a POST request to use it."

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # This is the code that will be used by PythonAnywhere
    # Make sure to configure your WSGI file to point to this application
    application = app