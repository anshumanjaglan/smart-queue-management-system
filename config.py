import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-queue-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'smart_queue.db')
    MODEL_PATH = os.path.join(BASE_DIR, 'models', 'wait_time_model.pkl')

    @classmethod
    def get_setting(cls, key, default=''):
        try:
            conn = sqlite3.connect(cls.DATABASE_PATH)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception:
            pass
        return os.environ.get(key.upper(), default)

    @classmethod
    def set_setting(cls, key, value):
        try:
            conn = sqlite3.connect(cls.DATABASE_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (key, value))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving setting {key}: {e}")
            return False

    @classmethod
    def get_telecom_config(cls):
        return {
            "fast2sms_api_key": cls.get_setting("fast2sms_api_key", ""),
            "twilio_account_sid": cls.get_setting("twilio_account_sid", os.environ.get("TWILIO_ACCOUNT_SID", "")),
            "twilio_auth_token": cls.get_setting("twilio_auth_token", os.environ.get("TWILIO_AUTH_TOKEN", "")),
            "twilio_phone_number": cls.get_setting("twilio_phone_number", os.environ.get("TWILIO_PHONE_NUMBER", "")),
            "active_provider": cls.get_setting("active_provider", "auto") # 'auto', 'fast2sms', 'twilio', 'simulation'
        }
