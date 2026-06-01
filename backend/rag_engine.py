import json
import sqlite3
import re
from pathlib import Path
from typing import Optional

from .vector_store import VectorStore

DATA_DIR = Path(__file__).parent.parent / "data"


class DatabaseQuery:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def query(self, sql: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute(sql)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            conn.close()
            return [{"error": str(e)}]

    def get_table_schema(self) -> str:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        schema_parts = []
        for table in tables:
            c.execute(f"PRAGMA table_info({table})")
            cols = [f"  {r[1]} ({r[2]})" for r in c.fetchall()]
            schema_parts.append(f"TABLE {table}:\n" + "\n".join(cols))
        conn.close()
        return "\n\n".join(schema_parts)

    def infer_query(self, question: str) -> Optional[str]:
        q = question.lower()

        salary_patterns = [
            (r"(highest|top|max|maximum).*salar", "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 5"),
            (r"(lowest|bottom|min|minimum).*salar", "SELECT name, position, department, salary FROM employees ORDER BY salary ASC LIMIT 5"),
            (r"average.*salar", "SELECT department, ROUND(AVG(salary), 0) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC"),
            (r"who.*(highest|most).*paid|top.*(earner|paid)", "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 10"),
            (r"(salar|pay).*(\d+)" , lambda m: f"SELECT name, position, department, salary FROM employees WHERE salary > {m.group(2)} ORDER BY salary DESC LIMIT 10"),
        ]
        employee_patterns = [
            (r"(how many|count).*employee|headcount|total.*employee", "SELECT department, COUNT(*) as count FROM employees GROUP BY department ORDER BY count DESC"),
            (r"list.*employee|all.*employee|show.*employee", "SELECT name, position, department, email FROM employees ORDER BY department, name LIMIT 30"),
            (r"employee.*(engineer|engineering|tech|dev)", "SELECT name, position, department, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC"),
            (r"employee.*(hr|human.?resources)", "SELECT name, position, salary FROM employees WHERE department = 'Human Resources' ORDER BY name"),
            (r"employee.*(sales|marketing)", "SELECT name, position, department, salary FROM employees WHERE department IN ('Sales', 'Marketing') ORDER BY department, name"),
            (r"employee.*(executive|c.?suite|ceo|cfo|cto)", "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' ORDER BY salary DESC"),
            (r"employee.*(finance|accounting)", "SELECT name, position, salary FROM employees WHERE department = 'Finance' ORDER BY name"),
            (r"(who|which).*(manager|management|director|vp)", "SELECT name, position, department, salary FROM employees WHERE is_management = 1 ORDER BY department"),
        ]
        customer_patterns = [
            (r"(how many|count).*customer", "SELECT COUNT(*) as total_customers FROM customers"),
            (r"(high.?risk|risk.*score).*customer", "SELECT name, email, risk_score FROM customers WHERE risk_score > 75 ORDER BY risk_score DESC LIMIT 10"),
            (r"customer.*(card|credit|payment)", "SELECT name, credit_card_type, credit_card_number FROM customers LIMIT 10"),
            (r"list.*customer|all.*customer", "SELECT name, email, account_created FROM customers ORDER BY account_created DESC LIMIT 20"),
        ]
        order_patterns = [
            (r"(how many|total|count).*order", "SELECT COUNT(*) as total_orders, ROUND(SUM(amount), 0) as total_revenue FROM orders"),
            (r"(highest|top|largest).*order", "SELECT customer_name, product, amount, status FROM orders ORDER BY amount DESC LIMIT 10"),
            (r"(pending|processing).*order", "SELECT customer_name, product, amount, status FROM orders WHERE status IN ('pending', 'processing') ORDER BY amount DESC LIMIT 10"),
            (r"order.*(refund|disputed|dispute)", "SELECT customer_name, product, amount, status FROM orders WHERE status IN ('refunded', 'disputed') LIMIT 10"),
            (r"revenue|total.*amount|sales", "SELECT STRFTIME('%Y-%m', created_at) as month, COUNT(*) as orders, ROUND(SUM(amount), 0) as revenue FROM orders GROUP BY month ORDER BY month DESC LIMIT 12"),
        ]
        payroll_patterns = [
            (r"(payroll|total.*payroll|salary.*cost)", "SELECT ROUND(SUM(salary), 0) as total_annual_payroll FROM employees"),
            (r"(bonus|bonuses)", "SELECT employee_name, bonuses, pay_period_start FROM payroll WHERE bonuses > 0 ORDER BY bonuses DESC LIMIT 10"),
        ]
        email_patterns = [
            (r"(email|mail).*(ceo|executive|exec|confidential|secret)", None),  # handled by vector search
        ]

        for patterns, target in [ (salary_patterns, "employees"), (employee_patterns, "employees"),
                                  (customer_patterns, "customers"), (order_patterns, "orders"),
                                  (payroll_patterns, "payroll") ]:
            for pattern, sql in patterns:
                if callable(sql):
                    m = re.search(pattern, q)
                    if m:
                        return sql(m)
                elif re.search(pattern, q):
                    return sql

        return None


class RAGEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "novafi.db")
        self.vector_store = VectorStore(db_path=self.db_path)
        self.db_query = DatabaseQuery(self.db_path)

        secrets_path = DATA_DIR / "secrets.json"
        if secrets_path.exists():
            with open(secrets_path) as f:
                self.secrets_data = json.load(f)
        else:
            self.secrets_data = {"secrets": []}

    def summarize_context(self, emails: list[dict], sql_results: list[dict]) -> str:
        parts = []

        if emails:
            email_lines = ["--- RELEVANT EMAILS ---"]
            for e in emails[:5]:
                email_lines.append(
                    f"[{e['department']}] {e['from_name']} -> {e['to_name']} | "
                    f"Subject: {e['subject']} | Score: {e.get('relevance_score', 'N/A')}"
                )
                email_lines.append(f"Snippet: {e['body'][:300]}")
                email_lines.append("")
            parts.append("\n".join(email_lines))

        if sql_results:
            sql_lines = ["--- DATABASE RESULTS ---"]
            for row in sql_results[:10]:
                sql_lines.append(str(row))
            parts.append("\n".join(sql_lines))

        return "\n".join(parts)

    def query(self, question: str, use_llm: bool = False, llm_client=None) -> dict:
        question_lower = question.lower()

        sql = self.db_query.infer_query(question)
        sql_results = []
        if sql:
            sql_results = self.db_query.query(sql)

        vector_results = self.vector_store.search(question, top_k=10)

        intent = self._classify_intent(question_lower)
        context = self.summarize_context(vector_results, sql_results)

        if use_llm and llm_client:
            response = self._llm_answer(question, context, llm_client, intent)
        else:
            response = self._template_answer(question, vector_results, sql_results, intent)

        return {
            "query": question,
            "intent": intent,
            "response": response,
            "emails_found": len(vector_results),
            "records_found": len(sql_results),
            "top_emails": vector_results[:5],
            "sql_results": sql_results[:10],
            "sql_used": sql,
        }

    def _classify_intent(self, q: str) -> str:
        if any(w in q for w in ["salar", "pay", "compensation", "bonus", "top earn", "highest paid", "lowest paid", "payroll"]):
            return "salary_query"
        if any(w in q for w in ["employee", "staff", "people", "who", "manage", "hire", "headcount", "workforce"]):
            return "employee_query"
        if any(w in q for w in ["customer", "client", "user"]):
            return "customer_query"
        if any(w in q for w in ["order", "sell", "sale", "revenue", "transaction", "purchase"]):
            return "order_query"
        if any(w in q for w in ["password", "security", "breach", "hack", "vulnerability", "exploit"]):
            return "security_query"
        if any(w in q for w in ["layoff", "fire", "terminate", "offshore", "phoenix"]):
            return "layoff_query"
        if any(w in q for w in ["affair", "relationship", "affair", "personal"]):
            return "personal_query"
        if any(w in q for w in ["email", "mail", "message", "thread", "communicat"]):
            return "email_query"
        if any(w in q for w in ["secrets", "secrets", "easter egg", "hidden", "plant"]):
            return "secrets_query"
        return "general_query"

    def _template_answer(self, question: str, emails: list[dict], sql_results: list[dict], intent: str) -> str:
        intent_responses = {
            "salary_query": self._answer_salary,
            "employee_query": self._answer_employees,
            "customer_query": self._answer_customers,
            "order_query": self._answer_orders,
            "security_query": self._answer_security,
            "layoff_query": self._answer_layoffs,
            "personal_query": self._answer_personal,
            "email_query": self._answer_emails,
            "secrets_query": self._answer_secrets,
            "general_query": self._answer_general,
        }
        handler = intent_responses.get(intent, self._answer_general)
        return handler(question, emails, sql_results)

    def _answer_salary(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Salary Analysis"]
        lines.append(">>> ACCESS GRANTED: PAYROLL DATABASE")
        if sql_results:
            lines.append(f"{'DEPARTMENT':<25} {'ROLE':<30} {'SALARY':<12}")
            lines.append("-" * 67)
            for r in sql_results:
                lines.append(f"{r.get('name', r.get('department', '')):<25} {r.get('position', ''):<30} ${r.get('salary', r.get('avg_salary', 0)):<10,}")
        if email_data := [e for e in emails if "salary" in e.get("subject", "").lower() or "salary" in e.get("body", "").lower()]:
            lines.append("\n>>> RELATED EMAIL REFERENCES:")
            for e in email_data[:3]:
                lines.append(f"  [{e['department']}] {e['subject']}")
        lines.append("\n>>> NOTE: Salary data is confidential. Do not share externally.")
        return "\n".join(lines)

    def _answer_employees(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Employee Records"]
        lines.append(">>> ACCESS GRANTED: HR DATABASE")
        if sql_results:
            for r in sql_results:
                if 'department' in r and 'count' in r:
                    lines.append(f"  {r['department']:<25} {r['count']} employees")
                else:
                    lines.append(f"  {r.get('name', 'N/A'):<25} | {r.get('position', r.get('email', ''))}")
        if not sql_results and emails:
            for e in emails[:5]:
                lines.append(f"  [{e['department']}] {e['from_name']}: {e['subject']}")
        lines.append(f"\n>>> {len(sql_results) if sql_results else len(emails)} records returned")
        return "\n".join(lines)

    def _answer_customers(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Customer Records"]
        lines.append(">>> ACCESS GRANTED: CUSTOMER DATABASE")
        if sql_results:
            for r in sql_results:
                if 'total_customers' in r:
                    lines.append(f"  Total Customers: {r['total_customers']}")
                else:
                    masked_cc = r.get('credit_card_number', '')[:4] + " **** **** " + r.get('credit_card_number', '')[-4:] if r.get('credit_card_number') else ''
                    lines.append(f"  {r.get('name', 'N/A'):<25} Risk: {r.get('risk_score', 'N/A')} Card: {masked_cc}")
        else:
            lines.append("  No matching records found via structured query.")
            if emails:
                lines.append("\n>>> Related communications found:")
                for e in emails[:3]:
                    lines.append(f"  {e['subject']}")
        lines.append("\n>>> WARNING: Customer PII is regulated data. Handle with care.")
        return "\n".join(lines)

    def _answer_orders(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Order & Transaction Records"]
        lines.append(">>> ACCESS GRANTED: FINANCIAL DATABASE")
        if sql_results:
            for r in sql_results:
                if 'total_revenue' in r:
                    lines.append(f"  Total Orders: {r['total_orders']} | Total Revenue: ${r['total_revenue']:,}")
                elif 'revenue' in r:
                    lines.append(f"  {r['month']:<10} Orders: {r['orders']:<5} Revenue: ${r['revenue']:>10,}")
                else:
                    lines.append(f"  {r.get('customer_name', 'N/A'):<25} ${r.get('amount', 0):>8,} | {r.get('product', '')} | {r.get('status', '')}")
        return "\n".join(lines)

    def _answer_security(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Security Incident Analysis"]
        lines.append(">>> ACCESSING SECURITY LOGS...")
        relevant = [e for e in emails if e.get('relevance_score', 0) > 0.3]
        if relevant:
            lines.append(f">>> {len(relevant)} relevant security communications found:")
            for e in relevant[:5]:
                sens = " [CONFIDENTIAL]" if e.get('sensitivity') == "confidential" else ""
                lines.append(f"  [{e['department']}]{sens} {e['subject']}")
                if 'password' in e.get('body', '').lower() or 'credential' in e.get('body', '').lower():
                    snippet = e['body'][:200]
                    lines.append(f"    >> Contains potential credential exposure: {snippet}")
        else:
            lines.append("  No direct security incidents found in indexed data.")
        lines.append("\n>>> WARNING: Security incidents must be reported per compliance policy.")
        return "\n".join(lines)

    def _answer_layoffs(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Layoff / Restructuring Intelligence"]
        lines.append(">>> ACCESSING CONFIDENTIAL HR FILES...")
        relevant = [e for e in emails if e.get('relevance_score', 0) > 0.2]
        if relevant:
            for e in relevant[:4]:
                sens = " [CONFIDENTIAL]" if e.get('sensitivity') == "confidential" else ""
                lines.append(f"  [{e['department']}]{sens} {e['subject']}")
                lines.append(f"  From: {e['from_name']} | {e['timestamp']}")
                lines.append(f"  {e['body'][:200]}\n")
        else:
            lines.append("  No explicit layoff communications found.")
        return "\n".join(lines)

    def _answer_personal(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Personal / Relationship Intelligence"]
        lines.append(">>> ACCESSING CONFIDENTIAL COMMUNICATIONS...")
        relevant = [e for e in emails if e.get('sensitivity') == "confidential"]
        personal = [e for e in relevant if ('dinner' in e.get('body', '').lower()
                    or 'personal' in e.get('body', '').lower() or 'paris' in e.get('body', '').lower())]
        if personal:
            for e in personal[:4]:
                lines.append(f"  [{e['department']}] Subject: {e['subject']}")
                lines.append(f"  From: {e['from_name']} To: {e['to_name']}")
                lines.append(f"  {e['body'][:300]}\n")
        return "\n".join(lines)

    def _answer_emails(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: Email Search Results"]
        lines.append(f">>> {len(emails)} relevant messages found")
        if emails:
            for e in emails[:8]:
                ts = e['timestamp'][:19].replace('T', ' ')
                sens = " [CONFIDENTIAL]" if e.get('sensitivity') == "confidential" else ""
                lines.append(f"\n  [{ts}] {e['department']}{sens}")
                lines.append(f"  From: {e['from_name']} <{e['from_addr']}>")
                lines.append(f"  To: {e['to_name']} <{e['to_addr']}>")
                lines.append(f"  Subject: {e['subject']}")
                lines.append(f"  {e['body'][:200]}...")
        return "\n".join(lines)

    def _answer_secrets(self, question, emails, sql_results) -> str:
        lines = [">>> DATABASE EASTER EGGS / PLANTED SECRETS"]
        lines.append(">>> The following secrets were planted in the dataset for players to discover:\n")
        for s in self.secrets_data.get("secrets", []):
            lines.append(f"[{s['difficulty']}] {s['name']}")
            lines.append(f"  {s['description']}")
            lines.append(f"  Location: {s['found_in']}\n")
        return "\n".join(lines)

    def _answer_general(self, question, emails, sql_results) -> str:
        lines = [">>> QUERY: General Intelligence"]
        if emails:
            lines.append(f">>> Found {len(emails)} relevant emails:")
            for e in emails[:5]:
                lines.append(f"  [{e['department']}] {e['subject']} ({e['from_name']})")
        if sql_results:
            lines.append(f"\n>>> Database records: {len(sql_results)}")
            for r in sql_results[:5]:
                lines.append(f"  {r}")
        if not emails and not sql_results:
            lines.append("  No direct results found. Try being more specific, or search by:")
            lines.append("  - employee names, salaries, departments")
            lines.append("  - customer data, orders, transactions")
            lines.append("  - keywords like 'layoff', 'password', 'breach', 'complaint'")
            lines.append("  - confidential communications / secrets")
        return "\n".join(lines)

    def _llm_answer(self, question: str, context: str, llm_client, intent: str) -> str:
        system_prompt = """You are a cybersecurity investigation assistant. You have accessed a corporate dataset from NovaFi Financial Solutions.
Answer questions based ONLY on the provided context below. If the context doesn't contain the answer, say so.
Format your response like a hacker terminal - concise, factual, with a sense of discovery.
Use > prompt-style formatting. Highlight sensitive findings."""
        try:
            response = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                ],
                max_tokens=800,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception:
            return self._template_answer(question, [], [], intent)
