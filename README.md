# 🍱 Saanjh Ki Roti API

A production-ready FastAPI backend for managing a home-cooked tiffin subscription business. This project provides APIs for customer management, subscription plans, deliveries, billing, complaints, reporting, and analytics.

---

## 📖 Overview

Saanjh Ki Roti is a home-cooked tiffin service based in Kota. The goal of this project is to digitize daily operations by replacing manual notebook-based management with a scalable backend system.

The API supports customer subscriptions, meal planning, delivery tracking, payment management, complaint handling, and automated reporting.

---

## ✨ Features

- Customer Management
- Subscription Plans
- Pause & Resume Subscription
- Meal Add-ons
- Delivery Route Management
- Delivery Status Tracking
- Billing & Payments
- Referral Discounts
- Complaint Management
- Monthly PDF Reports
- Dashboard Analytics
- Document Upload (Aadhaar / Driving License)
- Role-Based Access Control (Admin, Delivery Staff, Customer)
- JWT Authentication
- RESTful APIs
- Swagger Documentation

---

## 🛠 Tech Stack

- FastAPI
- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT Authentication
- Docker
- Pytest

---

## 🏗 Project Architecture

This project follows Clean Architecture with a layered structure.

- API Layer
- Service Layer
- Repository Layer
- Database Layer

---

## 📂 Project Structure

```text
app/
├── api/
├── core/
├── database/
├── models/
├── schemas/
├── services/
├── repositories/
├── routers/
├── middleware/
├── utils/
├── tests/
└── main.py
```

---

## 🚀 Getting Started

### Clone the Repository

```bash
git clone https://github.com/<your-username>/saanjh-ki-roti-api.git
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file.

Example:

```env
DATABASE_URL=
SECRET_KEY=
JWT_ALGORITHM=
ACCESS_TOKEN_EXPIRE_MINUTES=
SMTP_EMAIL=
SMTP_PASSWORD=
```

### Run Server

```bash
uvicorn app.main:app --reload
```

---

## 📚 API Documentation

After running the server:

- Swagger UI → `/docs`
- ReDoc → `/redoc`

---

## 🧪 Testing

```bash
pytest
```

---

## 📈 Roadmap

- Customer Mobile APIs
- Push Notifications
- Inventory Management
- Online Payments
- Route Optimization
- Customer Self-Service Portal

---

## 🤝 Contributing

Contributions are welcome through Pull Requests.

---

## 📄 License

This project is licensed under the MIT License.
