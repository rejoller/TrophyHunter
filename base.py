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
import requests
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

api_key = "4bc045b03add4da58f6ce570eada124b"

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

def find_games_by_genre(service, genre):
    game_data = {}

    range_name = 'Евген!A1:H'  # расширьте диапазон до 'H'
    response = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = response.get('values', [])

    for row in values:
        if len(row) > 7 and row[4] == genre:  # убедитесь, что в строке есть достаточно элементов

            game_title = row[1]
            difficulty = row[2]
            duration = row[3]
            trophy = row[7]  # данные о трофее в столбце G
            stratege_link = row[6]  # ссылка на stratege.ru в столбце H

            game_data[game_title] = {"difficulty": difficulty, "duration": duration, "trophy": trophy, "stratege_link": stratege_link}

    return game_data














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


def get_game_description_and_cover(game_title: str, api_key: str) -> Tuple[str, str]:

    api_key = "4bc045b03add4da58f6ce570eada124b"
    search_url = f"https://api.rawg.io/api/games?key={api_key}&search={game_title}&language=ru-RU"
    search_response = requests.get(search_url)
    search_data = search_response.json()

    if search_data["count"] > 0:
        game_info = search_data["results"][0]
        game_slug = game_info["slug"]

        game_details_url_ru = f"https://api.rawg.io/api/games/{game_slug}?key={api_key}&language=ru-RU"
        game_details_response_ru = requests.get(game_details_url_ru)
        game_details_data_ru = game_details_response_ru.json()

        game_details_url_en = f"https://api.rawg.io/api/games/{game_slug}?key={api_key}&language=en-US"
        game_details_response_en = requests.get(game_details_url_en)
        game_details_data_en = game_details_response_en.json()

        game_description_ru = game_details_data_ru["description_raw"]
        game_description_en = game_details_data_en["description_raw"]

        game_cover_url = game_info["background_image"]

        if game_description_ru:
            return game_description_ru, game_cover_url
        else:
            return game_description_en, game_cover_url
    else:
        return "Описание игры не найдено.", None




async def on_game_selected(call: types.CallbackQuery, game_title: str, game_info: dict):
    difficulty = game_info["difficulty"]
    duration = game_info["duration"]
    trophy = game_info["trophy"]
    stratege_link = game_info["stratege_link"]

    api_key = "4bc045b03add4da58f6ce570eada124b"
    game_description, game_cover_url = get_game_description_and_cover(game_title, api_key)

    response = text(
        bold(game_title), "\n\n",
        'Сложность', ": ", difficulty, "\n",
        'Продолжительность', ": ", duration, "\n",

        sep=""
    )


#'Трофей', ": ", trophy, "\n",
 #       'Описание', ": ", game_description, "\n",

    # Обрезаем подпись, если она слишком длинная
    max_caption_length = 1024
    if len(response) > max_caption_length:
        response = response[:max_caption_length - 3] + "..."

    # Создаем инлайн кнопку для ссылки
    link_button = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Перейти к игре", url=stratege_link))

    if game_cover_url:
        await bot.send_photo(chat_id=call.from_user.id, photo=game_cover_url, caption=response, parse_mode=ParseMode.MARKDOWN, reply_markup=link_button)
    else:
        await bot.send_message(chat_id=call.from_user.id, text=response, parse_mode=ParseMode.MARKDOWN, reply_markup=link_button)
















@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Введите жанр игры, и я помогу найти игры этого жанра.")


game_genre_data = None

@dp.message_handler()
async def process_message(message: types.Message):
    global game_genre_data
    genre = message.text
    service = get_google_sheets_service()
    game_genre_data = find_games_by_genre(service, genre)

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
