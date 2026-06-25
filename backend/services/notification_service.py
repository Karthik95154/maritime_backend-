import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def send_email(to: str, subject: str, body: str):
        logger.info(f"[MOCK NOTIFICATION - EMAIL] To: {to} | Subject: {subject} | Body: {body}")
        return True

    @staticmethod
    async def send_sms(to: str, message: str):
        logger.info(f"[MOCK NOTIFICATION - SMS] To: {to} | Message: {message}")
        return True

    @staticmethod
    async def send_whatsapp(to: str, message: str):
        logger.info(f"[MOCK NOTIFICATION - WHATSAPP] To: {to} | Message: {message}")
        return True

    @staticmethod
    async def send_teams_alert(webhook_url: str, title: str, text: str):
        logger.info(f"[MOCK NOTIFICATION - TEAMS] Webhook: {webhook_url} | Title: {title} | Text: {text}")
        return True
