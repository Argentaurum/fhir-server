from datetime import datetime, timezone
from app.extensions import db


class ResourceEntity(db.Model):
    """Core resource table — mirrors HAPI's HFJ_RESOURCE."""

    __tablename__ = "hfj_resource"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fhir_id = db.Column(db.String(64), nullable=False, index=True)
    res_type = db.Column(db.String(40), nullable=False, index=True)
    version_id = db.Column(db.Integer, nullable=False, default=1)
    res_text = db.Column(db.Text, nullable=False)  # FHIR JSON blob
    last_updated = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("res_type", "fhir_id", name="uq_resource_type_fhir_id"),
        db.Index("ix_resource_type_updated", "res_type", "last_updated"),
    )

    # Relationships
    history = db.relationship(
        "ResourceHistory", back_populates="resource", cascade="all, delete-orphan"
    )
    string_indexes = db.relationship(
        "StringIndex", back_populates="resource", cascade="all, delete-orphan"
    )
    token_indexes = db.relationship(
        "TokenIndex", back_populates="resource", cascade="all, delete-orphan"
    )
    date_indexes = db.relationship(
        "DateIndex", back_populates="resource", cascade="all, delete-orphan"
    )
    quantity_indexes = db.relationship(
        "QuantityIndex", back_populates="resource", cascade="all, delete-orphan"
    )
    resource_links = db.relationship(
        "ResourceLink",
        back_populates="source_resource",
        cascade="all, delete-orphan",
        foreign_keys="ResourceLink.src_resource_id",
    )
    composite_indexes = db.relationship(
        "CompositeIndex", back_populates="resource", cascade="all, delete-orphan"
    )
