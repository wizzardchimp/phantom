import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional
from collections import Counter

from .vector_store import VectorStore
from .llm_client import check_ollama, list_ollama_models, ask_ollama, ask_openai

DATA_DIR = Path(__file__).parent.parent / "data"

SYSTEM_PROMPT = """You are analyzing an exfiltrated corporate dataset from NovaFi Financial Solutions. 
Answer the user's question based ONLY on the retrieved context below. Be direct and concise. 
If the context doesn't contain the answer, say so. Never make up information.

Format your answer as a brief summary (2-4 sentences). If listing items, use bullet points.
Highlight anything marked [CONFIDENTIAL] as it's a sensitive finding."""


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

    def infer_sql(self, question: str) -> Optional[str]:
        q = question.lower()
        patterns = [
            (r"(boss|ceo|cto|cfo|chief|president|executive|leader|head of|in charge|who.*run|who.*lead)",
             "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' OR position LIKE '%VP%' OR position LIKE '%Director%' ORDER BY salary DESC"),
            (r"(salar|payroll|compensation|wage)",
             "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 20"),
            (r"(highest|top|max|maximum).*salar",
             "SELECT name, position, department, salary FROM employees ORDER BY salary DESC LIMIT 5"),
            (r"(lowest|bottom|min|minimum).*salar",
             "SELECT name, position, department, salary FROM employees ORDER BY salary ASC LIMIT 5"),
            (r"average.*salar",
             "SELECT department, ROUND(AVG(salary), 0) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC"),
            (r"(how many|count).*employee|headcount|total.*employee",
             "SELECT department, COUNT(*) as count FROM employees GROUP BY department ORDER BY count DESC"),
            (r"employee.*(engineer|engineering|tech|dev)",
             "SELECT name, position, department, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC"),
            (r"employee.*(hr|human.?resources)",
             "SELECT name, position, salary FROM employees WHERE department = 'Human Resources' ORDER BY name"),
            (r"employee.*(sales|marketing)",
             "SELECT name, position, department, salary FROM employees WHERE department IN ('Sales', 'Marketing') ORDER BY department, name"),
            (r"employee.*(executive|c.?suite|ceo|cfo|cto)",
             "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' ORDER BY salary DESC"),
            (r"employee.*(finance|accounting)",
             "SELECT name, position, salary FROM employees WHERE department = 'Finance' ORDER BY name"),
            (r"(who|which).*(manager|management|director|vp)",
             "SELECT name, position, department, salary FROM employees WHERE is_management = 1 ORDER BY department"),
            (r"list.*employee|all.*employee|show.*employee",
             "SELECT name, position, department, email FROM employees ORDER BY department, name LIMIT 30"),
            (r"(how many|count).*customer",
             "SELECT COUNT(*) as total_customers FROM customers"),
            (r"(high.?risk|risk.*score).*customer",
             "SELECT name, email, risk_score FROM customers WHERE risk_score > 75 ORDER BY risk_score DESC LIMIT 10"),
            (r"customer.*(card|credit|payment)",
             "SELECT name, credit_card_type, credit_card_number FROM customers LIMIT 10"),
            (r"list.*customer|all.*customer",
             "SELECT name, email, account_created FROM customers ORDER BY account_created DESC LIMIT 20"),
            (r"(how many|total|count).*order",
             "SELECT COUNT(*) as total_orders, ROUND(SUM(amount), 0) as total_revenue FROM orders"),
            (r"(highest|top|largest).*order",
             "SELECT customer_name, product, amount, status FROM orders ORDER BY amount DESC LIMIT 10"),
            (r"(pending|processing).*order",
             "SELECT customer_name, product, amount, status FROM orders WHERE status IN ('pending', 'processing') ORDER BY amount DESC LIMIT 10"),
            (r"order.*(refund|disputed|dispute)",
             "SELECT customer_name, product, amount, status FROM orders WHERE status IN ('refunded', 'disputed') LIMIT 10"),
            (r"revenue|total.*amount|sales",
             "SELECT STRFTIME('%Y-%m', created_at) as month, COUNT(*) as orders, ROUND(SUM(amount), 0) as revenue FROM orders GROUP BY month ORDER BY month DESC LIMIT 12"),
            (r"(payroll|total.*payroll|salary.*cost)",
             "SELECT ROUND(SUM(salary), 0) as total_annual_payroll FROM employees"),
            (r"(bonus|bonuses)",
             "SELECT employee_name, bonuses, pay_period_start FROM payroll WHERE bonuses > 0 ORDER BY bonuses DESC LIMIT 10"),
        ]
        for pattern, sql in patterns:
            if re.search(pattern, q):
                return sql
        return None


class RAGEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "novafi.db")
        self.vector_store = VectorStore(db_path=self.db_path)
        self.db_query = DatabaseQuery(self.db_path)
        self.llm_mode = None
        self.llm_model = None
        self._init_llm()

        secrets_path = DATA_DIR / "secrets.json"
        if secrets_path.exists():
            with open(secrets_path) as f:
                self.secrets_data = json.load(f)
        else:
            self.secrets_data = {"secrets": []}

        try:
            self.vector_store.ensure_embeddings()
        except Exception:
            pass

    def _init_llm(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.llm_mode = "openai"
            self.llm_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return
        if check_ollama():
            models = list_ollama_models()
            preferred = ["llama3.2:3b", "llama3.2", "llama3", "mistral", "phi3", "phi"]
            for p in preferred:
                if p in models:
                    self.llm_mode = "ollama"
                    self.llm_model = p
                    return
            if models:
                self.llm_mode = "ollama"
                self.llm_model = models[0]

    def query(self, question: str) -> dict:
        try:
            q = question.lower()
            emails = self.vector_store.search(question, top_k=15)
            sql = self.db_query.infer_sql(question)
            sql_results = self.db_query.query(sql) if sql else []
            intent = self._classify_intent(q)

            if self.llm_mode and intent not in ("salary_query", "employee_query", "customer_query", "order_query"):
                response = self._llm_summary(question, emails, sql_results, intent)
            else:
                response = self._smart_template(question, emails, sql_results, intent)

            return {
                "query": question,
                "intent": intent,
                "response": response,
                "emails_found": len(emails),
                "records_found": len(sql_results),
                "llm_used": self.llm_mode is not None and intent not in ("salary_query", "employee_query", "customer_query", "order_query"),
            }
        except Exception as exc:
            return {
                "query": question,
                "intent": "error",
                "response": f"[Error] Could not process query: {exc}",
                "emails_found": 0,
                "records_found": 0,
                "llm_used": False,
            }

    def _classify_intent(self, q: str) -> str:
        if any(w in q for w in ["boss", "ceo", "cfo", "cto", "executive", "leader", "manager", "supervisor", "head of", "in charge", "president"]):
            return "executive_query"
        if any(w in q for w in ["salar", "pay", "compensation", "bonus", "payroll", "earn"]):
            return "salary_query"
        if any(w in q for w in ["employee", "staff", "people", "hire", "headcount", "workforce", "who work"]):
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
        if any(w in q for w in ["hiding", "secret", "cover", "controversial", "scandal"]):
            return "hiding_query"
        if any(w in q for w in ["email", "mail", "message", "thread", "communicat"]):
            return "email_query"
        if any(w in q for w in ["secrets", "easter egg", "hidden", "plant"]):
            return "secrets_query"
        if any(w in q for w in ["trouble", "problem", "issue", "conflict", "dispute", "complaint", "warning", "risk"]):
            return "trouble_query"
        return "general_query"

    def _llm_summary(self, question: str, emails: list[dict], sql_results: list[dict], intent: str) -> str:
        context_parts = []

        if emails:
            email_block = "RELEVANT EMAILS:\n"
            for i, e in enumerate(emails[:8], 1):
                tag = "[CONFIDENTIAL]" if e.get("sensitivity") == "confidential" else ""
                email_block += f"{i}. {tag} From: {e['from_name']} ({e['department']}) → To: {e['to_name']}\n"
                email_block += f"   Subject: {e['subject']}\n"
                email_block += f"   Body: {e['body'][:500]}\n\n"
            context_parts.append(email_block)

        if sql_results:
            context_parts.append(f"DATABASE RECORDS ({len(sql_results)}):\n" + json.dumps(sql_results[:5], indent=2))

        if not emails and not sql_results:
            return "No relevant data found for that question."

        context = "\n".join(context_parts)

        if self.llm_mode == "ollama":
            result = ask_ollama(question, system=SYSTEM_PROMPT, prompt=f"Context:\n{context}")
        elif self.llm_mode == "openai":
            result = ask_openai(question, system=SYSTEM_PROMPT, prompt=f"Context:\n{context}",
                                api_key=os.getenv("OPENAI_API_KEY", ""))
        else:
            return self._smart_template(question, emails, sql_results, intent)

        result = (result or "").strip()
        if result:
            return result
        return self._smart_template(question, emails, sql_results, intent)

    def _smart_template(self, question: str, emails: list[dict], sql_results: list[dict], intent: str) -> str:
        handlers = {
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
            "hiding_query": self._answer_hiding,
            "trouble_query": self._answer_trouble,
            "general_query": self._answer_general,
        }
        h = handlers.get(intent, self._answer_general)
        return h(question, emails, sql_results)

    # --- Structured answers for SQL-backed queries ---

    def _answer_executive(self, question, emails, sql_results) -> str:
        execs = [r for r in sql_results if r.get('department') == 'Executive']
        if not execs:
            execs = self.db_query.query(
                "SELECT name, position, department, salary FROM employees WHERE department = 'Executive' ORDER BY salary DESC"
            )
        if execs:
            lines = ["Executive team at NovaFi Financial:"]
            ceo = None
            for e in execs:
                lines.append(f"  \u2022 {e['name']} — {e['position']} (${e['salary']:,})")
                if e.get('position') == 'CEO':
                    ceo = e['name']
            if ceo:
                lines.append(f"\nThe CEO is {ceo}.")
            return "\n".join(lines)
        return "No executive records found."

    def _answer_salary(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No salary data found."
        lines = [f"Found {len(sql_results)} salary records:"]
        for r in sql_results[:10]:
            name = r.get('name', r.get('department', 'Unknown'))
            pos = r.get('position', '')
            salary = r.get('salary', r.get('avg_salary', 0))
            if 'avg_salary' in r:
                lines.append(f"  \u2022 {name}: ${salary:,}/yr (avg)")
            else:
                lines.append(f"  \u2022 {name} ({pos}): ${salary:,}/yr")
        return "\n".join(lines)

    def _answer_employees(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No employee records found."
        if 'count' in sql_results[0]:
            return "\n".join([f"  \u2022 {r['department']}: {r['count']} employees" for r in sql_results])
        lines = [f"Found {len(sql_results)} employees:"]
        for r in sql_results[:10]:
            lines.append(f"  \u2022 {r.get('name', '?')} — {r.get('position', r.get('email', ''))}")
        return "\n".join(lines)

    def _answer_customers(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No customer records found."
        if 'total_customers' in sql_results[0]:
            return f"Total customers: {sql_results[0]['total_customers']}"
        lines = [f"Found {len(sql_results)} customers:"]
        for r in sql_results[:5]:
            cc = r.get('credit_card_number', '')
            masked = f"{cc[:4]} **** **** {cc[-4:]}" if len(cc) > 4 else ''
            lines.append(f"  \u2022 {r['name']} | {masked} | Risk: {r.get('risk_score', 'N/A')}")
        return "\n".join(lines)

    def _answer_orders(self, question, emails, sql_results) -> str:
        if not sql_results:
            return "No order records found."
        if 'total_revenue' in sql_results[0]:
            r = sql_results[0]
            return f"Total orders: {r['total_orders']} | Total revenue: ${r['total_revenue']:,}"
        if 'revenue' in sql_results[0]:
            lines = ["Monthly revenue:"]
            for r in sql_results:
                lines.append(f"  \u2022 {r['month']}: ${r['revenue']:,} ({r['orders']} orders)")
            return "\n".join(lines[:6])
        lines = [f"Found {len(sql_results)} orders:"]
        for r in sql_results[:5]:
            lines.append(f"  \u2022 {r['customer_name']} — {r['product']} — ${r['amount']:,.0f}")
        return "\n".join(lines)

    # --- Semantic answers for natural language questions ---

    def _answer_security(self, question, emails, sql_results) -> str:
        if not emails:
            return "No security-related communications found."
        lines = [f"Found {len(emails)} relevant emails about security:"]
        for e in emails[:5]:
            tag = " [CONF]" if e.get('sensitivity') == "confidential" else ""
            lines.append(f"  \u2022 {e['subject']}{tag}")
            body = e.get('body', '').lower()
            if 'breach' in body or 'exposed' in body:
                lines.append(f"    \u2192 Data exposure incident")
            if 'password' in body or 'credential' in body:
                lines.append(f"    \u2192 Credential leak")
        return "\n".join(lines)

    def _answer_layoffs(self, question, emails, sql_results) -> str:
        if not emails:
            return "No communications about layoffs or restructuring found."
        lines = [f"Found {len(emails)} internal communications about restructuring:"]
        for e in emails[:4]:
            tag = " [CONF]" if e.get('sensitivity') == "confidential" else ""
            lines.append(f"  \u2022 {e['subject']}{tag}")
            body = e.get('body', '').lower()
            if 'phoenix' in body:
                lines.append(f"    \u2192 References Project Phoenix (workforce reduction)")
            if 'offshore' in body:
                lines.append(f"    \u2192 Discusses offshoring")
            if 'layoff' in body or 'reduction' in body:
                lines.append(f"    \u2192 Layoff related")
        return "\n".join(lines)

    def _answer_personal(self, question, emails, sql_results) -> str:
        personal = [e for e in emails if e.get('sensitivity') == 'confidential' and
                    any(w in e.get('body', '').lower() for w in ['dinner', 'paris', 'weekend', 'personal'])]
        if not personal:
            return "No personal or confidential communications found."
        lines = [f"Found {len(personal)} confidential personal communications:"]
        for e in personal[:4]:
            lines.append(f"  \u2022 {e['subject']}")
            lines.append(f"    {e['from_name']} \u2192 {e['to_name']}")
        return "\n".join(lines)

    def _answer_emails(self, question, emails, sql_results) -> str:
        if not emails:
            return "No emails matched your query."
        lines = [f"Found {len(emails)} relevant emails:"]
        for e in emails[:8]:
            tag = " [CONF]" if e.get('sensitivity') == "confidential" else ""
            lines.append(f"  \u2022 {e['subject']}{tag}")
            lines.append(f"    {e['from_name']} \u2192 {e['to_name']} ({e['department']})")
        return "\n".join(lines)

    def _answer_secrets(self, question, emails, sql_results) -> str:
        lines = ["Planted secrets in the NovaFi dataset:"]
        for s in self.secrets_data.get("secrets", []):
            lines.append(f"  [{s['difficulty']}] {s['name']}")
            lines.append(f"    {s['description']}")
        return "\n".join(lines)

    def _answer_hiding(self, question, emails, sql_results) -> str:
        confidential = [e for e in emails if e.get('sensitivity') == 'confidential']
        if not emails:
            return "No evidence found of the company hiding anything."
        lines = [f"Analysis of {len(emails)} relevant communications. Key findings:"]
        confidential = [e for e in emails if e.get('sensitivity') == 'confidential']
        if confidential:
            lines.append(f"\n  \u2022 {len(confidential)} confidential emails found. Topics include:")
            topics = set()
            for e in confidential[:5]:
                topics.add(e['subject'])
            for t in list(topics)[:4]:
                lines.append(f"    — {t}")
        breach_emails = [e for e in emails if 'breach' in e.get('body', '').lower() or 'exposed' in e.get('body', '').lower()]
        if breach_emails:
            lines.append(f"\n  \u2022 {len(breach_emails)} emails discuss a data breach or data exposure")
        layoff_emails = [e for e in emails if any(w in e.get('body', '').lower() for w in ['layoff', 'phoenix', 'offshore', 'reduction'])]
        if layoff_emails:
            lines.append(f"  \u2022 {len(layoff_emails)} emails reference layoffs, offshoring, or restructuring")
        personal = [e for e in emails if 'dinner' in e.get('body', '').lower() or 'paris' in e.get('body', '').lower()]
        if personal:
            lines.append(f"  \u2022 Personal relationship detected between executive and HR (confidential)")
        return "\n".join(lines)

    def _answer_trouble(self, question, emails, sql_results) -> str:
        if not emails:
            return "No signs of trouble found in the dataset."
        lines = [f"Scanned {len(emails)} relevant communications for signs of trouble:"]
        complaint = [e for e in emails if 'complaint' in e.get('body', '').lower() or 'discrimination' in e.get('body', '').lower()]
        if complaint:
            lines.append(f"\n  \u2022 Formal complaint: {complaint[0]['subject']}")
        breach = [e for e in emails if 'breach' in e.get('body', '').lower()]
        if breach:
            lines.append(f"  \u2022 Security incident: {breach[0]['subject']}")
        layoff = [e for e in emails if any(w in e.get('body', '').lower() for w in ['layoff', 'phoenix', 'reduction'])]
        if layoff:
            lines.append(f"  \u2022 Restructuring: {layoff[0]['subject']}")
        dispute = [e for e in emails if 'dispute' in e.get('body', '').lower() or 'unauthorized' in e.get('body', '').lower()]
        if dispute:
            lines.append(f"  \u2022 Customer dispute: {dispute[0]['subject']}")
        if not complaint and not breach and not layoff and not dispute:
            from collections import Counter
            depts = Counter(e.get('department', 'Unknown') for e in emails)
            top_dept = depts.most_common(1)
            if top_dept:
                lines.append(f"\n  No specific trouble found. Most activity in: {top_dept[0][0]}")
        return "\n".join(lines)

    def _answer_general(self, question, emails, sql_results) -> str:
        parts = []
        if emails:
            parts.append(f"Found {len(emails)} relevant emails.")
            for e in emails[:3]:
                tag = " [CONF]" if e.get('sensitivity') == "confidential" else ""
                parts.append(f"  \u2022 {e['subject']}{tag} ({e['department']})")
        if sql_results:
            parts.append(f"\n{len(sql_results)} database records found.")
            for r in sql_results[:3]:
                parts.append(f"  \u2022 {r}")
        if not parts:
            return "No results found. Try asking about: employees, salaries, customers, orders, security incidents, layoffs, or confidential communications."
        return "\n".join(parts)
