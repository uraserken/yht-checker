import os
from dotenv import load_dotenv

load_dotenv()


def load_config() -> dict:
    """
    .env dosyasından konfigürasyonu yükler.
    Eksik zorunlu alanlar için ValueError fırlatır.
    """
    departure = os.getenv("DEPARTURE_STATION", "").strip()
    arrival = os.getenv("ARRIVAL_STATION", "").strip()
    travel_date = os.getenv("TRAVEL_DATE", "").strip()

    if not departure:
        raise ValueError("DEPARTURE_STATION tanımlanmamış (.env)")
    if not arrival:
        raise ValueError("ARRIVAL_STATION tanımlanmamış (.env)")
    if not travel_date:
        raise ValueError("TRAVEL_DATE tanımlanmamış (.env)")

    hour_start_raw = os.getenv("HOUR_START", "").strip()
    hour_end_raw = os.getenv("HOUR_END", "").strip()

    hour_start = int(hour_start_raw) if hour_start_raw else None
    hour_end = int(hour_end_raw) if hour_end_raw else None

    interval_minutes = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
    headless = os.getenv("HEADLESS", "true").strip().lower() != "false"

    # Bildirim kanalları
    telegram_cfg = {}
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if tg_token and tg_chat:
        telegram_cfg = {"token": tg_token, "chat_id": tg_chat}

    email_cfg = {}
    email_sender = os.getenv("EMAIL_SENDER", "").strip()
    email_pass = os.getenv("EMAIL_PASSWORD", "").strip()
    email_recipient = os.getenv("EMAIL_RECIPIENT", "").strip()
    if email_sender and email_pass and email_recipient:
        email_cfg = {
            "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender": email_sender,
            "password": email_pass,
            "recipient": email_recipient,
        }

    whatsapp_cfg = {}
    wa_phone = os.getenv("WHATSAPP_PHONE", "").strip()
    wa_key = os.getenv("WHATSAPP_API_KEY", "").strip()
    if wa_phone and wa_key:
        whatsapp_cfg = {"phone": wa_phone, "api_key": wa_key}

    return {
        "departure": departure,
        "arrival": arrival,
        "travel_date": travel_date,
        "hour_start": hour_start,
        "hour_end": hour_end,
        "interval_minutes": interval_minutes,
        "headless": headless,
        "notify": {
            "telegram": telegram_cfg,
            "email": email_cfg,
            "whatsapp": whatsapp_cfg,
        },
    }
