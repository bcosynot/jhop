# tests/test_main.py

import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_sleep_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/sleep")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Good night!"
    assert "slept_at" in response.json()
    assert "slept_clock_time" in response.json()

