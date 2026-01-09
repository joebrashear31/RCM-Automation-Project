"""Shared pytest fixtures and configuration."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime
from faker import Faker

from common.db import Base, get_db
from main import app
from services.claims.models import Claim
from common.enums import ClaimStatus, PayerType

fake = Faker()


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session with in-memory SQLite."""
    # Use SQLite in-memory for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_claim_data():
    """Generate sample claim data for testing."""
    return {
        "claim_number": fake.bothify(text="CLM-####-####", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        "provider_npi": fake.numerify(text="##########"),
        "patient_id": fake.uuid4(),
        "payer_id": fake.bothify(text="PAY-#####"),
        "payer_type": PayerType.COMMERCIAL.value,
        "amount": float(fake.pydecimal(left_digits=4, right_digits=2, positive=True)),
        "cpt_codes": ["99213", "36415"],
        "icd_codes": ["E11.9", "I10"],
        "service_date_from": datetime(2024, 1, 15, 10, 0, 0).isoformat(),
        "service_date_to": datetime(2024, 1, 15, 10, 30, 0).isoformat(),
    }


@pytest.fixture
def sample_claim(db_session, sample_claim_data):
    """Create a sample claim in the database."""
    claim = Claim(
        claim_number=sample_claim_data["claim_number"],
        provider_npi=sample_claim_data["provider_npi"],
        patient_id=sample_claim_data["patient_id"],
        payer_id=sample_claim_data["payer_id"],
        payer_type=sample_claim_data["payer_type"],
        amount=sample_claim_data["amount"],
        cpt_codes=sample_claim_data["cpt_codes"],
        icd_codes=sample_claim_data["icd_codes"],
        service_date_from=sample_claim_data["service_date_from"],
        service_date_to=sample_claim_data["service_date_to"],
        status=ClaimStatus.CREATED.value,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


@pytest.fixture
def medicare_claim_data(sample_claim_data):
    """Generate Medicare claim data."""
    data = sample_claim_data.copy()
    data["payer_type"] = PayerType.MEDICARE.value
    data["cpt_codes"] = ["99213", "80053"]
    data["icd_codes"] = ["E11.9", "Z79.4"]
    return data


@pytest.fixture
def medicaid_claim_data(sample_claim_data):
    """Generate Medicaid claim data."""
    data = sample_claim_data.copy()
    data["payer_type"] = PayerType.MEDICAID.value
    return data
