from twilio.rest import Client
from tokens import account_sid, auth_token

client = Client(account_sid, auth_token)

message = client.messages.create(
  from_='whatsapp:+14155238886',
  body='123 Probando',
  to='whatsapp:+5491151128207'
)

print(message.sid)