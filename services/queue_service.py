from datetime import datetime
from database.db import get_db_connection
from services.ml_service import MLWaitTimeService
from services.notification_service import NotificationService

class QueueService:
    @staticmethod
    def get_all_outlets():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM outlets ORDER BY id ASC")
        outlets = [dict(row) for row in cur.fetchall()]
        conn.close()
        return outlets

    @staticmethod
    def get_outlet_by_id(outlet_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM outlets WHERE id = ?", (outlet_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_token(outlet_id, customer_name, customer_phone, notification_pref='both', notes=''):
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch outlet details
        cur.execute("SELECT * FROM outlets WHERE id = ?", (outlet_id,))
        outlet = cur.fetchone()
        if not outlet:
            conn.close()
            raise ValueError("Invalid outlet ID.")

        # Determine next token sequence for today
        cur.execute("""
            SELECT COUNT(*) as token_seq 
            FROM tokens 
            WHERE outlet_id = ? AND date(joined_at) = date('now')
        """, (outlet_id,))
        seq = cur.fetchone()['token_seq'] + 1
        token_number = f"{outlet['code']}-{seq:03d}"

        # Count how many people are currently waiting for this outlet
        cur.execute("""
            SELECT COUNT(*) as waiting_count
            FROM tokens
            WHERE outlet_id = ? AND status = 'WAITING'
        """, (outlet_id,))
        people_ahead = cur.fetchone()['waiting_count']

        # Predict wait time using ML model
        est_wait = MLWaitTimeService.predict_wait_time(
            outlet_id=outlet_id,
            people_ahead=people_ahead,
            outlet_base_service_mins=outlet['avg_service_time_mins']
        )

        cur.execute("""
            INSERT INTO tokens (
                outlet_id, token_number, customer_name, customer_phone,
                notification_pref, status, notes, queue_position, estimated_wait_mins
            ) VALUES (?, ?, ?, ?, ?, 'WAITING', ?, ?, ?)
        """, (outlet_id, token_number, customer_name, customer_phone,
              notification_pref, notes, people_ahead, est_wait))
        
        token_id = cur.lastrowid
        conn.commit()
        conn.close()

        return {
            "token_id": token_id,
            "token_number": token_number,
            "customer_name": customer_name,
            "outlet_name": outlet['name'],
            "counter_number": outlet['counter_number'],
            "people_ahead": people_ahead,
            "estimated_wait_mins": est_wait,
            "status": "WAITING"
        }

    @staticmethod
    def get_token_status(token_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, o.name as outlet_name, o.code as outlet_code, o.counter_number, o.avg_service_time_mins
            FROM tokens t
            JOIN outlets o ON t.outlet_id = o.id
            WHERE t.id = ?
        """, (token_id,))
        token = cur.fetchone()
        if not token:
            conn.close()
            return None

        token_dict = dict(token)

        if token_dict['status'] == 'WAITING':
            # Calculate dynamic count of people ahead
            cur.execute("""
                SELECT COUNT(*) as people_ahead
                FROM tokens
                WHERE outlet_id = ? AND status = 'WAITING' AND id < ?
            """, (token_dict['outlet_id'], token_id))
            people_ahead = cur.fetchone()['people_ahead']
            token_dict['people_ahead'] = people_ahead

            # Dynamic real-time ML wait time
            token_dict['estimated_wait_mins'] = MLWaitTimeService.predict_wait_time(
                outlet_id=token_dict['outlet_id'],
                people_ahead=people_ahead,
                outlet_base_service_mins=token_dict['avg_service_time_mins']
            )
        elif token_dict['status'] == 'CALLED':
            token_dict['people_ahead'] = 0
            token_dict['estimated_wait_mins'] = 0.0
        else:
            token_dict['people_ahead'] = 0
            token_dict['estimated_wait_mins'] = 0.0

        conn.close()
        return token_dict

    @staticmethod
    def get_outlet_queue(outlet_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tokens
            WHERE outlet_id = ? AND status IN ('WAITING', 'CALLED')
            ORDER BY 
                CASE status WHEN 'CALLED' THEN 0 WHEN 'WAITING' THEN 1 ELSE 2 END,
                id ASC
        """, (outlet_id,))
        queue = [dict(r) for r in cur.fetchall()]
        conn.close()
        return queue

    @staticmethod
    def call_token(token_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tokens WHERE id = ?", (token_id,))
        token = cur.fetchone()
        if not token:
            conn.close()
            return None, "Token not found"

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        joined_at = datetime.strptime(token['joined_at'], '%Y-%m-%d %H:%M:%S')
        called_time = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        wait_duration_secs = int((called_time - joined_at).total_seconds())

        cur.execute("""
            UPDATE tokens 
            SET status = 'CALLED', called_at = ?, wait_duration_secs = ?
            WHERE id = ?
        """, (now, wait_duration_secs, token_id))
        conn.commit()
        conn.close()
        return QueueService.get_token_status(token_id), None

    @staticmethod
    def complete_token(token_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, o.name as outlet_name, o.counter_number 
            FROM tokens t
            JOIN outlets o ON t.outlet_id = o.id
            WHERE t.id = ?
        """, (token_id,))
        token = cur.fetchone()
        if not token:
            conn.close()
            return None, "Token not found"

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        called_at = token['called_at']
        if called_at:
            start_service = datetime.strptime(called_at, '%Y-%m-%d %H:%M:%S')
        else:
            start_service = datetime.strptime(token['joined_at'], '%Y-%m-%d %H:%M:%S')
        
        comp_time = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        service_duration_secs = max(int((comp_time - start_service).total_seconds()), 60)

        cur.execute("""
            UPDATE tokens
            SET status = 'COMPLETED', completed_at = ?, service_duration_secs = ?
            WHERE id = ?
        """, (now, service_duration_secs, token_id))
        conn.commit()
        conn.close()

        # TRIGGER AUTOMATED SMS / CALL NOTIFICATION
        notification_results = NotificationService.send_order_ready_notification(
            token_id=token_id,
            customer_name=token['customer_name'],
            customer_phone=token['customer_phone'],
            token_number=token['token_number'],
            outlet_name=token['outlet_name'],
            counter_number=token['counter_number'],
            pref=token['notification_pref']
        )

        completed_token = QueueService.get_token_status(token_id)
        return {
            "token": completed_token,
            "notifications": notification_results
        }, None

    @staticmethod
    def cancel_token(token_id, reason="Customer cancelled"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE tokens SET status = 'CANCELLED', notes = ? WHERE id = ?", (reason, token_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_public_display_board():
        """
        Returns active 'Now Serving' and 'Ready for Pickup' across all outlets.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id as outlet_id, o.name as outlet_name, o.counter_number, o.code
            FROM outlets o
            WHERE o.is_active = 1
        """)
        outlets = [dict(o) for o in cur.fetchall()]

        board = []
        for out in outlets:
            # Current token in progress / called
            cur.execute("""
                SELECT token_number, customer_name, called_at
                FROM tokens
                WHERE outlet_id = ? AND status = 'CALLED'
                ORDER BY called_at DESC LIMIT 1
            """, (out['outlet_id'],))
            current = cur.fetchone()

            # Recently completed / Ready for pickup (last 5)
            cur.execute("""
                SELECT token_number, customer_name, completed_at
                FROM tokens
                WHERE outlet_id = ? AND status = 'COMPLETED'
                ORDER BY completed_at DESC LIMIT 5
            """, (out['outlet_id'],))
            ready_tokens = [dict(r) for r in cur.fetchall()]

            # Count of waiting
            cur.execute("""
                SELECT COUNT(*) as waiting_count
                FROM tokens
                WHERE outlet_id = ? AND status = 'WAITING'
            """, (out['outlet_id'],))
            waiting_count = cur.fetchone()['waiting_count']

            board.append({
                "outlet_name": out['outlet_name'],
                "counter_number": out['counter_number'],
                "outlet_code": out['code'],
                "current_token": current['token_number'] if current else "--",
                "ready_tokens": ready_tokens,
                "waiting_count": waiting_count
            })

        conn.close()
        return board
