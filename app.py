from flask import Flask, request, jsonify, render_template, session
import requests
import pickle
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-123')

# Add datetime to template globals
@app.context_processor
def inject_datetime():
    return {
        'datetime': datetime,
        'timedelta': timedelta,
        'now': datetime.now
    }

# Load ML model with error handling
try:
    with open('weather_model.pkl', 'rb') as f:
        model = pickle.load(f)
    print("ML model loaded successfully")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    model = None

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY not found in environment variables")

# Constants
MAX_FORECAST_DAYS = 7
HISTORICAL_DAYS_DEFAULT = 30

def generate_alerts(current):
    """Generate weather alerts based on current conditions"""
    alerts = []
    if not isinstance(current, dict):
        return alerts
    
    thresholds = {
        'heat': {'temp_c': 35, 'message': 'Heat warning: Temperature is {value}°C', 'severity': 'high'},
        'cold': {'temp_c': 0, 'message': 'Freeze warning: Temperature is {value}°C', 'severity': 'medium'},
        'wind_high': {'wind_kph': 40, 'message': 'High wind warning: {value} km/h', 'severity': 'medium'},
        'wind_low': {'wind_kph': 30, 'message': 'Windy conditions: {value} km/h', 'severity': 'low'},
        'uv_extreme': {'uv': 8, 'message': 'Extreme UV index: {value}', 'severity': 'high'},
        'uv_high': {'uv': 6, 'message': 'High UV index: {value}', 'severity': 'medium'},
        'rain_heavy': {'precip_mm': 15, 'message': 'Heavy precipitation: {value}mm', 'severity': 'high'},
        'rain_light': {'precip_mm': 5, 'message': 'Rain expected: {value}mm', 'severity': 'low'}
    }

    # Check each threshold
    for key, config in thresholds.items():
        param = key.split('_')[0]
        if param in current and current[param] > config.get(param, float('inf')):
            alerts.append({
                'type': param,
                'message': config['message'].format(value=current[param]),
                'severity': config['severity']
            })
    
    return alerts

@app.route('/')
def home():
    """Homepage with weather dashboard"""
    return render_template('index.html')

@app.route('/current-weather')
def current_weather():
    """Current weather page with alerts"""
    default_location = session.get('last_location', 'London')
    return render_template('current_weather.html', 
                         default_location=default_location)

@app.route('/forecast')
def forecast():
    """Weather forecast page"""
    return render_template('forecast.html')

@app.route('/historical')
def historical():
    """Historical weather data page"""
    default_location = session.get('last_location', 'London')
    yesterday = datetime.now() - timedelta(days=1)
    week_ago = datetime.now() - timedelta(days=7)
    
    return render_template('historical.html',
                         default_location=default_location,
                         yesterday=yesterday.strftime('%Y-%m-%d'),
                         week_ago=week_ago.strftime('%Y-%m-%d'))

@app.route('/maps')
def maps():
    """Weather maps page"""
    return render_template('maps.html')

