import os
import sys
import random
from datetime import datetime, timedelta

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db_connection, init_db
from services.ml_service import MLWaitTimeService

FIRST_NAMES = ["Aarav", "Priya", "Rahul", "Ananya", "Rohan", "Sneha", "Aditya", "Neha", "Vikram", "Pooja", "Arjun", "Kavya", "Varun", "Tanvi", "Karan", "Ishita", "Siddharth", "Meera", "Kabir", "Riya"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Singh", "Gupta", "Kumar", "Iyer", "Reddy", "Mehta", "Joshi", "Das", "Choudhury", "Nair", "Bose", "Saxena"]

def generate_sample_phone():
    return f"+91{random.randint(7000000000, 9999999999)}"

def seed_historical_queue_data(num_records=550):
    print("Initializing Database...")
    init_db()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, code, name, avg_service_time_mins FROM outlets")
    outlets = [dict(r) for r in cur.fetchall()]
    if not outlets:
        print("No outlets found. Exiting.")
        return

    # Check if records already exist
    cur.execute("SELECT COUNT(*) as count FROM tokens WHERE status = 'COMPLETED'")
    count = cur.fetchone()['count']
    if count >= 100:
        print(f"Database already contains {count} completed records. Retraining model...")
        res = MLWaitTimeService.train_model()
        print(f"ML Training result: {res}")
        conn.close()
        return

    print(f"Generating {num_records} realistic historical records over the past 30 days...")
    now = datetime.now()
    records = []

    for i in range(num_records):
        # Pick random day in last 30 days
        days_ago = random.randint(1, 30)
        
        # Bias hours towards peak times:
        # Peak: 12-14 (lunch) and 17-19 (evening), medium: 10-12 and 14-17, low: 8-10 and 19-20
        hour_weights = [
            1, 1, 1, 1, 1, 1, 1, 1, # 0-7
            2, 3, 5, 7, 18, 20, 10, 8, 9, 16, 17, 6, 2, 1, 1, 1 # 8-23
        ]
        hour = random.choices(range(24), weights=hour_weights, k=1)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        joined_time = now - timedelta(days=days_ago)
        joined_time = joined_time.replace(hour=hour, minute=minute, second=second)

        outlet = random.choice(outlets)
        outlet_id = outlet['id']
        base_service_mins = outlet['avg_service_time_mins']

        # More people ahead during peak hours
        if hour in [12, 13, 17, 18]:
            queue_pos = random.randint(3, 14)
        elif hour in [10, 11, 14, 15, 16]:
            queue_pos = random.randint(1, 6)
        else:
            queue_pos = random.randint(0, 3)

        # Service duration in seconds with some variation
        service_duration_secs = int(max(60, random.gauss(base_service_mins * 60, 45)))

        # Wait duration is correlated with queue position and rush factor
        rush_mult = 1.3 if hour in [12, 13, 17, 18] else 1.0
        calculated_wait = int(max(60, (queue_pos * base_service_mins * 60 * rush_mult) + random.gauss(30, 40)))

        called_time = joined_time + timedelta(seconds=calculated_wait)
        completed_time = called_time + timedelta(seconds=service_duration_secs)

        c_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        c_phone = generate_sample_phone()
        token_num = f"{outlet['code']}-{random.randint(101, 999)}"

        records.append((
            outlet_id,
            token_num,
            c_name,
            c_phone,
            random.choice(['sms', 'both', 'call']),
            'COMPLETED',
            'Historical seeded data',
            queue_pos,
            joined_time.strftime('%Y-%m-%d %H:%M:%S'),
            called_time.strftime('%Y-%m-%d %H:%M:%S'),
            completed_time.strftime('%Y-%m-%d %H:%M:%S'),
            calculated_wait,
            service_duration_secs,
            round(calculated_wait / 60.0, 1)
        ))

    cur.executemany("""
        INSERT INTO tokens (
            outlet_id, token_number, customer_name, customer_phone,
            notification_pref, status, notes, queue_position,
            joined_at, called_at, completed_at, wait_duration_secs,
            service_duration_secs, estimated_wait_mins
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(records)} records.")

    print("Training initial Scikit-learn ML Wait-Time Prediction Model...")
    res = MLWaitTimeService.train_model()
    print(f"ML Model Training Finished: {res}")

if __name__ == '__main__':
    seed_historical_queue_data()
