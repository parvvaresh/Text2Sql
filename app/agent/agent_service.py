from typing import Dict, List, Optional, Tuple
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from app.agent.graph import get_graph
from app.agent.ollama_models import resolve_model
from app.agent.tools import db

# Upper bound on agent/tool round trips, so a confused model cannot loop forever
RECURSION_LIMIT = 12

class AgentService:
    """
    This service encapsulates the logic for interacting with the LangGraph agent.
    """
    def __init__(self):
        # Get the database schema information to provide to the LLM
        self.db_schema = db.get_table_info()

    def _create_system_prompt(self) -> str:
        """
        Create a complete and structured prompt for the LLM.
        """
        prompt_template = f"""
You are a smart agent specialized in MySQL databases.
Your task is to answer user questions (asked in Persian) about the store data.

Important notes:
1. For every question about the data, FIRST call the sql_db_query tool with one MySQL SELECT query.
   Never answer from memory, and never ask the user for clarification before trying a query.
2. Never create queries that modify data (UPDATE, DELETE, INSERT). Use SELECT only.
3. Prefer aggregate queries (COUNT, SUM, AVG, MAX, MIN) and add LIMIT 10 when listing rows.
4. After the tool returns, provide the final answer only in Persian (Farsi), in one or two short sentences
   for a non-technical user. Copy names and numbers from the tool result exactly as they are: no rounding,
   no thousands separators, no currency unit. Never write the answer in Chinese or English.
5. If the question is not about the store data, reply briefly in Persian without calling the tool.

Persian vocabulary: مشتری = customers, محصول/کالا = products, سفارش = orders, قیمت = price, موجودی = stock,
برند = brand, دسته‌بندی = category, شهر = city, مبلغ = total_amount.
orders.status values: 'Pending' = در انتظار, 'Shipped' = ارسال‌شده, 'Delivered' = تحویل‌شده, 'Cancelled' = لغوشده.

Example questions and the query to pass to sql_db_query:
- گران‌ترین محصول کدام است؟ => SELECT name, price FROM products ORDER BY price DESC LIMIT 1
- چند سفارش ارسال‌شده داریم؟ => SELECT COUNT(*) FROM orders WHERE status = 'Shipped'
- کدام شهر بیشترین مشتری را دارد؟ => SELECT city, COUNT(*) AS n FROM customers GROUP BY city ORDER BY n DESC LIMIT 1
- مجموع مبلغ سفارش‌های در انتظار چقدر است؟ => SELECT SUM(total_amount) FROM orders WHERE status = 'Pending'

Database schema is as follows:
---
{self.db_schema}
---
"""
        return prompt_template.strip()

    async def run_agent(self, query: str, session_id: str, model: Optional[str] = None) -> Tuple[str, str, List[Dict[str, str]]]:
        """
        Run the agent graph with a given query.
        Returns the final answer, the model that produced it, and the SQL queries that were executed with their raw results.
        """
        model_name = await resolve_model(model)

        # Initial input for the graph
        inputs = {
            "messages": [
                SystemMessage(content=self._create_system_prompt()),
                HumanMessage(content=query),
            ]
        }

        # Run the graph asynchronously
        try:
            final_state = await get_graph(model_name).ainvoke(inputs, {"recursion_limit": RECURSION_LIMIT})
        except GraphRecursionError:
            return "متأسفانه نتوانستم به پاسخ برسم. لطفاً سؤال را ساده‌تر یا دقیق‌تر بپرسید.", model_name, []

        messages = final_state["messages"]

        # Collect the SQL the model ran and what the database returned, so the caller can verify the answer
        results = {m.tool_call_id: m.content for m in messages if isinstance(m, ToolMessage)}
        sql_queries = [
            {"query": tool_call["args"].get("query", ""), "result": results.get(tool_call["id"], "")}
            for message in messages
            if isinstance(message, AIMessage)
            for tool_call in message.tool_calls
        ]

        # Extract the final response from the last message
        response_message = messages[-1]

        return response_message.content, model_name, sql_queries

agent_service = AgentService()
