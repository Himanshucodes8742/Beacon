"""
server.py — Flask API Server for SAIL Freight Smart Charter AI
Wraps existing ML models and optimizer as REST endpoints, connects to Neon PostgreSQL.
"""

import os
import json
import datetime
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import joblib

load_dotenv()

# Import existing project modules
from optimizer import optimize_vessel_charter, analyze_market_entry_timing, PORT_CONSTRAINTS, VESSEL_SPECS

# Import database layer
import db

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'sail-smart-charter-dev-key')
CORS(app)

# Load ML models at startup
try:
    model = joblib.load('freight_xgb_model.pkl')
    le_route = joblib.load('le_route.pkl')
    le_vessel = joblib.load('le_vessel.pkl')
    MODEL_LOADED = True
except Exception:
    MODEL_LOADED = False
    print("[WARNING] ML model files not found. Forecast endpoints will return mock data.")


# ─────────────────────────────────────────────
# HELPER: JSON serializer for dates/UUIDs/Decimals
# ─────────────────────────────────────────────

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if hasattr(obj, 'hex'):  # UUID
            return str(obj)
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        try:
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return float(obj)
        except ImportError:
            pass
        return super().default(obj)

app.json_encoder = CustomEncoder


def json_response(data, status=200):
    return app.response_class(
        response=json.dumps(data, cls=CustomEncoder),
        status=status,
        mimetype='application/json'
    )


# ─────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


# ─────────────────────────────────────────────
# AUTH ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    employee_id = data.get('employee_id', '').strip()
    password = data.get('password', '').strip()

    if not employee_id or not password:
        return json_response({"error": "Employee ID and password are required"}, 400)

    try:
        user = db.authenticate_user(employee_id, password)
        if user:
            session['user_id'] = str(user['id'])
            session['employee_id'] = user['employee_id']
            return json_response({
                "success": True,
                "user": {
                    "id": str(user['id']),
                    "employee_id": user['employee_id'],
                    "full_name": user['full_name'],
                    "role": user['role'],
                    "department": user['department']
                }
            })
        else:
            return json_response({"error": "Invalid credentials"}, 401)
    except Exception as e:
        # Fallback: if DB is not connected, allow demo login
        if employee_id == "SAIL001" and password == "demo123":
            return json_response({
                "success": True,
                "user": {
                    "id": "demo-user-001",
                    "employee_id": "SAIL001",
                    "full_name": "Demo Logistics Manager",
                    "role": "procurement_manager",
                    "department": "SAIL Raw Materials Division"
                }
            })
        return json_response({"error": f"Database connection error. Use demo credentials (SAIL001/demo123). Detail: {str(e)}"}, 500)


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return json_response({"success": True})


# ─────────────────────────────────────────────
# DASHBOARD — MOCK DATA FOR SHOWCASE
# ─────────────────────────────────────────────

