import logging
from telegram.ext import update, ApplicationBuilder, ContextTypes, CommandHandler
from telegram.ext import Updater  # Add this import

import nest_asyncio
nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.first_name
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Hola {user}! soy Deltix, el bot del humedal. Soy un bot en desarrollo y por ahora tan sólo puedo mandarte una vez por día el pronóstico de mareas del INA para el Puerto de San Fernando. ¿Querés recibir el pronóstico de mareas todos los días? Por favor respóndeme escribiendo 'Si' o 'No'.")

if __name__ == '__main__':
    # Replace "YOUR_BOT_TOKEN" with your actual bot token
    application = Updater("YOUR_BOT_TOKEN", use_context=True)
    
    start_handler = CommandHandler('start', start)
    application.dispatcher.add_handler(start_handler)  # Use dispatcher.add_handler()
    
    application.start_polling()
