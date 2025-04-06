from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').lower()
    response = MessagingResponse()
    msg = response.message()

    if 'hola' in incoming_msg:
        msg.body('Hola! Soy Deltix, el bot del humedal. ¿En qué puedo ayudarte?')
    else:
        msg.body('Lo siento, no entendí tu mensaje. Por favor, intenta de nuevo.')

    return str(response)

if __name__ == '__main__':
    app.run()