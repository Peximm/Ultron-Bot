import os
import json
import logging
import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

TOKEN = '7882548745:AAEh7yTF34sXju1S3IcjCZ3izRkrZEtMNKc'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = '1Vdd13R0bbKRETLNH9tcrbKl5S2Ip-s3p?hl=pt-br'

# ===== Autenticação com Google Drive =====
def authenticate_drive():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_console()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service

drive_service = authenticate_drive()

# ===== Variáveis globais =====
registro = []
inicio_data = None

# ===== Handlers do Telegram =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Iniciar preventiva", callback_data='iniciar')],
        [InlineKeyboardButton("Encerrar preventiva", callback_data='encerrar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("O que deseja fazer?", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    global inicio_data, registro

    if query.data == 'iniciar':
        inicio_data = datetime.datetime.now()
        registro = []
        await query.edit_message_text(text="Cronômetro iniciado.")
    elif query.data == 'encerrar':
        if inicio_data:
            fim_data = datetime.datetime.now()
            duracao = fim_data - inicio_data
            await query.edit_message_text(
                text=f"Cronômetro encerrado. Duração: {str(duracao)}"
            )
            inicio_data = None
        else:
            await query.edit_message_text(text="Nenhuma preventiva em andamento.")

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    foto = update.message.photo[-1]
    arquivo = await foto.get_file()
    data_hora = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nome_arquivo = f"{data_hora}.jpg"

    await arquivo.download_to_drive(nome_arquivo)

    # Upload pro Google Drive
    file_metadata = {'name': nome_arquivo, 'parents': [FOLDER_ID]}
    media = MediaFileUpload(nome_arquivo, mimetype='image/jpeg')
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    os.remove(nome_arquivo)
    await update.message.reply_text("Foto recebida e enviada ao Drive.")

# ===== Flask app =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Ultron Bot rodando com Flask."

# ===== Inicialização =====
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, receber_foto))

    # Inicia o bot com polling em thread separada
    import threading
    threading.Thread(target=app.run_polling).start()

    # Roda Flask (Render requer um servidor ativo)
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
