import qrcode
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.utils import executor

# Token bot dari BotFather
BOT_TOKEN = "8183122181:AAFd4urRYq5p2FYQUDb-iKFLDmWC8xyBAg4"

# Inisialisasi bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Dictionary untuk menyimpan data pengguna
user_data = {}

def calculate_crc16(qr_string):
    """
    Menghitung checksum CRC16-CCITT untuk QRIS.
    """
    crc = 0xFFFF
    poly = 0x1021
    
    for byte in qr_string.encode():
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF  # Masking agar tetap 16-bit

    return f"{crc:04X}"  # Output dalam format hexadecimal

def generate_dynamic_qris(qris_static, amount):
    """
    Mengubah QRIS statis menjadi dinamis dengan menambahkan nominal pembayaran.
    """
    qris_body = qris_static[:-8]  # Hapus checksum lama
    formatted_amount = "{:.2f}".format(amount)
    tag_54 = f"54{len(formatted_amount):02}{formatted_amount}"
    qris_dynamic = qris_body + tag_54
    checksum = calculate_crc16(qris_dynamic)
    qris_dynamic += f"6304{checksum}"
    return qris_dynamic

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("Kirimkan teks QRIS statis yang ingin diubah menjadi dinamis.")

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in user_data and user_data[user_id].get("waiting_amount"):
        try:
            amount = float(text)
            qris_statis = user_data[user_id]["qris"]
            qris_dinamis = generate_dynamic_qris(qris_statis, amount)

            # Generate QR Code
            qr = qrcode.make(qris_dinamis)
            qr_path = f"qris_{user_id}.png"
            qr.save(qr_path)

            # Kirim hasil
            await message.reply(f"QRIS Dinamis:\n```{qris_dinamis}```", parse_mode="Markdown")
            await message.reply_photo(photo=InputFile(qr_path), caption="Berikut QR Code-nya.")

            # Hapus gambar setelah dikirim
            os.remove(qr_path)
            del user_data[user_id]

        except ValueError:
            await message.reply("Format nominal tidak valid. Masukkan angka, contoh: 50000")
    else:
        # Simpan QRIS statis dan minta nominal
        user_data[user_id] = {"qris": text, "waiting_amount": True}
        await message.reply("Masukkan nominal pembayaran (contoh: 50000).")

if __name__ == "__main__":
    print("Bot sedang berjalan...")
    executor.start_polling(dp, skip_updates=True)
