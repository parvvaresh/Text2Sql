from typing import List, Optional
import httpx
from app.core.config import settings


class NoChatModelError(RuntimeError):
    """Raised when Ollama has no installed model that the agent can use."""


async def _capabilities(client: httpx.AsyncClient, model: dict) -> List[str]:
    # Recent Ollama versions report capabilities in /api/tags; older ones only in /api/show
    if "capabilities" in model:
        return model["capabilities"]
    response = await client.post("/api/show", json={"model": model["name"]})
    response.raise_for_status()
    return response.json().get("capabilities", [])


async def list_chat_models() -> List[dict]:
    """
    Discover the models installed in the local Ollama server.
    Embedding-only models are skipped; tool-capable models come first, largest first.
    """
    async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=10) as client:
        response = await client.get("/api/tags")
        response.raise_for_status()

        models = []
        for model in response.json().get("models", []):
            capabilities = await _capabilities(client, model)
            if "completion" not in capabilities:
                continue
            models.append({
                "name": model["name"],
                "size": model.get("size", 0),
                "parameter_size": model.get("details", {}).get("parameter_size"),
                "supports_tools": "tools" in capabilities,
            })

    models.sort(key=lambda m: (m["supports_tools"], m["size"]), reverse=True)
    return models


def pick_default_model(models: List[dict]) -> Optional[str]:
    """
    Choose the model used when the request does not name one.
    """
    usable = [m["name"] for m in models if m["supports_tools"]]
    if settings.OLLAMA_MODEL in usable:
        return settings.OLLAMA_MODEL
    return usable[0] if usable else None


async def resolve_model(requested: Optional[str] = None) -> str:
    """
    Return the requested model, or auto-detect one from the local Ollama server.
    """
    if requested:
        return requested
    default = pick_default_model(await list_chat_models())
    if default is None:
        raise NoChatModelError("No Ollama model with tool-calling support is installed.")
    return default
