document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('searchBtn');
    const locationInput = document.getElementById('locationInput');
    const weatherContainer = document.getElementById('weatherContainer');
    const alertContainer = document.getElementById('alertContainer');
    const subscriptionForm = document.getElementById('subscriptionForm');

    searchBtn.addEventListener('click', fetchWeatherData);
    subscriptionForm.addEventListener('submit', handleSubscription);

    async function fetchWeatherData() {
        const location = locationInput.value.trim();
        if (!location) return;

        try {
            // First fetch from our Flask API which will use WeatherAPI
            const response = await fetch(`/api/weather?location=${encodeURIComponent(location)}`);
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            displayWeatherData(data);
            checkForAlerts(data);
            
        } catch (error) {
            console.error('Error fetching weather data:', error);
            alert('Failed to fetch weather data. Please try again.');
        }
    }

    function displayWeatherData(data) {
        weatherContainer.classList.remove('d-none');
        
        document.getElementById('locationName').textContent = `${data.location.name}, ${data.location.country}`;
        document.getElementById('temperature').textContent = `${data.current.temp_c}°C`;
        document.getElementById('weatherDescription').textContent = data.current.condition.text;
        
        const weatherIcon = document.getElementById('weatherIcon');
        weatherIcon.innerHTML = `<img src="https:${data.current.condition.icon}" alt="${data.current.condition.text}">`;
        
        const details = document.getElementById('weatherDetails');
        details.innerHTML = `
            <div class="col-md-6">
                <p><strong>Humidity:</strong> ${data.current.humidity}%</p>
                <p><strong>Wind:</strong> ${data.current.wind_kph} km/h</p>
                <p><strong>Pressure:</strong> ${data.current.pressure_mb} mb</p>
            </div>
            <div class="col-md-6">
                <p><strong>Feels Like:</strong> ${data.current.feelslike_c}°C</p>
                <p><strong>Visibility:</strong> ${data.current.vis_km} km</p>
                <p><strong>UV Index:</strong> ${data.current.uv}</p>
            </div>
        `;
    }

    function checkForAlerts(data) {
        const alertMessage = document.getElementById('alertMessage');
        alertContainer.classList.add('d-none');
        
        // Check for severe weather conditions
        if (data.current.temp_c <= 0) {
            alertMessage.textContent = `FREEZE WARNING: Temperature is ${data.current.temp_c}°C`;
            alertContainer.classList.remove('d-none');
        } else if (data.current.wind_kph > 30) {
            alertMessage.textContent = `WIND ALERT: Strong winds at ${data.current.wind_kph} km/h`;
            alertContainer.classList.remove('d-none');
        } else if (data.current.uv > 8) {
            alertMessage.textContent = `UV WARNING: Extreme UV index (${data.current.uv})`;
            alertContainer.classList.remove('d-none');
        } else if (data.current.precip_mm > 10) {
            alertMessage.textContent = `HEAVY RAIN ALERT: ${data.current.precip_mm}mm precipitation`;
            alertContainer.classList.remove('d-none');
        }
    }

    async function handleSubscription(e) {
        e.preventDefault();
        const email = document.getElementById('emailInput').value;
        const smsEnabled = document.getElementById('smsCheck').checked;
        
        try {
            const response = await fetch('/api/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, sms_enabled: smsEnabled })
            });
            
            const result = await response.json();
            alert(result.message || 'Subscription successful!');
        } catch (error) {
            console.error('Subscription error:', error);
            alert('Failed to subscribe. Please try again.');
        }
    }
});