import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils.markdown import bold, text
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import Dict, Tuple
import json

API_TOKEN = '6223143592:AAE3Di2QclY7OAx-P6v_0j5VuBs_xx0ZAxc'
CREDENTIALS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '14iMjA7HdkSCAkInETlOxk98xRLq3YnrSiiWXFj120A0'
RANGE_NAME = 'Евген!A1:E1000'
GENRE_RANGE = 'Евген!G2:H4'

logging.basicConfig(level=logging.INFO)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_gspread_client_manager():
    return gspread.service_account(filename=CREDENTIALS_FILE)

def get_gspread_client():
    return gspread.service_account(filename=CREDENTIALS_FILE)

def get_cell_info(service, spreadsheet_id, sheet_name, row, col):
    cell_address = f"{sheet_name}!{gspread.utils.rowcol_to_a1(row, col)}"
    print(f"Getting cell info for address: {cell_address}")
    response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=[cell_address], fields="sheets/data/rowData/values(userEnteredFormat,formattedValue)").execute()
    
    if "sheets" not in response or len(response["sheets"]) == 0 or "data" not in response["sheets"][0] or len(response["sheets"][0]["data"]) == 0 or "rowData" not in response["sheets"][0]["data"][0] or len(response["sheets"][0]["data"][0]["rowData"]) == 0:
        return None, None
    
    cell_data = response["sheets"][0]["data"][0]["rowData"][0]["values"][0]
    cell_value = cell_data["formattedValue"] if "formattedValue" in cell_data else None
    cell_format = cell_data["userEnteredFormat"] if "userEnteredFormat" in cell_data else None
    color = cell_format["backgroundColor"] if cell_format and "backgroundColor" in cell_format else None
    print(f"Cell value: {cell_value}, Cell color: {color}")
    return cell_value, color

import time

def find_games_by_genre_color(service, genre_color):
    game_data = {}
    row = 1
    game_count = 0

    while game_count < 3:
        cell_value, _ = get_cell_info(service, SPREADSHEET_ID, "Евген", row, 2)
        if cell_value == "Игра":
            game_count += 1
        row += 1

    range_name = f'Евген!B{row}:E'
    response = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = response.get('values', [])

    response = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=[range_name], fields="sheets/data/rowData/values(userEnteredFormat,formattedValue)").execute()
    rowData = response['sheets'][0]['data'][0]['rowData']

    for i, row in enumerate(rowData):
        if 'userEnteredFormat' in row['values'][0] and 'backgroundColor' in row['values'][0]['userEnteredFormat']:
            cell_color = row['values'][0]['userEnteredFormat']['backgroundColor']
            if colors_are_similar(cell_color, genre_color):
                game_title = values[i][0]
                difficulty = values[i][1]
                duration = values[i][2]
                trophy = values[i][3]
                game_data[game_title] = {"difficulty": difficulty, "duration": duration, "trophy": trophy}
        time.sleep(0.1)  # Задержка между запросами

    return game_data






def colors_are_similar(color1, color2, tolerance=30):
    color1_rgb = {
        "red": int(color1.get("red", 0) * 255),
        "green": int(color1.get("green", 0) * 255),
        "blue": int(color1.get("blue", 0) * 255),
    }
    color2_rgb = {
        "red": int(color2.get("red", 0) * 255),
        "green": int(color2.get("green", 0) * 255),
        "blue": int(color2.get("blue", 0) * 255),
    }
    return (
        abs(color1_rgb["red"] - color2_rgb["red"]) <= tolerance and
        abs(color1_rgb["green"] - color2_rgb["green"]) <= tolerance and
        abs(color1_rgb["blue"] - color2_rgb["blue"]) <= tolerance
    )


def get_game_genre_data(genre):
    service = get_google_sheets_service()
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=GENRE_RANGE).execute()
    genre_values = result.get('values', [])

    print(f"Genre values: {genre_values}")

    genre_color = None
    game_genre_data = {}

    for row in range(len(genre_values)):
        if genre_color is not None:
            break
        for col in range(len(genre_values[row])):
            cell_value = genre_values[row][col]
            if cell_value == genre:
                row_number = row + 2
                col_number = col + 7
                _, genre_color = get_cell_info(service, SPREADSHEET_ID, "Евген", row_number, col_number)
                print(f"Found genre color: {genre_color}")
                break

    if genre_color:
        game_genre_data = find_games_by_genre_color(service, genre_color)

    print(f"Game genre data: {game_genre_data}")

    return game_genre_data




def get_inline_keyboard(game_genre_data):
    keyboard = types.InlineKeyboardMarkup()
    print("Game genre data items:", game_genre_data.items())

    for game_id, game_title in game_genre_data.items():
        keyboard.add(types.InlineKeyboardButton(text=game_title, callback_data=str(game_id)))

    return keyboard


def create_inline_keyboard(game_genre_data: Dict[str, Tuple[float, float, float]]) -> InlineKeyboardMarkup:
    inline_keyboard = InlineKeyboardMarkup(row_width=1)
    for game_title in game_genre_data.keys():
        inline_keyboard.insert(InlineKeyboardButton(game_title, callback_data=game_title))
    return inline_keyboard



async def on_game_selected(call: types.CallbackQuery, game_title: str, game_info: dict):
    difficulty = game_info["difficulty"]
    duration = game_info["duration"]
    trophy = game_info["trophy"]

    response = text(
        bold('Название игры'), ": ", game_title, "\n",
        bold('Сложность'), ": ", difficulty, "\n",
        bold('Продолжительность'), ": ", duration, "\n",
        bold('Трофей'), ": ", trophy,
        sep=""
    )

    await bot.send_message(chat_id=call.from_user.id, text=response, parse_mode=ParseMode.MARKDOWN)




@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Введите жанр игры, и я помогу найти игры этого жанра.")


game_genre_data = None

@dp.message_handler()
async def process_message(message: types.Message):
    global game_genre_data
    genre = message.text
    game_genre_data = get_game_genre_data(genre)

    if game_genre_data:
        inline_keyboard = create_inline_keyboard(game_genre_data)
        await bot.send_message(chat_id=message.chat.id, text="Выберите игру:", reply_markup=inline_keyboard)
    else:
        message.reply(f"Игр с жанром {genre} не найдено. Попробуйте ввести другой жанр.")


@dp.callback_query_handler()
async def process_callback(call: types.CallbackQuery):
    game_title = call.data
    game_info = game_genre_data.get(game_title)
    if game_info:
        await on_game_selected(call, game_title, game_info)
    else:
        await call.answer("Ошибка: информация об игре не найдена.")

if __name__ == "__main__":
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
