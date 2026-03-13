import os
from flask import Flask
from .config import configs
from .extensions import db


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "dev")

    app = Flask(__name__)
    app.config.from_object(configs[config_name])

    db.init_app(app)

    # Import models so they're registered with SQLAlchemy
    from .models import resource, resource_history, search_index, resource_link  # noqa: F401

    # Register blueprints
    from .api.metadata import metadata_bp
    from .api.fhir_blueprint import fhir_bp
    from .api.binary import binary_bp
    from .api.batch import batch_bp
    from .api.operations import operations_bp
    from .api.bulk_export import bulk_export_bp
    from .api.admin import admin_bp
    from .api.errors import register_error_handlers

    app.register_blueprint(metadata_bp)
    app.register_blueprint(operations_bp)  # Before fhir_bp so $lookup routes match first
    app.register_blueprint(bulk_export_bp)  # Before fhir_bp so $export routes match first
    app.register_blueprint(binary_bp)       # Before fhir_bp so /Binary routes take precedence
    app.register_blueprint(fhir_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)

    # Register middleware
    from .middleware.base import interceptor_chain
    from .middleware.logging_interceptor import LoggingInterceptor
    from .middleware.validation_interceptor import ValidationInterceptor
    from .middleware.subscription_interceptor import SubscriptionInterceptor

    interceptor_chain.register(LoggingInterceptor())
    if app.config.get("FHIR_VALIDATE_ON_WRITE"):
        interceptor_chain.register(ValidationInterceptor())
    interceptor_chain.register(SubscriptionInterceptor())

    # CORS
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/fhir/*": {"origins": "*"}})
    except ImportError:
        pass

    # Create tables if using SQLite
    with app.app_context():
        db.create_all()

    return app
