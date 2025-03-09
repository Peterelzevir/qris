import qrcode
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Token Telegram Bot
TOKEN = "8183122181:AAFd4urRYq5p2FYQUDb-iKFLDmWC8xyBAg4"

# Inisialisasi bot
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Fungsi CRC16
def crc16(data: str) -> str:
    crc = 0xFFFF
    for char in data:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    return format(crc & 0xFFFF, '04X')

# Fungsi konversi QRIS
def convert_qris(qris_statis: str, nominal: str, biaya: str = None) -> str:
    qris_statis = qris_statis[:-4]  # Hapus checksum lama
    qris_dinamis = qris_statis.replace("010211", "010212")  # Ubah statis ke dinamis
    
    # Pisah berdasarkan '5802ID'
    step2 = qris_dinamis.split("5802ID")
    
    # Format nominal (Tag 54)
    nominal_tag = f"54{len(nominal):02}{nominal}"
    
    # Tambahkan biaya layanan jika ada
    biaya_tag = ""
    if biaya:
        biaya_tag = f"55020256{len(biaya):02}{biaya}"
    
    # Gabungkan kembali
    qris_final = f"{step2[0]}{nominal_tag}{biaya_tag}5802ID{step2[1]}"
    
    # Hitung ulang CRC16
    qris_final += crc16(qris_final)
    return qris_final

# Fungsi untuk membuat QR Code
def generate_qr(qris_data: str, filename: str):
    qr = qrcode.make(qris_data)
    qr.save(filename)

# Command Start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Kirimkan QRIS statis Anda:")

# Handler untuk menerima QRIS statis
@dp.message(lambda msg: len(msg.text) > 50)  # QRIS umumnya panjang
async def get_qris_statis(message: types.Message):
    qris_statis = message.text
    await message.answer("Masukkan nominal pembayaran:")
    
    # Simpan data sementara
    await bot.storage.set_data(message.from_user.id, {"qris_statis": qris_statis})

# Handler untuk menerima nominal pembayaran
@dp.message(lambda msg: msg.text.isdigit())
async def get_nominal(message: types.Message):
    nominal = message.text
    data = await bot.storage.get_data(message.from_user.id)
    
    qris_statis = data.get("qris_statis")
    
    # Keyboard biaya layanan
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Tanpa Biaya", callback_data=f"biaya_none|{qris_statis}|{nominal}")
    keyboard.button(text="Tambah Biaya", callback_data=f"biaya_add|{qris_statis}|{nominal}")
    
    await message.answer("Apakah ada biaya layanan?", reply_markup=keyboard.as_markup())

# Handler untuk biaya layanan
@dp.callback_query(lambda c: c.data.startswith("biaya_"))
async def biaya_handler(callback: types.CallbackQuery):
    data = callback.data.split("|")
    biaya_type, qris_statis, nominal = data[0], data[1], data[2]

    if biaya_type == "biaya_none":
        biaya = None
        qris_dinamis = convert_qris(qris_statis, nominal, biaya)
        
        # Buat QR Code
        filename = f"qris_{callback.from_user.id}.png"
        generate_qr(qris_dinamis, filename)

        # Kirim hasil QR Code
        await bot.send_photo(callback.from_user.id, FSInputFile(filename), caption=f"QRIS Dinamis:\n`{qris_dinamis}`", parse_mode="Markdown")
    
    elif biaya_type == "biaya_add":
        await bot.storage.set_data(callback.from_user.id, {"qris_statis": qris_statis, "nominal": nominal})
        await callback.message.answer("Masukkan biaya layanan dalam rupiah:")

# Handler untuk biaya layanan dalam rupiah
@dp.message(lambda msg: msg.text.isdigit())
async def get_biaya_layanan(message: types.Message):
    biaya = message.text
    data = await bot.storage.get_data(message.from_user.id)
    
    qris_statis = data.get("qris_statis")
    nominal = data.get("nominal")
    
    qris_dinamis = convert_qris(qris_statis, nominal, biaya)
    
    # Buat QR Code
    filename = f"qris_{message.from_user.id}.png"
    generate_qr(qris_dinamis, filename)

    # Kirim hasil QR Code
    await bot.send_photo(message.chat.id, FSInputFile(filename), caption=f"QRIS Dinamis:\n`{qris_dinamis}`", parse_mode="Markdown")

# Menjalankan bot
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
