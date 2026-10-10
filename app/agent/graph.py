import operator
import re
import uuid
from functools import lru_cache
from typing import TypedDict, Annotated, List
from langchain_core.messages import AIMessage, BaseMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.core.config import settings
from app.agent.tools import execute_query_tool

# Define the tools that the agent can use
tools = [execute_query_tool]

# Matches a reply that is nothing but a SQL query, optionally wrapped in a Markdown code fence
_BARE_SQL_PATTERN = re.compile(r"^\s*(?:```(?:sql)?\s*)?((?:select|with)\b.+?)\s*(?:```)?\s*$", re.IGNORECASE | re.DOTALL)

def _bare_sql_to_tool_call(response: AIMessage) -> AIMessage:
    """
    Small local models often reply with the SQL as plain text instead of a structured tool call.
    Turn such a reply into a real tool call so the query still gets executed.
    """
    if response.tool_calls or not isinstance(response.content, str):
        return response
    match = _BARE_SQL_PATTERN.match(response.content)
    if not match:
        return response
    tool_call = {
        "name": execute_query_tool.name,
        "args": {"query": match.group(1)},
        "id": str(uuid.uuid4()),
        "type": "tool_call",
    }
    return AIMessage(content="", tool_calls=[tool_call])

class AgentState(TypedDict):
    """
    Defines the state of the graph. This dictionary passes information between different graph nodes.
    """
    messages: Annotated[List[BaseMessage], operator.add]

def should_continue(state: AgentState) -> str:
    """
    A conditional node that decides whether the cycle should continue or end.
    """
    last_message = state["messages"][-1]
    # If the last message does not have any tool calls, the LLM has reached a final answer.
    if not last_message.tool_calls:
        return "end"
    # Otherwise, proceed to the tool execution node.
    return "continue"

@lru_cache(maxsize=8)
def get_graph(model_name: str):
    """
    Build (and cache) the agent graph for a given local Ollama model.
    """
    # Define the LLM model (served locally by Ollama)
    # temperature=0 makes responses more deterministic and less creative, which is suitable for generating SQL queries.
    model = ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
    )

    # Bind tools to the model
    # This allows the model to know which tools are available and how to use them.
    model_with_tools = model.bind_tools(tools)

    def call_model(state: AgentState) -> dict:
        """
        Node that calls the LLM model.
        """
        response = _bare_sql_to_tool_call(model_with_tools.invoke(state["messages"]))
        # Append the model's response to the message list.
        return {"messages": [response]}

    # Define the graph
    workflow = StateGraph(AgentState)

    # Add nodes to the graph
    workflow.add_node("agent", call_model)
    workflow.add_node("action", ToolNode(tools))

    # Define the graph entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END,
        },
    )

    # Add edge from tool node back to agent node
    workflow.add_edge("action", "agent")

    # Compile the graph to create an executable agent
    return workflow.compile()
