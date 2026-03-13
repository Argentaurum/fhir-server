from app.extensions import db


class StringIndex(db.Model):
    """String search parameter index — mirrors HAPI's HFJ_SPIDX_STRING."""

    __tablename__ = "hfj_spidx_string"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    res_type = db.Column(db.String(40), nullable=False)
    param_name = db.Column(db.String(100), nullable=False)
    value_normalized = db.Column(db.String(200))  # lowercased
    value_exact = db.Column(db.String(200))

    __table_args__ = (
        db.Index("ix_spidx_string_lookup", "res_type", "param_name", "value_normalized"),
    )

    resource = db.relationship("ResourceEntity", back_populates="string_indexes")


class TokenIndex(db.Model):
    """Token search parameter index — mirrors HAPI's HFJ_SPIDX_TOKEN."""

    __tablename__ = "hfj_spidx_token"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    res_type = db.Column(db.String(40), nullable=False)
    param_name = db.Column(db.String(100), nullable=False)
    system = db.Column(db.String(200))
    value = db.Column(db.String(200))

    __table_args__ = (
        db.Index("ix_spidx_token_lookup", "res_type", "param_name", "system", "value"),
    )

    resource = db.relationship("ResourceEntity", back_populates="token_indexes")


class DateIndex(db.Model):
    """Date search parameter index — mirrors HAPI's HFJ_SPIDX_DATE."""

    __tablename__ = "hfj_spidx_date"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    res_type = db.Column(db.String(40), nullable=False)
    param_name = db.Column(db.String(100), nullable=False)
    value_low = db.Column(db.DateTime)
    value_high = db.Column(db.DateTime)

    __table_args__ = (
        db.Index("ix_spidx_date_lookup", "res_type", "param_name", "value_low", "value_high"),
    )

    resource = db.relationship("ResourceEntity", back_populates="date_indexes")


class QuantityIndex(db.Model):
    """Quantity search parameter index — mirrors HAPI's HFJ_SPIDX_QUANTITY."""

    __tablename__ = "hfj_spidx_quantity"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    res_type = db.Column(db.String(40), nullable=False)
    param_name = db.Column(db.String(100), nullable=False)
    system = db.Column(db.String(200))
    units = db.Column(db.String(100))
    value = db.Column(db.Float)

    __table_args__ = (
        db.Index("ix_spidx_quantity_lookup", "res_type", "param_name", "value"),
    )

    resource = db.relationship("ResourceEntity", back_populates="quantity_indexes")


class CompositeIndex(db.Model):
    """Composite search parameter index — hfj_spidx_composite."""

    __tablename__ = "hfj_spidx_composite"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("hfj_resource.id", ondelete="CASCADE"), nullable=False
    )
    res_type = db.Column(db.String(40), nullable=False)
    param_name = db.Column(db.String(100), nullable=False)
    comp1_system = db.Column(db.String(200))
    comp1_value = db.Column(db.String(200))
    comp2_system = db.Column(db.String(200))
    comp2_value = db.Column(db.String(200))

    __table_args__ = (
        db.Index("ix_spidx_composite_lookup", "res_type", "param_name", "comp1_value", "comp2_value"),
    )

    resource = db.relationship("ResourceEntity", back_populates="composite_indexes")
