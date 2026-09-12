# SmartQueue: Intelligent Queue Management & Waiting-Time Prediction System

An intelligent, full-stack digital queue management web application designed for campus cafeterias, administrative offices, libraries, student service counters, clinics, and banks. 

SmartQueue eliminates chaotic physical lines by generating digital tokens, predicting wait times using machine learning (**Scikit-learn**), analyzing historical peak rush hours (**Pandas & NumPy**), and automatically dispatching **SMS & Voice Call updates** to the customer the moment an employee marks their order complete at the counter terminal.

---

## 🌟 Key Features

1. **Multi-Outlet / Counter Management**:
   - Manage distinct outlets (e.g., *Campus Canteen Meals Counter 1*, *Quick Bites & Beverages Counter 2*, *Student Fee & Admin Office Counter 3*, *Central Library Circulation Desk*).
   - Independent queues and token sequence prefixes (e.g., `CAN-101`, `BEV-102`, `ADM-201`, `LIB-301`).

2. **Customer Digital Token & Live Status Tracker**:
   - Join a queue with customer name, phone number, notification preference, and order notes.
   - Dynamic real-time tracker displaying:
     - Exact number of people ahead in queue.
     - Machine learning-predicted wait time with live countdown.
     - Audio chime and visual alert notifications when called or ready.

3. **Automated SMS & Voice Call Notifications**:
   - When the counter employee clicks **"Mark Complete & Send SMS/Call"** at their terminal:
     - Dispatches an SMS alert:  
       `"SmartQueue Alert: Hello [Name]! Your token #[Token] at [Outlet] ([Counter]) is READY for pickup! Please proceed to the counter."`
     - Dispatches a Voice Call notification using text-to-speech audio synthesis.
   - **Dual Mode**:
     - Live **Twilio API** integration using environment variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`).
     - Interactive **Built-in Simulator**: Enables seamless demonstration and offline testing without paid API accounts. Live audit logs and in-app feeds allow visual inspection.

4. **Machine Learning Wait-Time Prediction**:
   - Built with **Scikit-learn** (`RandomForestRegressor`).
   - Trained on historical queue features:
     - `people_ahead`
     - `hour_of_day` (rush hours vs non-peak)
     - `day_of_week`
     - `outlet_id`
     - `recent_avg_service_time`
   - High prediction accuracy ($R^2 \approx 0.946$, $\text{MAE} \approx 2.6\text{ mins}$).
   - Includes real-time one-click retraining directly from the Admin portal.

5. **Historical Peak Period & Rush-Hour Analytics**:
   - Powered by **Pandas & NumPy** with **Chart.js** visualizations.
   - **Hourly Customer Volume**: Identifies peak rush hours (e.g., 12:00–14:00 lunch rush and 17:00–19:00 evening rush).
   - **Wait-Time Trends**: Visualizes wait time elevation during high-traffic periods.
   - **Weekly Traffic Distribution**: Compares customer volume across Monday through Sunday.
   - **Outlet Efficiency**: Side-by-side comparison of average wait time vs counter service time.

6. **Public TV / Display Screen**:
   - Fullscreen-ready monitor board for waiting halls and cafeteria walls displaying **"Now Serving"** and **"Ready for Pickup"** tokens across all outlets with live digital clock.

7. **SDG Alignment**:
   - **SDG 9** (Industry, Innovation & Infrastructure): Modernizes manual lines into intelligent, data-driven campus infrastructure.
   - **SDG 11** (Sustainable Cities & Communities): Reduces indoor congestion and optimizes personal time.

---

## 🚀 Quick Start

### 1. Requirements & Setup
The project runs with Python 3.11+. The virtual environment `.venv` is pre-configured.

To start the server:
```bash
.venv\Scripts\python.exe app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 2. Available Portals
- **Home / Launcher**: `http://127.0.0.1:5000/`
- **Customer Portal**: `http://127.0.0.1:5000/customer`
- **Staff Counter Terminal**: `http://127.0.0.1:5000/staff`
- **Public Display Board**: `http://127.0.0.1:5000/display`
- **Peak Analytics & ML**: `http://127.0.0.1:5000/admin`

---

## 📲 Optional: Twilio Configuration for Live SMS & Calls
If you wish to send real SMS and phone calls to physical mobile phones:
Set the following environment variables before starting `app.py`:

```powershell
$env:TWILIO_ACCOUNT_SID="your_account_sid"
$env:TWILIO_AUTH_TOKEN="your_auth_token"
$env:TWILIO_PHONE_NUMBER="+1xxxxxxxxxx"
```

If not set, the system automatically runs in **Interactive Simulation Mode**, logging every SMS and Call in the database and modal feed with zero setup required.

---

## 🧪 Running the Automated Test Suite

Run the full end-to-end integration and unit tests:
```bash
.venv\Scripts\python.exe tests\test_smart_queue.py
```

---

## 📁 Architecture & File Structure

```
Smart Queue Management System/
├── app.py                      # Flask Application, Routing & REST API
├── config.py                   # Configuration & Twilio settings
├── requirements.txt            # Project dependencies
├── database/
│   ├── schema.sql              # SQLite schema (outlets, tokens, notifications)
│   └── db.py                   # Connection manager & DB bootstrap
├── services/
│   ├── queue_service.py        # Token lifecycle & dynamic queue math
│   ├── notification_service.py # Twilio SMS/Call + Simulation engine
│   ├── ml_service.py           # Scikit-learn RandomForestRegressor wait-time model
│   └── analytics_service.py    # Pandas & NumPy peak hour analytics
├── scripts/
│   └── seed_data.py            # Historical dataset generator (550+ records)
├── models/
│   └── wait_time_model.pkl     # Trained ML model weights
├── static/
│   ├── css/style.css           # Modern design system & animations
│   └── js/
│       ├── customer.js         # Real-time token polling & chime notifications
│       ├── staff.js            # Counter actions & Mark Complete trigger
│       ├── display.js          # Public TV screen live board
│       └── admin.js            # Chart.js peak period analytics
├── templates/
│   ├── base.html               # Base layout with live SMS/Call feed modal
│   ├── index.html              # Landing page & quick launcher
│   ├── customer.html           # Customer registration & live token tracker
│   ├── staff.html              # Staff terminal
│   ├── display.html            # Public waiting room screen
│   └── admin.html              # Admin analytics & ML specs
└── tests/
    └── test_smart_queue.py     # Automated test suite
```
