import logging
from config import Config
from database.db import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_order_ready_notification(token_id, customer_name, customer_phone, token_number, outlet_name, counter_number, pref='both'):
        """
        Sends SMS and/or Voice Call update when order/token is marked complete.
        Supports both real Twilio API (if keys set) and interactive simulator.
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
        
        if not Config.SIMULATION_MODE:
            try:
                from twilio.rest import Client
                client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=text,
                    from_=Config.TWILIO_PHONE_NUMBER,
                    to=phone
                )
                status = 'SENT'
                provider_sid = message.sid
                logger.info(f"[SMS Live] Sent to {phone}: SID {provider_sid}")
            except Exception as e:
                logger.warning(f"[SMS Live Error] Falling back to simulation: {e}")
                status = 'SIMULATED'
                provider_sid = f"SIM-SMS-{token_id}"
        else:
            status = 'SIMULATED'
            provider_sid = f"SIM-SMS-{token_id}"
            logger.info(f"[SMS Simulated] To: {phone} | Message: {text}")

        cur.execute("""
            INSERT INTO notifications (token_id, customer_phone, type, status, message_body, provider_sid)
            VALUES (?, ?, 'SMS', ?, ?, ?)
        """, (token_id, phone, status, text, provider_sid))
        conn.commit()
        conn.close()

        return {
            "type": "SMS",
            "phone": phone,
            "status": status,
            "provider_sid": provider_sid,
            "message": text
        }

    @staticmethod
    def _dispatch_call(token_id, phone, voice_text):
        conn = get_db_connection()
        cur = conn.cursor()
        
        if not Config.SIMULATION_MODE:
            try:
                from twilio.rest import Client
                client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                # TwiML for text-to-speech voice call
                twiml_url = f"http://twimlets.com/message?Message%5B0%5D={voice_text.replace(' ', '%20')}"
                call = client.calls.create(
                    twiml=f"<Response><Say voice='alice'>{voice_text}</Say></Response>",
                    to=phone,
                    from_=Config.TWILIO_PHONE_NUMBER
                )
                status = 'SENT'
                provider_sid = call.sid
                logger.info(f"[Voice Call Live] Call placed to {phone}: SID {provider_sid}")
            except Exception as e:
                logger.warning(f"[Voice Call Live Error] Falling back to simulation: {e}")
                status = 'SIMULATED'
                provider_sid = f"SIM-CALL-{token_id}"
        else:
            status = 'SIMULATED'
            provider_sid = f"SIM-CALL-{token_id}"
            logger.info(f"[Voice Call Simulated] To: {phone} | Voice script: {voice_text}")

        cur.execute("""
            INSERT INTO notifications (token_id, customer_phone, type, status, message_body, provider_sid)
            VALUES (?, ?, 'CALL', ?, ?, ?)
        """, (token_id, phone, status, voice_text, provider_sid))
        conn.commit()
        conn.close()

        return {
            "type": "CALL",
            "phone": phone,
            "status": status,
            "provider_sid": provider_sid,
            "message": voice_text
        }

    @staticmethod
    def get_notification_logs(limit=50):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT n.*, t.token_number, t.customer_name, o.name as outlet_name
            FROM notifications n
            JOIN tokens t ON n.token_id = t.id
            JOIN outlets o ON t.outlet_id = o.id
            ORDER BY n.sent_at DESC
            LIMIT ?
        """, (limit,))
        logs = [dict(row) for row in cur.fetchall()]
        conn.close()
        return logs
