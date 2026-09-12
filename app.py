import os
from flask import Flask, render_template, request, jsonify
from config import Config
from database.db import init_db
from services.queue_service import QueueService
from services.analytics_service import AnalyticsService
from services.ml_service import MLWaitTimeService
from services.notification_service import NotificationService

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database on app start
with app.app_context():
    init_db()
    # Pre-load ML model if available
    MLWaitTimeService.load_model()

# ----------------- PAGE ROUTES ----------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/customer')
def customer_portal():
    outlets = QueueService.get_all_outlets()
    return render_template('customer.html', outlets=outlets)

@app.route('/staff')
def staff_portal():
    outlets = QueueService.get_all_outlets()
    return render_template('staff.html', outlets=outlets)

@app.route('/display')
def display_board():
    return render_template('display.html')

@app.route('/admin')
def admin_portal():
    return render_template('admin.html')


# ----------------- API ROUTES: TOKEN & QUEUE ----------------- #

@app.route('/api/outlets', methods=['GET'])
def api_get_outlets():
    outlets = QueueService.get_all_outlets()
    return jsonify({"success": True, "outlets": outlets})

@app.route('/api/token/create', methods=['POST'])
def api_create_token():
    data = request.get_json() or {}
    outlet_id = data.get('outlet_id')
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    notification_pref = data.get('notification_pref', 'both')
    notes = data.get('notes', '').strip()

    if not outlet_id or not customer_name or not customer_phone:
        return jsonify({"success": False, "message": "Outlet, Name, and Phone are required."}), 400

    try:
        token = QueueService.create_token(
            outlet_id=int(outlet_id),
            customer_name=customer_name,
            customer_phone=customer_phone,
            notification_pref=notification_pref,
            notes=notes
        )
        return jsonify({"success": True, "token": token}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/token/status/<int:token_id>', methods=['GET'])
def api_token_status(token_id):
    token = QueueService.get_token_status(token_id)
    if not token:
        return jsonify({"success": False, "message": "Token not found"}), 404
    return jsonify({"success": True, "token": token})

@app.route('/api/token/cancel/<int:token_id>', methods=['POST'])
def api_cancel_token(token_id):
    success = QueueService.cancel_token(token_id)
    return jsonify({"success": success})


# ----------------- API ROUTES: STAFF COUNTER ----------------- #

@app.route('/api/staff/queue', methods=['GET'])
def api_staff_queue():
    outlet_id = request.args.get('outlet_id')
    if not outlet_id:
        return jsonify({"success": False, "message": "outlet_id parameter required"}), 400

    outlet = QueueService.get_outlet_by_id(int(outlet_id))
    queue = QueueService.get_outlet_queue(int(outlet_id))
    return jsonify({
        "success": True,
        "outlet": outlet,
        "queue": queue
    })

@app.route('/api/staff/call-next', methods=['POST'])
def api_call_next():
    data = request.get_json() or {}
    outlet_id = data.get('outlet_id')
    if not outlet_id:
        return jsonify({"success": False, "message": "outlet_id is required"}), 400

    queue = QueueService.get_outlet_queue(int(outlet_id))
    waiting_tokens = [t for t in queue if t['status'] == 'WAITING']
    if not waiting_tokens:
        return jsonify({"success": False, "message": "No customers waiting in this queue."}), 404

    next_token = waiting_tokens[0]
    called_token, err = QueueService.call_token(next_token['id'])
    if err:
        return jsonify({"success": False, "message": err}), 500

    return jsonify({"success": True, "token": called_token})

@app.route('/api/staff/call', methods=['POST'])
def api_call_token():
    data = request.get_json() or {}
    token_id = data.get('token_id')
    if not token_id:
        return jsonify({"success": False, "message": "token_id is required"}), 400

    called_token, err = QueueService.call_token(int(token_id))
    if err:
        return jsonify({"success": False, "message": err}), 500

    return jsonify({"success": True, "token": called_token})

@app.route('/api/staff/complete', methods=['POST'])
def api_complete_token():
    """
    Called by the outlet employee when the order/service is complete.
    Triggers automated SMS and Voice Call update to the customer.
    """
    data = request.get_json() or {}
    token_id = data.get('token_id')
    if not token_id:
        return jsonify({"success": False, "message": "token_id is required"}), 400

    result, err = QueueService.complete_token(int(token_id))
    if err:
        return jsonify({"success": False, "message": err}), 500

    return jsonify({
        "success": True,
        "token": result['token'],
        "notifications": result['notifications'],
        "message": f"Order #{result['token']['token_number']} marked complete. Automated customer alert dispatched!"
    })


# ----------------- API ROUTES: DISPLAY & ANALYTICS ----------------- #

@app.route('/api/display/board', methods=['GET'])
def api_display_board():
    board = QueueService.get_public_display_board()
    return jsonify({"success": True, "board": board})

@app.route('/api/analytics/dashboard', methods=['GET'])
def api_analytics_dashboard():
    summary = AnalyticsService.get_dashboard_summary()
    return jsonify(summary)

@app.route('/api/analytics/peak-hours', methods=['GET'])
def api_analytics_peak_hours():
    data = AnalyticsService.get_peak_hours_analysis()
    return jsonify(data)

@app.route('/api/analytics/daily-load', methods=['GET'])
def api_analytics_daily_load():
    data = AnalyticsService.get_daily_load_analysis()
    return jsonify(data)

@app.route('/api/analytics/outlets', methods=['GET'])
def api_analytics_outlets():
    outlets = AnalyticsService.get_outlet_performance()
    return jsonify({"success": True, "outlets": outlets})

@app.route('/api/notifications/logs', methods=['GET'])
def api_notification_logs():
    limit = int(request.args.get('limit', 50))
    logs = NotificationService.get_notification_logs(limit=limit)
    return jsonify({"success": True, "logs": logs})

@app.route('/api/ml/info', methods=['GET'])
def api_ml_info():
    info = MLWaitTimeService.get_model_info()
    return jsonify(info)

@app.route('/api/ml/train', methods=['POST'])
def api_ml_train():
    res = MLWaitTimeService.train_model()
    return jsonify(res)


# ----------------- API ROUTES: TELECOM GATEWAYS & SETTINGS ----------------- #

@app.route('/api/settings/telecom', methods=['GET'])
def api_get_telecom_settings():
    cfg = Config.get_telecom_config()
    # Mask secrets for display
    fast2sms_key = cfg.get('fast2sms_api_key', '')
    masked_fast2sms = f"{fast2sms_key[:4]}...{fast2sms_key[-4:]}" if len(fast2sms_key) > 8 else fast2sms_key
    
    tw_token = cfg.get('twilio_auth_token', '')
    masked_tw_token = f"{tw_token[:4]}...{tw_token[-4:]}" if len(tw_token) > 8 else tw_token

    return jsonify({
        "success": True,
        "config": {
            "fast2sms_api_key": masked_fast2sms,
            "fast2sms_configured": bool(fast2sms_key),
            "twilio_account_sid": cfg.get('twilio_account_sid', ''),
            "twilio_auth_token": masked_tw_token,
            "twilio_phone_number": cfg.get('twilio_phone_number', ''),
            "twilio_configured": bool(cfg.get('twilio_account_sid') and cfg.get('twilio_auth_token')),
            "active_provider": cfg.get('active_provider', 'auto')
        }
    })

@app.route('/api/settings/telecom', methods=['POST'])
def api_save_telecom_settings():
    data = request.get_json() or {}
    
    fast2sms_key = data.get('fast2sms_api_key', '').strip()
    if fast2sms_key and not fast2sms_key.startswith('...'):
        Config.set_setting('fast2sms_api_key', fast2sms_key)
        
    tw_sid = data.get('twilio_account_sid', '').strip()
    if tw_sid:
        Config.set_setting('twilio_account_sid', tw_sid)
        
    tw_token = data.get('twilio_auth_token', '').strip()
    if tw_token and not tw_token.startswith('...'):
        Config.set_setting('twilio_auth_token', tw_token)
        
    tw_phone = data.get('twilio_phone_number', '').strip()
    if tw_phone:
        Config.set_setting('twilio_phone_number', tw_phone)
        
    provider = data.get('active_provider', 'auto').strip()
    if provider:
        Config.set_setting('active_provider', provider)

    return jsonify({"success": True, "message": "Telecom gateway settings saved successfully."})

@app.route('/api/telecom/test-sms', methods=['POST'])
def api_test_sms():
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    message = data.get('message', 'SmartQueue Test: Real SMS gateway connection successful!').strip()

    if not phone:
        return jsonify({"success": False, "message": "Phone number is required."}), 400

    result = NotificationService.test_send_sms(phone=phone, message=message)
    return jsonify({
        "success": True,
        "result": result,
        "message": f"Test SMS processed ({result.get('provider')}: {result.get('status')})"
    })


if __name__ == '__main__':
    print("Starting SmartQueue Server on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

