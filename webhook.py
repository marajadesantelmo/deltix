from flask import Flask, request
from twilio.rest import Client
import os
from token import account_sid, auth_token
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
        message = client.messages.create(
  from_='whatsapp:+14155238886',
  body='123 Probando',
  to='whatsapp:+5491151128207'
)
        
        return str(message)
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