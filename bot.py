import json
import os
import secrets
import time
from urllib.request import Request, urlopen

codes = {}


def telegram(method, **data):
    token = os.environ['BOT_TOKEN']
    request = Request(
        f'https://api.telegram.org/bot{token}/{method}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=40) as response:
        return json.load(response)['result']


def reply(chat_id, text):
    telegram('sendMessage', chat_id=chat_id, text=text)


def handle(message):
    chat = message['chat']
    if chat['type'] != 'private' or 'text' not in message:
        return

    chat_id = chat['id']
    text = message['text'].strip()
    now = time.monotonic()

    if text == '/start':
        reply(chat_id, 'Напиши /code, чтобы получить одноразовый код.')
        return

    if text == '/code':
        code = f'{secrets.randbelow(1_000_000):06d}'
        codes[chat_id] = (code, now + 300, 3)
        reply(chat_id, f'Твой код: {code}\nОтправь его сюда в течение 5 минут.')
        return

    entry = codes.get(chat_id)
    if entry is None or now >= entry[1]:
        codes.pop(chat_id, None)
        reply(chat_id, 'Нет действующего кода. Напиши /code.')
        return

    if len(text) != 6 or not text.isascii() or not text.isdigit():
        reply(chat_id, 'Отправь ровно шесть цифр.')
        return

    code, expires_at, attempts = entry
    if secrets.compare_digest(text, code):
        del codes[chat_id]
        reply(chat_id, '✅ Код подтверждён!')
    elif attempts == 1:
        del codes[chat_id]
        reply(chat_id, 'Попытки закончились. Запроси новый код через /code.')
    else:
        codes[chat_id] = (code, expires_at, attempts - 1)
        reply(chat_id, f'Неверный код. Осталось попыток: {attempts - 1}.')


def main():
    if not os.environ.get('BOT_TOKEN'):
        raise SystemExit('Задай переменную BOT_TOKEN перед запуском.')

    offset = 0
    print('Бот запущен. Для остановки нажми Ctrl+C.')
    while True:
        try:
            updates = telegram(
                'getUpdates', offset=offset, timeout=25, allowed_updates=['message']
            )
        except OSError as error:
            print(f'Ошибка связи с Telegram ({type(error).__name__}). Повтор через 3 секунды.')
            time.sleep(3)
            continue

        for update in updates:
            offset = update['update_id'] + 1
            if 'message' in update:
                try:
                    handle(update['message'])
                except OSError as error:
                    print(f'Не удалось отправить ответ ({type(error).__name__}).')


if __name__ == '__main__':
    main()
