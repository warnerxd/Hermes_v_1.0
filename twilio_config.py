from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None

def enviar_whatsapp(numero_destino: str, mensaje: str):
    if not client:
        return {"status": "error", "error": "Twilio no configurado (falta TWILIO_ACCOUNT_SID en .env)"}
    try:
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=mensaje,
            to=f"whatsapp:+{numero_destino}"
        )
        return {"status": "ok", "sid": message.sid}
    except Exception as e:
        return {"status": "error", "error": str(e)}
