import requests
import json
from datetime import datetime
import os
from tokens import openweather_key

def get_weather(api_key, city):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric'
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_forecast(api_key, city):
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric'
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def save_data_for_rag(data, filename, data_type='weather'):
    """Save weather data to a file for RAG system usage"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Format data with timestamp
    formatted_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": data_type,
        "data": data
    }
    
    # Write to file
    with open(filename, 'w') as file:
        json.dump(formatted_data, file, indent=2)
    
    return filename

def save_combined_data(weather_data, forecast_data, filename):
    """Save both current weather and forecast data to a single file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Format combined data with timestamp
    formatted_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_weather": weather_data,
        "forecast": forecast_data
    }
    
    # Write to file
    with open(filename, 'w') as file:
        json.dump(formatted_data, file, indent=2)
    
    return filename

def main():
    api_key = openweather_key
    city = "Tigre, Buenos Aires"
    
    # Get current weather
    weather_data = get_weather(api_key, city)
    
    # Get forecast data
    forecast_data = get_forecast(api_key, city)
    
    if weather_data and forecast_data:
        # Print current weather info
        print(f"Weather in {city}:")
        print(f"Temperature: {weather_data['main']['temp']}°C")
        print(f"Weather: {weather_data['weather'][0]['description']}")
        print(f"Humidity: {weather_data['main']['humidity']}%")
        print(f"Wind Speed: {weather_data['wind']['speed']} m/s")
        
        # Print sample of forecast
        print("\nSample of 5-day forecast:")
        for item in forecast_data['list'][:3]:
            dt = datetime.fromtimestamp(item['dt'])
            temp = item['main']['temp']
            desc = item['weather'][0]['description']
            print(f"  {dt.strftime('%Y-%m-%d %H:%M')}: {temp}°C, {desc}")
        
        # Save combined data for RAG
        weather_file = os.path.join(os.path.dirname(__file__), "rag/weather_data.json")
        save_combined_data(weather_data, forecast_data, weather_file)
        print(f"Weather and forecast data saved to {weather_file}")
        
        # Optionally save separate files too
        current_file = os.path.join(os.path.dirname(__file__), "rag/current_weather.json")
        save_data_for_rag(weather_data, current_file, 'current')
        print(f"Current weather saved to {current_file}")
        
        forecast_file = os.path.join(os.path.dirname(__file__), "rag/forecast_data.json")
        save_data_for_rag(forecast_data, forecast_file, 'forecast')
        print(f"Forecast data saved to {forecast_file}")
    else:
        if not weather_data:
            print("Failed to get current weather data")
        if not forecast_data:
            print("Failed to get forecast data")

if __name__ == "__main__":
    main()