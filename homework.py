import logging
import sys
import time
from http import HTTPStatus

import requests
from telebot import TeleBot

from constants import (ENDPOINT, HEADERS, HOMEWORK_VERDICTS,
                       PRACTICUM_TOKEN, HOMEWORKS_KEY,
                       RETRY_PERIOD, TELEGRAM_CHAT_ID,
                       TELEGRAM_TOKEN
                       )
from exeptions import (EndpointNotAvailable, HomeworkNameNotFound,
                       HomeworkNotFound,
                       UnexpectedHomeworkStatus
                       )


logging.basicConfig(level=logging.INFO)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if any(token is None for token in tokens):
        logging.critical('Отсутствует обязательная переменная окружения.')
        sys.exit('Программа принудительно остановлена.')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: "{message}"')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ."""
    payload = {'from_date': timestamp}
    try:
        api_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if api_response.status_code != HTTPStatus.OK:
            raise EndpointNotAvailable(
                f'Ошибка при запросе к API: {api_response.status_code} '
                f'{api_response.reason}. '
                f'Проверьте корректность ENDPOINT ({ENDPOINT}) '
                'и параметры запроса.'
            )
        return api_response.json()
    except requests.exceptions.RequestException as error:
        raise EndpointNotAvailable(
            f'Ошибка при запросе к API: {error}'
        ) from error


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ожидался словарь в ответе от {ENDPOINT}, '
            f'но получен объект типа {type(response).__name__}.'
        )
    homeworks = response.get(HOMEWORKS_KEY)
    if homeworks is None:
        raise HomeworkNotFound(
            f'Не найден ключ {HOMEWORKS_KEY} в ответе от ({ENDPOINT})!'
        )
    if not isinstance(homeworks, list):
        raise TypeError('Ожидался список под ключом "homeworks".')
    if not homeworks:  # Если список пустой
        logging.debug('Нет новых статусов.')
        return


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        logging.error('Отсутствует название домашней работы.')
        raise HomeworkNameNotFound('Название домашней работы не найдено.')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        logging.error(f'Неожиданный статус домашней работы: {status}')
        raise UnexpectedHomeworkStatus('Неожиданный статус работы.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get(HOMEWORKS_KEY)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logging.debug('Нет новых статусов.')
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
