import pandas as pd

# Updated to include ALL ports from PS 26006
PORT_CONSTRAINTS = {
    "Paradip": {"max_draft_m": 16.0, "max_loa_m": 300, "demurrage_rate_usd_day": 20000},
    "Vizag": {"max_draft_m": 18.1, "max_loa_m": 330, "demurrage_rate_usd_day": 22000},
    "Haldia": {"max_draft_m": 8.5, "max_loa_m": 230, "demurrage_rate_usd_day": 15000},
    "Dhamra": {"max_draft_m": 18.0, "max_loa_m": 340, "demurrage_rate_usd_day": 22000},
    "Gangavaram": {"max_draft_m": 19.5, "max_loa_m": 350, "demurrage_rate_usd_day": 25000},
    "Gopalpur": {"max_draft_m": 14.5, "max_loa_m": 280, "demurrage_rate_usd_day": 18000},
    "Sagar-Sandheads": {"max_draft_m": 22.0, "max_loa_m": 400, "demurrage_rate_usd_day": 12000}, # Offshore lighterage zone
}

VESSEL_SPECS = {
    "Handysize": {"capacity_tons": 30000, "draft_m": 10.0, "loa_m": 180},
    "Supramax": {"capacity_tons": 55000, "draft_m": 11.5, "loa_m": 200},
    "Panamax": {"capacity_tons": 75000, "draft_m": 13.5, "loa_m": 225},
    "Capesize": {"capacity_tons": 170000, "draft_m": 18.0, "loa_m": 290},
}

def analyze_market_entry_timing(forecast_df_vessel):
    current_rate = forecast_df_vessel.iloc[0]['Predicted_Rate']
    min_row = forecast_df_vessel.loc[forecast_df_vessel['Predicted_Rate'].idxmin()]
    min_rate = min_row['Predicted_Rate']
    min_date = min_row['Date'].strftime('%Y-%m-%d')
    
    pct_change = ((min_rate - current_rate) / current_rate) * 100
    
    if min_row['Date'] == forecast_df_vessel.iloc[0]['Date'] or abs(pct_change) < 2.0:
        signal = "BUY NOW"
        badge_color = "green"
        reason = "Current market represents a local trough. Lock in short/mid-term CVC contracts today."
    elif pct_change < -2.0:
        signal = "WAIT"
        badge_color = "orange"
        reason = f"Freight rates projected to fall by {abs(pct_change):.1f}%. Target window: **{min_date}** (${min_rate:.2f}/Ton)."
    else:
        signal = "HURRY"
        badge_color = "red"
        reason = f"Freight rates surging (+{abs(pct_change):.1f}%). Secure multi-voyage charters immediately to avoid spot spikes."
        
    return {
        "signal": signal,
        "color": badge_color,
        "reason": reason,
        "current_rate": current_rate,
        "lowest_rate": min_rate,
        "best_date": min_date
    }

def calculate_idle_and_demurrage_risk(destination_port, congestion_days, market_signal):
    """
    Computes idle time penalties and recommends mitigation/deadheading strategies.
    """
    daily_demurrage = PORT_CONSTRAINTS[destination_port]["demurrage_rate_usd_day"]
    total_demurrage_risk = congestion_days * daily_demurrage
    
    idle_strategy = ""
    if congestion_days > 4:
        idle_strategy = f"⚠️ High congestion alert at {destination_port}. Recommend slow-steaming at sea to save fuel or diverting to Sagar-Sandheads for floating transshipment."
    elif market_signal == "WAIT":
        idle_strategy = "💡 Low-demand period projected. Recommend fixing short-term backhaul employment (e.g., coastal iron ore movement) to eliminate ballasting/deadheading costs."
    else:
        idle_strategy = "✅ Port turnaround expected within normal limits. Maintain standard charter schedule."
        
    return total_demurrage_risk, idle_strategy

def optimize_vessel_charter(cargo_volume_tons, destination_port, forecasted_rates):
    port_draft = PORT_CONSTRAINTS[destination_port]["max_draft_m"]
    port_loa = PORT_CONSTRAINTS[destination_port]["max_loa_m"]
    
    best_option = None
    lowest_cost = float('inf')
    recommendations = []

    for vessel, specs in VESSEL_SPECS.items():
        can_dock = (specs["draft_m"] <= port_draft) and (specs["loa_m"] <= port_loa)
        status = "Eligible" if can_dock else f"Rejected (Draft Limit: {port_draft}m)"
        
        voyages_needed = (cargo_volume_tons // specs["capacity_tons"]) + (1 if cargo_volume_tons % specs["capacity_tons"] > 0 else 0)
        rate_per_ton = forecasted_rates.get(vessel, 20.0)
        total_freight_cost = voyages_needed * specs["capacity_tons"] * rate_per_ton
        
        recommendations.append({
            "Vessel": vessel,
            "Voyages Needed": voyages_needed,
            "Status": status,
            "Est. Cost ($)": round(total_freight_cost, 2),
            "Rate/Ton ($)": round(rate_per_ton, 2)
        })
        
        if can_dock and total_freight_cost < lowest_cost:
            lowest_cost = total_freight_cost
            best_option = vessel
            
    return best_option, recommendations