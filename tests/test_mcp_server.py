import runpy
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "test-key")
    return runpy.run_path("mcp_server.py")


def mock_client(monkeypatch, response=None, error=None):
    client = MagicMock()
    client.get = AsyncMock(return_value=response, side_effect=error)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=context)
    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return factory, client


def test_server_requires_api_key(monkeypatch):
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="API_KEY is not set"):
        runpy.run_path("mcp_server.py")


def test_server_uses_configured_host_and_port(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "test-key")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "9000")
    server = runpy.run_path("mcp_server.py")

    assert server["mcp"].settings.host == "0.0.0.0"
    assert server["mcp"].settings.port == 9000


@pytest.mark.asyncio
async def test_get_weather_success(server, monkeypatch):
    response = httpx.Response(200, json={
        "name": "London", "sys": {"country": "GB"},
        "main": {"temp": 12.5, "humidity": 80}, "wind": {"speed": 5},
    }, request=httpx.Request("GET", server["URL"]))
    factory, client = mock_client(monkeypatch, response=response)

    result = await server["get_weather"]("London")

    assert result == "Weather in London (GB): temperature is 12.5°Cspeed of wind: 5 kph, Humidity is 80%"
    factory.assert_called_once_with(timeout=10)
    client.get.assert_awaited_once_with(server["URL"], params={
        "appid": "test-key", "q": "London", "units": "metric",
    })


@pytest.mark.asyncio
async def test_get_weather_network_error(server, monkeypatch):
    mock_client(monkeypatch, error=httpx.ConnectError("connection failed"))

    assert await server["get_weather"]("London") == "Could not reach the weather service to check London"


@pytest.mark.asyncio
async def test_get_weather_unrecognized_city(server, monkeypatch):
    mock_client(monkeypatch, response=httpx.Response(400))

    assert await server["get_weather"]("unknown") == "unknown is not a recognized city"


@pytest.mark.asyncio
async def test_get_weather_raises_other_http_errors(server, monkeypatch):
    response = httpx.Response(500, request=httpx.Request("GET", server["URL"]))
    mock_client(monkeypatch, response=response)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await server["get_weather"]("London")
    assert exc_info.value.response.status_code == 500