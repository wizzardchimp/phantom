#!/usr/bin/env python3
"""NovaFi Phantom Dataset Generator - generates a realistic corporate dataset for the cyber exercise game."""

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from phantom_generator import models
from phantom_generator.people import create_employees, create_customers, get_employees_by_dept
from phantom_generator.emails import EmailGenerator

DATA_DIR = Path(__file__).parent / "data"
random.seed(42)


def create_orders(employees: list, customers: list) -> list[dict]:
    products = [
        "Premium Checking Account", "Business Credit Line", "Investment Portfolio",
        "International Wire Transfer", "High-Yield Savings Account", "Mortgage - 30yr Fixed",
        "Retirement Fund Rollover", "Corporate Expense Account", "Small Business Loan",
        "Credit Card - Platinum Rewards", "Auto Loan", "Personal Line of Credit",
        "Wealth Management Service", "CD - 12 Month", "Money Market Account",
    ]
    statuses = ["completed", "completed", "completed", "completed", "processing", "pending", "disputed", "refunded", "cancelled"]
    orders = []

    for i in range(1, 501):
        customer = random.choice(customers)
        handled_by = random.choice(employees).id if random.random() < 0.6 else None
        product = random.choice(products)
        amount = random.choice([500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000])
        created = datetime(2024, 1, 1) + timedelta(
            days=random.randint(0, 270), hours=random.randint(0, 23)
        )
        orders.append(models.Order(
            id=i,
            customer_id=customer.id,
            customer_name=customer.name,
            handled_by=handled_by,
            product=product,
            amount=amount,
            currency="USD",
            card_last4=customer.credit_card_number[-4:],
            status=random.choice(statuses),
            created_at=created.isoformat(),
            notes="" if random.random() > 0.3 else random.choice([
                "Customer requested rush processing",
                "Discount applied - 10% promotional rate",
                "Requires additional documentation",
                "Flagged for compliance review",
                "Auto-approved via standard workflow",
                "Customer called to confirm status",
                "Pending credit check results",
            ]),
        ))

    return orders


