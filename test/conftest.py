import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    """Create an asynchronous HTTP client to send requests to the application."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
