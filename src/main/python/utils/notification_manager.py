import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)

class NotificationManager:
    """
    負責發送各種通知，例如通過 Telegram。
    """
    def __init__(self, telegram_bot_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

    def send_telegram_message(self, message: str) -> bool:
        """
        通過 Telegram 發送消息。
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            log.warning("Telegram bot token or chat ID not configured. Skipping Telegram notification.")
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML" # 可以使用 HTML 格式
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            log.info("Telegram message sent successfully.")
            return True
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send Telegram message: {e}")
            return False

    def send_alert(self, message: str, level: str = "ERROR"):
        """
        發送通用警報。
        """
        full_message = f"<b>[{level.upper()}]</b>: {message}"
        log.log(getattr(logging, level.upper()), f"Sending alert: {message}")
        self.send_telegram_message(full_message)

