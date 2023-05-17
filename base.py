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
RANGE_NAME = 'Евген!A1:H1000'
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





def parse_message(message_text):
    filters = {
        "difficulty_min": "-",
        "difficulty_max": "-",
        "duration_min": "-",
        "duration_max": "-",
        "genre": None,
        "is_single": True
    }

    words = message_text.lower().split()
    for i, word in enumerate(words):
        if word == 'сложность':
            if words[i + 1] == 'от':
                filters["difficulty_min"] = float(words[i + 2])
                if len(words) > i+3 and words[i + 3] == 'до':
                    filters["difficulty_max"] = float(words[i + 4])
            elif words[i + 1] == 'до':
                filters["difficulty_max"] = float(words[i + 2])
            else:
                filters["difficulty_min"] = filters["difficulty_max"] = float(words[i + 1])

        elif word == 'время':
            if words[i + 1] == 'от':
                filters["duration_min"] = float(words[i + 2])
                if len(words) > i+3 and words[i + 3] == 'до':
                    filters["duration_max"] = float(words[i + 4])
            elif words[i + 1] == 'до':
                filters["duration_max"] = float(words[i + 2])
            else:
                filters["duration_min"] = filters["duration_max"] = float(words[i + 1])

        elif word in ['гонки', 'шутеры', 'rpg', 'платформеры','соулсы', 'экшены']:
            filters["genre"] = word.lower()

        elif word in ['соло', 'кооп']:
            filters["type"] = word.lower()
    print(f"Filters: {filters}")
    return filters



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



from bs4 import BeautifulSoup


