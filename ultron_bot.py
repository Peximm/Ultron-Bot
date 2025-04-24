
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get('TELEGRAM_TOKEN')
BASE_DIR = 'fotos_preventiva'

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

cronometro = {}
grupos_recebidos = {}
fotos_recebidas = {}

def get_today():
    return datetime.now().strftime('%Y-%m-%d')

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
        await update.message.reply_text("⚠️ A preventiva de hoje ainda não foi iniciada. Use /iniciar primeiro.")
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

    await update.message.reply_text(
        f"✅ Preventiva encerrada. Tempo total: {str(duration)}. Log salvo em: {log_path}"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or "sem_legenda"
    today = get_today()

    if today in cronometro and 'start' in cronometro[today] and 'end' not in cronometro[today]:
        grupos_recebidos[today].add(caption)
        fotos_recebidas[today] += 1

    daily_path = os.path.join(BASE_DIR, today)
    album_path = os.path.join(daily_path, caption)
    os.makedirs(album_path, exist_ok=True)

    photo = await message.photo[-1].get_file()
    count = len(os.listdir(album_path)) + 1
    filename = os.path.join(album_path, f"{count:02d}.jpg")
    await photo.download_to_drive(filename)

    print(f"📸 Foto salva em: {filename}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("iniciar", iniciar))
app.add_handler(CommandHandler("encerrar", encerrar))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.run_polling()
