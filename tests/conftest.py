import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("test")
    yield app


@pytest.fixture(autouse=True)
def db(app):
    """Create fresh tables for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_patient():
    return {
        "resourceType": "Patient",
        "name": [{"family": "Smith", "given": ["John"]}],
        "gender": "male",
        "birthDate": "1990-01-15",
        "identifier": [
            {"system": "http://example.com/mrn", "value": "MRN123"}
        ],
        "address": [
            {
                "line": ["123 Main St"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62704",
            }
        ],
    }


@pytest.fixture
def sample_observation():
    return {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate",
                }
            ]
        },
        "valueQuantity": {
            "value": 72,
            "unit": "beats/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min",
        },
        "effectiveDateTime": "2024-06-15T10:30:00Z",
    }