def parse_game_info(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    selectors = {
        "Игра есть у:": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(2)',
        "получили платину": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(6)',
        "среднее завершение": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(10)',
        "среднее время платины": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(14)',
        "получили платины": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(18)',
        "хардкорные очки": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div.tlpf_bsc_label_list_right.htmlTPLBox',
        "очки редкости": '#tlpfid_global_uploads_bx > div > div.tlpf_global_content_static > div:nth-child(1) > div.gtpl_gb_body.gtpl_gb_bindent > div > div:nth-child(26)',
    }

    game_info = {}
    for label, selector in selectors.items():
        element = soup.select_one(selector)
        if element:
            game_info[label] = element.text
        else:
            game_info[label] = "Не найдено"

    return game_info





def find_games_by_filters(service, filters):
    game_data = {}

    range_name = 'Евген!A1:H'
    response = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = response.get('values', [])

    count_of_ones = 0
    for row in values:
        if row and row[0] == "1":
            count_of_ones += 1

        if count_of_ones < 3 or not row:
            continue

        if len(row) > 5:
            difficulty = row[2] if row[2] != "-" else None
            duration = row[3] if row[3] != "-" else None
            genre = row[4] if row[4] else ''
            game_type = row[5] if row[5] else ''
            stratege_link = row[6] if len(row) > 6 else None

            difficulty_min = float(filters.get("difficulty_min")) if filters.get("difficulty_min") != "-" else None
            difficulty_max = float(filters.get("difficulty_max")) if filters.get("difficulty_max") != "-" else None
            duration_min = float(filters.get("duration_min")) if filters.get("duration_min") != "-" else None
            duration_max = float(filters.get("duration_max")) if filters.get("duration_max") != "-" else None

            matches_difficulty = (difficulty is None) or ((difficulty_min is None or difficulty_min <= float(difficulty)) and (difficulty_max is None or difficulty_max >= float(difficulty)))
            matches_duration = (duration is None) or ((duration_min is None or duration_min <= float(duration)) and (duration_max is None or duration_max >= float(duration)))
            matches_genre = filters.get("genre") == genre.lower() if filters.get("genre") else True
            matches_type = "type" in filters and filters["type"].lower() == game_type.lower() if filters.get("type") else True


            if matches_difficulty and matches_duration and matches_genre and matches_type:
                game_title = row[1]
                game_data[game_title] = {
                    'difficulty': difficulty,
                    'duration': duration,
                    'genre': genre,
                    'type': game_type,
                    'stratege_link': stratege_link,
                }

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
@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Введите жанр игры, и я помогу найти игры этого жанра.")


game_genre_data = None

message_with_inline_keyboard_id = None

@dp.message_handler()
async def process_message(message: types.Message):
    global game_genre_data, message_with_inline_keyboard_id
    filters = parse_message(message.text)
    service = get_google_sheets_service()
    game_genre_data = find_games_by_filters(service, filters)

    if game_genre_data:
        inline_keyboard = create_inline_keyboard(game_genre_data)
        sent_message = await bot.send_message(chat_id=message.chat.id, text="Выберите игру:", reply_markup=inline_keyboard)
        message_with_inline_keyboard_id = sent_message.message_id  # сохраняем id сообщения
    else:
        await message.reply(f"Игр, соответствующих вашим критериям, не найдено. Попробуйте изменить фильтры.")




last_messages = []

async def delete_old_message(chat_id):
    if len(last_messages) >= 3:
        message_id_to_delete = last_messages.pop(0)
        try:
            await bot.delete_message(chat_id, message_id_to_delete)
        except Exception as e:
            logging.error(f"Failed to delete message: {e}")



async def on_game_selected(call: types.CallbackQuery, game_title: str, game_info: dict):
    await delete_old_message(call.from_user.id)

    difficulty = game_info["difficulty"]
    duration = game_info["duration"]
    stratege_link = game_info["stratege_link"]
    game_type = game_info["type"]

    api_key = "4bc045b03add4da58f6ce570eada124b"
    game_description, game_cover_url = get_game_description_and_cover(game_title, api_key)

    # Добавить информацию со страницы Stratege
    stratege_info = parse_game_info(stratege_link)

    response = text(
        bold(game_title), "\n\n",
        'Сложность', ": ", difficulty, "\n",
        'Продолжительность', ": ", duration, "\n",
        'Тип игры', ": ", game_type, "\n",
        # Дополнительные данные с Stratege
        'Игра есть у', ": ", stratege_info.get("Игра есть у:", "Не найдено"), "\n",
        'Получили платину', ": ", stratege_info.get("получили платину", "Не найдено"), "\n",
        'Среднее завершение', ": ", stratege_info.get("среднее завершение", "Не найдено"), "\n",
        'Среднее время платины', ": ", stratege_info.get("среднее время платины", "Не найдено"), "\n",
        'Получили платины', ": ", stratege_info.get("получили платины", "Не найдено"), "\n",
        'Хардкорные очки', ": ", stratege_info.get("хардкорные очки", "Не найдено"), "\n",
        'Очки редкости', ": ", stratege_info.get("очки редкости", "Не найдено"), "\n",
        sep=""
    )  # Здесь была пропущена закрывающая скобка

    max_caption_length = 1024
    if len(response) > max_caption_length:
        response = response[:max_caption_length - 3] + "..."

    link_button = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text="Перейти к игре", url=stratege_link))

    if game_cover_url:
        sent_message = await bot.send_photo(chat_id=call.from_user.id, photo=game_cover_url, caption=response, parse_mode=ParseMode.MARKDOWN, reply_markup=link_button)
    else:
        sent_message = await bot.send_message(chat_id=call.from_user.id, text=response, parse_mode=ParseMode.MARKDOWN, reply_markup=link_button)

    last_messages.append(sent_message.message_id)





@dp.callback_query_handler()
async def process_callback(call: types.CallbackQuery):
    global message_with_inline_keyboard_id
    game_title = call.data
    game_info = game_genre_data.get(game_title)
    if game_info:
        # удаление сообщения с кнопками
        await on_game_selected(call, game_title, game_info)
        if message_with_inline_keyboard_id is not None:
            try:
                await bot.delete_message(chat_id=call.message.chat.id, message_id=message_with_inline_keyboard_id)
                message_with_inline_keyboard_id = None
            except Exception as e:
                logging.error(f"Failed to delete message: {e}")
        #await on_game_selected(call, game_title, game_info)
    else:
        await call.answer("Ошибка: информация об игре не найдена.")


if __name__ == "__main__":
    from aiogram import executor


    dp.register_message_handler(process_message)

    executor.start_polling(dp, skip_updates=True)