# API Endpoints
@app.route('/api/current', methods=['GET'])
def api_current():
    """API endpoint for current weather data"""
    location = request.args.get('location', 'London')
    try:
        current_url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}"
        response = requests.get(current_url, timeout=10)
        response.raise_for_status()
        current_data = response.json()
        
        if model:
            features = [
                current_data['current']['temp_c'],
                current_data['current']['wind_kph'],
                current_data['current']['pressure_mb'],
                current_data['current']['precip_mm'],
                current_data['current']['humidity'],
                current_data['current']['cloud'],
                current_data['current']['feelslike_c'],
                current_data['current']['vis_km'],
                current_data['current']['uv'],
                datetime.now().hour,
                datetime.now().month
            ]
            prediction = model.predict_proba([features])[0][1]
        else:
            prediction = 0.0
        
        alerts = generate_alerts(current_data['current'])
        session['last_location'] = location
        
        return jsonify({
            'location': current_data['location'],
            'current': current_data['current'],
            'alert_probability': float(prediction),
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Weather API request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/api/historical', methods=['GET'])
def api_historical():
    """API endpoint for historical weather data"""
    location = request.args.get('location', 'London')
    date = request.args.get('date', (datetime.now() - timedelta(days=HISTORICAL_DAYS_DEFAULT)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date)
    
    try:
        url = f"http://api.weatherapi.com/v1/history.json?key={WEATHER_API_KEY}&q={location}&dt={date}"
        if date != end_date:
            url = f"{url}&end_dt={end_date}"
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        processed_data = []
        for forecast in data.get('forecast', {}).get('forecastday', []):
            day_data = {
                'date': forecast['date'],
                'day_of_week': datetime.strptime(forecast['date'], '%Y-%m-%d').strftime('%A'),
                'maxtemp_c': forecast['day']['maxtemp_c'],
                'mintemp_c': forecast['day']['mintemp_c'],
                'avgtemp_c': forecast['day']['avgtemp_c'],
                'totalprecip_mm': forecast['day']['totalprecip_mm'],
                'maxwind_kph': forecast['day']['maxwind_kph'],
                'avghumidity': forecast['day']['avghumidity'],
                'condition': forecast['day']['condition'],
                'hourly': [{
                    'time': hour['time'].split()[1],
                    'temp_c': hour['temp_c'],
                    'wind_kph': hour['wind_kph'],
                    'precip_mm': hour['precip_mm'],
                    'humidity': hour['humidity'],
                    'condition': hour['condition'],
                    'pressure_mb': hour['pressure_mb']
                } for hour in forecast['hour']]
            }
            processed_data.append(day_data)
        
        return jsonify({
            'location': data['location'],
            'historical': processed_data
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Weather API request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/api/maps', methods=['GET'])
def api_maps():
    """API endpoint for weather maps"""
    location = request.args.get('location', 'London')
    map_type = request.args.get('type', 'precipitation')
    
    try:
        geocode_url = f"http://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={location}"
        response = requests.get(geocode_url, timeout=10)
        response.raise_for_status()
        location_data = response.json()[0]
        
        map_types = {
            'precipitation': 'radar',
            'temperature': 'temp',
            'wind': 'wind',
            'clouds': 'cloud'
        }
        
        map_urls = {
            name: f"https://maps.weatherapi.com/weather/maplight/1.2/{path}?key={WEATHER_API_KEY}&q={location_data['lat']},{location_data['lon']}&size=600x400"
            for name, path in map_types.items()
        }
        
        return jsonify({
            'lat': location_data['lat'],
            'lon': location_data['lon'],
            'name': location_data['name'],
            'region': location_data['region'],
            'country': location_data['country'],
            'map_types': map_urls
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Location search failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/api/forecast', methods=['GET'])
def api_forecast():
    """API endpoint for weather forecast"""
    location = request.args.get('location', 'London')
    days = min(int(request.args.get('days', 3)), MAX_FORECAST_DAYS)
    
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&days={days}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        forecast_days = []
        for day in data['forecast']['forecastday']:
            hourly = day['hour']
            if model:
                features = [
                    np.mean([h['temp_c'] for h in hourly]),  # avg temp
                    np.mean([h['wind_kph'] for h in hourly]),  # avg wind
                    day['day']['avgtemp_c'],  # pressure proxy
                    day['day']['totalprecip_mm'],
                    np.mean([h['humidity'] for h in hourly]),
                    np.mean([h['cloud'] for h in hourly]),
                    day['day']['avgtemp_c'],  # feelslike proxy
                    np.mean([h['vis_km'] for h in hourly]),
                    day['day']['uv'],
                    datetime.strptime(day['date'], '%Y-%m-%d').hour,
                    datetime.strptime(day['date'], '%Y-%m-%d').month
                ]
                risk_probability = float(model.predict_proba([features])[0][1])
            else:
                risk_probability = 0.0
            
            forecast_days.append({
                'date': day['date'],
                'day_of_week': datetime.strptime(day['date'], '%Y-%m-%d').strftime('%A'),
                'maxtemp_c': day['day']['maxtemp_c'],
                'mintemp_c': day['day']['mintemp_c'],
                'condition': day['day']['condition'],
                'risk_probability': risk_probability,
                'hourly': [{
                    'time': hour['time'].split()[1],
                    'temp_c': hour['temp_c'],
                    'condition': hour['condition'],
                    'chance_of_rain': hour['chance_of_rain'],
                    'chance_of_snow': hour['chance_of_snow']
                } for hour in day['hour'] if int(hour['time'].split()[1].split(':')[0]) % 3 == 0]
            })
        
        return jsonify({
            'location': data['location'],
            'current': data['current'],
            'forecast': forecast_days
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Weather API request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)