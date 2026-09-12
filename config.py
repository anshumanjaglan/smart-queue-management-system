import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-queue-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'smart_queue.db')
    MODEL_PATH = os.path.join(BASE_DIR, 'models', 'wait_time_model.pkl')
    
    # Twilio SMS & Voice Call Settings (Optional - fallback to built-in simulation if missing)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
    
    # Enable simulation mode if Twilio credentials are not set
    SIMULATION_MODE = not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)