@app.route('/api/dashboard/summary', methods=['GET'])
def dashboard_summary():
    """Returns BDI data, route stats, fleet utilization — all mock for showcase."""
    np.random.seed(int(datetime.date.today().toordinal()))

    # Mock 30-day BDI trend
    bdi_base = 1650
    bdi_data = []
    for i in range(30):
        d = datetime.date.today() - timedelta(days=29 - i)
        bdi_base += np.random.normal(0, 25)
        bdi_base = max(800, min(3000, bdi_base))
        bdi_data.append({"date": d.isoformat(), "value": round(bdi_base, 1)})

    current_bdi = bdi_data[-1]['value']
    prev_bdi = bdi_data[-2]['value']
    bdi_change = round(((current_bdi - prev_bdi) / prev_bdi) * 100, 2)

    # Mock route rates with sparklines
    routes = [
        {
            "route": "Australia → Paradip",
            "current_rate": round(15.2 + np.random.normal(0, 0.5), 2),
            "trend": [round(14.5 + np.random.normal(0, 0.3), 2) for _ in range(7)],
            "change": round(np.random.normal(0.5, 1.2), 2)
        },
        {
            "route": "US → Vizag",
            "current_rate": round(38.5 + np.random.normal(0, 1), 2),
            "trend": [round(37.8 + np.random.normal(0, 0.5), 2) for _ in range(7)],
            "change": round(np.random.normal(-0.3, 0.8), 2)
        },
        {
            "route": "Indonesia → Haldia",
            "current_rate": round(11.8 + np.random.normal(0, 0.3), 2),
            "trend": [round(11.5 + np.random.normal(0, 0.2), 2) for _ in range(7)],
            "change": round(np.random.normal(0.2, 0.5), 2)
        },
        {
            "route": "Mozambique → Dhamra",
            "current_rate": round(22.1 + np.random.normal(0, 0.7), 2),
            "trend": [round(21.5 + np.random.normal(0, 0.4), 2) for _ in range(7)],
            "change": round(np.random.normal(0.1, 0.9), 2)
        }
    ]

    # Mock upcoming charter opportunities
    opportunities = [
        {"voyage_id": "VYG-2026-0187", "route": "Australia → Paradip", "cargo_mt": 150000, "target_date": "2026-10-15", "status": "Optimal"},
        {"voyage_id": "VYG-2026-0192", "route": "US → Vizag", "cargo_mt": 80000, "target_date": "2026-10-22", "status": "Watch"},
        {"voyage_id": "VYG-2026-0198", "route": "Indonesia → Haldia", "cargo_mt": 55000, "target_date": "2026-11-05", "status": "Optimal"},
        {"voyage_id": "VYG-2026-0201", "route": "Mozambique → Dhamra", "cargo_mt": 120000, "target_date": "2026-11-12", "status": "Watch"}
    ]

    # Mock fleet utilization
    fleet_by_type = {"Capesize": 35, "Panamax": 30, "Supramax": 20, "Handysize": 15}
    fleet_by_charter = {"CVC (Medium-Term)": 55, "Spot": 30, "Time Charter": 15}

    return json_response({
        "bdi": {
            "current": current_bdi,
            "change_pct": bdi_change,
            "trend": bdi_data
        },
        "routes": routes,
        "opportunities": opportunities,
        "fleet_by_type": fleet_by_type,
        "fleet_by_charter": fleet_by_charter
    })


# ─────────────────────────────────────────────
# RISK ALERTS — MOCK DATA
# ─────────────────────────────────────────────

@app.route('/api/risks', methods=['GET'])
def get_risks():
    alerts = [
        {"severity": "danger", "title": "Port Congestion: Paradip", "detail": "Average wait time exceeded 5 days. Berth allocation delays reported.", "timestamp": "2h ago"},
        {"severity": "warning", "title": "Weather Advisory: Indian Ocean", "detail": "Cyclonic activity detected in Bay of Bengal. Possible route diversions for NE coast.", "timestamp": "4h ago"},
        {"severity": "warning", "title": "Market Volatility: Capesize Rates", "detail": "Capesize spot rates surged +8.2% in 48 hours. BDI momentum turning bullish.", "timestamp": "6h ago"},
        {"severity": "info", "title": "CVC Renewal Window", "detail": "Contract CVC-AU-PD-24-001 renewal due in 21 days. Current market favors extension.", "timestamp": "1d ago"},
    ]
    return json_response({"alerts": alerts})


# ─────────────────────────────────────────────
# FORECAST ENDPOINT — REAL ML PREDICTIONS
# ─────────────────────────────────────────────

