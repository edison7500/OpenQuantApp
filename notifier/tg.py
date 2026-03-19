import logging

import requests


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def notify(self, message: str, silent: bool = False) -> bool:
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
            "disable_notification": silent,
        }
        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Telegram Notification Failed: {e}")
            return False
