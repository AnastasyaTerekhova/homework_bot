from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from telebot import TeleBot, apihelper
from exceptions import (
    NoKeyException, UnknownStatusException, UnexpectedStatusException
)
from http import HTTPStatus

import time
import os
import requests
import logging
import sys


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(lineno)s',
    level=logging.INFO,
    filename='logger.log'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.setLevel(logging.CRITICAL)
logger.setLevel(logging.ERROR)
handler = RotatingFileHandler('logger.log', maxBytes=50000000, backupCount=5)
logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logging.critical('отсутствует токен PRACTICUM_TOKEN')
        return False
    elif TELEGRAM_TOKEN is None:
        logging.critical('отсутствует токен TELEGRAM_TOKEN')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('отсутствует токен TELEGRAM_CHAT_ID')
        return False
    else:
        return True


def send_message(bot, message):
    """отправляет сообщение в Telegram-чат."""
    bot.send_message(
        TELEGRAM_CHAT_ID,
        message,
    )
    logging.debug(msg='сообщение отправлено')


def get_api_answer(timestamp):
    """делает запрос к эндпоинту API-сервиса."""
    response = None
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code != HTTPStatus.OK:
            raise UnexpectedStatusException
    except requests.RequestException:
        pass
    return response.json() if response else None


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if 'homeworks' not in response or 'current_date' not in response:
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        raise TypeError
    if len(response.get('homeworks')) == 0:
        logging.debug('в ответе API получен пустой список домашних работ')
    return True


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if 'homework_name' not in homework.keys():
        raise NoKeyException
    if homework['status'] not in HOMEWORK_VERDICTS.keys():
        raise UnknownStatusException
    homework_name = homework['homework_name']
    status = homework['status']
    verdict = HOMEWORK_VERDICTS[f'{status}']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('отсутствует токен')
        return

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = {'from_date': 0}
    last_status = None

    while True:
        try:
            response = get_api_answer(timestamp)
            if not check_response(response):
                break
            last_homework = response.get('homeworks')[-1]
            cur_status = last_homework['status']
            if cur_status != last_status:
                verdict = parse_status(last_homework)
                send_message(bot, verdict)
                last_status = cur_status
            bot.polling()
        except apihelper.ApiException:
            logger.error('Произошла ошибка при отправке сообщения в Telegram')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            try:
                bot.send_message(TELEGRAM_CHAT_ID, message)
            except apihelper.ApiException:
                logger.error('Произошла ошибка при отправке сообщения')
            finally:
                time.sleep(RETRY_PERIOD)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
