import os


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://localhost:5000/fhir")
    FHIR_VALIDATE_ON_WRITE = True


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(Config.BASE_DIR, "..", "fhir.db"),
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    FHIR_VALIDATE_ON_WRITE = False


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///fhir.db")


configs = {
    "dev": DevConfig,
    "test": TestConfig,
    "prod": ProdConfig,
}
