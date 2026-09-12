import pandas as pd
import numpy as np
from database.db import get_db_connection

class AnalyticsService:
    @staticmethod
    def get_dashboard_summary():
        conn = get_db_connection()
        cur = conn.cursor()

        # Total tokens completed
        cur.execute("SELECT COUNT(*) as total_completed FROM tokens WHERE status = 'COMPLETED'")
        total_completed = cur.fetchone()['total_completed']

        # Currently waiting
        cur.execute("SELECT COUNT(*) as currently_waiting FROM tokens WHERE status = 'WAITING'")
        currently_waiting = cur.fetchone()['currently_waiting']

        # Currently in-progress
        cur.execute("SELECT COUNT(*) as in_progress FROM tokens WHERE status = 'CALLED'")
        in_progress = cur.fetchone()['in_progress']

        # Active outlets
        cur.execute("SELECT COUNT(*) as total_outlets FROM outlets WHERE is_active = 1")
        total_outlets = cur.fetchone()['total_outlets']

        # Total notifications sent
        cur.execute("SELECT COUNT(*) as total_notifs FROM notifications")
        total_notifs = cur.fetchone()['total_notifs']

        # Average wait time
        cur.execute("""
            SELECT AVG(wait_duration_secs) as avg_wait_secs, AVG(service_duration_secs) as avg_service_secs 
            FROM tokens WHERE status = 'COMPLETED'
        """)
        row = cur.fetchone()
        avg_wait_mins = round((row['avg_wait_secs'] or 0) / 60.0, 1)
        avg_service_mins = round((row['avg_service_secs'] or 0) / 60.0, 1)

        conn.close()

        return {
            "total_completed": total_completed,
            "currently_waiting": currently_waiting,
            "in_progress": in_progress,
            "total_outlets": total_outlets,
            "total_notifications": total_notifs,
            "avg_wait_mins": avg_wait_mins,
            "avg_service_mins": avg_service_mins
        }

    @staticmethod
    def get_peak_hours_analysis():
        conn = get_db_connection()
        query = """
            SELECT 
                t.id,
                t.outlet_id,
                o.name as outlet_name,
                t.joined_at,
                t.wait_duration_secs,
                t.service_duration_secs
            FROM tokens t
            JOIN outlets o ON t.outlet_id = o.id
            WHERE t.status = 'COMPLETED'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        hours = list(range(8, 21)) # 8:00 to 20:00 (8 AM to 8 PM typical campus/office hours)
        hourly_labels = [f"{h:02d}:00" for h in hours]
        hourly_counts = [0] * len(hours)
        hourly_wait_avg = [0.0] * len(hours)

        if not df.empty:
            df['joined_at'] = pd.to_datetime(df['joined_at'])
            df['hour'] = df['joined_at'].dt.hour
            df['wait_mins'] = df['wait_duration_secs'] / 60.0

            grouped = df.groupby('hour').agg(
                customer_count=('id', 'count'),
                avg_wait=('wait_mins', 'mean')
            ).reset_index()

            for _, row in grouped.iterrows():
                h = int(row['hour'])
                if h in hours:
                    idx = hours.index(h)
                    hourly_counts[idx] = int(row['customer_count'])
                    hourly_wait_avg[idx] = round(float(row['avg_wait']), 1)

        # Identify peak rush hour
        peak_idx = int(np.argmax(hourly_counts)) if hourly_counts else 0
        peak_hour_str = hourly_labels[peak_idx] if sum(hourly_counts) > 0 else "N/A"

        return {
            "labels": hourly_labels,
            "customer_volume": hourly_counts,
            "avg_wait_times": hourly_wait_avg,
            "peak_hour": peak_hour_str,
            "peak_count": hourly_counts[peak_idx] if hourly_counts else 0
        }

    @staticmethod
    def get_daily_load_analysis():
        conn = get_db_connection()
        query = """
            SELECT joined_at, wait_duration_secs
            FROM tokens
            WHERE status = 'COMPLETED'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_counts = [0] * 7

        if not df.empty:
            df['joined_at'] = pd.to_datetime(df['joined_at'])
            df['day'] = df['joined_at'].dt.dayofweek
            counts = df['day'].value_counts()
            for day_idx, count in counts.items():
                if 0 <= day_idx < 7:
                    day_counts[int(day_idx)] = int(count)

        return {
            "labels": day_labels,
            "counts": day_counts
        }

    @staticmethod
    def get_outlet_performance():
        conn = get_db_connection()
        query = """
            SELECT 
                o.name as outlet_name,
                o.code as outlet_code,
                COUNT(t.id) as total_tokens,
                AVG(CASE WHEN t.status = 'COMPLETED' THEN t.wait_duration_secs ELSE NULL END) as avg_wait,
                AVG(CASE WHEN t.status = 'COMPLETED' THEN t.service_duration_secs ELSE NULL END) as avg_service
            FROM outlets o
            LEFT JOIN tokens t ON o.id = t.outlet_id
            GROUP BY o.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        outlets_data = []
        for _, row in df.iterrows():
            avg_w = round((row['avg_wait'] or 0) / 60.0, 1)
            avg_s = round((row['avg_service'] or 0) / 60.0, 1)
            outlets_data.append({
                "name": row['outlet_name'],
                "code": row['outlet_code'],
                "total_tokens": int(row['total_tokens'] or 0),
                "avg_wait_mins": avg_w,
                "avg_service_mins": avg_s
            })

        return outlets_data
