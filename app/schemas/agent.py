from pydantic import BaseModel
from typing import Dict, List, Optional

class AskRequest(BaseModel):
    """Request model for asking the agent"""
    query: str
    session_id: Optional[str] = "default_session"
    # Ollama model to use; auto-detected when omitted
    model: Optional[str] = None

class SqlQuery(BaseModel):
    """A SQL query the agent executed, with the raw result returned by the database"""
    query: str
    result: str

class AskResponse(BaseModel):
    """Response model from the agent"""
    response: str
    session_id: str
    model: str
    sql_queries: List[SqlQuery] = []

class ModelInfo(BaseModel):
    """A chat model installed in the local Ollama server"""
    name: str
    size: int
    parameter_size: Optional[str] = None
    supports_tools: bool

class ModelsResponse(BaseModel):
    """Locally installed Ollama models and the one used by default"""
    models: List[ModelInfo]
    default: Optional[str] = None

class StatsResponse(BaseModel):
    """Row count per database table"""
    tables: Dict[str, int]
