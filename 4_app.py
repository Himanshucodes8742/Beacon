import streamlit as st
import pandas as pd
import joblib
import datetime
from datetime import timedelta
import plotly.express as px
from optimizer import optimize_vessel_charter, analyze_market_entry_timing

st.set_page_config(page_title="SAIL Smart Charter AI", layout="wide")

# Load Models
try:
    model = joblib.load('freight_xgb_model.pkl')
    le_route = joblib.load('le_route.pkl')
    le_vessel = joblib.load('le_vessel.pkl')
except Exception as e:
    st.error("⚠️ Model files not found. Please run 1_data_simulator.py and 2_forecaster.py first.")
    st.stop()

st.title("🚢 Intelligent Freight Forecasting & Charter Optimizer")
st.markdown("### Ministry of Steel (SAIL) | East Coast India Bulk Procurement Platform")

# Sidebar Controls
st.sidebar.header("📋 Cargo & Route Parameters")
route = st.sidebar.selectbox("Trade Route", ["Australia_to_EC_India", "US_to_EC_India", "Indonesia_to_EC_India", "Mozambique_to_EC_India"])
dest_port = st.sidebar.selectbox("Destination Port (East Coast)", ["Paradip", "Vizag", "Haldia", "Dhamra"])
cargo_volume = st.sidebar.number_input("Cargo Volume (Metric Tons)", min_value=10000, max_value=1000000, value=150000, step=10000)
start_date = st.sidebar.date_input("Analysis Start Date", datetime.date.today())
forecast_days = st.sidebar.slider("Forecast Horizon (Days)", 14, 90, 60)
bunker_price = st.sidebar.slider("Bunker Fuel Price Index ($/Ton)", 300, 800, 450)
congestion = st.sidebar.slider("Est. Port Congestion (Days)", 0, 15, 2)

# Generate Horizon Predictions
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
        rate = model.predict(X_pred)[0]
        forecast_records.append({"Date": pd.to_datetime(d), "Vessel_Type": v_type, "Predicted_Rate": rate})

df_forecast = pd.DataFrame(forecast_records)

# 1. Market Entry Timing Analysis
best_vessel_single, _ = optimize_vessel_charter(cargo_volume, dest_port, {})
target_vessel_df = df_forecast[df_forecast['Vessel_Type'] == (best_vessel_single if best_vessel_single else "Panamax")]
timing_info = analyze_market_entry_timing(target_vessel_df)

# Top Action Metric Display
st.markdown("---")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Recommended Entry Signal", timing_info['signal'])
    if timing_info['signal'] == "BUY NOW":
        st.success(timing_info['reason'])
    elif timing_info['signal'] == "WAIT":
        st.warning(timing_info['reason'])
    else:
        st.error(timing_info['reason'])

with col_b:
    st.metric("Current Freight Rate Today", f"${timing_info['current_rate']:.2f} / Ton")
    
with col_c:
    st.metric(f"Lowest Projected Rate ({timing_info['best_date']})", f"${timing_info['lowest_rate']:.2f} / Ton")

st.markdown("---")

# 2. Time-Series Rate Trend Graph
st.subheader("📈 Freight Rate Forecast Trend (30-90 Day Horizon)")
fig = px.line(
    df_forecast, 
    x="Date", 
    y="Predicted_Rate", 
    color="Vessel_Type",
    title=f"Predicted Rates ($/Ton) for {route.replace('_', ' ')}",
    labels={"Predicted_Rate": "Freight Rate ($/Ton)", "Date": "Shipment Date"},
    template="plotly_white"
)
fig.add_vline(x=timing_info['best_date'], line_dash="dash", line_color="green", annotation_text="Optimal Entry Window")
st.plotly_chart(fig, use_container_width=True)

# 3. Optimization Table & Draft Restrictions
st.subheader(f"⚙️ Vessel Optimization & Port Physical Constraint Analysis ({dest_port})")

# Extract day 0 rate for all vessel types
day_0_rates = df_forecast[df_forecast['Date'] == pd.to_datetime(start_date)].set_index('Vessel_Type')['Predicted_Rate'].to_dict()
best_vessel, constraints_report = optimize_vessel_charter(cargo_volume, dest_port, day_0_rates)

df_report = pd.DataFrame(constraints_report)

def highlight_status(s):
    return ['background-color: #ffcccc' if v.startswith('Rejected') else 'background-color: #ccffcc' for v in s]

st.dataframe(df_report.style.apply(highlight_status, subset=['Status']), use_container_width=True)

if best_vessel:
    st.success(f"💡 **Recommendation:** Lock in contract for **{best_vessel}** vessels to dock at **{dest_port}**. Draft and LOA parameters strictly compliant.")
else:
    st.error(f"⚠️ **Port Restriction Warning:** No direct vessel docking available for {cargo_volume} MT at {dest_port}. Lighterage/Offloading required at Sandheads.")