@app.route('/api/forecast', methods=['POST'])
def run_forecast():
    data = request.get_json()
    route = data.get('route', 'Australia_to_EC_India')
    dest_port = data.get('destination_port', 'Paradip')
    cargo_volume = data.get('cargo_volume', 150000)
    start_date_str = data.get('start_date', datetime.date.today().isoformat())
    forecast_days = data.get('forecast_days', 60)
    bunker_price = data.get('bunker_price', 450)
    congestion = data.get('congestion', 2)
    contract_type = data.get('contract_type', 'CVC')

    start_date = datetime.date.fromisoformat(start_date_str)

    if not MODEL_LOADED:
        # Return mock forecast data if model not available
        return _mock_forecast(route, start_date, forecast_days)

    # Generate predictions using XGBoost model
    dates = [start_date + timedelta(days=i) for i in range(forecast_days)]
    forecast_records = []

    for d in dates:
        for v_type in le_vessel.classes_:
            X_pred = pd.DataFrame({
                'Year': [d.year],
                'Month': [d.month],
                'DayOfYear': [d.timetuple().tm_yday],
                'Route_Encoded': le_route.transform([route]),
                'Vessel_Encoded': le_vessel.transform([v_type]),
                'Bunker_Price': [bunker_price],
                'Port_Congestion_Days': [congestion]
            })
            rate = float(model.predict(X_pred)[0])
            forecast_records.append({
                "date": d.isoformat(),
                "vessel_type": v_type,
                "predicted_rate": round(rate, 2)
            })

    df_forecast = pd.DataFrame(forecast_records)

    # Market entry timing analysis
    best_vessel_single, _ = optimize_vessel_charter(cargo_volume, dest_port, {})
    target_vessel = best_vessel_single if best_vessel_single else "Panamax"
    target_df = df_forecast[df_forecast['vessel_type'] == target_vessel].copy()
    target_df['Date'] = pd.to_datetime(target_df['date'])
    target_df = target_df.rename(columns={'predicted_rate': 'Predicted_Rate'})

    timing_info = analyze_market_entry_timing(target_df)

    # Vessel optimization using day-0 rates
    day_0_df = df_forecast[df_forecast['date'] == start_date.isoformat()]
    day_0_rates = {r['vessel_type']: r['predicted_rate'] for r in day_0_df.to_dict('records')}
    best_vessel, constraints_report = optimize_vessel_charter(cargo_volume, dest_port, day_0_rates)

    # Confidence data (simulated 90% band)
    confidence_band = []
    for rec in forecast_records:
        if rec['vessel_type'] == target_vessel:
            rate = rec['predicted_rate']
            confidence_band.append({
                "date": rec['date'],
                "upper": round(rate * 1.06, 2),
                "lower": round(rate * 0.94, 2),
                "predicted": rate
            })

    return json_response({
        "forecast": forecast_records,
        "timing": timing_info,
        "optimization": {
            "best_vessel": best_vessel,
            "constraints": constraints_report
        },
        "confidence": confidence_band,
        "port_constraints": PORT_CONSTRAINTS.get(dest_port, {}),
        "vessel_specs": VESSEL_SPECS
    })


def _mock_forecast(route, start_date, forecast_days):
    """Fallback mock data when ML model is not loaded."""
    vessels = ["Handysize", "Supramax", "Panamax", "Capesize"]
    base_rates = {"Handysize": 28, "Supramax": 24, "Panamax": 19, "Capesize": 15}
    records = []
    for i in range(forecast_days):
        d = start_date + timedelta(days=i)
        for v in vessels:
            rate = base_rates[v] + np.sin(i / 30 * np.pi) * 2 + np.random.normal(0, 0.3)
            records.append({"date": d.isoformat(), "vessel_type": v, "predicted_rate": round(float(rate), 2)})
    return json_response({
        "forecast": records,
        "timing": {"signal": "BUY NOW", "color": "green", "reason": "Mock data — model not loaded", "current_rate": 19.0, "lowest_rate": 17.5, "best_date": start_date.isoformat()},
        "optimization": {"best_vessel": "Panamax", "constraints": []},
        "confidence": [],
        "port_constraints": {},
        "vessel_specs": VESSEL_SPECS
    })


# ─────────────────────────────────────────────
# VESSEL OPTIMIZER ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    cargo_volume = data.get('cargo_volume', 150000)
    dest_port = data.get('destination_port', 'Paradip')
    rates = data.get('rates', {})

    if not rates:
        rates = {"Handysize": 28, "Supramax": 24, "Panamax": 19, "Capesize": 15}

    best_vessel, report = optimize_vessel_charter(cargo_volume, dest_port, rates)

    return json_response({
        "best_vessel": best_vessel,
        "report": report,
        "port_constraints": PORT_CONSTRAINTS.get(dest_port, {}),
        "vessel_specs": VESSEL_SPECS
    })


