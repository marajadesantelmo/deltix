
#import os 
#import urllib.request
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler

import nest_asyncio
nest_asyncio.apply()

#os.chdir('/Users/facun/deltix/')
#urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")

# URL de la imagen del pronóstico de mareas
IMAGEN_URL = "https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stages
ELEGIR, SI, NO = range(3)

# Lista para almacenar los números de teléfono de los suscriptores
suscriptores = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data="si"),
            InlineKeyboardButton("No, gracias deltix", callback_data="no"),
        ], ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Hola {user.first_name}! soy Deltix, el bot del humedal. Soy un bot en desarrollo y por ahora tan sólo puedo mandarte una vez por día el pronóstico de mareas del INA para el Puerto de San Fernando. Querés recibir el pronóstico de mareas todos los días?", 
                                    reply_markup=reply_markup)
    return ELEGIR

async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data="si"),
            InlineKeyboardButton("No, gracias deltix", callback_data="no"),
        ], ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=f"Hola {user.first_name}... entonces querés que te mande una vez por día el pronóstico de mareas del INA para el Puerto de San Fernando?", reply_markup=reply_markup)
    return ELEGIR

async def si(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#    user = update.message.from_user
#    chat_id = f"{user.id}"
#    suscriptores.append(chat_id)
    await update.message.reply_text("¡Gracias por suscribirte! A partir de ahora recibirás el pronóstico de mareas una vez al día a las 9 de la mañana. Te mando ahora el último pronóstico que tengo...")
#    await update.message.send_photo(chat_id, open("Marea.png", "rb"))
    await update.message.reply_text("Espero que te sirva! Para desuscribirte, simplemente escribime diciendo que no querés recibir más mensajes. Quedamos en contacto!")
    return SI


async def no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Gracias! Espero poder ayudarte en el futuro.")
    return ConversationHandler.END

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(text="Hablamos!")
    return ConversationHandler.END


def main() -> None:

    application = Application.builder().token("6349906625:AAHngVDiN8wacq_UraZ1H4bznKSLWLgjj_g").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ELEGIR: [MessageHandler(Filters.all, )
            ],
            END_ROUTES: [
                CallbackQueryHandler(start_over, pattern="^1$"),
                CallbackQueryHandler(end, pattern="^2$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)


    application.run_polling()


if __name__ == "__main__":
    main()