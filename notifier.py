import smtplib
import urllib.request
import urllib.parse
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from rich.console import Console

console = Console()


# ─────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────

def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    """Telegram Bot API üzerinden mesaj gönderir."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    ).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                console.print("[green]✓ Telegram bildirimi gönderildi.[/green]")
                return True
    except urllib.error.HTTPError as e:
        console.print(f"[red]Telegram HTTP hatası: {e.code} – {e.read().decode()}[/red]")
    except Exception as e:
        console.print(f"[red]Telegram hatası: {e}[/red]")
    return False


# ─────────────────────────────────────────────
# E-posta (Gmail / SMTP)
# ─────────────────────────────────────────────

def send_email(
    smtp_host: str,
    smtp_port: int,
    sender: str,
    password: str,
    recipient: str,
    subject: str,
    body: str,
    use_tls: bool = True,
) -> bool:
    """SMTP üzerinden e-posta gönderir (varsayılan: Gmail TLS)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)

        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        console.print("[green]✓ E-posta bildirimi gönderildi.[/green]")
        return True
    except smtplib.SMTPAuthenticationError:
        console.print(
            "[red]E-posta kimlik doğrulama hatası. "
            "Gmail kullanıyorsanız 'Uygulama Şifresi' oluşturun.[/red]"
        )
    except Exception as e:
        console.print(f"[red]E-posta hatası: {e}[/red]")
    return False


# ─────────────────────────────────────────────
# WhatsApp (Callmebot – ücretsiz)
# ─────────────────────────────────────────────

def send_whatsapp_callmebot(phone: str, api_key: str, message: str) -> bool:
    """
    Callmebot API ile WhatsApp mesajı gönderir (ücretsiz, kayıt gerekli).

    Kayıt:  https://www.callmebot.com/blog/free-api-whatsapp-messages/
    1. +34 644 82 99 38 numarasına WhatsApp'tan:
       "I allow callmebot to send me messages" yazın
    2. Size dönen API key'i .env dosyasına girin.

    phone: Başında + olan uluslararası format, örn. +905551234567
    """
    encoded_msg = urllib.parse.quote(message)
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={phone}&text={encoded_msg}&apikey={api_key}"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            if "Message queued" in body or resp.status == 200:
                console.print("[green]✓ WhatsApp bildirimi gönderildi.[/green]")
                return True
            console.print(f"[yellow]WhatsApp yanıtı: {body[:200]}[/yellow]")
    except Exception as e:
        console.print(f"[red]WhatsApp hatası: {e}[/red]")
    return False


# ─────────────────────────────────────────────
# Dispatcher – tüm kanalları tek çağrıda tetikler
# ─────────────────────────────────────────────

def notify_all(message: str, config: dict) -> None:
    """
    Konfigürasyona göre tüm aktif bildirim kanallarını tetikler.

    config örneği:
    {
        "telegram": {"token": "...", "chat_id": "..."},
        "email": {
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "sender": "...", "password": "...", "recipient": "..."
        },
        "whatsapp": {"phone": "+90...", "api_key": "..."},
    }
    """
    tg = config.get("telegram", {})
    if tg.get("token") and tg.get("chat_id"):
        send_telegram(tg["token"], tg["chat_id"], message)

    em = config.get("email", {})
    if em.get("sender") and em.get("password") and em.get("recipient"):
        send_email(
            smtp_host=em.get("smtp_host", "smtp.gmail.com"),
            smtp_port=int(em.get("smtp_port", 587)),
            sender=em["sender"],
            password=em["password"],
            recipient=em["recipient"],
            subject="🚂 TCDD Bilet Bulundu!",
            body=message,
        )

    wa = config.get("whatsapp", {})
    if wa.get("phone") and wa.get("api_key"):
        send_whatsapp_callmebot(wa["phone"], wa["api_key"], message)
