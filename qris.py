import qrcode
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Token Telegram Bot
TOKEN = "8183122181:AAFd4urRYq5p2FYQUDb-iKFLDmWC8xyBAg4"

# Inisialisasi bot dan dispatcher dengan storage untuk FSM
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Definisi FSM untuk menyimpan data
class QRISState(StatesGroup):
    waiting_for_qris = State()
    waiting_for_nominal = State()
    waiting_for_biaya = State()

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
async def start(message: types.Message, state: FSMContext):
    await state.set_state(QRISState.waiting_for_qris)
    await message.answer("Kirimkan QRIS statis Anda dalam bentuk teks:")

# Handler untuk menerima QRIS statis
@dp.message(QRISState.waiting_for_qris)
async def get_qris_statis(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Mohon kirim QRIS dalam bentuk teks, bukan gambar atau file.")
        return
    
    qris_statis = message.text
    await state.update_data(qris_statis=qris_statis)
    await state.set_state(QRISState.waiting_for_nominal)
    await message.answer("Masukkan nominal pembayaran (hanya angka):")

# Handler untuk menerima nominal pembayaran
@dp.message(QRISState.waiting_for_nominal)
async def get_nominal(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Mohon masukkan nominal dalam angka.")
        return
    
    nominal = message.text
    await state.update_data(nominal=nominal)
    
    # Keyboard untuk biaya layanan
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Tanpa Biaya", callback_data="biaya_none"))
    keyboard.add(types.InlineKeyboardButton(text="Tambah Biaya", callback_data="biaya_add"))

    await state.set_state(QRISState.waiting_for_biaya)
    await message.answer("Apakah ada biaya layanan?", reply_markup=keyboard)

# Handler untuk biaya layanan
@dp.callback_query(QRISState.waiting_for_biaya)
async def biaya_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qris_statis = data["qris_statis"]
    nominal = data["nominal"]

    if callback.data == "biaya_none":
        qris_dinamis = convert_qris(qris_statis, nominal, None)
        
        # Buat QR Code
        filename = f"qris_{callback.from_user.id}.png"
        generate_qr(qris_dinamis, filename)

        await bot.send_photo(callback.from_user.id, FSInputFile(filename), caption=f"QRIS Dinamis:\n`{qris_dinamis}`", parse_mode="Markdown")
        await state.clear()
    
    elif callback.data == "biaya_add":
        await callback.message.answer("Masukkan biaya layanan dalam angka:")
        await state.set_state(QRISState.waiting_for_biaya)

# Handler untuk biaya layanan dalam rupiah
@dp.message(QRISState.waiting_for_biaya)
async def get_biaya_layanan(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Mohon masukkan biaya layanan dalam angka.")
        return
    
    biaya = message.text
    data = await state.get_data()
    
    qris_statis = data["qris_statis"]
    nominal = data["nominal"]
    
    qris_dinamis = convert_qris(qris_statis, nominal, biaya)
    
    # Buat QR Code
    filename = f"qris_{message.from_user.id}.png"
    generate_qr(qris_dinamis, filename)

    await bot.send_photo(message.chat.id, FSInputFile(filename), caption=f"QRIS Dinamis:\n`{qris_dinamis}`", parse_mode="Markdown")
    await state.clear()

# Menjalankan bot
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
