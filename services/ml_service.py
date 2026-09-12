import os
import sqlite3
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from config import Config
from database.db import get_db_connection

class MLWaitTimeService:
    _model = None
    _metadata = None

    @classmethod
    def load_model(cls):
        if cls._model is None and os.path.exists(Config.MODEL_PATH):
            try:
                data = joblib.load(Config.MODEL_PATH)
                cls._model = data.get('model')
                cls._metadata = data.get('metadata', {})
            except Exception as e:
                print(f"Warning: Could not load ML model: {e}")
        return cls._model

    @classmethod
    def predict_wait_time(cls, outlet_id, people_ahead, outlet_base_service_mins=3.0):
        """
        Predicts wait time in minutes for a customer with `people_ahead` ahead in queue.
        Uses Scikit-learn trained model if available; otherwise uses analytical queueing formula.
        """
        if people_ahead <= 0:
            return 0.0

        now = datetime.now()
        hour_of_day = now.hour
        day_of_week = now.weekday()

        # Fetch recent average service time for this outlet from DB
        recent_service_time = cls._get_recent_avg_service_time(outlet_id, fallback=outlet_base_service_mins)

        model = cls.load_model()
        if model is not None:
            try:
                # Feature vector: [people_ahead, hour_of_day, day_of_week, outlet_id, recent_service_time]
                features = np.array([[
                    float(people_ahead),
                    float(hour_of_day),
                    float(day_of_week),
                    float(outlet_id),
                    float(recent_service_time)
                ]])
                pred = model.predict(features)[0]
                # Bound minimum predicted wait time
                return round(max(float(pred), float(people_ahead * 1.0)), 1)
            except Exception as e:
                print(f"ML inference error: {e}, using queuing formula fallback.")

        # Analytical Queueing Fallback:
        # Wait time = people_ahead * avg_service_time * rush_factor
        rush_factor = 1.35 if hour_of_day in [12, 13, 14, 18, 19, 20] else 1.0
        calculated = people_ahead * recent_service_time * rush_factor
        return round(float(calculated), 1)

    @classmethod
    def _get_recent_avg_service_time(cls, outlet_id, fallback=3.0):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT service_duration_secs
            FROM tokens
            WHERE outlet_id = ? AND status = 'COMPLETED' AND service_duration_secs > 0
            ORDER BY completed_at DESC
            LIMIT 10
        """, (outlet_id,))
        rows = cur.fetchall()
        conn.close()

        if rows:
            durations = [r['service_duration_secs'] / 60.0 for r in rows]
            return float(np.mean(durations))
        return float(fallback)

    @classmethod
    def train_model(cls):
        """
        Trains a Scikit-learn RandomForestRegressor using historical token data.
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score

        conn = get_db_connection()
        query = """
            SELECT 
                outlet_id,
                queue_position as people_ahead,
                wait_duration_secs,
                service_duration_secs,
                joined_at
            FROM tokens
            WHERE status = 'COMPLETED' AND wait_duration_secs > 0
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if len(df) < 20:
            return {
                "success": False,
                "message": f"Insufficient data for ML training ({len(df)} records found, minimum 20 required)."
            }

        # Feature engineering
        df['joined_at'] = pd.to_datetime(df['joined_at'])
        df['hour_of_day'] = df['joined_at'].dt.hour
        df['day_of_week'] = df['joined_at'].dt.dayofweek
        df['wait_duration_mins'] = df['wait_duration_secs'] / 60.0
        df['service_duration_mins'] = df['service_duration_secs'] / 60.0

        # Features & Target
        X = df[['people_ahead', 'hour_of_day', 'day_of_week', 'outlet_id', 'service_duration_mins']]
        y = df['wait_duration_mins']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))

        os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
        joblib.dump({
            'model': model,
            'metadata': {
                'trained_at': datetime.now().isoformat(),
                'sample_size': len(df),
                'mae_mins': round(mae, 2),
                'r2_score': round(r2, 3),
                'feature_names': list(X.columns)
            }
        }, Config.MODEL_PATH)

        cls._model = model
        cls._metadata = {
            'trained_at': datetime.now().isoformat(),
            'sample_size': len(df),
            'mae_mins': round(mae, 2),
            'r2_score': round(r2, 3)
        }

        return {
            "success": True,
            "sample_size": len(df),
            "mae_mins": round(mae, 2),
            "r2_score": round(r2, 3),
            "message": "Model trained and saved successfully."
        }

    @classmethod
    def get_model_info(cls):
        cls.load_model()
        return cls._metadata or {
            "status": "Analytical Fallback",
            "message": "Model not yet trained with sufficient live data."
        }
