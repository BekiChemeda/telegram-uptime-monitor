import httpx
from app.config import BREVO_API_KEY, BREVO_SENDER_EMAIL
import logging

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, html_content: str):
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        logger.warning("Brevo credentials not found. Skipping email.")
        return False
        
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {"email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201, 202):
                logger.info("Email sent to configured recipient")
                return True
            else:
                logger.error("Failed to send email via Brevo: status=%s", response.status_code)
                return False
        except Exception as e:
            logger.error("Exception sending email: %s", e)
            return False
