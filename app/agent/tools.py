import re
from decimal import Decimal
from langchain_core.tools import tool
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy.exc import SQLAlchemyError
from app.database.session import sync_engine

# Create a database instance to be used by LangChain tools
# This instance uses a synchronous (blocking) connection engine
db = SQLDatabase(engine=sync_engine)

# Rows beyond this are dropped, so a broad query cannot overflow the model's context window
MAX_RESULT_ROWS = 50

_READ_ONLY_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def _is_read_only(query: str) -> bool:
    """Accept a single SELECT statement only."""
    statement = query.strip().rstrip(";")
    return bool(_READ_ONLY_PATTERN.match(statement)) and ";" not in statement


def _format_value(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (float, Decimal)):
        # 5014355.0 -> 5014355, so the model does not have to deal with float noise
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


# Define a SQL query execution tool
# This tool allows the LLM (Large Language Model) to run SQL queries on the database
@tool("sql_db_query")
def execute_query_tool(query: str) -> str:
    """Execute a single read-only MySQL SELECT query against the shop database and return the rows.
    If the query is not correct, an error message is returned; fix the query and try again."""
    if not _is_read_only(query):
        return "Error: only a single SELECT statement is allowed."

    try:
        with sync_engine.connect() as connection:
            # The database itself rejects any write inside a read-only transaction
            connection.exec_driver_sql("START TRANSACTION READ ONLY")
            result = connection.exec_driver_sql(query.strip().rstrip(";"))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_RESULT_ROWS + 1)
    except SQLAlchemyError as e:
        return f"Error: {getattr(e, 'orig', e)}"

    if not rows:
        return "The query returned no rows."

    lines = [" | ".join(columns)]
    lines += [" | ".join(_format_value(value) for value in row) for row in rows[:MAX_RESULT_ROWS]]
    if len(rows) > MAX_RESULT_ROWS:
        lines.append(f"... (only the first {MAX_RESULT_ROWS} rows are shown; use aggregation or LIMIT)")
    return "\n".join(lines)
