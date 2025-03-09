import qrcode
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command

# Token bot dari BotFather
BOT_TOKEN = "8183122181:AAFd4urRYq5p2FYQUDb-iKFLDmWC8xyBAg4"

# Inisialisasi bot dan dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Dictionary untuk menyimpan data pengguna
user_data = {}

def calculate_crc16(qr_string):
    crc = 0xFFFF
    poly = 0x1021
    for byte in qr_string.encode():
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF  
    return f"{crc:04X}"

def generate_dynamic_qris(qris_static, amount):
    qris_body = qris_static[:-8]  
    formatted_amount = "{:.2f}".format(amount)
    tag_54 = f"54{len(formatted_amount):02}{formatted_amount}"
    qris_dynamic = qris_body + tag_54
    checksum = calculate_crc16(qris_dynamic)
    qris_dynamic += f"6304{checksum}"
    return qris_dynamic

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Kirimkan teks QRIS statis yang ingin diubah menjadi dinamis.")

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in user_data and user_data[user_id].get("waiting_amount"):
        try:
            amount = float(text)
            qris_statis = user_data[user_id]["qris"]
            qris_dinamis = generate_dynamic_qris(qris_statis, amount)

            # Escaping karakter khusus untuk MarkdownV2
            escaped_qris = qris_dinamis.replace("-", "\\-").replace(".", "\\.")

            # Generate QR Code
            qr = qrcode.make(qris_dinamis)
            qr_path = f"qris_{user_id}.png"
            qr.save(qr_path)

            # Mengirim QRIS dalam format monospace
            await message.answer(f"QRIS Dinamis:\n```\n{escaped_qris}\n```", parse_mode="MarkdownV2")

            # Mengirim gambar QR Code
            photo = FSInputFile(qr_path)
            await message.answer_photo(photo=photo, caption="Berikut QR Code-nya.")

            # Hapus gambar setelah dikirim
            os.remove(qr_path)
            del user_data[user_id]

        except ValueError:
            await message.answer("Format nominal tidak valid. Masukkan angka, contoh: 50000")
    else:
        user_data[user_id] = {"qris": text, "waiting_amount": True}
        await message.answer("Masukkan nominal pembayaran (contoh: 50000).")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Bot sedang berjalan...")
    asyncio.run(main())
