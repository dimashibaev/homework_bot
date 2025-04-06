import logging
import os
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from exceptions import (APIRequestError, APIResponseFormatError,
                        StatusUnknownError, TokenMissingError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('program.log', mode='w', encoding='utf-8')
    ]
)

def check_tokens():
    """Проверяет наличие всех обязательных переменных окружения."""
    if not PRACTICUM_TOKEN:
        raise TokenMissingError('Отсутствует переменная PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise TokenMissingError('Отсутствует переменная TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        raise TokenMissingError('Отсутствует переменная TELEGRAM_CHAT_ID')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        logging.info('Начинаю отправку сообщения в Telegram...')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except ApiTelegramException as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрашивает данные с API Практикума."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise APIRequestError(
                f'Ошибка при запросе к API: статус {response.status_code}, '
                f'ответ: {response.text}'
            )
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка соединения с API: {error}')
        raise APIRequestError(f'Сбой при запросе к API: {error}')


def check_response(response):
    """Проверяет структуру ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Ожидался словарь в ответе API.')
    if 'homeworks' not in response:
        raise APIResponseFormatError('Отсутствует ключ "homeworks" в ответе API.')
    if 'current_date' not in response:
        raise APIResponseFormatError('Отсутствует ключ "current_date" в ответе API.')
    homeworks = response.get('homeworks')
    current_date = response.get('current_date')
    if not isinstance(homeworks, list):
        raise TypeError('"homeworks" должен быть списком.')
    if not isinstance(current_date, int):
        raise APIResponseFormatError('"current_date" должен быть целым числом.')
    return homeworks


def parse_status(homework):
    """Формирует сообщение в зависимости от статуса домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise APIResponseFormatError('В ответе нет названия домашней работы.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise StatusUnknownError(f'Неизвестный статус: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основной цикл работы бота."""
    try:
        check_tokens()
    except TokenMissingError as error:
        logging.critical(f'Критическая ошибка: {error}')
        raise

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logging.debug('Новых статусов нет.')
            timestamp = response.get('current_date', timestamp)
        except (APIRequestError, APIResponseFormatError, StatusUnknownError) as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        except Exception as error:
            message = f'Неизвестная ошибка: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
