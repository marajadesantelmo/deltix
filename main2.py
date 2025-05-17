from telegram.ext import ApplicationBuilder,  CommandHandler, ConversationHandler, filters, MessageHandler
import pandas as pd
import nest_asyncio
import os
import asyncio
import random
from tokens import telegram_token
from deltix_funciones import *
from llm_connector import get_llm_response, create_conversation, get_db_connection
import mysql.connector
from mysql.connector import Error

# Initialize a dictionary to store project IDs for each user
user_projects = {}

if os.path.exists('/home/facundol/deltix/'):
    base_path = '/home/facundol/deltix/'
else:
        base_path = ''
user_experience_path = base_path + 'user_experience.csv'

# Define store_chat_message function directly in main2.py
def store_chat_message(phone_number, role, content):
    """Store a chat message in MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # get conversation ID from the database by phone number
        cursor.execute("SELECT id FROM conversations WHERE name = %s", (phone_number,))
        conversation_id = cursor.fetchone()
        
        if conversation_id is None:
            print(f"No conversation found for phone: {phone_number}. Creating a new one.")
            conversation_id = create_conversation(phone_number)
            # Get the conversation ID in the correct format
            if not isinstance(conversation_id, (tuple, list)):
                conversation_id = (conversation_id,)

        conn = get_db_connection()
        cursor = conn.cursor()    
        cursor.execute(
            "INSERT INTO chat_history (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id[0], role, content)
        )
        conn.commit()
        
        # Verify insertion
        message_id = cursor.lastrowid
        print(f"Message stored with ID: {message_id}")
        
        cursor.close()
        return True
    except Error as err:
        print(f"Error storing chat message: {err}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False

try:
    user_experience = pd.read_csv(user_experience_path)
except pd.errors.ParserError:
    # If there's a parser error, try with more robust error handling
    print("Warning: Issues detected in the CSV file. Attempting to load with error handling...")
    # Use on_bad_lines='skip' for newer pandas versions or error_bad_lines=False for older versions
    try:
        # Try with newer pandas syntax
        user_experience = pd.read_csv(user_experience_path, on_bad_lines='skip')
    except TypeError:
        # Fall back to older pandas syntax if needed
        user_experience = pd.read_csv(user_experience_path, error_bad_lines=False)
    
    # Save a clean version of the file to prevent future errors
    print("Saving a cleaned version of the user experience data...")
    user_experience.to_csv(user_experience_path, index=False)
    print("File cleaned and saved successfully.")

# Add a new fallback handler function that uses the LLM
async def llm_fallback(update, context):
    user_id = update.effective_user.id
    user_input = update.message.text
    
    # Create a task to send "Dejame pensar..." after 3 seconds
    thinking_message_task = asyncio.create_task(
        send_thinking_message_after_delay(update, 3)
    )
    
    try:
        # Get response from LLM (ensure this is awaited)
        # Note: get_llm_response already tracks the message, so we don't double-track it
        llm_response = await asyncio.to_thread(get_llm_response, user_input, user_id)
        
        # Cancel the thinking message task if it hasn't been sent yet
        thinking_message_task.cancel()
        
        # Send the response back to the user (no need to track again)
        await update.message.reply_text(llm_response)
    except Exception as e:
        # Log the error and notify the user
        print(f"Error in LLM fallback: {e}")
        await update.message.reply_text("Lo siento, ocurrió un error al procesar tu consulta. Por favor, intentá más tarde.")
    
    # Return to the conversation handler state
    return ConversationHandler.END

# Helper function to send "Dejame pensar..." after a delay
async def send_thinking_message_after_delay(update, delay_seconds):
    # List of possible thinking messages
    thinking_messages = [
        "Dejame pensar...",
        "...estoy pensando...",
        "...deltix pensando...",
        "Aguantame que pienso qué responderte",
        "Procesando tu consulta...",
        "Dame unos segundos para pensar...",
        "ya te pienso una respuesta...",
        "Un momento, por favor...",
        "Conectando neuronas artificiales...",
        "Buscando la mejor respuesta..."
    ]
    
    try:
        await asyncio.sleep(delay_seconds)
        # Choose a random message from the list
        thinking_message = random.choice(thinking_messages)
        await update.message.reply_text(thinking_message)
    except asyncio.CancelledError:
        # Task was cancelled because response arrived before timeout
        pass

# Add a function to track message history for all message handlers
async def track_message_middleware(update, context, next_handler):
    """Middleware to track all messages in the chat history"""
    if update.message and update.message.text:
        user_id = update.effective_user.id
        # Store user message in chat history using our local function
        try:
            store_chat_message(user_id, "user", update.message.text)
        except Exception as e:
            print(f"Failed to store user message: {e}")
    
    # Call the original handler and get its result
    result = await next_handler(update, context)
    
    return result

# Override the ApplicationBuilder.add_handler method to add the middleware
original_add_handler = ApplicationBuilder.add_handler

def add_handler_with_middleware(self, handler):
    """Add the handler with middleware that tracks messages"""
    # For CommandHandlers and MessageHandlers
    if isinstance(handler, (CommandHandler, MessageHandler)):
        original_callback = handler.callback
        
        async def wrapped_callback(update, context):
            return await track_message_middleware(update, context, original_callback)
        
        handler.callback = wrapped_callback
    
    # For ConversationHandler, wrap all callbacks in all states
    elif isinstance(handler, ConversationHandler):
        # Wrap entry points
        for entry_point in handler.entry_points:
            original_callback = entry_point.callback
            async def wrapped_entry(update, context):
                return await track_message_middleware(update, context, original_callback)
            entry_point.callback = wrapped_entry
        
        # Wrap state handlers
        for state, state_handlers in handler.states.items():
            for state_handler in state_handlers:
                original_callback = state_handler.callback
                async def wrapped_state(update, context):
                    return await track_message_middleware(update, context, original_callback)
                state_handler.callback = wrapped_state
        
        # Wrap fallbacks
        for fallback in handler.fallbacks:
            original_callback = fallback.callback
            async def wrapped_fallback(update, context):
                return await track_message_middleware(update, context, original_callback)
            fallback.callback = wrapped_fallback
    
    # Call the original add_handler method
    return original_add_handler(self, handler)

# Replace the original add_handler method with our version
ApplicationBuilder.add_handler = add_handler_with_middleware

nest_asyncio.apply()

if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_token).build()
    start_handler = CommandHandler('start', start)
    
    # Define command handlers first to ensure they take priority
    command_handlers = [
        CommandHandler("start", start),
        CommandHandler("menu", menu),
        CommandHandler("cancel", cancel),
        CommandHandler('charlar', charlar),
        CommandHandler('mareas', mareas),
        CommandHandler('mareaa', mareas),
        CommandHandler('windguru', windguru),
        CommandHandler('memes', memes),
        CommandHandler('colaborar', colaborar),
        CommandHandler('informacion', informacion),
        CommandHandler('mensajear', mensaje_trigger),
        CommandHandler('colectivas', colectivas),
        CommandHandler('almaceneras', almaceneras),
        CommandHandler('hidrografia', hidrografia),
        CommandHandler('suscribirme', suscribirme),
        CommandHandler('desuscribirme', desuscribirme),
        CommandHandler('amanita', amanita),
        CommandHandler('alfareria', alfareria),
        CommandHandler('labusqueda', labusqueda),
        CommandHandler('canaveralkayaks', canaveralkayaks),
    ]
    
    # Other handlers for message text
    message_handlers = [
        MessageHandler(filters.Regex(r'^(Windguru|windguru|WINDGURU)$'), windguru),
        MessageHandler(filters.Regex(r'^(Desuscribirme|desuscribirme|DESUSCRIBIRME)$'), desuscribirme),
        MessageHandler(filters.Regex(r'^(Memes|memes|MEMES|Meme|meme|MEME)$'), memes),
        MessageHandler(filters.Regex(r'^(Colaborar|colaborar|COLABORAR)$'), colaborar),
        MessageHandler(filters.Regex(r'^(Informacion|informacion|INFORMACION)$'), informacion),
        MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR)$'), mensaje_trigger),
        MessageHandler(filters.Regex(r'^(Hola|hola|HOLA)$'), start),
        MessageHandler(filters.Regex(r'^(Colectivas|colectivas|COLECTIVAS|horarios)$'), colectivas),
        MessageHandler(filters.Regex(r'^(Gracias|gracias|GRACIAS)$'), de_nada),
        MessageHandler(filters.Regex(r'^(Interislena|interislena|INTERISLENA)$'), Interislena),
        MessageHandler(filters.Regex(r'^(Jilguero|jilguero|JILGUERO)$'), Jilguero),
        MessageHandler(filters.Regex(r'^(LineasDelta|lineasdelta|LINEASDELTA)$'), LineasDelta),
        MessageHandler(filters.Regex(r'^(Almaceneras|almaceneras|ALMACENERAS)$'), almaceneras),
        MessageHandler(filters.Regex(r'^(Hidrografia|hidrografia|HIDROGRAFIA)$'), hidrografia),
        MessageHandler(filters.Regex(r'^(Suscribirme|suscribirme|SUSCRIBIRME)$'), suscribirme),
        MessageHandler(filters.Regex(r'^(Amanita|amanita|AMANITA)$'), amanita),
        MessageHandler(filters.Regex(r'^(Alfareria|alfareria|ALFARERIA)$'), alfareria),
        MessageHandler(filters.Regex(r'^(Labusqueda|labusqueda|LABUSQUEDA)$'), labusqueda),
        MessageHandler(filters.Regex(r'^(Canaveralkayaks|canaveralkayaks|CANAVERALKAYAKS)$'), canaveralkayaks),
        
        # Handlers for words contained in messages
        MessageHandler(filters.Regex(r'(?i)(.*\bcharlar\b.*)'), charlar),
        MessageHandler(filters.Regex(r'(?i)(.*\bmareas\b.*)'), mareas),
        MessageHandler(filters.Regex(r'(?i)(.*\bmarea\b.*)'), mareas),
        MessageHandler(filters.Regex(r'(?i)(.*\bhidrografia\b.*)'), hidrografia),
        MessageHandler(filters.Regex(r'(?i)(.*\bwindguru\b.*)'), windguru),
        MessageHandler(filters.Regex(r'(?i)(.*\bdesuscribirme\b.*)'), desuscribirme),
        MessageHandler(filters.Regex(r'(?i)(.*\bmemes\b.*)'), memes),
        MessageHandler(filters.Regex(r'(?i)(.*\bmeme\b.*)'), memes),
        MessageHandler(filters.Regex(r'(?i)(.*\bcolaborar\b.*)'), colaborar),
        MessageHandler(filters.Regex(r'(?i)(.*\binformacion\b.*)'), informacion),
        MessageHandler(filters.Regex(r'(?i)(.*\bmensajear\b.*)'), mensaje_trigger),
        MessageHandler(filters.Regex(r'(?i)(.*\bhola\b.*)'), start),
        MessageHandler(filters.Regex(r'(?i)(.*\bcolectivas\b.*)'), colectivas),
        MessageHandler(filters.Regex(r'(?i)(.*\bgracias\b.*)'), de_nada),
        MessageHandler(filters.Regex(r'(?i)(.*\bJilguero\b.*)'), Jilguero),
        MessageHandler(filters.Regex(r'(?i)(.*\bInterislena\b.*)'), Interislena),
        MessageHandler(filters.Regex(r'(?i)(.*\bLineasDelta\b.*)'), LineasDelta),
        MessageHandler(filters.Regex(r'(?i)(.*\balmaceneras\b.*)'), almaceneras),
        MessageHandler(filters.Regex(r'(?i)(.*\balmacenera\b.*)'), almaceneras),
        MessageHandler(filters.Regex(r'(?i)(.*\balmacén\b.*)'), almaceneras),
        MessageHandler(filters.Regex(r'(?i)(.*\balmacen\b.*)'), almaceneras),
        MessageHandler(filters.Regex(r'(?i)(.*\bhidrografia\b.*)'), hidrografia),
        MessageHandler(filters.Regex(r'(?i)(.*\bamanita\b.*)'), amanita),
        MessageHandler(filters.Regex(r'(?i)(.*\balfareria\b.*)'), alfareria),
        MessageHandler(filters.Regex(r'(?i)(.*\blabusqueda\b.*)'), labusqueda),
        MessageHandler(filters.Regex(r'(?i)(.*\bcanaveralkayaks\b.*)'), canaveralkayaks),
        # LLM como fallback
        MessageHandler(filters.TEXT, llm_fallback)
    ]
    
    # Combine all handlers, with command handlers first to ensure they take priority
    handlers = command_handlers + message_handlers

    conv_handler = ConversationHandler(
        entry_points=handlers,
        states={
            ANSWER_charlar: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_charlar)],
            ANSWER_meme: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme)],
            ANSWER_meme2: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_meme2)],
            ANSWER_informacion: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), answer_informacion)],
            ANSWER_colaborar: [MessageHandler(filters.Regex(r'^(Mensajear|mensajear|MENSAJEAR|Aportar|aportar|APORTAR)$'), answer_colaborar)],
            ANSWER_mareas_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), mareas_suscribir)],
            ANSWER_windguru_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), windguru_suscribir)],
            ANSWER_hidrografia_suscribir: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), hidrografia_suscribir)],
            ANSWER_mensajear: [MessageHandler(filters.TEXT, mensajear)],
            ANSWER_desuscribir: [MessageHandler(filters.Regex(r'^(Mareas|MAREAS|mareas|Windguru|WINDGURU|windguru|Hidrografía|HIDROGRAFÍA|hidrografia|Hidrografia)$'), answer_desuscribir)],
            ANSWER_charlar_windguru: [MessageHandler(filters.Regex(r'^(Si|si|SI|No|no|NO)$'), charlar_windguru)],
            ANSWER_jilguero: [MessageHandler(filters.TEXT, answer_jilguero)],
            ANSWER_interislena: [MessageHandler(filters.TEXT, answer_interislena)],
            ANSWER_direction: [MessageHandler(filters.TEXT, direction)],
            ANSWER_schedule: [MessageHandler(filters.TEXT, schedule)],
            ANSWER_almacenera_select: [MessageHandler(filters.TEXT, almacenera_selected)],
            ANSWER_colectivas: [MessageHandler(filters.TEXT, answer_colectivas)],
            ANSWER_suscribirme: [MessageHandler(filters.Regex(r'^(Mareas|mareas|Hidrografia|hidrografia|Windguru|windguru)$'), answer_suscribirme)],
        },
        # LLM fallback handler
        fallbacks=[MessageHandler(filters.TEXT, llm_fallback)] + handlers,
    )

    application.add_handler(conv_handler)
    application.run_polling()