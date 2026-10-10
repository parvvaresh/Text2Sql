import pytest
from httpx import AsyncClient

# Mark all tests in this file as asynchronous tests
pytestmark = pytest.mark.asyncio

async def test_read_root(async_client: AsyncClient):
    """Test the root endpoint to ensure the service is up and running."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "AI Database Agent is running!"}

@pytest.mark.ollama
async def test_ask_agent_simple_query(async_client: AsyncClient):
    """
    Test a simple question to the agent.
    Note: This test requires connection to the database and a local Ollama model.
    For successful execution, the database must be running with `docker-compose up -d db`.
    """
    # Request payload
    payload = {
        "query": "How many total customers are there?",
        "session_id": "test_session_1"
    }
    
    # Send request to the endpoint
    response = await async_client.post("/api/v1/agent/ask", json=payload)
    
    # Check the response
    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert response_data["session_id"] == "test_session_1"
    # The response should include the number 1000 (based on data/init.sql)
    assert "1000" in response_data["response"]

@pytest.mark.ollama
async def test_ask_agent_complex_query(async_client: AsyncClient):
    """
    Test a more complex question that requires a JOIN operation.
    """
    payload = {
        "query": "What is the name of the customer who placed the most orders?",
        "session_id": "test_session_2"
    }
    
    response = await async_client.post("/api/v1/agent/ask", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    # The agent must have queried the database rather than answering from memory.
    assert response_data["sql_queries"]

async def test_ask_agent_no_query(async_client: AsyncClient):
    """Test sending a request without a query, which should return a validation error."""
    payload = {"session_id": "test_session_3"}
    response = await async_client.post("/api/v1/agent/ask", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.ollama
async def test_list_models(async_client: AsyncClient):
    """Test that the locally installed Ollama models are discovered."""
    response = await async_client.get("/api/v1/agent/models")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["default"] in [model["name"] for model in response_data["models"]]

async def test_stats(async_client: AsyncClient):
    """Test that the row count of every table is reported."""
    response = await async_client.get("/api/v1/agent/stats")
    assert response.status_code == 200
    assert set(response.json()["tables"]) == {"customers", "products", "orders", "order_items"}