# ─────────────────────────────────────────────
# CHARTERS — DATABASE CRUD
# ─────────────────────────────────────────────

@app.route('/api/charters', methods=['GET'])
def list_charters():
    try:
        charters = db.get_active_charters()
        return json_response({"charters": charters})
    except Exception as e:
        # Fallback mock data
        return json_response({"charters": _mock_charters()})


@app.route('/api/charters', methods=['POST'])
def create_charter():
    data = request.get_json()
    try:
        charter = db.create_charter(data)
        return json_response({"success": True, "charter": charter}, 201)
    except Exception as e:
        return json_response({"error": str(e)}, 500)


@app.route('/api/charters/<charter_id>/status', methods=['PATCH'])
def patch_charter_status(charter_id):
    data = request.get_json()
    new_status = data.get('status')
    try:
        charter = db.update_charter_status(charter_id, new_status)
        if charter:
            return json_response({"success": True, "charter": charter})
        return json_response({"error": "Charter not found"}, 404)
    except Exception as e:
        return json_response({"error": str(e)}, 500)


def _mock_charters():
    """Fallback mock charters when DB is unavailable."""
    return [
        {
            "id": "c001", "vessel_name": "MV Sagar Pragati", "vessel_type": "Panamax",
            "cargo_type": "Coking Coal", "cargo_volume_tons": 75000,
            "origin_port": "Hay Point, Australia", "destination_port": "Paradip",
            "strategy_type": "CVC", "contract_rate_per_ton": 18.50,
            "total_landed_cost": 1387500.00, "status": "En-Route",
            "estimated_arrival_date": "2026-09-18"
        },
        {
            "id": "c002", "vessel_name": "MV Steel Voyager", "vessel_type": "Capesize",
            "cargo_type": "Coking Coal", "cargo_volume_tons": 170000,
            "origin_port": "Richards Bay, Mozambique", "destination_port": "Dhamra",
            "strategy_type": "Spot", "contract_rate_per_ton": 22.10,
            "total_landed_cost": 3757000.00, "status": "Loading",
            "estimated_arrival_date": "2026-10-02"
        },
        {
            "id": "c003", "vessel_name": "MV Eastern Glory", "vessel_type": "Supramax",
            "cargo_type": "Coking Coal", "cargo_volume_tons": 55000,
            "origin_port": "Hampton Roads, US", "destination_port": "Vizag",
            "strategy_type": "CVC", "contract_rate_per_ton": 38.20,
            "total_landed_cost": 2101000.00, "status": "Discharging",
            "estimated_arrival_date": "2026-09-05"
        },
        {
            "id": "c004", "vessel_name": "MV Bharat Shakti", "vessel_type": "Handysize",
            "cargo_type": "Coking Coal", "cargo_volume_tons": 28000,
            "origin_port": "Kalimantan, Indonesia", "destination_port": "Haldia",
            "strategy_type": "Spot", "contract_rate_per_ton": 11.80,
            "total_landed_cost": 330400.00, "status": "Awaiting Berth",
            "estimated_arrival_date": "2026-09-08"
        },
        {
            "id": "c005", "vessel_name": "MV Coal Express", "vessel_type": "Panamax",
            "cargo_type": "Coking Coal", "cargo_volume_tons": 74000,
            "origin_port": "Hay Point, Australia", "destination_port": "Paradip",
            "strategy_type": "CVC", "contract_rate_per_ton": 17.90,
            "total_landed_cost": 1324600.00, "status": "Completed",
            "estimated_arrival_date": "2026-08-25"
        }
    ]


# ─────────────────────────────────────────────
# REPORTS — DATABASE CRUD
# ─────────────────────────────────────────────

@app.route('/api/reports', methods=['GET'])
def list_reports():
    try:
        reports = db.get_reports()
        return json_response({"reports": reports})
    except Exception:
        return json_response({"reports": _mock_reports()})


@app.route('/api/reports', methods=['POST'])
def create_report():
    data = request.get_json()
    try:
        report = db.save_report(data)
        return json_response({"success": True, "report": report}, 201)
    except Exception as e:
        return json_response({"error": str(e)}, 500)


