import os
import mysql.connector
from mysql.connector import Error
import smtplib
from email.message import EmailMessage
from tokens import gmail_token
from datetime import datetime, timedelta

# Load environment variables or tokens
try:
    from tokens import openrouter_key, mysql_password, mysql_database
except ImportError:
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE')

# Database connection function with reconnect capability
def get_db_connection():
    """Create or refresh a database connection and return it"""
    try:
        # Check if there's a global connection that's still active
        global db
        if 'db' in globals() and db.is_connected():
            return db

        # Create a new connection
        db = mysql.connector.connect(
            host="facundol.mysql.pythonanywhere-services.com",
            user="facundol",
            password=mysql_password,
            database=mysql_database,
            use_pure=True,  # Use pure Python implementation for better compatibility
            connection_timeout=30
        )
        print("Database connection established")
        return db
    except Error as err:
        print(f"Error connecting to database: {err}")
        raise

# Initial database connection
try:
    db = get_db_connection()
except Error as err:
    print(f"Initial database connection failed: {err}")
    # Continue execution as we'll try to reconnect when needed

def fetch_conversations_and_chats():
    """Fetch yesterday's conversations and their chat histories from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Calculate yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).date()

        # Fetch conversations created yesterday
        cursor.execute("""
            SELECT *
            FROM conversations
            WHERE DATE(created_at) = %s
            ORDER BY created_at ASC
        """, (yesterday,))
        conversations = cursor.fetchall()

        # Fetch chat histories for conversations created yesterday
        cursor.execute("""
            SELECT ch.conversation_id, ch.role, ch.content, ch.created_at, c.name
            FROM chat_history ch
            JOIN conversations c ON ch.conversation_id = c.id
            WHERE DATE(ch.created_at) = %s
            ORDER BY ch.created_at ASC
        """, (yesterday,))
        chat_histories = cursor.fetchall()

        cursor.close()
        return conversations, chat_histories
    except Error as err:
        print(f"Error fetching data: {err}")
        return [], []

def format_conversations_and_chats(conversations, chat_histories):
    """Format conversations and chat histories for email."""
    formatted_report = "📋 *Reporte Diario de Conversaciones*\n\n"

    for conversation in conversations:
        formatted_report += f"🆔 *Conversación ID*: {conversation['id']}\n"
        formatted_report += f"👤 *Usuario*: {conversation['name']}\n"
        formatted_report += f"📅 *Creado el*: {conversation['created_at']}\n"
        formatted_report += "💬 *Historial de Mensajes*:\n"

        # Filter chat histories for this conversation
        messages = [chat for chat in chat_histories if chat['conversation_id'] == conversation['id']]
        for message in messages:
            role = "👤 Usuario" if message['role'] == "user" else "🤖 Asistente"
            formatted_report += f"  - {role} ({message['created_at']}): {message['content']}\n"

        formatted_report += "\n" + "-" * 50 + "\n\n"

    return formatted_report

def send_email_report(report_body):
    """Send the formatted report via email."""
    try:
        message = EmailMessage()
        message['From'] = "marajadesantelmo@gmail.com"
        message['To'] = "marajadesantelmo@gmail.com"
        message['Subject'] = "Reporte Diario de Conversaciones - Deltix"
        message.set_content(report_body)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("marajadesantelmo@gmail.com", gmail_token)
        server.send_message(message)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    # Fetch data from the database
    conversations, chat_histories = fetch_conversations_and_chats()

    # Format the data for the email report
    report_body = format_conversations_and_chats(conversations, chat_histories)

    # Send the email report
    send_email_report(report_body)