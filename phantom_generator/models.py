from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class Employee:
    id: int
    name: str
    email: str
    department: str
    position: str
    salary: int
    ssn: str
    dob: str
    address: str
    phone: str
    start_date: str
    manager_id: Optional[int] = None
    is_management: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class Customer:
    id: int
    name: str
    email: str
    address: str
    phone: str
    ssn: str
    credit_card_number: str
    credit_card_type: str
    billing_address: str
    account_created: str
    risk_score: int = 50

    def to_dict(self):
        return asdict(self)


@dataclass
class Order:
    id: int
    customer_id: int
    customer_name: str
    handled_by: Optional[int]
    product: str
    amount: float
    currency: str
    card_last4: str
    status: str
    created_at: str
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Email:
    id: int
    thread_id: int
    from_addr: str
    from_name: str
    to_addr: str
    to_name: str
    cc: str
    subject: str
    body: str
    timestamp: str
    department: str
    is_internal: bool
    sensitivity: str = "normal"

    def to_dict(self):
        return asdict(self)

    def to_rag_text(self) -> str:
        return f"From: {self.from_name} <{self.from_addr}>\nTo: {self.to_name} <{self.to_addr}>\nCc: {self.cc}\nSubject: {self.subject}\nDate: {self.timestamp}\n\n{self.body}"


@dataclass
class PayrollRecord:
    id: int
    employee_id: int
    employee_name: str
    pay_period_start: str
    pay_period_end: str
    base_salary: int
    bonuses: int
    deductions: int
    net_pay: int
    pay_date: str
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class DataBundle:
    employees: list[Employee]
    customers: list[Customer]
    orders: list[Order]
    emails: list[Email]
    payroll: list[PayrollRecord]
    company_name: str = "NovaFi Financial Solutions"
    company_domain: str = "novafi.com"

    def to_json(self, path: str):
        data = {
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "employees": [e.to_dict() for e in self.employees],
            "customers": [c.to_dict() for c in self.customers],
            "orders": [o.to_dict() for o in self.orders],
            "emails": [e.to_dict() for e in self.emails],
            "payroll": [p.to_dict() for p in self.payroll],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def summary(self) -> str:
        return (
            f"Company: {self.company_name}\n"
            f"Employees: {len(self.employees)}\n"
            f"Customers: {len(self.customers)}\n"
            f"Orders: {len(self.orders)}\n"
            f"Emails: {len(self.emails)}\n"
            f"Payroll Records: {len(self.payroll)}"
        )
