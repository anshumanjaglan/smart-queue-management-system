import sys
import os
import unittest
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database.db import init_db, get_db_connection
from services.ml_service import MLWaitTimeService

class SmartQueueTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        init_db()

    def test_01_get_outlets(self):
        res = self.client.get('/api/outlets')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['outlets']), 0)
        print(f"Verified {len(data['outlets'])} active outlets.")

    def test_02_create_token_and_wait_prediction(self):
        # Create token for Canteen (outlet 1)
        payload = {
            "outlet_id": 1,
            "customer_name": "Test Customer",
            "customer_phone": "+919876543210",
            "notification_pref": "both",
            "notes": "2x Sandwich & Coffee"
        }
        res = self.client.post('/api/token/create', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        token = data['token']
        self.assertIn('token_id', token)
        self.assertIn('token_number', token)
        self.assertEqual(token['status'], 'WAITING')
        print(f"Created token: {token['token_number']}, Estimated Wait: {token['estimated_wait_mins']} mins")
        self.__class__.test_token_id = token['token_id']

    def test_03_check_token_status(self):
        res = self.client.get(f'/api/token/status/{self.test_token_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        token = data['token']
        self.assertEqual(token['id'], self.test_token_id)
        self.assertEqual(token['status'], 'WAITING')
        print(f"Token status checked: People ahead = {token['people_ahead']}, Est Wait = {token['estimated_wait_mins']} mins")

    def test_04_staff_queue_and_call_token(self):
        # Get staff queue for outlet 1
        res = self.client.get('/api/staff/queue?outlet_id=1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # Staff calls specific token
        call_res = self.client.post('/api/staff/call', data=json.dumps({'token_id': self.test_token_id}), content_type='application/json')
        self.assertEqual(call_res.status_code, 200)
        call_data = call_res.get_json()
        self.assertTrue(call_data['success'])
        self.assertEqual(call_data['token']['status'], 'CALLED')
        print(f"Staff called token: {call_data['token']['token_number']}")

    def test_05_staff_complete_and_trigger_sms_call(self):
        # Staff marks order complete -> triggers automated SMS and Voice Call
        complete_res = self.client.post('/api/staff/complete', data=json.dumps({'token_id': self.test_token_id}), content_type='application/json')
        self.assertEqual(complete_res.status_code, 200)
        complete_data = complete_res.get_json()
        self.assertTrue(complete_data['success'])
        self.assertEqual(complete_data['token']['status'], 'COMPLETED')

        # Check notifications generated
        notifs = complete_data['notifications']
        self.assertGreater(len(notifs), 0)
        types = [n['type'] for n in notifs]
        self.assertIn('SMS', types)
        self.assertIn('CALL', types)
        print(f"Order completed! Automated notification triggered: {notifs}")

    def test_06_display_board(self):
        res = self.client.get('/api/display/board')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['board']), 0)
        print("Verified public display board endpoint.")

    def test_07_analytics_peak_hours(self):
        res = self.client.get('/api/analytics/peak-hours')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('labels', data)
        self.assertIn('customer_volume', data)
        self.assertIn('peak_hour', data)
        print(f"Analytics peak rush hour identified: {data['peak_hour']} with max customer volume.")

    def test_08_ml_info_and_training(self):
        res = self.client.get('/api/ml/info')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        print(f"ML Model info: R2={data.get('r2_score')}, MAE={data.get('mae_mins')} mins, Samples={data.get('sample_size')}")

if __name__ == '__main__':
    unittest.main()
