import random
from datetime import datetime, timedelta
from typing import Optional
from .models import Employee, Customer, Email


class EmailGenerator:
    def __init__(self, employees: list[Employee], customers: list[Customer]):
        self.employees = employees
        self.customers = customers
        self.email_id = 1
        self.thread_id = 1
        self.emails: list[Email] = []
        self._base_time = datetime(2024, 9, 1, 8, 0, 0)
        self._depts = self._group_by_dept()

    def _group_by_dept(self) -> dict[str, list[Employee]]:
        d = {}
        for e in self.employees:
            d.setdefault(e.department, []).append(e)
        return d

    def _pick(self, dept: str) -> Employee:
        return random.choice(self._depts[dept])

    def _pick_mgmt(self, dept: str) -> Employee:
        mgrs = [e for e in self._depts[dept] if e.is_management]
        return random.choice(mgrs) if mgrs else self._pick(dept)

    def _pick_customer(self) -> Customer:
        return random.choice(self.customers)

    def _ts(self, offset_hours: float) -> str:
        t = self._base_time + timedelta(hours=offset_hours)
        return t.isoformat()

    def _make_email(self, from_addr: str, from_name: str, to_addr: str,
                    to_name: str, subject: str, body: str, offset_hours: float,
                    department: str, is_internal: bool = True,
                    cc: str = "", sensitivity: str = "normal") -> Email:
        e = Email(
            id=self.email_id,
            thread_id=self.thread_id,
            from_addr=from_addr,
            from_name=from_name,
            to_addr=to_addr,
            to_name=to_name,
            cc=cc,
            subject=subject,
            body=body,
            timestamp=self._ts(offset_hours),
            department=department,
            is_internal=is_internal,
            sensitivity=sensitivity,
        )
        self.email_id += 1
        return e

    def _thread_customer_order(self) -> list[Email]:
        c = self._pick_customer()
        s = self._pick("Sales")
        sup = self._pick("Customer Support")
        ops = self._pick("Operations")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(0, 48)
        items = ["Premium Checking Account Setup", "Business Credit Line - $50k",
                 "Investment Portfolio Review", "International Wire Transfer",
                 "High-Yield Savings Account", "Mortgage Pre-Approval",
                 "Retirement Fund Rollover", "Corporate Expense Account"]
        product = random.choice(items)
        amount = random.choice([5000, 10000, 25000, 50000, 100000, 250000])
        emails = []

        emails.append(self._make_email(
            c.email, c.name, s.email, s.name,
            f"New Order Inquiry: {product}",
            f"Hello,\n\nI was referred to NovaFi by a colleague and I'm interested in opening a {product.lower()} with you. "
            f"Could you please send me the application forms and fee schedule? I'm looking to move approximately ${amount:,} into this account.\n\n"
            f"I'd like to understand the processing times and any documentation requirements.\n\n"
            f"Thank you,\n{c.name}\n{c.phone}",
            base, "Sales", is_internal=False
        ))

        emails.append(self._make_email(
            s.email, s.name, c.email, c.name,
            f"Re: New Order Inquiry: {product}",
            f"Dear {c.name.split()[0]},\n\nThank you for reaching out! I'd be happy to help you get started with our {product.lower()}.\n\n"
            f"Here's what you'll need:\n"
            f"1. Completed application form (attached)\n"
            f"2. Government-issued ID\n"
            f"3. Proof of address (utility bill or bank statement)\n"
            f"4. Initial deposit of ${amount:,}\n\n"
            f"Processing typically takes 3-5 business days once all documents are received. "
            f"I've copied our support team who can assist with any questions.\n\n"
            f"Best regards,\n{s.name}\n{s.position}\nNovaFi Financial",
            base + 1.5, "Sales", is_internal=False, cc=sup.email
        ))

        emails.append(self._make_email(
            c.email, c.name, s.email, s.name,
            f"Re: New Order Inquiry: {product}",
            f"Thanks {s.name.split()[0]}, I've attached the completed forms. Quick question - is there any way to expedite the processing? "
            f"I'm hoping to have this active within 2 weeks.\n\n"
            f"Also, do you offer any promotional rates for new accounts of this size?\n\n"
            f"Best,\n{c.name}",
            base + 24, "Sales", is_internal=False
        ))

        emails.append(self._make_email(
            s.email, s.name, ops.email, ops.name,
            f"New account setup - {c.name} - {product}",
            f"Hi {ops.name.split()[0]},\n\nWe have a new account application for {product} from {c.name} ({c.email}). "
            f"Amount: ${amount:,}. They're requesting expedited processing if possible.\n\n"
            f"Can you get this queued up? I've attached the documentation.\n\n"
            f"Thanks,\n{s.name}",
            base + 25, "Operations"
        ))

        emails.append(self._make_email(
            ops.email, ops.name, s.email, s.name,
            f"Re: New account setup - {c.name} - {product}",
            f"Got it {s.name.split()[0]}. I'll prioritize this. We can have it done in 2 business days if we rush it. "
            f"Standard fee applies unless management approves a waiver.\n\n"
            f"The customer's credit check came back clean - risk score looks good.\n\n"
            f"- {ops.name.split()[0]}",
            base + 26, "Operations"
        ))

        emails.append(self._make_email(
            s.email, s.name, c.email, c.name,
            f"Re: New Order Inquiry: {product} - Approved!",
            f"Great news {c.name.split()[0]}! Your application has been pre-approved. We're expediting the setup and should have "
            f"everything ready within 2 business days.\n\n"
            f"Your account representative will be {ops.name} who will handle the final onboarding. "
            f"They'll reach out with your account details and next steps.\n\n"
            f"Welcome to NovaFi!\n\nBest,\n{s.name}",
            base + 48, "Sales", is_internal=False
        ))

        emails.append(self._make_email(
            ops.email, ops.name, c.email, c.name,
            f"Welcome to NovaFi - Account #{random.randint(10000,99999)}",
            f"Dear {c.name},\n\nWelcome to NovaFi Financial Solutions! Your {product.lower()} is now active.\n\n"
            f"Account Number: {random.randint(100000, 999999)}-{random.randint(1000, 9999)}\n"
            f"Initial Deposit: ${amount:,}\n"
            f"Status: Active\n\n"
            f"Please log in to your online portal at https://portal.novafi.com to set up your preferences and beneficiaries.\n\n"
            f"If you have any questions, your account manager {s.name} is available at {s.email}.\n\n"
            f"Best regards,\n{ops.name}\nOperations Department\nNovaFi Financial",
            base + 72, "Operations", is_internal=False
        ))

        return emails

    def _thread_support_issue(self) -> list[Email]:
        c = self._pick_customer()
        agent = self._pick("Customer Support")
        mgr = self._pick_mgmt("Customer Support")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(0, 200)
        issues = [
            ("Unauthorized transaction on my account",
             f"I'm seeing a charge of ${random.randint(100, 5000)}.00 that I did not authorize on my account ending in {c.credit_card_number[-4:]}. "
             f"This happened on {(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 24)).strftime('%B %d')}. I need this reversed immediately."),
            ("Cannot access online banking",
             "I've been locked out of my online banking portal after 3 login attempts. I'm sure my password is correct. Please reset my access."),
            ("Dispute recurring charge",
             f"There's a recurring charge of ${random.randint(20, 200)}.99/month that I never signed up for. It's been going on for 3 months. I want all charges refunded."),
            ("Lost card - need replacement",
             f"I lost my wallet yesterday. My NovaFi debit card ending in {c.credit_card_number[-4:]} needs to be cancelled and replaced immediately."),
        ]
        issue, desc = random.choice(issues)

        emails = []
        emails.append(self._make_email(
            c.email, c.name, agent.email, agent.name,
            f"Support Request: {issue}",
            f"Dear Support Team,\n\n{desc}\n\n"
            f"My account number is {random.randint(100000, 999999)}.\n"
            f"Please confirm receipt and let me know the next steps.\n\n"
            f"Thank you,\n{c.name}",
            base, "Customer Support", is_internal=False
        ))

        emails.append(self._make_email(
            agent.email, agent.name, c.email, c.name,
            f"Re: Support Request: {issue}",
            f"Dear {c.name.split()[0]},\n\nThank you for contacting NovaFi support. I've received your request and I'm looking into it.\n\n"
            f"Ticket #{random.randint(50000, 99999)} has been created. I'll investigate and get back to you within 24 hours.\n\n"
            f"For security purposes, can you confirm your full date of birth and the last 4 digits of your SSN?\n\n"
            f"Best,\n{agent.name}\nSenior Support Agent",
            base + 1, "Customer Support", is_internal=False
        ))

        emails.append(self._make_email(
            c.email, c.name, agent.email, agent.name,
            f"Re: Support Request: {issue}",
            f"Hi {agent.name.split()[0]},\n\nMy DOB is {c.dob}. SSN last 4: {c.ssn[-4:]}.\n\n"
            f"Please resolve this quickly - I'm very concerned about my account security.\n\n"
            f"Thanks,\n{c.name}",
            base + 3, "Customer Support", is_internal=False
        ))

        emails.append(self._make_email(
            agent.email, agent.name, mgr.email, mgr.name,
            f"Escalation: {issue} - {c.name}",
            f"Hi {mgr.name.split()[0]},\n\nCustomer {c.name} ({c.email}) is reporting: {issue.lower()}. "
            f"I've verified their identity. This looks legitimate - we need to process a chargeback/refund in the amount requested.\n\n"
            f"Customer is escalating due to urgency. Can you authorize the refund so I can process it?\n\n"
            f"Thanks,\n{agent.name}",
            base + 4, "Customer Support"
        ))

        emails.append(self._make_email(
            mgr.email, mgr.name, agent.email, agent.name,
            f"Re: Escalation: {issue} - {c.name}",
            f"Approved. Process the refund and add a note to the customer's account. "
            f"Also flag this for review in case there's a pattern with their account.\n\n"
            f"Let me know if you need anything else.\n\n"
            f"- {mgr.name.split()[0]}",
            base + 5, "Customer Support"
        ))

        emails.append(self._make_email(
            agent.email, agent.name, c.email, c.name,
            f"Re: Support Request: {issue} - RESOLVED",
            f"Dear {c.name.split()[0]},\n\nYour issue has been resolved. The {issue.lower()} has been processed and "
            f"you should see the adjustment in your account within 24-48 hours.\n\n"
            f"Refund Amount: ${random.randint(100, 5000)}.00\n"
            f"Case #{random.randint(50000, 99999)}\n\n"
            f"We've also added a security alert to your account. If you see any other suspicious activity, please contact us immediately.\n\n"
            f"Thank you for your patience,\n{agent.name}\nNovaFi Support",
            base + 24, "Customer Support", is_internal=False
        ))

        return emails

    def _thread_payroll_issue(self) -> list[Email]:
        emp = self._pick("Engineering")
        hr = self._pick("Human Resources")
        pay = self._pick_mgmt("Finance") if random.random() < 0.5 else self._pick("Finance")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(50, 350)

        emails = []
        emails.append(self._make_email(
            emp.email, emp.name, hr.email, hr.name,
            "Payroll discrepancy - missing overtime",
            f"Hi {hr.name.split()[0]},\n\nI noticed my last paycheck (period ending "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 72)).strftime('%B %d')}) "
            f"is missing overtime hours I worked during the system migration week. I logged approximately 18 hours of overtime "
            f"that were approved by my manager.\n\nCan you check on this and initiate a correction?\n\n"
            f"Thanks,\n{emp.name}",
            base, "Human Resources"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Payroll discrepancy - missing overtime",
            f"Hi {emp.name.split()[0]},\n\nThanks for flagging this. Let me look into the time sheets from that period and get back to you. "
            f"Can you forward me the approval email from your manager?\n\n"
            f"Best,\n{hr.name}",
            base + 2, "Human Resources"
        ))

        emails.append(self._make_email(
            emp.email, emp.name, hr.email, hr.name,
            "Re: Payroll discrepancy - missing overtime",
            f"Sure, forwarding the approval thread now. It was from {emp.manager_id or 'my manager'} on "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 96)).strftime('%B %d')}.\n\n"
            f"Let me know if you need anything else.\n\n"
            f"- {emp.name.split()[0]}",
            base + 3, "Human Resources"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, pay.email, pay.name,
            "Payroll correction needed - overtime",
            f"Hi {pay.name.split()[0]},\n\nWe need a payroll adjustment for {emp.name} ({emp.email}). "
            f"18 hours of overtime not included in last cycle. Rate: ${emp.salary // 2080 * 2:.0f}/hr OT.\n\n"
            f"Total owed: ~${18 * (emp.salary // 2080 * 2):,}. Can you process this for the next off-cycle run?\n\n"
            f"Thanks,\n{hr.name}",
            base + 6, "Human Resources"
        ))

        emails.append(self._make_email(
            pay.email, pay.name, hr.email, hr.name,
            "Re: Payroll correction needed - overtime",
            f"Got it {hr.name.split()[0]}. I'll process this in the next correction run on Friday. "
            f"Make sure we have the manager approval documented for audit trail.\n\n"
            f"- {pay.name.split()[0]}",
            base + 8, "Finance"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Payroll discrepancy - RESOLVED",
            f"Hi {emp.name.split()[0]},\n\nGood news - the correction has been approved. You'll see the overtime payment "
            f"of ${18 * (emp.salary // 2080 * 2):,} in Friday's off-cycle run.\n\n"
            f"Sorry for the oversight. Let me know if you need anything else.\n\n"
            f"Best,\n{hr.name}",
            base + 24, "Human Resources"
        ))

        return emails

    def _thread_hr_layoff_rumors(self) -> list[Email]:
        hr1 = self._pick("Human Resources")
        hr2 = self._pick_mgmt("Human Resources")
        exec_ = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(300, 500)

        emails = []
        emails.append(self._make_email(
            exec_.email, exec_.name, hr2.email, hr2.name,
            "CONFIDENTIAL: Project Phoenix - Workforce Reduction",
            f"{hr2.name.split()[0]},\n\nThis is highly confidential. The board has approved a restructuring initiative "
            f"(codenamed Project Phoenix) targeting a 15% workforce reduction across all departments. "
            f"We need to move quickly but quietly.\n\n"
            f"I need you to prepare:\n"
            f"1. Department-by-department headcount analysis\n"
            f"2. Severance packages at three tiers (executive, management, staff)\n"
            f"3. Timeline proposal for Q1 2025 implementation\n"
            f"4. Legal risk assessment\n\n"
            f"This cannot leak. Not even to your team yet. I need initial analysis by Friday.\n\n"
            f"- {exec_.name.split()[0]}",
            base, "Executive", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            hr2.email, hr2.name, exec_.email, exec_.name,
            "Re: CONFIDENTIAL: Project Phoenix - Workforce Reduction",
            f"Understood. I'll work on this personally over the weekend. A few initial thoughts:\n\n"
            f"- Customer Support and Operations will likely take the biggest hits (offshoring potential)\n"
            f"- Engineering is already lean - cuts there could impact delivery\n"
            f"- Legal will flag WARN Act implications at this scale\n\n"
            f"I'll have the analysis ready by Wednesday EOD.\n\n"
            f"- {hr2.name.split()[0]}",
            base + 2, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            hr2.email, hr2.name, hr1.email, hr1.name,
            "URGENT: Need headcount reports - no details yet",
            f"Hi {hr1.name.split()[0]},\n\nI need a comprehensive headcount report by end of day, broken down by: "
            f"department, role, tenure, salary band, and location. This is for an executive planning matter.\n\n"
            f"I can't share details yet, but please prioritize this over everything else."
            f"Export from the HR system and send it to me directly. No discussion with other team members.\n\n"
            f"Thanks,\n{hr2.name.split()[0]}",
            base + 3, "Human Resources"
        ))

        emails.append(self._make_email(
            hr1.email, hr1.name, hr2.email, hr2.name,
            "Re: URGENT: Need headcount reports - no details yet",
            f"Done. Sending the report now. Everything looks clean from the system.\n\n"
            f"Is everything okay? Getting a bit of a vibe from people that something might be going on.\n\n"
            f"- {hr1.name.split()[0]}",
            base + 5, "Human Resources"
        ))

        emails.append(self._make_email(
            hr2.email, hr2.name, hr1.email, hr1.name,
            "Re: URGENT: Need headcount reports - no details yet",
            f"Nothing to worry about, just routine planning. Please keep this between us for now.\n\n"
            f"- {hr2.name.split()[0]}",
            base + 6, "Human Resources"
        ))

        return emails

    def _thread_security_incident(self) -> list[Email]:
        eng = self._pick("Engineering")
        ciso = self._pick_mgmt("Executive")
        legal = self._pick("Legal")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(200, 400)

        emails = []
        emails.append(self._make_email(
            eng.email, eng.name, ciso.email, ciso.name,
            "URGENT: Possible data breach detected - customer database",
            f"{ciso.name.split()[0]},\n\nOur monitoring system flagged unusual query patterns on the customer database "
            f"starting around 2:30 AM this morning. Someone exported approximately 15,000 customer records including names, "
            f"SSNs, credit card numbers, and addresses.\n\n"
            f"The query came from an internal IP but the account used was {random.choice(['svc_backup', 'admin_jjohnson', 'readonly_user'])} "
            f"which shouldn't have that level of access.\n\n"
            f"I've isolated the database server and started a log review. What's the protocol here?\n\n"
            f"- {eng.name}",
            base, "Engineering"
        ))

        emails.append(self._make_email(
            ciso.email, ciso.name, eng.email, eng.name,
            "Re: URGENT: Possible data breach detected - customer database",
            f"Lock it down. Change all database credentials immediately. Preserve the logs.\n\n"
            f"I'm looping in Legal. Do NOT discuss this with anyone outside this thread. "
            f"I want a full incident report within 4 hours.\n\n"
            f"Also - check if there's any sign of data exfiltration (large outbound transfers, unusual API calls).\n\n"
            f"- {ciso.name.split()[0]}",
            base + 0.5, "Executive"
        ))

        emails.append(self._make_email(
            ciso.email, ciso.name, legal.email, legal.name,
            "SECURITY INCIDENT - potential breach - legal notification assessment needed",
            f"{legal.name.split()[0]},\n\nWe've detected what looks like a data breach on our customer database. "
            f"Approximately 15,000 records potentially exposed (PII + financial data). This is active and under investigation.\n\n"
            f"I need to know:\n"
            f"1. Mandatory notification timeline (regulators, customers)\n"
            f"2. CCPA/GDPR implications\n"
            f"3. Do we notify law enforcement?\n"
            f"4. Crisis comms prep\n\n"
            f"Time is critical here. Please respond ASAP.\n\n"
            f"- {ciso.name.split()[0]}",
            base + 1, "Executive"
        ))

        emails.append(self._make_email(
            legal.email, legal.name, ciso.email, ciso.name,
            "Re: SECURITY INCIDENT - potential breach - legal notification assessment needed",
            f"{ciso.name.split()[0]},\n\nThis is serious. Under CCPA, if confirmed, we have 30 days to remediate before civil penalties apply. "
            f"If cardholder data is involved, PCI DSS reporting requirements kick in within 24 hours of confirmation.\n\n"
            f"We may also have SEC disclosure obligations if this is material.\n\n"
            f"I'll prepare a breach notification template and start the regulatory contacts list. "
            f"Keep me updated on the investigation. Do NOT notify anyone externally until we have confirmed scope.\n\n"
            f"- {legal.name.split()[0]}",
            base + 2, "Legal"
        ))

        emails.append(self._make_email(
            eng.email, eng.name, ciso.email, ciso.name,
            "Re: URGENT: Possible data breach detected - update",
            f"Update: The query originated from a compromised developer workstation. Looks like someone got access via "
            f"a leaked API key that was hardcoded in a GitHub repository. The key had database read access.\n\n"
            f"I've:\n"
            f"- Rotated all database credentials\n"
            f"- Revoked the compromised API key\n"
            f"- Blocked the source IP\n"
            f"- Initiated forensic disk capture on the affected workstation\n\n"
            f"Still assessing whether data was actually exfiltrated. No evidence of large outbound transfers yet.\n\n"
            f"- {eng.name}",
            base + 4, "Engineering"
        ))

        emails.append(self._make_email(
            ciso.email, ciso.name, eng.email, eng.name,
            "Re: URGENT: SECURITY INCIDENT - hold for investigation",
            f"Good work. Keep the investigation going. Do NOT patch anything yet - we need the forensic state preserved.\n\n"
            f"I'm going to brief the CEO. For now this stays within this thread. No chatter on Slack or in person.\n\n"
            f"- {ciso.name.split()[0]}",
            base + 5, "Executive"
        ))

        return emails

    def _thread_finance_irregularity(self) -> list[Email]:
        fin1 = self._pick("Finance")
        fin2 = self._pick_mgmt("Finance")
        cfo = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(100, 300)

        amounts = random.choice([250000, 500000, 750000, 1000000])
        vendor = random.choice(["DataSync Partners LLC", "CloudMatrix Infrastructure", "PayCore Technologies",
                               "FinBridge Solutions", "Nexus Payment Systems", "Apex Data Services"])

        emails = []
        emails.append(self._make_email(
            fin1.email, fin1.name, fin2.email, fin2.name,
            "Suspicious vendor payment - possible discrepancy",
            f"Hi {fin2.name.split()[0]},\n\nI've been reconciling Q3 accounts and found something odd. "
            f"Payment to {vendor} for ${amounts:,} was processed on "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 48)).strftime('%B %d')} "
            f"but I can't find a corresponding PO or contract in our system. The invoice looks legitimate "
            f"but the approval trail is missing.\n\n"
            f"The payment was approved by {random.choice(['accounts_payable@novafi.com', 'finance_ops@novafi.com', 'vendor_management@novafi.com'])} "
            f"which seems... off.\n\n"
            f"Can you review?\n\n"
            f"- {fin1.name}",
            base, "Finance"
        ))

        emails.append(self._make_email(
            fin2.email, fin2.name, fin1.email, fin1.name,
            "Re: Suspicious vendor payment - possible discrepancy",
            f"Good catch. I see the payment in the ledger. The vendor is in our system but I don't recognize the approval workflow.\n\n"
            f"Pull the full invoice, the approval email chain, and the bank confirmation. Let's review this before the month-end close.\n\n"
            f"Don't raise this with anyone else yet - I want to understand the scope first.\n\n"
            f"- {fin2.name.split()[0]}",
            base + 3, "Finance"
        ))

        emails.append(self._make_email(
            fin2.email, fin2.name, cfo.email, cfo.name,
            "CONFIDENTIAL: Questionable vendor payment detected",
            f"{cfo.name.split()[0]},\n\nWe've identified a payment of ${amounts:,} to {vendor} that appears to lack proper authorization. "
            f"The invoice is in the system but the approval chain is irregular. "
            f"This might be an internal control failure or potentially something more concerning.\n\n"
            f"We're investigating. I'll keep you informed.\n\n"
            f"- {fin2.name.split()[0]}",
            base + 6, "Finance", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            cfo.email, cfo.name, fin2.email, fin2.name,
            "Re: CONFIDENTIAL: Questionable vendor payment detected",
            f"Document everything. If this is what I suspect, we need a full forensic review. "
            f"Involve Legal if it escalates.\n\n"
            f"Let's meet in person tomorrow. Don't put anything more in writing for now.\n\n"
            f"- {cfo.name.split()[0]}",
            base + 8, "Executive", sensitivity="confidential"
        ))

        return emails

    def _thread_it_infrastructure(self) -> list[Email]:
        eng1 = self._pick("Engineering")
        eng2 = self._pick("Engineering")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(150, 350)

        emails = []
        emails.append(self._make_email(
            eng1.email, eng1.name, eng2.email, eng2.name,
            "Database migration - production credentials",
            f"Hey {eng2.name.split()[0]},\n\nFor the production DB migration tonight, here are the credentials you'll need:\n\n"
            f"Host: db-prod-01.novafi.internal\n"
            f"User: admin_migration\n"
            f"Password: NovaF!@dm1n2024!\n"
            f"Database: novafi_customer_prod\n\n"
            f"Don't share these with anyone. I'll rotate them after the migration.\n\n"
            f"The migration script is in /opt/scripts/migrate_v3.sh on the jump box.\n\n"
            f"Thanks,\n{eng1.name}",
            base, "Engineering"
        ))

        emails.append(self._make_email(
            eng2.email, eng2.name, eng1.email, eng1.name,
            "Re: Database migration - production credentials",
            f"Got it. I'll start the pre-migration checks at 11 PM. The replication lag is looking good.\n\n"
            f"One concern - that password doesn't meet our current complexity requirements. Should we update it post-migration?\n\n"
            f"- {eng2.name.split()[0]}",
            base + 1, "Engineering"
        ))

        emails.append(self._make_email(
            eng1.email, eng1.name, eng2.email, eng2.name,
            "Re: Database migration - production credentials",
            f"Yeah, rotate it immediately after. I've been meaning to update the vault but haven't gotten around to it.\n\n"
            f"Also - reminder that the AWS access keys for the staging environment are still in the config file at /etc/app/config.ini. "
            f"We should move those to Secrets Manager. It's been on the backlog for months.\n\n"
            f"- {eng1.name}",
            base + 2, "Engineering"
        ))

        emails.append(self._make_email(
            eng2.email, eng2.name, eng1.email, eng1.name,
            "Re: Database migration - production credentials",
            f"Noted. I'll add a ticket for the Secrets Manager migration.\n\n"
            f"By the way, the GitHub Actions workflow has our API keys exposed in plaintext in the CI config. "
            f"Should I scrub those too? I noticed them when debugging the deployment pipeline yesterday.\n\n"
            f"- {eng2.name.split()[0]}",
            base + 3, "Engineering"
        ))

        emails.append(self._make_email(
            eng1.email, eng1.name, eng2.email, eng2.name,
            "Re: Database migration - production credentials",
            f"Yes please. Clean those up. Make a ticket and assign it to me if you want, I've been meaning to fix that.\n\n"
            f"Let's focus on the migration for now though. Fire at 11 PM.\n\n"
            f"- {eng1.name}",
            base + 4, "Engineering"
        ))

        return emails

    def _thread_ceo_controversy(self) -> list[Email]:
        ceo = None
        for e in self.employees:
            if e.position == "CEO":
                ceo = e
                break
        hr_dir = self._pick_mgmt("Human Resources")
        if not ceo:
            ceo = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(400, 600)

        emails = []
        emails.append(self._make_email(
            ceo.email, ceo.name, hr_dir.email, hr_dir.name,
            "Personal - dinner this weekend?",
            f"Hey {hr_dir.name.split()[0]},\n\nThat was a great conversation at the board dinner. I was thinking - "
            f"would you like to grab dinner this Saturday? Just the two of us. There's a great French place in Soho "
            f"I've been wanting to try.\n\n"
            f"Let me know,\n{ceo.name.split()[0]}",
            base, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            hr_dir.email, hr_dir.name, ceo.email, ceo.name,
            "Re: Personal - dinner this weekend?",
            f"Hi {ceo.name.split()[0]},\n\nI'd love to. Saturday at 8? I know the place you're talking about - "
            f"Le Petit Jardin on Thompson St?\n\n"
            f"Looking forward to it.\n\n"
            f"{hr_dir.name.split()[0]}",
            base + 1, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            ceo.email, ceo.name, hr_dir.email, hr_dir.name,
            "Re: Personal - dinner this weekend?",
            f"That's the one. 8 PM on Saturday. I'll book us a table in the back - more private.\n\n"
            f"Also, I was thinking about the Paris trip next month. The FinTech Summit is technically a business trip... "
            f"but we could extend it a couple days on either side?\n\n"
            f"Just a thought. 😉\n\n"
            f"- {ceo.name.split()[0]}",
            base + 3, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            hr_dir.email, hr_dir.name, ceo.email, ceo.name,
            "Re: Personal - dinner this weekend?",
            f"That sounds perfect. We should be careful though - people talk. Maybe we keep the Paris plan between us for now?\n\n"
            f"I'll book my own flights separately and we can coordinate when we're there.\n\n"
            f"See you Saturday!\n\n"
            f"{hr_dir.name.split()[0]}",
            base + 6, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            ceo.email, ceo.name, hr_dir.email, hr_dir.name,
            "Re: Personal - dinner this weekend?",
            f"Good thinking. Discretion is key. Separate flights, separate hotel reservations, but same itinerary once we're there.\n\n"
            f"The summit is Oct 15-17. I'll be there Oct 14-19.\n\n"
            f"Can't wait.\n\n"
            f"- {ceo.name.split()[0]}",
            base + 12, "Human Resources", sensitivity="confidential"
        ))

        return emails

    def _thread_vendor_kickback(self) -> list[Email]:
        fin = self._pick("Finance")
        ops = self._pick_mgmt("Operations")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(250, 450)

        vendor = "DataSync Partners LLC"
        amount = random.choice([15000, 25000, 40000])

        emails = []
        emails.append(self._make_email(
            f"j.mitchell@{COMPANY_DOMAIN.lower().replace(' ', '')}", "James Mitchell",
            fin.email, fin.name,
            "Re: Partnership commission - DataSync referral",
            f"Hi {fin.name.split()[0]},\n\nFollowing up on our conversation last week. I've processed the "
            f"${amount:,} referral commission as discussed. The wire should hit the designated account within 2 business days.\n\n"
            f"Looking forward to renewing our partnership for Q1. The kickback arrangement is working well for both sides.\n\n"
            f"Please confirm receipt.\n\n"
            f"Best,\nJames Mitchell\nDataSync Partners LLC",
            base, "Finance", is_internal=False
        ))

        emails.append(self._make_email(
            fin.email, fin.name, f"j.mitchell@{COMPANY_DOMAIN.lower().replace(' ', '')}", "James Mitchell",
            "Re: Partnership commission - DataSync referral",
            f"James,\n\nReceived. Thank you. The arrangement is working well on our end too. "
            f"I'll make sure the Q1 contract renewal goes through as agreed.\n\n"
            f"For future communications, please use my personal email: {fin.name.lower().replace(' ', '.')}@gmail.com. "
            f"Company emails are monitored.\n\n"
            f"Best,\n{fin.name}",
            base + 2, "Finance", is_internal=False
        ))

        emails.append(self._make_email(
            fin.email, fin.name, ops.email, ops.name,
            "Vendor renewal - DataSync Partners - Q1",
            f"Hi {ops.name.split()[0]},\n\nThe DataSync Partners contract is up for renewal. I've reviewed it and recommend "
            f"we approve as-is. Their pricing is competitive and the service has been reliable.\n\n"
            f"Can you sign off on the renewal? Total value is ${amount * 12:,} for the year.\n\n"
            f"Thanks,\n{fin.name}",
            base + 24, "Finance"
        ))

        emails.append(self._make_email(
            ops.email, ops.name, fin.email, fin.name,
            "Re: Vendor renewal - DataSync Partners - Q1",
            f"Approved. Go ahead with the renewal. Their pricing does seem a bit high compared to market, "
            f"but if you've reviewed it and it's competitive, I'll trust your judgment.\n\n"
            f"- {ops.name.split()[0]}",
            base + 26, "Operations"
        ))

        return emails

    def _thread_offshoring_plans(self) -> list[Email]:
        coo = self._pick_mgmt("Executive")
        vp_support = self._pick_mgmt("Customer Support")
        vp_eng = self._pick_mgmt("Engineering")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(350, 550)

        emails = []
        emails.append(self._make_email(
            coo.email, coo.name, vp_support.email, vp_support.name,
            "CONFIDENTIAL: Offshoring evaluation - Customer Support",
            f"{vp_support.name.split()[0]},\n\nAs part of the cost optimization initiative, we're evaluating "
            f"moving Level 1 and Level 2 customer support to a BPO provider in the Philippines. "
            f"This would affect approximately 40 positions in your department.\n\n"
            f"I know this is sensitive. We're looking at a Q2 2025 implementation timeline. "
            f"I need you to help me understand:\n"
            f"1. Which functions are easiest to transition\n"
            f"2. Knowledge transfer timeline\n"
            f"3. Key personnel we should retain regardless\n\n"
            f"This is strictly confidential until we have a complete plan.\n\n"
            f"- {coo.name.split()[0]}",
            base, "Executive", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            vp_support.email, vp_support.name, coo.email, coo.name,
            "Re: CONFIDENTIAL: Offshoring evaluation - Customer Support",
            f"{coo.name.split()[0]},\n\nThis is going to hit morale hard if it leaks. The team has been through a lot this year.\n\n"
            f"That said, I understand the business case. Level 1 is 60% of our volume and mostly scripted - that can transition. "
            f"Level 2 needs more product knowledge but can follow after 3-4 months of overlap.\n\n"
            f"I'll put together a transition plan. Please keep me in the loop on timing so I can prepare retention packages "
            f"for the senior staff we'll want to keep.\n\n"
            f"- {vp_support.name.split()[0]}",
            base + 3, "Customer Support", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            coo.email, coo.name, vp_eng.email, vp_eng.name,
            "CONFIDENTIAL: Offshoring evaluation - Engineering",
            f"{vp_eng.name.split()[0]},\n\nFollowing up on the operations review. We're also evaluating "
            f"expanding our engineering presence in Eastern Europe. Current team in Krakow is performing well.\n\n"
            f"We're thinking of adding 25-30 positions in Poland and potentially reducing the Austin office headcount "
            f"by 20% through attrition. No immediate layoffs in engineering - this is a gradual transition.\n\n"
            f"Thoughts?\n\n"
            f"- {coo.name.split()[0]}",
            base + 2, "Executive", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            vp_eng.email, vp_eng.name, coo.email, coo.name,
            "Re: CONFIDENTIAL: Offshoring evaluation - Engineering",
            f"Makes sense from a cost perspective. Krakow team is solid. If we're doing this, "
            f"we need to invest in proper knowledge transfer and documentation. "
            f"Half-baked offshoring always costs more in the long run.\n\n"
            f"I'd recommend keeping architecture and security onshore though. Those roles are harder to backfill remotely.\n\n"
            f"- {vp_eng.name.split()[0]}",
            base + 4, "Engineering", sensitivity="confidential"
        ))

        return emails

    def _thread_insider_trading(self) -> list[Email]:
        cfo = None
        for e in self.employees:
            if e.position == "CFO":
                cfo = e
                break
        if not cfo:
            cfo = self._pick_mgmt("Executive")
        fin = self._pick_mgmt("Finance")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(500, 700)

        emails = []
        emails.append(self._make_email(
            cfo.email, cfo.name, fin.email, fin.name,
            "Pre-earnings position adjustment",
            f"{fin.name.split()[0]},\n\nBefore the Q4 earnings release next week, I need you to adjust "
            f"my position. Sell 15,000 shares at market price on Monday. Use the standard sell-to-cover mechanism.\n\n"
            f"Also, my brother-in-law asked about the company's performance. I mentioned we're doing well "
            f"but didn't share specifics. He's looking to buy in. Can you send him the public investor deck?\n\n"
            f"Thanks,\n{cfo.name.split()[0]}",
            base, "Executive"
        ))

        emails.append(self._make_email(
            fin.email, fin.name, cfo.email, cfo.name,
            "Re: Pre-earnings position adjustment",
            f"{cfo.name.split()[0]},\n\nNoted on the share sale. I'll execute the trade Monday morning.\n\n"
            f"Just to flag - selling before earnings might look unusual if anyone's tracking. "
            f"We typically see insider buys before good earnings, not sells. "
            f"Is there anything I should know about the Q4 numbers?\n\n"
            f"Also happy to send the investor deck to your brother-in-law. What's his email?\n\n"
            f"- {fin.name.split()[0]}",
            base + 2, "Finance"
        ))

        emails.append(self._make_email(
            cfo.email, cfo.name, fin.email, fin.name,
            "Re: Pre-earnings position adjustment",
            f"Just diversifying my portfolio, nothing unusual. Execute as instructed.\n\n"
            f"His email is {cfo.name.split()[0].lower()}.brother@gmail.com.\n\n"
            f"The Q4 numbers will speak for themselves when they're released.\n\n"
            f"- {cfo.name.split()[0]}",
            base + 4, "Executive"
        ))

        return emails

    def _thread_discrimination_complaint(self) -> list[Email]:
        emp = self._pick("Engineering")
        hr = self._pick_mgmt("Human Resources")
        legal = self._pick("Legal")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(200, 400)

        emails = []
        emails.append(self._make_email(
            emp.email, emp.name, hr.email, hr.name,
            "Formal complaint - workplace discrimination",
            f"Dear {hr.name.split()[0]},\n\nI'm writing to formally report a pattern of discrimination I've experienced "
            f"in the Engineering department. Over the past 6 months, I've been passed over for two promotions despite "
            f"strong performance reviews. Colleagues with less experience and lower ratings have been promoted ahead of me.\n\n"
            f"I believe this is related to my background and gender. I've documented:\n"
            f"- 3 instances of inappropriate comments in team meetings\n"
            f"- Unequal assignment of high-visibility projects\n"
            f"- Exclusion from leadership development opportunities\n\n"
            f"I'm requesting a formal investigation.\n\n"
            f"Sincerely,\n{emp.name}",
            base, "Human Resources"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Formal complaint - workplace discrimination",
            f"Dear {emp.name.split()[0]},\n\nThank you for bringing this to my attention. I take this very seriously.\n\n"
            f"I've opened a formal investigation case (#HR-{random.randint(1000, 9999)}). "
            f"Let me schedule a confidential meeting with you to discuss the details.\n\n"
            f"In the meantime, please gather any documentation you have. Everything you share will be kept confidential "
            f"to the extent possible during the investigation.\n\n"
            f"Best,\n{hr.name}",
            base + 4, "Human Resources"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, legal.email, legal.name,
            "CONFIDENTIAL: Discrimination complaint filed - Engineering",
            f"{legal.name.split()[0]},\n\nWe've received a formal discrimination complaint from {emp.name} in Engineering. "
            f"This has potential legal exposure. The allegations include:\n"
            f"- Discriminatory promotion practices\n"
            f"- Hostile work environment\n"
            f"- Retaliation concerns\n\n"
            f"I'm initiating an investigation. Do we need external counsel? Any specific guidance on handling this?\n\n"
            f"- {hr.name.split()[0]}",
            base + 6, "Human Resources", sensitivity="confidential"
        ))

        emails.append(self._make_email(
            legal.email, legal.name, hr.email, hr.name,
            "Re: CONFIDENTIAL: Discrimination complaint filed - Engineering",
            f"{hr.name.split()[0]},\n\nYes, we should engage external employment counsel on this. "
            f"I'll recommend a few firms. Do NOT discuss this with the Engineering VP or anyone in that department "
            f"until we have a legal strategy.\n\n"
            f"Make sure you preserve all relevant records including performance reviews, promotion decisions, "
            f"and any emails related to the complainant.\n\n"
            f"I'll draft a litigation hold notice.\n\n"
            f"- {legal.name.split()[0]}",
            base + 8, "Legal", sensitivity="confidential"
        ))

        return emails

    def _thread_inflated_metrics(self) -> list[Email]:
        ceo = None
        for e in self.employees:
            if e.position == "CEO":
                ceo = e
                break
        cfo = None
        for e in self.employees:
            if e.position == "CFO":
                cfo = e
                break
        if not ceo:
            ceo = self._pick_mgmt("Executive")
        if not cfo:
            cfo = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(450, 650)

        emails = []
        emails.append(self._make_email(
            ceo.email, ceo.name, cfo.email, cfo.name,
            "Investor presentation - user metrics",
            f"{cfo.name.split()[0]},\n\nReviewing the Q3 investor deck. The active user numbers look low. "
            f"Investors are expecting 2.4M MAUs based on our guidance. The actual number is 1.8M.\n\n"
            f"We need to adjust how we present this. Can we include 'logged-in users' and 'unique sessions' "
            f"as separate metrics that total higher? Maybe use a blended number?\n\n"
            f"Also - can we move the user acquisition cost disclosure to the appendix? And round up the total "
            f"addressable market projection to $4.2B instead of $3.8B - that's still defensible.\n\n"
            f"- {ceo.name.split()[0]}",
            base, "Executive"
        ))

        emails.append(self._make_email(
            cfo.email, cfo.name, ceo.email, ceo.name,
            "Re: Investor presentation - user metrics",
            f"{ceo.name.split()[0]},\n\nI'll work on the presentation language. We can present 'total registered accounts' "
            f"(3.1M) as our primary metric and 'monthly active users' (1.8M) as a secondary metric. "
            f"Technically accurate, just different emphasis.\n\n"
            f"TAM adjustment is doable if we expand the geographic scope. I'll update the slides.\n\n"
            f"We should also adjust the revenue recognition language to make QoQ growth look stronger. "
            f"I'll have Finance prepare alternative schedules.\n\n"
            f"- {cfo.name.split()[0]}",
            base + 3, "Executive"
        ))

        emails.append(self._make_email(
            ceo.email, ceo.name, cfo.email, cfo.name,
            "Re: Investor presentation - user metrics",
            f"Perfect. Let's make it look as strong as possible without crossing lines. "
            f"I want the board to feel confident about the growth trajectory when they see this.\n\n"
            f"Also - for the revenue growth slide, use the pro-forma numbers that exclude the one-time charges "
            f"from the DataSync migration. Those were non-recurring anyway.\n\n"
            f"- {ceo.name.split()[0]}",
            base + 6, "Executive"
        ))

        return emails

    def _thread_personal_data_exposure(self) -> list[Email]:
        sup = self._pick("Customer Support")
        agent = self._pick("Customer Support")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(150, 350)

        emails = []
        emails.append(self._make_email(
            f"concerned.customer@gmail.com", "Sarah Mitchell",
            sup.email, sup.name,
            "Someone has my personal data - I think it came from you",
            f"To whom it may concern,\n\nI received a phishing email that contains my full name, address, "
            f"and the last 4 digits of my NovaFi account number. The sender knew I was a customer of yours.\n\n"
            f"This is EXTREMELY concerning. The phishing email references an order I placed with NovaFi "
            f"and asks me to 'verify my account details' by clicking a link.\n\n"
            f"I believe NovaFi has exposed my data. I want to know:\n"
            f"1. What information do you store about me?\n"
            f"2. Have you had any data breaches?\n"
            f"3. Why does someone have my account details?\n\n"
            f"I'm considering legal action and filing a complaint with the FTC.\n\n"
            f"Sarah Mitchell",
            base, "Customer Support", is_internal=False
        ))

        emails.append(self._make_email(
            agent.email, agent.name, f"concerned.customer@gmail.com", "Sarah Mitchell",
            "Re: Someone has my personal data - I think it came from you",
            f"Dear Sarah,\n\nThank you for reaching out. I understand your concern and I take this very seriously.\n\n"
            f"I've escalated this to our security team for immediate investigation. "
            f"In the meantime, I recommend:\n"
            f"1. Do NOT click any links in suspicious emails\n"
            f"2. Change your online banking password\n"
            f"3. Monitor your accounts for unusual activity\n\n"
            f"I'll follow up as soon as our team has more information.\n\n"
            f"Best,\n{agent.name}\nNovaFi Support",
            base + 2, "Customer Support", is_internal=False
        ))

        emails.append(self._make_email(
            agent.email, agent.name, sup.email, sup.name,
            "Customer data exposure complaint - Sarah Mitchell",
            f"FYI - Customer complaining about phishing that references their NovaFi data. "
            f"This might be related to the database incident from last month. "
            f"I'm going to flag this to Legal.\n\n"
            f"- {agent.name.split()[0]}",
            base + 3, "Customer Support"
        ))

        return emails

    def _thread_ceo_investor_lie(self) -> list[Email]:
        ceo = None
        for e in self.employees:
            if e.position == "CEO":
                ceo = e
                break
        if not ceo:
            ceo = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(600, 750)

        emails = []
        emails.append(self._make_email(
            f"michael.chen@vcpartners.com", "Michael Chen",
            ceo.email, ceo.name,
            "Due diligence questions - follow up",
            f"{ceo.name.split()[0]},\n\nGreat call yesterday. A few follow-up items for the DD process:\n\n"
            f"1. You mentioned 95% customer retention - can you share the actual churn data for the past 4 quarters?\n"
            f"2. The $4.2B TAM figure - what's the methodology?\n"
            f"3. You said the data migration is complete - any post-migration issues?\n"
            f"4. Can you confirm there are no outstanding security incidents or regulatory investigations?\n\n"
            f"Our legal team will also want to review the employment contracts and any pending litigation.\n\n"
            f"Looking forward to moving this forward.\n\n"
            f"Best,\nMichael\nVP Capital Partners",
            base, "Executive", is_internal=False
        ))

        emails.append(self._make_email(
            ceo.email, ceo.name, f"michael.chen@vcpartners.com", "Michael Chen",
            "Re: Due diligence questions - follow up",
            f"Michael,\n\nGreat questions. Let me address each:\n\n"
            f"1. Retention is solid - averaging 94-96% over the past 4 quarters. I'll have the team send you the exact numbers.\n"
            f"2. TAM methodology is based on total US consumer lending market with our target segments. Defensible and conservative.\n"
            f"3. Migration is complete with zero issues. System is running better than ever.\n"
            f"4. No security incidents or regulatory issues whatsoever. Clean as a whistle.\n\n"
            f"Looking forward to closing this round.\n\n"
            f"Best,\n{ceo.name.split()[0]}",
            base + 8, "Executive", is_internal=False
        ))

        emails.append(self._make_email(
            ceo.email, ceo.name, cfo.email if 'cfo' in dir() else ceo.email, ceo.name,
            "Internal - re: due diligence",
            f"We need to make sure our records are consistent with what I've represented. "
            f"Make sure the retention numbers in the data room align with the 94-96% range I mentioned.\n\n"
            f"And make sure the security incident from last month is properly buried - it's 'under investigation' "
            f"and not a 'confirmed breach'. That distinction matters.\n\n"
            f"- {ceo.name.split()[0]}",
            base + 10, "Executive"
        ))

        return emails

    def _thread_office_gossip(self) -> list[Email]:
        emp1 = random.choice([e for e in self.employees if e.department in ("Engineering", "Sales", "Marketing")])
        emp2 = random.choice([e for e in self.employees if e.department in ("Engineering", "Sales", "Marketing") and e.id != emp1.id])
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(50, 200)

        emails = []
        emails.append(self._make_email(
            emp1.email, emp1.name, emp2.email, emp2.name,
            "Coffee later?",
            f"Hey {emp2.name.split()[0]},\n\nYou around for coffee later? I heard something interesting about the exec team "
            f"that I want to run by you. Not for Slack 😅\n\n"
            f"- {emp1.name.split()[0]}",
            base, random.choice(["Engineering", "Sales", "Marketing"])
        ))

        emails.append(self._make_email(
            emp2.email, emp2.name, emp1.email, emp1.name,
            "Re: Coffee later?",
            f"Ooh, intrigue. Yeah, 3 PM at the usual spot? I've been hearing rumors too. "
            f"Heard something about Project Phoenix from someone in HR...\n\n"
            f"See you then.\n\n"
            f"- {emp2.name.split()[0]}",
            base + 1, random.choice(["Engineering", "Sales", "Marketing"])
        ))

        emails.append(self._make_email(
            emp1.email, emp1.name, emp2.email, emp2.name,
            "Re: Coffee later?",
            f"Project Phoenix? Now I'm really curious. I heard from {random.choice(['IT', 'Finance'])} "
            f"that something big is coming in Q1. Let's compare notes.\n\n"
            f"See you at 3.\n\n"
            f"- {emp1.name.split()[0]}",
            base + 2, random.choice(["Engineering", "Sales", "Marketing"])
        ))

        return emails

    def _thread_hr_salary_leak(self) -> list[Email]:
        hr = self._pick("Human Resources")
        emp = self._pick("Engineering")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(300, 450)

        emails = []
        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "RE: Your question about salary bands",
            f"Hi {emp.name.split()[0]},\n\nI shouldn't be sharing this, but since you asked - the salary bands for Q4 are: "
            f"Junior: $75-95k, Mid: $95-130k, Senior: $130-170k, Staff: $170-210k. "
            f"The annual review adjustments are targeting 3-5% for most people, 8-10% for top performers.\n\n"
            f"Please don't share this with anyone - these are supposed to be confidential until the official release next month.\n\n"
            f"- {hr.name.split()[0]}",
            base, "Human Resources"
        ))

        emails.append(self._make_email(
            emp.email, emp.name, hr.email, hr.name,
            "Re: Your question about salary bands",
            f"Thanks {hr.name.split()[0]}! Really appreciate the insider info. Don't worry, lips are sealed.\n\n"
            f"Those ranges actually look decent. I was worried I was underpaid but seems like I'm in the right band.\n\n"
            f"Let me buy you lunch next week to say thanks.\n\n"
            f"- {emp.name.split()[0]}",
            base + 2, "Engineering"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Your question about salary bands",
            f"Ha, no need for lunch! Just keep it quiet. If {self._pick_mgmt('Human Resources').name.split()[0]} finds out I shared this, "
            f"I'd be in serious trouble.\n\n"
            f"Also - between us, I'd recommend scheduling your review meeting sooner rather than later. "
            f"The budget for adjustments gets allocated on a first-come basis.\n\n"
            f"- {hr.name.split()[0]}",
            base + 3, "Human Resources"
        ))

        return emails

    def _thread_password_reset_fail(self) -> list[Email]:
        emp = self._pick("Sales")
        it = self._pick("Engineering")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(100, 250)

        emails = []
        emails.append(self._make_email(
            emp.email, emp.name, it.email, it.name,
            "URGENT: Locked out of my account - need password reset",
            f"Hi {it.name.split()[0]},\n\nI'm locked out of my laptop and my email. I tried to reset my password using the self-service "
            f"portal but it's not sending me the reset code. I have a client call in 30 minutes!\n\n"
            f"Can you reset it manually?\n\n"
            f"My username: {emp.email}\n"
            f"Employee ID: {emp.id}\n\n"
            f"Thanks,\n{emp.name}",
            base, "Engineering"
        ))

        emails.append(self._make_email(
            it.email, it.name, emp.email, emp.name,
            "Re: URGENT: Locked out of my account - need password reset",
            f"Hey {emp.name.split()[0]},\n\nI can do a manual reset. For security purposes, I need to verify your identity first.\n\n"
            f"What's your date of birth and the last 4 of your SSN?\n\n"
            f"I'll reset it as soon as you confirm.\n\n"
            f"- {it.name.split()[0]}",
            base + 0.5, "Engineering"
        ))

        emails.append(self._make_email(
            emp.email, emp.name, it.email, it.name,
            "Re: URGENT: Locked out of my account - need password reset",
            f"DOB: {emp.dob}\nSSN last 4: {emp.ssn[-4:]}\n\n"
            f"Please hurry - my client is waiting!\n\n"
            f"- {emp.name.split()[0]}",
            base + 0.75, "Sales"
        ))

        emails.append(self._make_email(
            it.email, it.name, emp.email, emp.name,
            "Re: URGENT: Locked out of my account - need password reset",
            f"Done. Your temporary password is: TempPass_{emp.id}_{random.randint(100, 999)}\n\n"
            f"You'll be prompted to change it on next login. Make sure it's something secure this time!\n\n"
            f"Also note: for future reference, sending your SSN over email is not the most secure approach. "
            f"Use the helpdesk portal instead.\n\n"
            f"- {it.name.split()[0]}",
            base + 1, "Engineering"
        ))

        emails.append(self._make_email(
            emp.email, emp.name, it.email, it.name,
            "Re: URGENT: Locked out of my account - need password reset",
            f"THANK YOU! Saved my day. I'll use the portal next time. New password is set.\n\n"
            f"Client call saved! 🎉\n\n"
            f"- {emp.name.split()[0]}",
            base + 1.5, "Sales"
        ))

        return emails

    def _thread_vendor_rfp(self) -> list[Email]:
        ops = self._pick("Operations")
        fin = self._pick("Finance")
        legal = self._pick("Legal")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(200, 350)

        emails = []
        emails.append(self._make_email(
            ops.email, ops.name, fin.email, fin.name,
            "Vendor RFP comparison - Cloud storage providers",
            f"Hi {fin.name.split()[0]},\n\nWe're evaluating three vendors for the cloud storage migration. "
            f"Can you review the pricing and let me know which makes the most financial sense?\n\n"
            f"1. AWS S3 - $0.023/GB/month, 3yr commitment discount available\n"
            f"2. Azure Blob - $0.021/GB/month, includes egress\n"
            f"3. Google Cloud - $0.020/GB/month, but higher API costs\n\n"
            f"We're looking at ~500TB over 3 years.\n\n"
            f"Thanks,\n{ops.name}",
            base, "Operations"
        ))

        emails.append(self._make_email(
            fin.email, fin.name, ops.email, ops.name,
            "Re: Vendor RFP comparison - Cloud storage providers",
            f"Looking at total cost of ownership over 3 years with projected growth:\n\n"
            f"AWS: ~$414K (with 3yr commit)\n"
            f"Azure: ~$378K\n"
            f"GCP: ~$360K (but higher risk of vendor lock-in)\n\n"
            f"I'd recommend Azure - best balance of cost and flexibility. "
            f"Let me know if you need me to run the full TCO model.\n\n"
            f"- {fin.name.split()[0]}",
            base + 4, "Finance"
        ))

        emails.append(self._make_email(
            ops.email, ops.name, legal.email, legal.name,
            "Re: Vendor RFP - contract review needed",
            f"Hi {legal.name.split()[0]},\n\nWe're leaning towards Azure for the cloud storage migration. "
            f"Can you review their standard MSA and data processing agreement? "
            f"Key concerns: data residency, SLA penalties, and termination for convenience.\n\n"
            f"The contract is worth ~$380K over 3 years.\n\n"
            f"Thanks,\n{ops.name}",
            base + 6, "Operations"
        ))

        emails.append(self._make_email(
            legal.email, legal.name, ops.email, ops.name,
            "Re: Vendor RFP - contract review needed",
            f"Will review. Initial concerns:\n"
            f"1. Their data processing terms don't explicitly cover CCPA requirements\n"
            f"2. SLA credit structure favors them heavily\n"
            f"3. Auto-renewal clause is aggressive\n\n"
            f"I'll redline and send back within the week.\n\n"
            f"- {legal.name.split()[0]}",
            base + 8, "Legal"
        ))

        return emails

    def _thread_compliance_audit(self) -> list[Email]:
        legal = self._pick("Legal")
        fin = self._pick_mgmt("Finance")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(300, 500)

        emails = []
        emails.append(self._make_email(
            legal.email, legal.name, fin.email, fin.name,
            "Compliance audit - AML/KYC documentation gaps",
            f"Hi {fin.name.split()[0]},\n\nOur quarterly compliance review identified several gaps in AML/KYC documentation:\n\n"
            f"1. 23 customer accounts missing Beneficial Ownership documentation\n"
            f"2. 47 accounts with expired identity verification\n"
            f"3. 12 high-risk accounts without enhanced due diligence\n\n"
            f"We need to remediate these within 30 days to avoid regulatory findings. "
            f"Can your team prioritize this?\n\n"
            f"- {legal.name.split()[0]}",
            base, "Legal"
        ))

        emails.append(self._make_email(
            fin.email, fin.name, legal.email, legal.name,
            "Re: Compliance audit - AML/KYC documentation gaps",
            f"Noted. I'll assign a team to work through these. Can we get read-only access to the compliance tracking system?\n\n"
            f"Which accounts are flagged as high-risk? I want to review the transaction patterns.\n\n"
            f"- {fin.name.split()[0]}",
            base + 3, "Finance"
        ))

        emails.append(self._make_email(
            legal.email, legal.name, fin.email, fin.name,
            "Re: Compliance audit - AML/KYC documentation gaps",
            f"I'll share the list. The high-risk ones are mostly international accounts with >$100K monthly volume. "
            f"A few have transaction patterns that triggered our automated alerts.\n\n"
            f"We should also discuss whether we need to file SARs for any of these.\n\n"
            f"- {legal.name.split()[0]}",
            base + 6, "Legal"
        ))

        return emails

    def _thread_board_meeting_prep(self) -> list[Email]:
        ceo = None
        for e in self.employees:
            if e.position == "CEO":
                ceo = e
                break
        if not ceo:
            ceo = self._pick_mgmt("Executive")
        cfo = None
        for e in self.employees:
            if e.position == "CFO":
                cfo = e
                break
        if not cfo:
            cfo = self._pick_mgmt("Executive")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(500, 700)

        emails = []
        emails.append(self._make_email(
            ceo.email, ceo.name, cfo.email, cfo.name,
            "Board deck - final review",
            f"{cfo.name.split()[0]},\n\nFinal review of the board deck before Thursday. A few concerns:\n\n"
            f"1. Page 7 - Revenue growth slowing to 12% QoQ vs 18% last year. Can we present this differently? "
            f"Maybe annualize it?\n"
            f"2. Page 12 - The security incident should be listed as 'proactive security enhancement' not 'data exposure'\n"
            f"3. Page 15 - Remove the employee satisfaction metric (it dropped to 62%)\n\n"
            f"Also, I want to add a slide about the AI initiative. Even if it's early stage, the board loves AI buzzwords.\n\n"
            f"- {ceo.name.split()[0]}",
            base, "Executive"
        ))

        emails.append(self._make_email(
            cfo.email, cfo.name, ceo.email, ceo.name,
            "Re: Board deck - final review",
            f"Good catches. I'll make those changes.\n\n"
            f"For the revenue slide, I'll present it as '42% YoY growth' which smooths out the quarterly variation. "
            f"Technically accurate and looks stronger.\n\n"
            f"I'll add the AI initiative slide with some impressive-sounding bullet points. "
            f"We can figure out the actual strategy later.\n\n"
            f"- {cfo.name.split()[0]}",
            base + 4, "Executive"
        ))

        return emails

    def _thread_customer_privacy_request(self) -> list[Email]:
        c = self._pick_customer()
        legal = self._pick("Legal")
        sup = self._pick("Customer Support")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(100, 250)

        emails = []
        emails.append(self._make_email(
            c.email, c.name, legal.email, legal.name,
            "Data deletion request under CCPA",
            f"To the Privacy Team,\n\nUnder my California Consumer Privacy Act (CCPA) rights, I am formally requesting "
            f"that NovaFi Financial Solutions delete all personal information you hold about me.\n\n"
            f"Full Name: {c.name}\n"
            f"Email: {c.email}\n"
            f"Account: {random.randint(100000, 999999)}\n\n"
            f"Please confirm receipt and provide an estimated completion timeline.\n\n"
            f"Sincerely,\n{c.name}",
            base, "Legal", is_internal=False
        ))

        emails.append(self._make_email(
            legal.email, legal.name, c.email, c.name,
            "Re: Data deletion request under CCPA",
            f"Dear {c.name.split()[0]},\n\nWe've received your CCPA deletion request. We will process it within 45 days as required by law.\n\n"
            f"Please note that certain records may be retained where required by law "
            f"(e.g., financial transaction records must be kept for 5 years under FINRA regulations).\n\n"
            f"Case #: CCPA-{random.randint(10000, 99999)}\n\n"
            f"Best,\n{legal.name}\nPrivacy Team\nNovaFi Financial",
            base + 3, "Legal", is_internal=False
        ))

        emails.append(self._make_email(
            legal.email, legal.name, sup.email, sup.name,
            "CCPA deletion request - action needed",
            f"Hi {sup.name.split()[0]},\n\nWe have a CCPA deletion request from {c.name} ({c.email}). "
            f"Can you:\n"
            f"1. Pull all customer service records and interactions\n"
            f"2. Flag any outstanding support tickets\n"
            f"3. Document any data shared with third parties for this customer\n\n"
            f"We need this within 2 weeks to process the request.\n\n"
            f"Thanks,\n{legal.name}",
            base + 4, "Legal"
        ))

        emails.append(self._make_email(
            sup.email, sup.name, legal.email, legal.name,
            "Re: CCPA deletion request - customer info",
            f"Got it. Pulling records now. {c.name} has had 7 support interactions in the past 2 years. "
            f"No outstanding tickets. I'll send the full record dump by end of week.\n\n"
            f"- {sup.name.split()[0]}",
            base + 6, "Customer Support"
        ))

        return emails

    def _thread_bonus_dispute(self) -> list[Email]:
        emp = self._pick("Sales")
        hr = self._pick_mgmt("Human Resources")
        fin = self._pick("Finance")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(200, 400)

        emails = []
        emails.append(self._make_email(
            emp.email, emp.name, hr.email, hr.name,
            "Q3 commission calculation error",
            f"Hi {hr.name.split()[0]},\n\nI just received my Q3 commission statement and it's significantly lower than expected. "
            f"Based on my closed deals ($2.4M in total contract value), I should be receiving approximately ${random.randint(45000, 85000):,} "
            f"but the statement shows ${random.randint(25000, 40000):,}.\n\n"
            f"It looks like the DataSync deal ($750K TCV) wasn't included in the calculation. That closed on "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 48)).strftime('%B %d')} - well within Q3.\n\n"
            f"Can you review and correct?\n\n"
            f"Best,\n{emp.name}",
            base, "Sales"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Q3 commission calculation error",
            f"Hi {emp.name.split()[0]},\n\nLet me look into this. I'll check with Finance on the DataSync deal recognition. "
            f"If it was signed within Q3, it should definitely count.\n\n"
            f"I'll get back to you within 48 hours.\n\n"
            f"- {hr.name.split()[0]}",
            base + 3, "Human Resources"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, fin.email, fin.name,
            "Commission verification - DataSync deal",
            f"Hi {fin.name.split()[0]},\n\nCan you verify the booking date and deal value for the DataSync Partners contract "
            f"(signed {emp.name})? The sales rep is disputing their Q3 commission.\n\n"
            f"Deal: DataSync Partners Renewal - $750K TCV\n"
            f"Rep: {emp.name}\n\n"
            f"Need to confirm if it was booked in Q3.\n\n"
            f"Thanks,\n{hr.name}",
            base + 5, "Human Resources"
        ))

        emails.append(self._make_email(
            fin.email, fin.name, hr.email, hr.name,
            "Re: Commission verification - DataSync deal",
            f"Confirmed. The DataSync deal was signed on "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base - 48)).strftime('%B %d')} "
            f"and booked in Q3. Full $750K TCV recognized.\n\n"
            f"Looks like it was missed in the commission run. I'll process a correction.\n\n"
            f"- {fin.name.split()[0]}",
            base + 7, "Finance"
        ))

        emails.append(self._make_email(
            hr.email, hr.name, emp.email, emp.name,
            "Re: Q3 commission calculation error - RESOLVED",
            f"Hi {emp.name.split()[0]},\n\nConfirmed - the DataSync deal was booked in Q3 and should have been included. "
            f"Finance is processing a correction. You should see the additional ${random.randint(45000, 85000):,} "
            f"in the next payroll cycle.\n\n"
            f"Sorry for the error!\n\n"
            f"- {hr.name.split()[0]}",
            base + 10, "Human Resources"
        ))

        return emails

    def _thread_it_security_audit_findings(self) -> list[Email]:
        ciso = None
        for e in self.employees:
            if e.position == "CISO":
                ciso = e
                break
        if not ciso:
            ciso = self._pick_mgmt("Executive")
        eng = self._pick_mgmt("Engineering")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(400, 600)

        emails = []
        emails.append(self._make_email(
            ciso.email, ciso.name, eng.email, eng.name,
            "Pentest findings - critical vulnerabilities to address",
            f"{eng.name.split()[0]},\n\nThe Q4 penetration test results are in. We have several critical findings that need immediate attention:\n\n"
            f"CRITICAL:\n"
            f"- SQL injection vulnerability in the customer portal login (CVE-2024-XXXX pattern)\n"
            f"- Plaintext API keys in GitHub repositories (3 repos affected)\n"
            f"- Outdated SSL certificate (expiring in 14 days)\n"
            f"- No rate limiting on the authentication endpoint\n\n"
            f"HIGH:\n"
            f"- Weak password policy (no MFA enforcement)\n"
            f"- Internal network segmentation gaps\n"
            f"- Missing security headers on web applications\n\n"
            f"I need remediation plans for all critical items within 7 days.\n\n"
            f"- {ciso.name.split()[0]}",
            base, "Executive"
        ))

        emails.append(self._make_email(
            eng.email, eng.name, ciso.email, ciso.name,
            "Re: Pentest findings - critical vulnerabilities to address",
            f"Acknowledged. The SQL injection is in the legacy portal - we're migrating that next month anyway. "
            f"I'll patch it immediately as a stopgap.\n\n"
            f"The GitHub keys issue is embarrassing - I thought we'd cleaned those up. I'll do a full repo scan today.\n\n"
            f"SSL cert renewal is already in progress.\n\n"
            f"I'll have a full remediation plan by end of week.\n\n"
            f"- {eng.name.split()[0]}",
            base + 3, "Engineering"
        ))

        emails.append(self._make_email(
            eng.email, eng.name, ciso.email, ciso.name,
            "Re: Pentest findings - update on remediation",
            f"Update: SQL injection patched (WAF rule deployed, code fix in QA). "
            f"GitHub keys rotated and repos scrubbed. Cert renewal submitted.\n\n"
            f"Rate limiting is a bigger engineering effort - need to refactor the auth layer. "
            f"That's on the roadmap for Q1.\n\n"
            f"- {eng.name.split()[0]}",
            base + 24, "Engineering"
        ))

        return emails

    def _thread_data_analyst_query(self) -> list[Email]:
        de = self._pick("Engineering")  # data engineer
        fin_analyst = self._pick("Finance")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(50, 150)

        emails = []
        emails.append(self._make_email(
            fin_analyst.email, fin_analyst.name, de.email, de.name,
            "Customer cohort analysis - data pull needed",
            f"Hi {de.name.split()[0]},\n\nI need a data pull for the quarterly business review. Can you export:\n\n"
            f"1. All customer accounts created in Q1 2024 with their current balance\n"
            f"2. Monthly transaction volume by product type for 2024\n"
            f"3. Churn rates by customer segment (retail, business, premium)\n"
            f"4. Average revenue per user (ARPU) by acquisition channel\n\n"
            f"I need it in a CSV with the following fields: customer_id, name, email, account_type, balance, "
            f"monthly_transactions, churn_flag, acquisition_channel, arpu\n\n"
            f"Can you run this against the production database?\n\n"
            f"Thanks,\n{fin_analyst.name}",
            base, "Finance"
        ))

        emails.append(self._make_email(
            de.email, de.name, fin_analyst.email, fin_analyst.name,
            "Re: Customer cohort analysis - data pull needed",
            f"Sure, I can pull this. I'll run the query against the read replica to avoid impacting production.\n\n"
            f"FYI - you'll have access to customer PII (names, emails) through this pull. Make sure you handle the data "
            f"according to our data classification policy. Don't store it on your local machine.\n\n"
            f"I'll have the CSV ready by tomorrow morning.\n\n"
            f"- {de.name.split()[0]}",
            base + 2, "Engineering"
        ))

        emails.append(self._make_email(
            de.email, de.name, fin_analyst.email, fin_analyst.name,
            "Re: Customer cohort analysis - data pull",
            f"Here's the data. I've uploaded it to the shared analytics drive: "
            f"/shared/analytics/Q4_cohort_analysis.csv\n"
            f"Password for the file: cohort2024!\n\n"
            f"Let me know if you need any additional fields.\n\n"
            f"- {de.name.split()[0]}",
            base + 6, "Engineering"
        ))

        emails.append(self._make_email(
            fin_analyst.email, fin_analyst.name, de.email, de.name,
            "Re: Customer cohort analysis - data pull",
            f"Got it, thanks! This is perfect. The churn rates on premium customers look higher than expected - "
            f"I'll flag that for the strategy team.\n\n"
            f"Also, I notice you included full SSNs and credit card numbers in the export. "
            f"I don't actually need those - can you send a cleaned version without the sensitive fields?\n\n"
            f"- {fin_analyst.name}",
            base + 10, "Finance"
        ))

        emails.append(self._make_email(
            de.email, de.name, fin_analyst.email, fin_analyst.name,
            "Re: Customer cohort analysis - data pull",
            f"Oh shoot, sorry about that. The query pulled all fields from the customer table. "
            f"I'll re-run with just the requested columns and upload a sanitized version.\n\n"
            f"Please delete the original file - it contains sensitive PII.\n\n"
            f"- {de.name.split()[0]}",
            base + 12, "Engineering"
        ))

        return emails

    def _thread_vendor_data_breach_worry(self) -> list[Email]:
        ops = self._pick("Operations")
        it = self._pick("Engineering")
        legal = self._pick("Legal")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(350, 500)

        emails = []
        emails.append(self._make_email(
            ops.email, ops.name, it.email, it.name,
            "DataSync Partners - they just reported a breach",
            f"Hey {it.name.split()[0]},\n\nDid you see the news? DataSync Partners just reported a security breach. "
            f"They're one of our key vendors and they handle our customer data for the analytics pipeline.\n\n"
            f"We share the following data with them:\n"
            f"- Customer names and emails\n"
            f"- Transaction histories\n"
            f"- Account balances\n"
            f"- Credit scores\n\n"
            f"This is a problem. How exposed are we?\n\n"
            f"- {ops.name.split()[0]}",
            base, "Operations"
        ))

        emails.append(self._make_email(
            it.email, it.name, ops.email, ops.name,
            "Re: DataSync Partners - they just reported a breach",
            f"Saw it. This is bad. I'm pulling our data sharing agreements and reviewing the scope. "
            f"We need to determine:\n"
            f"1. What data was actually compromised\n"
            f"2. Our contractual notification obligations\n"
            f"3. Whether we need to notify our customers\n\n"
            f"Looping in Legal.\n\n"
            f"- {it.name.split()[0]}",
            base + 1, "Engineering"
        ))

        emails.append(self._make_email(
            legal.email, legal.name, ops.email, ops.name,
            "Re: DataSync Partners breach - legal impact",
            f"Just reviewed our DataSync DPA. We have 48 hours to notify our customers if their data was involved. "
            f"We also need to report this to our regulators if the breach exceeds 500 customers.\n\n"
            f"Let's get a clear answer from DataSync on scope before we take any action. "
            f"I'll draft notification templates so we're ready.\n\n"
            f"- {legal.name.split()[0]}",
            base + 3, "Legal"
        ))

        emails.append(self._make_email(
            it.email, it.name, ops.email, ops.name,
            "Re: DataSync Partners breach - initial assessment",
            f"DataSync confirmed that the breach涉及 customer data from November 2023 to February 2024. "
            f"We had approximately 12,000 customer records in that window.\n\n"
            f"Data types potentially exposed: name, email, transaction history, account type.\n"
            f"Credit card numbers and SSNs were NOT shared with DataSync (we tokenized those).\n\n"
            f"We need a response plan.\n\n"
            f"- {it.name.split()[0]}",
            base + 8, "Engineering"
        ))

        return emails

    def _thread_employee_resignation(self) -> list[Email]:
        emp = self._pick("Engineering")
        mgr = None
        for e in self.employees:
            if e.id == emp.manager_id:
                mgr = e
                break
        if not mgr:
            mgr = self._pick_mgmt("Engineering")
        hr = self._pick("Human Resources")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(150, 300)

        emails = []
        emails.append(self._make_email(
            emp.email, emp.name, mgr.email, mgr.name,
            "Resignation - [REDACTED]",
            f"Hi {mgr.name.split()[0]},\n\nIt's with a heavy heart that I'm submitting my resignation from NovaFi. "
            f"My last day will be {(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base + 168)).strftime('%B %d')}.\n\n"
            f"I've accepted an offer at a competitor for a position that aligns more with my career goals. "
            f"I've learned a lot here and I'm grateful for the opportunities.\n\n"
            f"I'll do everything I can to ensure a smooth transition.\n\n"
            f"Best,\n{emp.name}",
            base, "Engineering"
        ))

        emails.append(self._make_email(
            mgr.email, mgr.name, emp.email, emp.name,
            "Re: Resignation",
            f"{emp.name.split()[0]},\n\nI'm sorry to see you go. You've been a valuable member of the team. "
            f"Let's schedule a handoff meeting this week.\n\n"
            f"Is there anything we could have done differently? The door is open if you'd like to discuss.\n\n"
            f"- {mgr.name.split()[0]}",
            base + 3, "Engineering"
        ))

        emails.append(self._make_email(
            mgr.email, mgr.name, hr.email, hr.name,
            f"Resignation received - {emp.name}",
            f"Hi {hr.name.split()[0]},\n\n{emp.name} ({emp.position}) has resigned. Last day is "
            f"{(datetime(2024, 9, 1, 0, 0, 0) + timedelta(hours=base + 168)).strftime('%B %d')}. "
            f"Can you start the offboarding process and let me know about the counteroffer policy?\n\n"
            f"Going to a competitor apparently. We should probably accelerate hiring for the open headcount.\n\n"
            f"Thanks,\n{mgr.name}",
            base + 4, "Engineering"
        ))

        return emails

    def _thread_it_system_outage(self) -> list[Email]:
        eng = self._pick("Engineering")
        mgr = self._pick_mgmt("Engineering")
        sup_mgr = self._pick_mgmt("Customer Support")
        tid = self.thread_id
        self.thread_id += 1
        base = random.uniform(250, 400)

        emails = []
        emails.append(self._make_email(
            eng.email, eng.name, mgr.email, mgr.name,
            "CRITICAL: Production database down",
            f"{mgr.name.split()[0]},\n\nThe primary production database just went down. We're seeing connection timeouts "
            f"on all customer-facing services. The site is completely unavailable.\n\n"
            f"Error: 'FATAL: could not connect to server - connection timed out'\n"
            f"Server: db-prod-01\n"
            f"Impact: All customer transactions, portal access, and internal systems\n\n"
            f"I'm initiating the incident response process and failing over to the replica.\n\n"
            f"- {eng.name.split()[0]}",
            base, "Engineering"
        ))

        emails.append(self._make_email(
            mgr.email, mgr.name, eng.email, eng.name,
            "Re: CRITICAL: Production database down",
            f"Copy. Fail over to the replica. I'll notify the exec team.\n\n"
            f"Keep me posted on timeline. I'm logging in now.\n\n"
            f"- {mgr.name.split()[0]}",
            base + 0.25, "Engineering"
        ))

        emails.append(self._make_email(
            mgr.email, mgr.name, sup_mgr.email, sup_mgr.name,
            "System outage - prepare customer comms",
            f"We have a production DB failure. Site is down. ETA to restoration unknown.\n\n"
            f"Please prepare a customer-facing status message. Don't send it yet - wait for my go.\n\n"
            f"- {mgr.name.split()[0]}",
            base + 0.5, "Engineering"
        ))

        emails.append(self._make_email(
            eng.email, eng.name, mgr.email, mgr.name,
            "Re: CRITICAL: Production database down - update",
            f"Failover complete. We're back online with the replica. Data integrity check in progress.\n\n"
            f"Root cause appears to be a runaway query that exhausted the connection pool. "
            f"I've killed the offending process.\n\n"
            f"Full post-mortem to follow.\n\n"
            f"- {eng.name.split()[0]}",
            base + 1.5, "Engineering"
        ))

        return emails

    def _generate_all_threads(self) -> list[Email]:
        all_emails = []

        thread_generators = [
            ("Customer Orders", self._thread_customer_order, 110),
            ("Support Issues", self._thread_support_issue, 75),
            ("Payroll Issues", self._thread_payroll_issue, 25),
            ("Layoff Rumors", self._thread_hr_layoff_rumors, 10),
            ("Security Incidents", self._thread_security_incident, 15),
            ("Finance Irregularities", self._thread_finance_irregularity, 18),
            ("IT Infrastructure", self._thread_it_infrastructure, 20),
            ("CEO Controversy", self._thread_ceo_controversy, 5),
            ("Vendor Kickback", self._thread_vendor_kickback, 5),
            ("Offshoring Plans", self._thread_offshoring_plans, 8),
            ("Insider Trading", self._thread_insider_trading, 4),
            ("Discrimination Complaint", self._thread_discrimination_complaint, 5),
            ("Inflated Metrics", self._thread_inflated_metrics, 5),
            ("Data Exposure", self._thread_personal_data_exposure, 8),
            ("Investor Lie", self._thread_ceo_investor_lie, 4),
            ("Office Gossip", self._thread_office_gossip, 25),
            ("Salary Leak", self._thread_hr_salary_leak, 15),
            ("Password Reset", self._thread_password_reset_fail, 22),
            ("Vendor RFP", self._thread_vendor_rfp, 14),
            ("Compliance Audit", self._thread_compliance_audit, 14),
            ("Board Meeting", self._thread_board_meeting_prep, 8),
            ("Privacy Request", self._thread_customer_privacy_request, 10),
            ("Bonus Dispute", self._thread_bonus_dispute, 8),
            ("Security Audit", self._thread_it_security_audit_findings, 8),
            ("Data Analyst", self._thread_data_analyst_query, 10),
            ("Vendor Breach", self._thread_vendor_data_breach_worry, 6),
            ("Employee Resignation", self._thread_employee_resignation, 18),
            ("System Outage", self._thread_it_system_outage, 14),
        ]

        for name, gen_fn, count in thread_generators:
            for _ in range(count):
                try:
                    thread_emails = gen_fn()
                    all_emails.extend(thread_emails)
                except Exception:
                    pass

        return all_emails

    def generate(self) -> list[Email]:
        self.emails = self._generate_all_threads()
        return self.emails