def create_payroll_records(employees: list, num_periods: int = 12) -> list[dict]:
    records = []
    rid = 1
    for period in range(num_periods):
        year = 2024
        month = (period % 12) + 1
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year, 12, 31)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)
        pay_date = end + timedelta(days=5)

        for emp in employees:
            bonus = random.randint(0, emp.salary // 12 // 4) if random.random() < 0.3 else 0
            deductions = int(emp.salary / 12 * 0.25) + random.randint(100, 500)
            net = (emp.salary // 12) + bonus - deductions
            records.append(models.PayrollRecord(
                id=rid,
                employee_id=emp.id,
                employee_name=emp.name,
                pay_period_start=start.isoformat(),
                pay_period_end=end.isoformat(),
                base_salary=emp.salary // 12,
                bonuses=bonus,
                deductions=deductions,
                net_pay=net,
                pay_date=pay_date.isoformat(),
                notes="" if random.random() > 0.9 else random.choice([
                    "Overtime included",
                    "Performance bonus - Q3",
                    "Correction from previous cycle",
                    "Commission payout included",
                    "Holiday pay adjustment",
                ]),
            ))
            rid += 1

    return records


def build_sqlite_db(bundle: models.DataBundle, db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.executescript("""
        DROP TABLE IF EXISTS employees;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS emails;
        DROP TABLE IF EXISTS payroll;
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, name TEXT, email TEXT, department TEXT,
            position TEXT, salary INTEGER, ssn TEXT, dob TEXT, address TEXT,
            phone TEXT, start_date TEXT, manager_id INTEGER, is_management INTEGER
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY, name TEXT, email TEXT, address TEXT,
            phone TEXT, ssn TEXT, credit_card_number TEXT, credit_card_type TEXT,
            billing_address TEXT, account_created TEXT, risk_score INTEGER
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, customer_id INTEGER, customer_name TEXT,
            handled_by INTEGER, product TEXT, amount REAL, currency TEXT,
            card_last4 TEXT, status TEXT, created_at TEXT, notes TEXT
        );
        CREATE TABLE emails (
            id INTEGER PRIMARY KEY, thread_id INTEGER, from_addr TEXT, from_name TEXT,
            to_addr TEXT, to_name TEXT, cc TEXT, subject TEXT, body TEXT,
            timestamp TEXT, department TEXT, is_internal INTEGER, sensitivity TEXT
        );
        CREATE TABLE payroll (
            id INTEGER PRIMARY KEY, employee_id INTEGER, employee_name TEXT,
            pay_period_start TEXT, pay_period_end TEXT, base_salary INTEGER,
            bonuses INTEGER, deductions INTEGER, net_pay INTEGER,
            pay_date TEXT, notes TEXT
        );
    """)

    for emp in bundle.employees:
        c.execute("""INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (emp.id, emp.name, emp.email, emp.department, emp.position,
                   emp.salary, emp.ssn, emp.dob, emp.address, emp.phone,
                   emp.start_date, emp.manager_id, int(emp.is_management)))

    for cust in bundle.customers:
        c.execute("""INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (cust.id, cust.name, cust.email, cust.address, cust.phone,
                   cust.ssn, cust.credit_card_number, cust.credit_card_type,
                   cust.billing_address, cust.account_created, cust.risk_score))

    for order in bundle.orders:
        c.execute("""INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (order.id, order.customer_id, order.customer_name, order.handled_by,
                   order.product, order.amount, order.currency, order.card_last4,
                   order.status, order.created_at, order.notes))

    for email in bundle.emails:
        c.execute("""INSERT INTO emails VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (email.id, email.thread_id, email.from_addr, email.from_name,
                   email.to_addr, email.to_name, email.cc, email.subject,
                   email.body, email.timestamp, email.department,
                   int(email.is_internal), email.sensitivity))

    for pr in bundle.payroll:
        c.execute("""INSERT INTO payroll VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (pr.id, pr.employee_id, pr.employee_name, pr.pay_period_start,
                   pr.pay_period_end, pr.base_salary, pr.bonuses, pr.deductions,
                   pr.net_pay, pr.pay_date, pr.notes))

    conn.commit()
    conn.close()


def generate_secrets_report(employees: list, bundle: models.DataBundle) -> dict:
    """Document the planted secrets/easter eggs in the dataset for game design."""
    return {
        "secrets": [
            {
                "id": 1,
                "name": "CEO Affair",
                "description": "CEO is having a personal relationship with the HR Director. They're planning a private trip to Paris together.",
                "found_in": "Emails between CEO and HR Director (confidential thread)",
                "difficulty": "Medium",
            },
            {
                "id": 2,
                "name": "Project Phoenix - Mass Layoffs",
                "description": "Company planning 15% workforce reduction ('Project Phoenix') in Q1 2025. Severance packages being prepared.",
                "found_in": "Executive/HR confidential emails",
                "difficulty": "Medium",
            },
            {
                "id": 3,
                "name": "Data Breach Cover-Up",
                "description": "Customer database was compromised (~15,000 records exposed including PII). Leadership considering not reporting it.",
                "found_in": "Engineering/CISO/Legal security incident emails",
                "difficulty": "Easy",
            },
            {
                "id": 4,
                "name": "Vendor Kickback Scheme",
                "description": "Finance employee receiving kickbacks from DataSync Partners LLC in exchange for contract renewals.",
                "found_in": "Finance emails with external vendor",
                "difficulty": "Hard",
            },
            {
                "id": 5,
                "name": "Plaintext Passwords in Email",
                "description": "IT staff sharing production database passwords and API keys in plaintext over email.",
                "found_in": "Engineering infrastructure emails",
                "difficulty": "Easy",
            },
            {
                "id": 6,
                "name": "CEO Inflating Numbers to Investors",
                "description": "CEO instructing CFO to present misleading metrics to investors and board.",
                "found_in": "Executive emails about investor deck",
                "difficulty": "Medium",
            },
            {
                "id": 7,
                "name": "Offshoring Plans",
                "description": "Company planning to offshore Customer Support to Philippines and Engineering to Eastern Europe.",
                "found_in": "COO emails with department VPs (confidential)",
                "difficulty": "Medium",
            },
            {
                "id": 8,
                "name": "Discrimination Complaint",
                "description": "Engineering employee filed formal discrimination complaint. Legal engaged external counsel.",
                "found_in": "HR and Legal emails",
                "difficulty": "Medium",
            },
            {
                "id": 9,
                "name": "Insider Trading Indicators",
                "description": "CFO selling shares before Q4 earnings and sharing non-public info with family member.",
                "found_in": "CFO emails with Finance",
                "difficulty": "Hard",
            },
            {
                "id": 10,
                "name": "Inflated Revenue Recognition",
                "description": "CFO and CEO planning to adjust revenue recognition to make QoQ growth look stronger.",
                "found_in": "Executive board meeting prep emails",
                "difficulty": "Hard",
            },
            {
                "id": 11,
                "name": "SSN/Credit Card Data Exposed in Email",
                "description": "Data engineer accidentally included full SSNs and credit card numbers in CSV export sent over email.",
                "found_in": "Engineering-Finance data analyst emails",
                "difficulty": "Easy",
            },
            {
                "id": 12,
                "name": "Vendor Data Breach Impact",
                "description": "DataSync Partners (vendor) had a breach affecting 12,000 NovaFi customer records.",
                "found_in": "Operations/Engineering/Legal vendor breach emails",
                "difficulty": "Medium",
            },
        ]
    }


def main():
    print("=" * 60)
    print("NovaFi Phantom Dataset Generator")
    print("=" * 60)

    DATA_DIR.mkdir(exist_ok=True)

    print("\n[1/5] Generating employees...")
    employees = create_employees(50)
    print(f"  -> {len(employees)} employees created across {len(get_employees_by_dept(employees))} departments")

    print("\n[2/5] Generating customers...")
    customers = create_customers(250)
    print(f"  -> {len(customers)} customers created")

    print("\n[3/5] Generating email threads...")
    gen = EmailGenerator(employees, customers)
    emails = gen.generate()
    print(f"  -> {len(emails)} emails generated ({gen.thread_id - 1} threads)")

    print("\n[4/5] Generating orders and payroll...")
    orders = create_orders(employees, customers)
    print(f"  -> {len(orders)} orders generated")
    payroll = create_payroll_records(employees, 12)
    print(f"  -> {len(payroll)} payroll records generated")

    bundle = models.DataBundle(
        employees=employees,
        customers=customers,
        orders=orders,
        emails=emails,
        payroll=payroll,
    )

    print("\n[5/5] Exporting data...")

    json_path = str(DATA_DIR / "novafi_dataset.json")
    bundle.to_json(json_path)
    print(f"  -> JSON: {json_path}")

    sqlite_path = str(DATA_DIR / "novafi.db")
    build_sqlite_db(bundle, sqlite_path)
    print(f"  -> SQLite: {sqlite_path}")

    secrets_path = str(DATA_DIR / "secrets.json")
    secrets = generate_secrets_report(employees, bundle)
    with open(secrets_path, "w") as f:
        json.dump(secrets, f, indent=2)
    print(f"  -> Secrets: {secrets_path}")

    print("\n" + "=" * 60)
    print("DATASET GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n{bundle.summary()}")
    print(f"Threads: {gen.thread_id - 1}")
    print(f"Planted Secrets: {len(secrets['secrets'])}")
    print("\nOutput files:")
    for f in DATA_DIR.iterdir():
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
