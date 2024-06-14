from flask import Flask, jsonify, request
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

# Initialize the Bot instance
bot = Bot(token='7256914379:AAFSDgHNuCZy8JAx1Wxu_-WLjf_fniHnfUs')

# Create a Dispatcher instance
dp = Dispatcher()

# Assign the bot to the dispatcher
dp.bot = bot

app = Flask(__name__)
counter = 0

# Create a new book
@app.route('/book', methods=['POST'])
def create_book():
    global counter
    if request.json:
        match_number = request.json['match_number']
        total_price = request.json['total_price']
        unit_price = request.json['unit_price']
        category = request.json['category']
        formatted_data = f'<b>Матч:</b> <i>{match_number}</i>\n<b>Кількість квитків та категорія:</b> <i>{category}</i>\n<b>Ціна за квиток:</b> <i>{unit_price}</i>\n<b>Ціна за всі квитки:</b> <i>{total_price}</i>'
        asyncio.run(send_to_group_channel(formatted_data))
    return ''

async def send_to_group_channel(data):
    # Replace 'GROUP_CHANNEL_ID' with the actual ID of your group channel
    await bot.send_message(chat_id='-4228000254', text=data, parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app.run(debug=True, port=8000)