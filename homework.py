import logging
import sys
import time
from http import HTTPStatus

import requests
from telebot import TeleBot
from telebot.apihelper import ApiException

from constants import (ENDPOINT, HEADERS, HOMEWORK_VERDICTS,
                       PRACTICUM_TOKEN, HOMEWORKS_KEY,
                       RETRY_PERIOD, TELEGRAM_CHAT_ID,
                       TELEGRAM_TOKEN
                       )
from exeptions import (EndpointNotAvailable, HomeworkNameNotFound,
                       HomeworkNotFound, StatusNotFound,
                       UnexpectedHomeworkStatus
                       )


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    missing_tokens = []

    for name, token in tokens.items():
        if token is None:
            missing_tokens.append(name)

    if missing_tokens:
        logging.critical(
            f"Отсутствуют обязательные переменные окружения: "
            f"{', '.join(missing_tokens)}"
        )
        raise TokenError(missing_tokens)
        logging.info("Все токены в порядке!")


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    logging.debug(f'Начало отправки сообщения: "{message}"')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: "{message}"')
    except (ApiException, requests.exceptions.RequestException) as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ."""
    payload = {'from_date': timestamp}
    logging.info(
        "Начинаем запрос к API: %s, Заголовки: %s, Параметры: %s",
        ENDPOINT, HEADERS, payload
    )
    try:
        api_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.exceptions.RequestException as error:
        raise EndpointNotAvailable(
            f'Ошибка при запросе к API: {error}'
        ) from error

    if api_response.status_code != HTTPStatus.OK:
        raise EndpointNotAvailable(
            f'Ошибка при запросе к API: {api_response.status_code} '
            f'{api_response.reason}. '
            f'Проверьте корректность ENDPOINT ({ENDPOINT}) '
            'и параметры запроса.'
        )

    return api_response.json()


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
        raise TypeError(
            f'Ожидался список под ключом "{HOMEWORKS_KEY}", '
            f'но получен объект типа {type(homeworks).__name__}.'
        )

    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        raise HomeworkNameNotFound('Название домашней работы не найдено.')
    if status is None:
        raise StatusNotFound('Статус домашней работы не найден.')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise UnexpectedHomeworkStatus('Неожиданный статус работы.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get(HOMEWORKS_KEY)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if send_message(bot, message):
                    timestamp = response.get('current_date', timestamp)
                    last_message = None
            else:
                logging.debug('Нет новых статусов.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
