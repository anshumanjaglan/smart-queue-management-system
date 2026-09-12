import logging
import urllib.parse
import requests
from config import Config
from database.db import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_order_ready_notification(token_id, customer_name, customer_phone, token_number, outlet_name, counter_number, pref='both'):
        """
        Sends SMS and/or Voice Call update when order/token is marked complete.
        Supports Fast2SMS (India), Twilio (Global SMS/Voice Calls), WhatsApp Direct Link, and Simulation.
        """
        results = []
        sms_text = f"SmartQueue Alert: Hello {customer_name}! Your token #{token_number} at {outlet_name} ({counter_number}) is READY for pickup! Please proceed to the counter."
        voice_twiml_message = f"Hello {customer_name}. This is an automated notification from {outlet_name}. Your token number {token_number} is ready for pickup at {counter_number}. Thank you!"

        # SMS Notification
        if pref in ('sms', 'both'):
            sms_res = NotificationService._dispatch_sms(token_id, customer_phone, sms_text)
            results.append(sms_res)

        # Voice Call Notification
        if pref in ('call', 'both'):
            call_res = NotificationService._dispatch_call(token_id, customer_phone, voice_twiml_message)
            results.append(call_res)

        return results

    @staticmethod
    def _dispatch_sms(token_id, phone, text):
        conn = get_db_connection()
        cur = conn.cursor()
        cfg = Config.get_telecom_config()

        clean_phone = "".join(filter(str.isdigit, phone))
        # If 10 digits (India standard), format appropriately
        if len(clean_phone) == 10:
            clean_phone_10 = clean_phone
            clean_phone_intl = f"+91{clean_phone}"
        elif len(clean_phone) > 10 and clean_phone.startswith('91'):
            clean_phone_10 = clean_phone[-10:]
            clean_phone_intl = f"+{clean_phone}"
        else:
            clean_phone_10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
            clean_phone_intl = f"+{clean_phone}" if not phone.startswith('+') else phone

        status = 'SIMULATED'
        provider_name = 'SIMULATOR'
        provider_sid = f"SIM-SMS-{token_id}"

        # 1. Check Fast2SMS Provider
        if cfg.get('fast2sms_api_key'):
            try:
                url = "https://www.fast2sms.com/dev/bulkV2"
                payload = {
                    "authorization": cfg['fast2sms_api_key'],
                    "route": "q",
                    "message": text,
                    "language": "english",
                    "flash": "0",
                    "numbers": clean_phone_10
                }
                headers = {'cache-control': "no-cache"}
                resp = requests.get(url, params=payload, headers=headers, timeout=10)
                res_json = resp.json()
                if res_json.get('return'):
                    status = 'SENT'
                    provider_name = 'FAST2SMS'
                    provider_sid = str(res_json.get('request_id', f"F2S-{token_id}"))
                    logger.info(f"[Fast2SMS Live] Real SMS sent to {clean_phone_10}: {provider_sid}")
                else:
                    logger.warning(f"[Fast2SMS Warning] Response: {res_json}")
            except Exception as e:
                logger.error(f"[Fast2SMS Error] {e}")

        # 2. Check Twilio Provider (if not sent by Fast2SMS)
        if status != 'SENT' and cfg.get('twilio_account_sid') and cfg.get('twilio_auth_token') and cfg.get('twilio_phone_number'):
            try:
                from twilio.rest import Client
                client = Client(cfg['twilio_account_sid'], cfg['twilio_auth_token'])
                message = client.messages.create(
                    body=text,
                    from_=cfg['twilio_phone_number'],
                    to=clean_phone_intl
                )
                status = 'SENT'
                provider_name = 'TWILIO'
                provider_sid = message.sid
                logger.info(f"[Twilio Live] Real SMS sent to {clean_phone_intl}: SID {provider_sid}")
            except Exception as e:
                logger.warning(f"[Twilio Live Error] {e}")

        # Fallback simulation log if no live credentials or live provider failed
        if status == 'SIMULATED':
            logger.info(f"[SMS Simulated] To: {phone} | Message: {text}")

        cur.execute("""
            INSERT INTO notifications (token_id, customer_phone, type, status, message_body, provider_sid)
            VALUES (?, ?, 'SMS', ?, ?, ?)
        """, (token_id, phone, status, text, f"{provider_name}:{provider_sid}"))
        conn.commit()
        conn.close()

        # Generate direct WhatsApp click-to-chat URL
        whatsapp_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(text)}"

        return {
            "type": "SMS",
            "phone": phone,
            "status": status,
            "provider": provider_name,
            "provider_sid": provider_sid,
            "message": text,
            "whatsapp_url": whatsapp_url
        }

    @staticmethod
    def _dispatch_call(token_id, phone, voice_text):
        conn = get_db_connection()
        cur = conn.cursor()
        cfg = Config.get_telecom_config()

        status = 'SIMULATED'
        provider_name = 'SIMULATOR'
        provider_sid = f"SIM-CALL-{token_id}"

        # Real Twilio Voice Call
        if cfg.get('twilio_account_sid') and cfg.get('twilio_auth_token') and cfg.get('twilio_phone_number'):
            try:
                from twilio.rest import Client
                client = Client(cfg['twilio_account_sid'], cfg['twilio_auth_token'])
                clean_phone = phone if phone.startswith('+') else f"+{phone}"
                call = client.calls.create(
                    twiml=f"<Response><Say voice='alice'>{voice_text}</Say></Response>",
                    to=clean_phone,
                    from_=cfg['twilio_phone_number']
                )
                status = 'SENT'
                provider_name = 'TWILIO_VOICE'
                provider_sid = call.sid
                logger.info(f"[Twilio Voice Live] Call initiated to {clean_phone}: SID {provider_sid}")
            except Exception as e:
                logger.warning(f"[Twilio Voice Error] {e}")

        if status == 'SIMULATED':
            logger.info(f"[Voice Call Simulated] To: {phone} | Voice script: {voice_text}")

        cur.execute("""
            INSERT INTO notifications (token_id, customer_phone, type, status, message_body, provider_sid)
            VALUES (?, ?, 'CALL', ?, ?, ?)
        """, (token_id, phone, status, voice_text, f"{provider_name}:{provider_sid}"))
        conn.commit()
        conn.close()

        return {
            "type": "CALL",
            "phone": phone,
            "status": status,
            "provider": provider_name,
            "provider_sid": provider_sid,
            "message": voice_text
        }

    @staticmethod
    def test_send_sms(phone, message):
        """Sends a test SMS to verify provider credentials."""
        return NotificationService._dispatch_sms(token_id=0, phone=phone, text=message)

    @staticmethod
    def get_notification_logs(limit=50):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT n.*, 
                   COALESCE(t.token_number, 'TEST-001') as token_number, 
                   COALESCE(t.customer_name, 'Test Customer') as customer_name, 
                   COALESCE(o.name, 'Admin Terminal') as outlet_name
            FROM notifications n
            LEFT JOIN tokens t ON n.token_id = t.id
            LEFT JOIN outlets o ON t.outlet_id = o.id
            ORDER BY n.sent_at DESC
            LIMIT ?
        """, (limit,))
        logs = [dict(row) for row in cur.fetchall()]
        conn.close()
        return logs
