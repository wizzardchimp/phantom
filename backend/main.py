"""NovaFi Phantom - Backend API for the cyber exercise game."""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .rag_engine import RAGEngine

DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(
    title="NovaFi Phantom API",
    description="Backend for the NovaFi cyber security exercise game. Query the corporate dataset via RAG-powered LLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RAGEngine()


class QueryRequest(BaseModel):
    query: str
    use_llm: bool = False


class QueryResponse(BaseModel):
    query: str
    intent: str
    response: str
    emails_found: int
    records_found: int
    llm_used: bool = False


class SQLQueryRequest(BaseModel):
    sql: str


@app.get("/")
async def root():
    return {"service": "NovaFi Phantom API", "version": "1.0.0", "status": "online"}


@app.get("/stats")
async def get_stats():
    db_path = str(DATA_DIR / "novafi.db")
    if not os.path.exists(db_path):
        raise HTTPException(404, "Database not found. Run generate.py first.")
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    stats = {}
    for table in ["employees", "customers", "orders", "emails", "payroll"]:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = c.fetchone()[0]
    conn.close()

    secrets_path = DATA_DIR / "secrets.json"
    if secrets_path.exists():
        with open(secrets_path) as f:
            secrets = json.load(f)
        stats["planted_secrets"] = len(secrets["secrets"])
    else:
        stats["planted_secrets"] = 0

    return stats


@app.post("/query")
async def query_data(request: QueryRequest):
    result = engine.query(request.query)
    return {
        "query": result["query"],
        "intent": result.get("intent", "unknown"),
        "response": result.get("response", "No response generated."),
        "emails_found": result.get("emails_found", 0),
        "records_found": result.get("records_found", 0),
        "llm_used": result.get("llm_used", False),
    }


@app.post("/sql")
async def run_sql(request: SQLQueryRequest):
    from .rag_engine import DatabaseQuery
    db_path = str(DATA_DIR / "novafi.db")
    dq = DatabaseQuery(db_path)
    results = dq.query(request.sql)
    return {"sql": request.sql, "results": results, "count": len(results)}


@app.get("/schema")
async def get_schema():
    from .rag_engine import DatabaseQuery
    db_path = str(DATA_DIR / "novafi.db")
    dq = DatabaseQuery(db_path)
    return {"schema": dq.get_table_schema()}


@app.get("/secrets")
async def get_secrets():
    secrets_path = DATA_DIR / "secrets.json"
    if not secrets_path.exists():
        raise HTTPException(404, "Secrets file not found")
    with open(secrets_path) as f:
        return json.load(f)


@app.get("/emails")
async def get_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    department: Optional[str] = None,
    search: Optional[str] = None,
):
    import sqlite3
    db_path = str(DATA_DIR / "novafi.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    where = []
    params = []
    if department:
        where.append("department = ?")
        params.append(department)
    if search:
        where.append("(subject LIKE ? OR body LIKE ? OR from_name LIKE ? OR to_name LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term] * 4)

    where_clause = " WHERE " + " AND ".join(where) if where else ""
    offset = (page - 1) * per_page

    c.execute(f"SELECT COUNT(*) FROM emails{where_clause}", params)
    total = c.fetchone()[0]

    c.execute(
        f"SELECT id, thread_id, from_name, from_addr, to_name, to_addr, subject, timestamp, department, sensitivity "
        f"FROM emails{where_clause} ORDER BY id LIMIT ? OFFSET ?",
        params + [per_page, offset],
    )
    emails = [dict(r) for r in c.fetchall()]
    conn.close()

    return {"emails": emails, "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page}


@app.get("/employees")
async def get_employees(department: Optional[str] = None):
    import sqlite3
    db_path = str(DATA_DIR / "novafi.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if department:
        c.execute("SELECT id, name, email, department, position, salary, is_management FROM employees WHERE department = ? ORDER BY name", (department,))
    else:
        c.execute("SELECT id, name, email, department, position, salary, is_management FROM employees ORDER BY department, name")
    employees = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"employees": employees, "count": len(employees)}


@app.get("/customers")
async def get_customers(limit: int = Query(20, ge=1, le=100)):
    import sqlite3
    db_path = str(DATA_DIR / "novafi.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, name, email, credit_card_type, risk_score, account_created FROM customers LIMIT ?",
        (limit,),
    )
    customers = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"customers": customers, "count": len(customers)}


@app.get("/orders")
async def get_orders(status: Optional[str] = None, limit: int = Query(20, ge=1, le=100)):
    import sqlite3
    db_path = str(DATA_DIR / "novafi.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if status:
        c.execute("SELECT id, customer_name, product, amount, status, created_at FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
    else:
        c.execute("SELECT id, customer_name, product, amount, status, created_at FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
    orders = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"orders": orders, "count": len(orders)}


@app.get("/terminal", response_class=HTMLResponse)
async def terminal_ui():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Frontend not found. Run: python3 generate.py</h1>"


def main():
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"[+] NovaFi Phantom API starting on http://localhost:{port}")
    print(f"[+] Terminal UI: http://localhost:{port}/terminal")
    print(f"[+] API Docs: http://localhost:{port}/docs")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
