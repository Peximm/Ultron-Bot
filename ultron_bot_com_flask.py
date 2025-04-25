
import os
import pickle
import shutil
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ===== FLASK PARA MANTER PORTA ATIVA =====
app = Flask(__name__)

@app.route('/')
def home():
    return 'Ultron bot está vivo!'

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# ===== CONFIGS =====
TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_DIR = 'fotos_preventiva'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_NAME = 'Ultron/fotos_preventiva'

# ===== AUTENTICAÇÃO GOOGLE DRIVE =====
def authenticate_drive():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
           import os
import json
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import tempfile

def authenticate_drive():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
        tmp_file.write(creds_json)
        tmp_file.flush()
        creds = InstalledAppFlow.from_client_secrets_file(tmp_file.name, SCOPES)
    return build('drive', 'v3', credentials=creds)
            creds = flow.run_console()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

drive_service = authenticate_drive()

# ===== DADOS EM TEMPO DE EXECUÇÃO =====
cronometro = {}
grupos_recebidos = {}
fotos_recebidas = {}

def get_today():
    return datetime.now().strftime('%Y-%m-%d')

# ===== GOOGLE DRIVE =====
def create_drive_folder_structure(parent_name, subfolder_name):
    def get_or_create_folder(name, parent_id=None):
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = drive_service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        file_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            file_metadata['parents'] = [parent_id]
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        return file['id']

    root = get_or_create_folder('Ultron')
    fotos = get_or_create_folder('fotos_preventiva', root)
    data = get_or_create_folder(parent_name, fotos)
    grupo = get_or_create_folder(subfolder_name, data)
    return grupo

def upload_to_drive(local_path, drive_folder_id):
    for file_name in os.listdir(local_path):
        file_path = os.path.join(local_path, file_name)
        if os.path.isfile(file_path):
            media = MediaFileUpload(file_path, resumable=True)
            drive_service.files().create(
                body={'name': file_name, 'parents': [drive_folder_id]},
                media_body=media,
                fields='id'
            ).execute()

# ===== TELEGRAM BOT =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟢 Iniciar Preventiva", callback_data='iniciar')],
        [InlineKeyboardButton("🔴 Encerrar Preventiva", callback_data='encerrar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Escolha uma ação:", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'iniciar':
        await iniciar(query, context)
    elif query.data == 'encerrar':
        await encerrar(query, context)

async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    if today in cronometro and 'start' in cronometro[today]:
        await update.message.reply_text("⏱ Preventiva já iniciada.")
        return
    cronometro[today] = {'start': datetime.now()}
    grupos_recebidos[today] = set()
    fotos_recebidas[today] = 0
    await update.message.reply_text(f"🟢 Preventiva iniciada às {cronometro[today]['start'].strftime('%H:%M:%S')}.")

async def encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    if today not in cronometro or 'start' not in cronometro[today]:
        await update.message.reply_text("⚠️ A preventiva ainda não foi iniciada.")
        return
    if 'end' in cronometro[today]:
        await update.message.reply_text("⏹ Preventiva já encerrada.")
        return
    cronometro[today]['end'] = datetime.now()
    start = cronometro[today]['start']
    end = cronometro[today]['end']
    duration = end - start
    total_grupos = len(grupos_recebidos.get(today, []))
    total_fotos = fotos_recebidas.get(today, 0)

    log_path = os.path.join(BASE_DIR, f"preventiva_{today}_log.txt")
    with open(log_path, 'w') as log:
        log.write(f"Data: {today}\n")
        log.write(f"Início: {start.strftime('%H:%M:%S')}\n")
        log.write(f"Fim: {end.strftime('%H:%M:%S')}\n")
        log.write(f"Duração total: {str(duration)}\n")
        log.write(f"Total de grupos recebidos: {total_grupos}\n")
        log.write(f"Total de fotos: {total_fotos}\n")

    await update.message.reply_text(f"✅ Preventiva encerrada. Tempo: {str(duration)}.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or "sem_legenda"
    today = get_today()

    if today in cronometro and 'start' in cronometro[today] and 'end' not in cronometro[today]:
        grupos_recebidos[today].add(caption)
        fotos_recebidas[today] += 1

    daily_path = os.path.join(BASE_DIR, today, caption)
    os.makedirs(daily_path, exist_ok=True)

    photo = await message.photo[-1].get_file()
    count = len(os.listdir(daily_path)) + 1
    filename = os.path.join(daily_path, f"{count:02d}.jpg")
    await photo.download_to_drive(filename)

    folder_id = create_drive_folder_structure(today, caption)
    upload_to_drive(daily_path, folder_id)

# ===== INICIAR BOT E FLASK =====
def start_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(handle_buttons))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.run_polling()

if __name__ == "__main__":
    Thread(target=start_bot).start()
    run_flask()