@app.route('/api/reports/<report_id>', methods=['DELETE'])
def remove_report(report_id):
    try:
        deleted = db.delete_report(report_id)
        if deleted:
            return json_response({"success": True})
        return json_response({"error": "Report not found"}, 404)
    except Exception as e:
        return json_response({"error": str(e)}, 500)


def _mock_reports():
    return [
        {
            "id": "r001", "report_title": "Q3 Australia-Paradip CVC Analysis",
            "trade_route": "Australia_to_EC_India", "destination_port": "Paradip",
            "cargo_volume_tons": 150000, "recommended_vessel": "Panamax",
            "market_signal": "BUY NOW", "forecasted_rate_per_ton": 17.85,
            "estimated_total_cost": 2677500, "projected_arbitrage_savings": 425000,
            "demurrage_risk_usd": 45000, "created_at": "2026-08-15T10:30:00"
        },
        {
            "id": "r002", "report_title": "US East Coast Spot vs CVC Comparison",
            "trade_route": "US_to_EC_India", "destination_port": "Vizag",
            "cargo_volume_tons": 80000, "recommended_vessel": "Supramax",
            "market_signal": "WAIT", "forecasted_rate_per_ton": 36.20,
            "estimated_total_cost": 2896000, "projected_arbitrage_savings": 180000,
            "demurrage_risk_usd": 28000, "created_at": "2026-08-22T14:15:00"
        }
    ]


# ─────────────────────────────────────────────
# MARKET INSIGHTS — MOCK DATA
# ─────────────────────────────────────────────

@app.route('/api/market-insights', methods=['GET'])
def market_insights():
    """Port congestion, idle time, savings — all mock for showcase."""

    # Port congestion 6-month trends
    congestion_data = {}
    for port in ["Paradip", "Vizag", "Haldia", "Dhamra"]:
        base = {"Paradip": 4.5, "Vizag": 2.8, "Haldia": 6.2, "Dhamra": 3.1}[port]
        congestion_data[port] = []
        for m in range(6):
            d = datetime.date.today() - timedelta(days=(5 - m) * 30)
            val = base + np.sin(m / 3 * np.pi) * 1.5 + np.random.normal(0, 0.5)
            congestion_data[port].append({"month": d.strftime("%b %Y"), "days": round(max(0, float(val)), 1)})

    # Vessel idle time breakdown
    idle_time = {
        "Capesize": {"waiting_berth": 4.2, "weather_delay": 1.8, "technical": 0.5},
        "Panamax": {"waiting_berth": 2.8, "weather_delay": 1.2, "technical": 0.8},
        "Supramax": {"waiting_berth": 1.5, "weather_delay": 0.9, "technical": 0.3},
        "Handysize": {"waiting_berth": 1.0, "weather_delay": 0.6, "technical": 0.2}
    }

    # Freight cost savings comparison
    savings = {
        "quarters": ["Q1 2026", "Q2 2026", "Q3 2026"],
        "actual_spend": [48500000, 52200000, 47800000],
        "predicted_spend": [45200000, 48900000, 44100000],
        "savings": [3300000, 3300000, 3700000]
    }

    # What-if comparison mock
    whatif = {
        "cvc_12m": {"rate_per_ton": 17.20, "total_cost": 30960000, "risk": "Low", "savings_vs_spot": 4280000},
        "spot_12m": {"rate_per_ton": 19.58, "total_cost": 35240000, "risk": "High", "savings_vs_spot": 0}
    }

    return json_response({
        "congestion": congestion_data,
        "idle_time": idle_time,
        "savings": savings,
        "whatif": whatif
    })


# ─────────────────────────────────────────────
# PORT & VESSEL REFERENCE DATA
# ─────────────────────────────────────────────

@app.route('/api/reference/ports', methods=['GET'])
def get_ports():
    return json_response({"ports": PORT_CONSTRAINTS})


@app.route('/api/reference/vessels', methods=['GET'])
def get_vessels():
    return json_response({"vessels": VESSEL_SPECS})


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("SAIL Freight Smart Charter AI -- Server Starting...")
    print("   Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
