import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
import joblib

def train_forecasting_model():
    df = pd.read_csv("freight_historical_data.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['DayOfYear'] = df['Date'].dt.dayofyear
    
    le_route = LabelEncoder()
    le_vessel = LabelEncoder()
    df['Route_Encoded'] = le_route.fit_transform(df['Route'])
    df['Vessel_Encoded'] = le_vessel.fit_transform(df['Vessel_Type'])
    
    joblib.dump(le_route, 'le_route.pkl')
    joblib.dump(le_vessel, 'le_vessel.pkl')
    
    features = ['Year', 'Month', 'DayOfYear', 'Route_Encoded', 'Vessel_Encoded', 'Bunker_Price', 'Port_Congestion_Days']
    X = df[features]
    y = df['Freight_Rate_USD_Per_Ton']
    
    print("⏳ Training XGBoost Forecasting Engine...")
    model = xgb.XGBRegressor(n_estimators=300, learning_rate=0.08, max_depth=6, random_state=42)
    model.fit(X, y)
    
    joblib.dump(model, 'freight_xgb_model.pkl')
    print("✅ Model trained & saved as freight_xgb_model.pkl")

if __name__ == "__main__":
    train_forecasting_model()