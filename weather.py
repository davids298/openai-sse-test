"""Resolve a city and fetch current model-based weather from Open-Meteo."""
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException

from models import ChatRequest

GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'

CONDITIONS = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Depositing rime fog',
    51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
    56: 'Light freezing drizzle', 57: 'Dense freezing drizzle',
    61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
    66: 'Light freezing rain', 67: 'Heavy freezing rain',
    71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow', 77: 'Snow grains',
    80: 'Slight rain showers', 81: 'Moderate rain showers', 82: 'Violent rain showers',
    85: 'Slight snow showers', 86: 'Heavy snow showers',
    95: 'Thunderstorm', 96: 'Thunderstorm with slight hail', 99: 'Thunderstorm with heavy hail',
}


def fail(status, code, message, **extra):
    return HTTPException(status, detail={'code': code, 'message': message, **extra})


async def get_context(client: httpx.AsyncClient, request: ChatRequest) -> dict:
    try:
        response = await client.get(GEOCODING_URL, params={
            'name': request.city, 'countryCode': request.country,
            'count': 100, 'language': 'en',
        })
        response.raise_for_status()
        places = [p for p in response.json().get('results', [])
                  if p.get('country_code') == request.country
                  and p.get('feature_code', '').startswith('PPL')]
        if request.region:
            places = [p for p in places if p.get('admin1', '').casefold() == request.region.casefold()]
        exact = [p for p in places if p['name'].casefold() == request.city.casefold()]
        places = exact or places
        if not places:
            raise fail(404, 'location_not_found', 'No city found in that country. Check spelling or region.')
        if len(places) != 1:
            raise fail(409, 'ambiguous_location', 'Several cities match. Specify a region or a more exact city name.',
                       candidates=[{'city': p['name'], 'region': p.get('admin1'), 'country': p['country_code']}
                                   for p in places[:10]])
        place = places[0]
        response = await client.get(WEATHER_URL, params={
            'latitude': place['latitude'], 'longitude': place['longitude'],
            'current': 'temperature_2m,apparent_temperature,weather_code,wind_speed_10m',
            'timezone': 'auto', 'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh',
        })
        response.raise_for_status()
        data = response.json()
        timezone = data['timezone']
        now = datetime.now(ZoneInfo(timezone))
        current = data['current']
        required = ('time', 'temperature_2m', 'apparent_temperature', 'weather_code', 'wind_speed_10m')
        if any(current.get(key) is None for key in required):
            raise ValueError('Missing current weather')
        return {
            'location': {'city': place['name'], 'region': place.get('admin1'),
                         'country': place['country_code'], 'latitude': place['latitude'],
                         'longitude': place['longitude']},
            'timezone': timezone, 'local_datetime': now.isoformat(),
            'local_day': now.strftime('%A, %d %B %Y'),
            'weather': {**current, 'conditions': CONDITIONS.get(current['weather_code'], 'Unknown'),
                        'units': data['current_units']},
            'source': {'name': 'Open-Meteo', 'url': 'https://open-meteo.com/',
                       'location_data': 'GeoNames', 'description': 'Current model-based weather, not a station observation'},
        }
    except httpx.TimeoutException:
        raise fail(504, 'weather_timeout', 'Location or weather lookup timed out. Try again.') from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise fail(502, 'weather_unavailable', 'Location or weather service returned unavailable or invalid data.') from None
