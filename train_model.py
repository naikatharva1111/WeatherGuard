import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle

def generate_weather_data(num_samples=1000):
    np.random.seed(42)
    
    data = {
        'temp_c': np.random.normal(15, 10, num_samples),
        'wind_kph': np.random.gamma(2, 5, num_samples),
        'pressure_mb': np.random.normal(1010, 10, num_samples),
        'precip_mm': np.random.exponential(2, num_samples),
        'humidity': np.random.randint(20, 100, num_samples),
        'cloud': np.random.randint(0, 100, num_samples),
        'feelslike_c': np.random.normal(15, 10, num_samples),
        'vis_km': np.random.exponential(10, num_samples),
        'uv': np.random.exponential(5, num_samples),
        'hour': np.random.randint(0, 24, num_samples),
        'month': np.random.randint(1, 13, num_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Create synthetic target (1 = severe weather)
    severe_conditions = (
        (df['temp_c'] < -5) | 
        (df['temp_c'] > 35) | 
        (df['wind_kph'] > 40) | 
        (df['precip_mm'] > 15) | 
        (df['uv'] > 8) | 
        (df['pressure_mb'] < 980) | 
        (df['pressure_mb'] > 1030)
    )
    df['severe'] = severe_conditions.astype(int)
    
    return df

# Generate and split data
weather_df = generate_weather_data(5000)
X = weather_df.drop('severe', axis=1)
y = weather_df['severe']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Save model
with open('weather_model.pkl', 'wb') as f:
    pickle.dump(model, f)