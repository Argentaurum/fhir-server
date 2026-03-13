from app.extensions import db


class ResourceLink(db.Model):
    """Reference tracking — mirrors HAPI's HFJ_RES_LINK."""

    __tablename__ = "hfj_res_link"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    src_resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    src_path = db.Column(db.String(200), nullable=False)  # e.g. "Observation.subject"
    target_resource_type = db.Column(db.String(40), nullable=False)
    target_fhir_id = db.Column(db.String(64), nullable=False)

    __table_args__ = (
        db.Index("ix_res_link_src", "src_resource_id"),
        db.Index("ix_res_link_target", "target_resource_type", "target_fhir_id"),
    )

    source_resource = db.relationship(
        "ResourceEntity",
        back_populates="resource_links",
        foreign_keys=[src_resource_id],
    )
