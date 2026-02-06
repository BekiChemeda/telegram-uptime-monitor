import asyncio
from app.services.email_service import send_email
from app.config import BREVO_SENDER_EMAIL

async def test_email():
    print(f"Sending from: {BREVO_SENDER_EMAIL}")
    success = await send_email(
        to_email="bekichemeda@gmail.com", # Send to specified email
        subject="Test Email from Bot",
        html_content="<h1>It Works!</h1><p>This is a test email sent to verified if email service is working.</p>"
    )
    print(f"Email success: {success}")

if __name__ == "__main__":
    asyncio.run(test_email())
