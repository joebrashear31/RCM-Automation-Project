🧾 RCM Workflow Engine

Async, event-driven backend for medical claims lifecycle management and denial automation

The RCM Workflow Engine is a backend system that models the end-to-end revenue cycle management (RCM) process for healthcare providers. It focuses on claims state transitions, payer rule validation, and denial workflows, with the goal of reducing administrative overhead and improving time-to-cash.

This project is inspired by real-world healthcare billing systems and is designed to reflect production-grade backend patterns used in modern healthcare fintech companies.

🚨 Problem Statement

Medical billing is one of the most complex and costly administrative processes in the U.S. healthcare system. Providers must navigate:

Payer-specific billing rules

Complex CPT / ICD code combinations

Claim rejections vs denials

Manual resubmissions and appeals

Poor visibility into claim status and revenue leakage

As a result, healthcare organizations spend billions annually on administrative overhead just to get paid.

🎯 Project Goals

This project aims to:

Model the full lifecycle of a medical claim

Enforce state-based workflows instead of ad-hoc updates

Automate payer rule validation and denial classification

Support async background processing for long-running tasks

Expose financial and operational analytics relevant to RCM teams

🏗️ System Architecture
Client / API Consumer
        │
        ▼
 FastAPI Gateway
        │
        ▼
 Claims Service ──────► Postgres
        │
        ▼
 Rules Engine
        │
        ▼
 Denials Engine
        │
        ▼
 Celery Workers ──────► Redis

🔄 Claim Lifecycle

Each medical claim is modeled as a finite state machine:

CREATED
  ↓
VALIDATED
  ↓
SUBMITTED
  ↓
ACCEPTED ──► PAID
   │
   └──► DENIED ──► RESUBMITTED


State transitions are explicitly enforced at the service layer to ensure data integrity and auditability.

🧱 Tech Stack
Backend

Python 3.11

FastAPI

Pydantic v2

SQLAlchemy 2.0

Celery + Redis

PostgreSQL

Infrastructure

Docker & Docker Compose

Async task queues

Structured logging

Health checks and retries

📁 Project Structure
rcm-backend/
│
├── services/
│   ├── claims/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routes.py
│   │   └── state_machine.py
│   │
│   ├── rules/
│   │   └── validator.py
│   │
│   └── denials/
│       └── classifier.py
│
├── common/
│   ├── db.py
│   ├── celery_app.py
│   └── enums.py
│
├── docker-compose.yml
├── requirements.txt
└── README.md

🧪 Data

This project is designed to work with synthetic claims data (e.g., CMS SynPUF-style datasets) to simulate realistic payer workflows while avoiding PHI.

📊 Analytics (Planned)

Claim acceptance and denial rates

Time-to-cash metrics

Denial reasons by payer

Revenue at risk due to denials

🚧 Current Status

This project is under active development. Initial focus is on:

Claim ingestion and validation

Explicit claim state management

Background denial workflows

🛣️ Roadmap

 Claim ingestion API

 Payer rule validation engine

 Denial classification

 Async resubmission workflows

 Financial analytics endpoints

 Optional ML-based denial prediction

🧠 Design Philosophy

Explicit state over implicit logic

Async-first for long-running workflows

Domain-driven modeling over CRUD

Healthcare finance as a first-class concern

📜 Disclaimer

This project is for educational and demonstration purposes only. It does not process real patient data and is not intended for production use.