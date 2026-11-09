import httpx
import os
from mcp.server.fastmcp import FastMCP

# 5199e72500ffafdfe30678de48b81ce7

URL = 'https://api.openweathermap.org/data/2.5/weather'
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

if not WEATHER_API_KEY:
    raise RuntimeError("API_KEY is not set")

mcp = FastMCP(
    name="weather",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", 8000)),
)

@mcp.tool()
async def get_weather(city):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(URL, params={"appid": WEATHER_API_KEY, "q": city, "units": "metric"})
    except httpx.RequestError:
        return f"Could not reach the weather service to check {city}"

    if resp.status_code == 400:
        return f"{city} is not a recognized city"
    resp.raise_for_status()

    data = resp.json()
    city = data['name']
    country = data['sys']['country']
    temp = data['main']['temp']
    wind_kph = data['wind']['speed']
    humidity = data['main']['humidity']
    return (
        f"Weather in {city} ({country}): "
        f"temperature is {temp}°C"
        f"speed of wind: {wind_kph} kph, Humidity is {humidity}%"
    )

if __name__ == "__main__":
    mcp.run(transport='streamable-http')
