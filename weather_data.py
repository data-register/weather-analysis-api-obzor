import httpx
from fastapi import HTTPException
import logging
from datetime import datetime, timedelta

# Настройка на логването
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_historical_weather(location="8250 Obzor, Bulgaria", weather_api_key=None):
    """Извлича данни за времето от предишния ден"""
    try:
        if not weather_api_key:
            raise ValueError("WEATHER_API_KEY не е предоставен")
            
        # Изчисляваме датата за вчерашния ден
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Заявка за исторически данни
        history_url = f"http://api.weatherapi.com/v1/history.json?key={weather_api_key}&q={location}&dt={yesterday}&lang=bg"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(history_url)
            
            if response.status_code != 200:
                logger.error(f"Грешка при извличане на исторически данни: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Неуспешно извличане на исторически данни")
            
            return response.json()
    except Exception as e:
        logger.error(f"Грешка при заявка за исторически данни: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Грешка при заявка за исторически данни: {str(e)}")

async def get_forecast_weather(location="8250 Obzor, Bulgaria", days=1, weather_api_key=None):
    """Извлича прогнозни данни за времето"""
    try:
        if not weather_api_key:
            raise ValueError("WEATHER_API_KEY не е предоставен")
            
        forecast_url = f"http://api.weatherapi.com/v1/forecast.json?key={weather_api_key}&q={location}&days={days}&lang=bg"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(forecast_url)
            
            if response.status_code != 200:
                logger.error(f"Грешка при извличане на прогнозни данни: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Неуспешно извличане на прогнозни данни")
            
            return response.json()
    except Exception as e:
        logger.error(f"Грешка при заявка за прогнозни данни: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Грешка при заявка за прогнозни данни: {str(e)}")

def format_historical_data(weather_data):
    """Форматира историческите данни за времето"""
    try:
        location = weather_data.get("location", {})
        forecast_day = weather_data.get("forecast", {}).get("forecastday", [{}])[0]
        day_data = forecast_day.get("day", {})
        
        # Конвертиране на скоростта на вятъра от км/ч в м/с
        wind_speed_ms = round(day_data.get('maxwind_kph', 0) / 3.6, 1)
        
        text = f"Местоположение: {location.get('name')}, {location.get('country')}. "
        text += f"Средна температура: {day_data.get('avgtemp_c')}°C. "
        text += f"Минимална температура: {day_data.get('mintemp_c')}°C. "
        text += f"Максимална температура: {day_data.get('maxtemp_c')}°C. "
        text += f"Условия: {day_data.get('condition', {}).get('text')}. "
        text += f"Валежи: {day_data.get('totalprecip_mm')} мм. "
        text += f"Средна влажност: {day_data.get('avghumidity')}%. "
        text += f"Максимална скорост на вятъра: {wind_speed_ms} м/с."
        
        return text
    except Exception as e:
        logger.error(f"Грешка при форматиране на историческите данни: {str(e)}")
        return "Не можахме да форматираме историческите данни."

def format_forecast_data(weather_data):
    """Форматира прогнозните данни за времето"""
    try:
        location = weather_data.get("location", {})
        current = weather_data.get("current", {})
        forecast_days = weather_data.get("forecast", {}).get("forecastday", [])
        
        text = f"Местоположение: {location.get('name')}, {location.get('country')}. "
        text += f"Текущо време: Температура {current.get('temp_c')}°C, {current.get('condition', {}).get('text')}. "
        
        for i, day in enumerate(forecast_days):
            day_name = "Днес" if i == 0 else "Утре" if i == 1 else f"След {i} дни"
            date = day.get("date")
            day_data = day.get("day", {})
            
            # Конвертиране на скоростта на вятъра от км/ч в м/с
            wind_speed_ms = round(day_data.get('maxwind_kph', 0) / 3.6, 1)
            
            text += f"{day_name} ({date}): "
            text += f"Минимална температура: {day_data.get('mintemp_c')}°C, "
            text += f"Максимална температура: {day_data.get('maxtemp_c')}°C, "
            text += f"Условия: {day_data.get('condition', {}).get('text')}, "
            text += f"Вероятност за валеж: {day_data.get('daily_chance_of_rain')}%, "
            text += f"Очаквани валежи: {day_data.get('totalprecip_mm')} мм, "
            text += f"Влажност: {day_data.get('avghumidity')}%, "
            text += f"Скорост на вятъра: {wind_speed_ms} м/с. "
        
        return text
    except Exception as e:
        logger.error(f"Грешка при форматиране на прогнозните данни: {str(e)}")
        return "Не можахме да форматираме прогнозните данни."