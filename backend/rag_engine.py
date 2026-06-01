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
            (r"(salar|payroll|compensation|wage)", "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 20"),
            (r"(highest|top|max|maximum).*salar", "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 5"),
            (r"(lowest|bottom|min|minimum).*salar", "SELECT name, position, department, salary FROM employees ORDER BY salary ASC LIMIT 5"),
            (r"average.*salar", "SELECT department, ROUND(AVG(salary), 0) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC"),
            (r"who.*(highest|most).*paid|top.*(earner|paid)", "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 10"),
            (r"(salar|pay).*(\d+)" , lambda m: f"SELECT name, position, department, salary FROM employees WHERE salary > {m.group(2)} ORDER BY salary DESC LIMIT 10"),
        ]
        exec_patterns = [
            (r"(boss|ceo|cto|cfo|chief|president|top.*exec|executive|leader|head of|in charge|who.*run|who.*lead)", 
             "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' OR position LIKE '%VP%' OR position LIKE '%Director%' ORDER BY salary DESC"),
            (r"(who.*(manager|supervisor)|list.*(manager|supervisor))",
             "SELECT name, position, department, salary FROM employees WHERE is_management = 1 ORDER BY department"),
        ]
        employee_patterns = [
            (r"(how many|count).*employee|headcount|total.*employee", "SELECT department, COUNT(*) as count FROM employees GROUP BY department ORDER BY count DESC"),
            (r"employee.*(engineer|engineering|tech|dev)", "SELECT name, position, department, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC"),
            (r"employee.*(hr|human.?resources)", "SELECT name, position, salary FROM employees WHERE department = 'Human Resources' ORDER BY name"),
            (r"employee.*(sales|marketing)", "SELECT name, position, department, salary FROM employees WHERE department IN ('Sales', 'Marketing') ORDER BY department, name"),
            (r"employee.*(executive|c.?suite|ceo|cfo|cto)", "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' ORDER BY salary DESC"),
            (r"employee.*(finance|accounting)", "SELECT name, position, salary FROM employees WHERE department = 'Finance' ORDER BY name"),
            (r"(who|which).*(manager|management|director|vp)", "SELECT name, position, department, salary FROM employees WHERE is_management = 1 ORDER BY department"),
            (r"list.*employee|all.*employee|show.*employee", "SELECT name, position, department, email FROM employees ORDER BY department, name LIMIT 30"),
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

        for patterns, target in [ (exec_patterns, "employees"), (salary_patterns, "employees"),
                                  (employee_patterns, "employees"), (customer_patterns, "customers"),
                                  (order_patterns, "orders"), (payroll_patterns, "payroll") ]:
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
        if any(w in q for w in ["boss", "ceo", "cfo", "cto", "executive", "leader", "manager", "supervisor", "head of", "in charge", "president"]):
            return "executive_query"
        if any(w in q for w in ["employee", "staff", "people", "who", "hire", "headcount", "workforce"]):
            return "employee_query"
        if any(w in q for w in ["customer", "client", "user"]):
            return "customer_query"
        if any(w in q for w in ["order", "sell", "sale", "revenue", "transaction", "purchase"]):
            return "order_query"
        if any(w in q for w in ["password", "security", "breach", "hack", "vulnerability", "exploit"]):
            return "security_query"
        if any(w in q for w in ["layoff", "fire", "terminate", "offshore", "phoenix"]):
            return "layoff_query"
        if any(w in q for w in ["affair", "relationship", "personal"]):
            return "personal_query"
        if any(w in q for w in ["email", "mail", "message", "thread", "communicat"]):
            return "email_query"
        if any(w in q for w in ["secrets", "easter egg", "hidden", "plant"]):
            return "secrets_query"
        return "general_query"

    def _template_answer(self, question: str, emails: list[dict], sql_results: list[dict], intent: str) -> str:
        intent_responses = {
            "executive_query": self._answer_executive,
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

    def _answer_executive(self, question, emails, sql_results) -> str:
        execs = [r for r in sql_results if r.get('department') == 'Executive']
        if not execs:
            from .rag_engine import DatabaseQuery
            dq = DatabaseQuery(self.db_path)
            execs = dq.query("SELECT name, position, department, salary FROM employees WHERE department = 'Executive' ORDER BY salary DESC")
        if execs:
            lines = ["Executive team at NovaFi Financial:\n"]
            ceo_name = None
            for e in execs:
                lines.append(f"  \u2022 {e['name']} — {e['position']} (${e['salary']:,})")
                if e.get('position') == 'CEO':
                    ceo_name = e['name']
            if ceo_name:
                lines.append(f"\nThe CEO is {ceo_name}.")
            return "\n".join(lines)
        return "No executive records found."

    def _answer_salary(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No salary data found."
        lines = [f"Found {len(sql_results)} salary records:\n"]
        for r in sql_results[:10]:
            name = r.get('name', r.get('department', 'Unknown'))
            pos = r.get('position', '')
            salary = r.get('salary', r.get('avg_salary', 0))
            if 'avg_salary' in r or 'department' in r and 'count' not in r:
                lines.append(f"  \u2022 {name}: ${salary:,}/yr (avg)")
            else:
                lines.append(f"  \u2022 {name} ({pos}): ${salary:,}/yr")
        return "\n".join(lines)

    def _answer_employees(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No employee records found."
        if 'count' in sql_results[0]:
            lines = ["Employee count by department:\n"]
            for r in sql_results:
                lines.append(f"  \u2022 {r['department']}: {r['count']} employees")
            return "\n".join(lines)
        lines = [f"Found {len(sql_results)} employees:\n"]
        for r in sql_results[:10]:
            lines.append(f"  \u2022 {r['name']} — {r.get('position', r.get('email', ''))}")
        return "\n".join(lines)

    def _answer_customers(self, question, emails, sql_results) -> str:
        if not sql_results:
            found_emails = [e for e in emails if any(w in (e.get('subject','') + e.get('body','')).lower()
                            for w in ['customer', 'client', 'data', 'breach', 'phish', 'account'])]
            if found_emails:
                lines = ["No direct customer database results. Relevant emails found:\n"]
                for e in found_emails[:3]:
                    lines.append(f"  \u2022 {e['subject']} ({e['from_name']})")
                return "\n".join(lines)
            return "No customer records found."
        if 'total_customers' in sql_results[0]:
            return f"Total customers in database: {sql_results[0]['total_customers']}"
        lines = [f"Found {len(sql_results)} customer records:\n"]
        for r in sql_results[:5]:
            name = r['name']
            cc = r.get('credit_card_number', '')
            masked = f"{cc[:4]} **** **** {cc[-4:]}" if len(cc) > 4 else ''
            risk = r.get('risk_score', '')
            lines.append(f"  \u2022 {name} | Card: {masked} | Risk: {risk}")
        return "\n".join(lines)

    def _answer_orders(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No order records found."
        if 'total_revenue' in sql_results[0]:
            r = sql_results[0]
            return f"Total orders: {r['total_orders']} | Total revenue: ${r['total_revenue']:,}"
        if 'revenue' in sql_results[0]:
            lines = ["Monthly revenue:\n"]
            for r in sql_results:
                lines.append(f"  \u2022 {r['month']}: ${r['revenue']:,} ({r['orders']} orders)")
            return "\n".join(lines[:6])
        lines = [f"Found {len(sql_results)} orders:\n"]
        for r in sql_results[:5]:
            lines.append(f"  \u2022 {r['customer_name']} — {r['product']} — ${r['amount']:,.0f} ({r['status']})")
        return "\n".join(lines)

    def _answer_security(self, question, emails, sql_results) -> str:
        relevant = [e for e in emails if e.get('relevance_score', 0) > 0.3]
        if relevant:
            lines = [f"Found {len(relevant)} emails related to security:\n"]
            for e in relevant[:5]:
                sens = " [CONFIDENTIAL]" if e.get('sensitivity') == "confidential" else ""
                lines.append(f"  \u2022 {e['subject']}{sens} ({e['department']})")
                if any(w in e.get('body','').lower() for w in ['password', 'credential']):
                    lines.append(f"    — Contains exposed credentials")
                if any(w in e.get('body','').lower() for w in ['breach', 'exposed', 'compromised']):
                    lines.append(f"    — Data breach related")
            return "\n".join(lines)
        return "No security-related communications found in the dataset."

    def _answer_layoffs(self, question, emails, sql_results) -> str:
        relevant = [e for e in emails if e.get('relevance_score', 0) > 0.2]
        if not relevant:
            return "No documents about layoffs or restructuring found."
        lines = [f"Found {len(relevant)} internal communications about restructuring:\n"]
        for e in relevant[:4]:
            sens = " [CONFIDENTIAL]" if e.get('sensitivity') == "confidential" else ""
            lines.append(f"  \u2022 {e['subject']}{sens}")
            lines.append(f"    From: {e['from_name']} ({e['timestamp'][:10]})")
            body_lower = e.get('body', '').lower()
            if 'phoenix' in body_lower:
                lines.append(f"    — References Project Phoenix (workforce reduction)")
            if 'offshore' in body_lower:
                lines.append(f"    — Discusses offshoring plans")
        return "\n".join(lines)

    def _answer_personal(self, question, emails, sql_results) -> str:
        relevant = [e for e in emails if e.get('sensitivity') == "confidential"]
        personal = [e for e in relevant if any(w in e.get('body', '').lower()
                    for w in ['dinner', 'paris', 'personal', 'weekend'])]
        if not personal:
            return "No personal or confidential communications found in this dataset."
        lines = [f"Found {len(personal)} confidential personal communications:\n"]
        for e in personal[:4]:
            lines.append(f"  \u2022 {e['subject']}")
            lines.append(f"    {e['from_name']} \u2192 {e['to_name']}")
            lines.append(f"    {e['body'][:200]}")
        return "\n".join(lines)

    def _answer_emails(self, question, emails, sql_results) -> str:
        if not emails:
            return "No emails matched your query."
        lines = [f"Found {len(emails)} relevant emails:\n"]
        for e in emails[:8]:
            ts = e['timestamp'][:19].replace('T', ' ')
            sens = " [CONF]" if e.get('sensitivity') == "confidential" else ""
            lines.append(f"  \u2022 {ts}{sens}")
            lines.append(f"    {e['from_name']} \u2192 {e['to_name']}")
            lines.append(f"    Subject: {e['subject']}")
        return "\n".join(lines)

    def _answer_secrets(self, question, emails, sql_results) -> str:
        lines = ["Planted secrets in the NovaFi dataset:\n"]
        for s in self.secrets_data.get("secrets", []):
            lines.append(f"  [{s['difficulty']}] {s['name']}")
            lines.append(f"    {s['description']}")
        return "\n".join(lines)

    def _answer_general(self, question, emails, sql_results) -> str:
        parts = []
        if emails:
            parts.append(f"Found {len(emails)} relevant emails in the dataset.")
            for e in emails[:3]:
                parts.append(f"  \u2022 {e['subject']} ({e['department']}, {e['from_name']})")
        if sql_results:
            parts.append(f"\n{len(sql_results)} database records found.")
            for r in sql_results[:3]:
                parts.append(f"  \u2022 {r}")
        if not parts:
            return "No results found. Try searching for: employees, salaries, customers, orders, security incidents, or specific topics like layoffs or breaches."
        return "\n".join(parts)

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
