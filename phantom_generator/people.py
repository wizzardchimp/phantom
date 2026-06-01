import random
from datetime import datetime, timedelta
from faker import Faker
from .models import Employee, Customer

fake = Faker()
Faker.seed(42)
random.seed(42)

COMPANY_DOMAIN = "novafi.com"

DEPARTMENTS = {
    "Executive": ["CEO", "CFO", "CTO", "COO", "CISO"],
    "Engineering": ["VP Engineering", "Senior Developer", "Developer", "Junior Developer", "DevOps Engineer", "Data Engineer", "QA Engineer", "Tech Lead"],
    "Sales": ["VP Sales", "Sales Director", "Account Executive", "Sales Representative", "Sales Operations", "Business Development"],
    "Marketing": ["VP Marketing", "Marketing Manager", "Content Strategist", "Social Media Manager", "Brand Designer", "SEO Specialist"],
    "Customer Support": ["VP Customer Success", "Support Manager", "Senior Support Agent", "Support Agent", "Support Agent", "Support Agent"],
    "Human Resources": ["VP HR", "HR Manager", "HR Coordinator", "Recruiter", "Payroll Specialist"],
    "Finance": ["VP Finance", "Finance Manager", "Senior Accountant", "Accountant", "Accounts Payable", "Financial Analyst"],
    "Legal": ["General Counsel", "Compliance Officer", "Paralegal", "Privacy Analyst"],
    "Operations": ["VP Operations", "Operations Manager", "Facilities Coordinator", "Procurement Specialist", "Logistics Coordinator"],
}

MANAGEMENT_POSITIONS = {
    "CEO", "CFO", "CTO", "COO", "CISO",
    "VP Engineering", "VP Sales", "VP Marketing", "VP Customer Success",
    "VP HR", "VP Finance", "VP Operations",
    "General Counsel",
    "Sales Director", "Support Manager", "HR Manager", "Finance Manager",
    "Operations Manager", "Marketing Manager", "Compliance Officer",
    "Tech Lead",
}


def create_employees(count: int = 45) -> list[Employee]:
    employees = []
    emp_id = 1

    dept_heads = {}
    dept_roster = {}

    for dept, roles in DEPARTMENTS.items():
        dept_roster[dept] = []
        for role in roles:
            name = fake.name()
            email = f"{name.lower().replace(' ', '.').replace('.', '.')}@{COMPANY_DOMAIN}"
            email = email.replace("..", ".")

            is_mgmt = role in MANAGEMENT_POSITIONS
            salary = random.randint(
                65000 if not is_mgmt else 140000,
                120000 if not is_mgmt else 350000,
            )

            start_date = fake.date_between(start_date="-8y", end_date="-3m")

            ssn = f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"

            emp = Employee(
                id=emp_id,
                name=name,
                email=email,
                department=dept,
                position=role,
                salary=salary,
                ssn=ssn,
                dob=fake.date_of_birth(minimum_age=24, maximum_age=65).isoformat(),
                address=fake.address().replace("\n", ", "),
                phone=fake.phone_number(),
                start_date=start_date.isoformat(),
                is_management=is_mgmt,
            )
            employees.append(emp)

            if is_mgmt and dept not in dept_heads:
                dept_heads[dept] = emp

            dept_roster[dept].append(emp)
            emp_id += 1

    for emp in employees:
        if emp.department in dept_heads and emp != dept_heads[emp.department]:
            emp.manager_id = dept_heads[emp.department].id

    return employees


def create_customers(count: int = 200) -> list[Customer]:
    customers = []
    card_types = ["Visa", "Mastercard", "American Express", "Discover"]

    for i in range(1, count + 1):
        name = fake.name()
        credit_card = fake.credit_card_number()
        customers.append(Customer(
            id=i,
            name=name,
            email=fake.email(),
            address=fake.address().replace("\n", ", "),
            phone=fake.phone_number(),
            ssn=f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
            credit_card_number=credit_card,
            credit_card_type=random.choice(card_types),
            billing_address=fake.address().replace("\n", ", "),
            account_created=fake.date_between(start_date="-5y", end_date="-1m").isoformat(),
            risk_score=random.randint(10, 95),
        ))
    return customers


def get_employees_by_dept(employees: list[Employee]) -> dict[str, list[Employee]]:
    depts = {}
    for emp in employees:
        depts.setdefault(emp.department, []).append(emp)
    return depts
