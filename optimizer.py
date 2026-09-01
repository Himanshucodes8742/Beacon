import pandas as pd

PORT_CONSTRAINTS = {
    "Paradip": {"max_draft_m": 16.0, "max_loa_m": 300},
    "Vizag": {"max_draft_m": 18.1, "max_loa_m": 330},
    "Haldia": {"max_draft_m": 8.5, "max_loa_m": 230},  # Riverine draft restriction
    "Dhamra": {"max_draft_m": 18.0, "max_loa_m": 340},
}

VESSEL_SPECS = {
    "Handysize": {"capacity_tons": 30000, "draft_m": 10.0, "loa_m": 180},
    "Supramax": {"capacity_tons": 55000, "draft_m": 11.5, "loa_m": 200},
    "Panamax": {"capacity_tons": 75000, "draft_m": 13.5, "loa_m": 225},
    "Capesize": {"capacity_tons": 170000, "draft_m": 18.0, "loa_m": 290},
}

def analyze_market_entry_timing(forecast_df_vessel):
    """
    Analyzes future rate trends to determine action: BUY NOW, WAIT, or HURRY.
    """
    current_rate = forecast_df_vessel.iloc[0]['Predicted_Rate']
    min_row = forecast_df_vessel.loc[forecast_df_vessel['Predicted_Rate'].idxmin()]
    min_rate = min_row['Predicted_Rate']
    min_date = min_row['Date'].strftime('%Y-%m-%d')
    
    pct_change = ((min_rate - current_rate) / current_rate) * 100
    
    # Logic for Signals
    if min_row['Date'] == forecast_df_vessel.iloc[0]['Date'] or abs(pct_change) < 2.0:
        signal = "BUY NOW"
        badge_color = "green"
        reason = f"Current rates represent a market trough. Secure contracts today."
    elif pct_change < -2.0:
        signal = "WAIT"
        badge_color = "orange"
        reason = f"Freight rates projected to drop by {abs(pct_change):.1f}%. Optimal entry window: **{min_date}** (${min_rate:.2f}/Ton)."
    else:
        signal = "HURRY"
        badge_color = "red"
        reason = f"Freight rates rising rapidly (+{abs(pct_change):.1f}% over target period). Lock in short-term contracts immediately."
        
    return {
        "signal": signal,
        "color": badge_color,
        "reason": reason,
        "current_rate": current_rate,
        "lowest_rate": min_rate,
        "best_date": min_date
    }

def optimize_vessel_charter(cargo_volume_tons, destination_port, forecasted_rates):
    """
    Filters vessels based on port draft/LOA limitations and calculates total costs.
    """
    port_draft = PORT_CONSTRAINTS[destination_port]["max_draft_m"]
    port_loa = PORT_CONSTRAINTS[destination_port]["max_loa_m"]
    
    best_option = None
    lowest_cost = float('inf')
    recommendations = []

    for vessel, specs in VESSEL_SPECS.items():
        can_dock = (specs["draft_m"] <= port_draft) and (specs["loa_m"] <= port_loa)
        status = "Eligible" if can_dock else f"Rejected (Draft/LOA Exceeded)"
        
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