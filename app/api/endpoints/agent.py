import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.schemas.agent import AskRequest, AskResponse, ModelsResponse, StatsResponse
from app.agent.agent_service import agent_service
from app.agent.ollama_models import NoChatModelError, list_chat_models, pick_default_model
from app.agent.tools import db
from app.database.session import sync_engine

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask_agent(request: AskRequest):
    """
    This endpoint receives a natural language question and returns the agent's response.
    """
    try:
        # Call the agent service to process the request
        response_text, model, sql_queries = await agent_service.run_agent(
            request.query, request.session_id, request.model
        )
        return AskResponse(
            response=response_text,
            session_id=request.session_id,
            model=model,
            sql_queries=sql_queries,
        )
    except NoChatModelError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Handle potential errors during agent execution
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    List the chat models found in the local Ollama server.
    """
    try:
        models = await list_chat_models()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Ollama: {str(e)}")
    return ModelsResponse(models=models, default=pick_default_model(models))

@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """
    Return the number of rows in each database table.
    """
    with sync_engine.connect() as connection:
        tables = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
            for table in sorted(db.get_usable_table_names())
        }
    return StatsResponse(tables=tables)
