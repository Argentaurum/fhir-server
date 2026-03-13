from datetime import datetime, timezone
from app.extensions import db


class ResourceHistory(db.Model):
    """Version history — mirrors HAPI's HFJ_RES_VER."""

    __tablename__ = "hfj_res_ver"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    fhir_id = db.Column(db.String(64), nullable=False)
    res_type = db.Column(db.String(40), nullable=False)
    version_id = db.Column(db.Integer, nullable=False)
    res_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.Index("ix_res_ver_lookup", "res_type", "fhir_id", "version_id"),
    )

    resource = db.relationship("ResourceEntity", back_populates="history")
