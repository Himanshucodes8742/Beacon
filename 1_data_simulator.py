import pandas as pd
import numpy as np

def generate_synthetic_freight_data():
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", end="2026-12-31", freq="D")
    routes = ["Australia_to_EC_India", "US_to_EC_India", "Indonesia_to_EC_India", "Mozambique_to_EC_India"]
    vessel_types = ["Handysize", "Supramax", "Panamax", "Capesize"]
    
    data = []
    for route in routes:
        for vessel in vessel_types:
            base_rate = {"Handysize": 25, "Supramax": 22, "Panamax": 18, "Capesize": 14}[vessel]
            route_multiplier = {"Australia_to_EC_India": 1.2, "US_to_EC_India": 2.5, "Indonesia_to_EC_India": 0.8, "Mozambique_to_EC_India": 1.5}[route]
            
            current_rate = base_rate * route_multiplier
            
            for d in dates:
                seasonality = np.sin(d.dayofyear / 365 * 2 * np.pi) * 4
                volatility = np.random.normal(0, 0.4)
                current_rate = max(5, current_rate + volatility + (seasonality * 0.04))
                bunker_fuel_price = 400 + np.sin(d.year) * 100 + np.random.normal(0, 10)
                
                data.append([d, route, vessel, current_rate, bunker_fuel_price, np.random.randint(0, 10)])

    df = pd.DataFrame(data, columns=["Date", "Route", "Vessel_Type", "Freight_Rate_USD_Per_Ton", "Bunker_Price", "Port_Congestion_Days"])
    df.to_csv("freight_historical_data.csv", index=False)
    print("✅ Historical dataset generated: freight_historical_data.csv")

if __name__ == "__main__":
    generate_synthetic_freight_data()