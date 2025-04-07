import logging
import os
import sys
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


def check_tokens():
    """Проверяет наличие всех обязательных переменных окружения."""
    required_tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )
    missing = []
    for name, token in required_tokens:
        if not token:
            logging.critical(f'Переменная {name} отсутствует.')
            missing.append(name)
    if missing:
        raise TokenMissingError(
            f'Отсутствуют переменные: {", ".join(missing)}')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        logging.info('Начинаю отправку сообщения в Telegram...')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
        return True
    except (ApiTelegramException, requests.RequestException) as error:
        raise APIRequestError(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Запрашивает данные с API Практикума."""
    params = {'from_date': timestamp}
    log_msg = (
        'Запрос к {url} с заголовками {headers} и параметрами {params}'
    ).format(url=ENDPOINT, headers=HEADERS, params=params)
    logging.info(log_msg)
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise APIRequestError(f'Ошибка запроса к API: {error}')
    if response.status_code != requests.codes.ok:
        raise APIRequestError(
            f'Ошибка ответа API: {response.status_code}, {response.text}'
        )
    return response.json()


def check_response(response):
    """Проверяет структуру ответа API."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ожидался словарь в ответе API, получено {type(response)}'
        )
    if 'homeworks' not in response:
        raise APIResponseFormatError('Отсутствует ключ "homeworks".')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            f'"homeworks" должен быть списком, получено {type(homeworks)}'
        )
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
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if send_message(bot, message):
                    timestamp = response.get('current_date', timestamp)
                    last_message = ''
            else:
                logging.debug('Новых статусов нет.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message != last_message:
                try:
                    send_message(bot, message)
                except Exception as send_err:
                    logging.error(
                        f'Ошибка при отправке в Telegram: {send_err}')
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('program.log', mode='w', encoding='utf-8')
        ]
    )
    try:
        main()
    except Exception as e:
        logging.critical(f'Критическая ошибка: {e}')
