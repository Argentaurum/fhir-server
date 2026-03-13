import glob
import logging
import os
import shutil
from datetime import datetime

from flask import Blueprint, current_app, jsonify

from app.extensions import db

admin_bp = Blueprint("admin", __name__)
logger = logging.getLogger("admin")

MAX_BACKUPS = 3


@admin_bp.post("/reset")
def reset():
    """Wipe every table and start fresh.

    If the database is a SQLite file, a timestamped backup is created first.
    At most MAX_BACKUPS backups are kept; older ones are removed automatically.
    """
    backup = _backup_db()

    db.drop_all()
    db.create_all()

    logger.warning("Database reset by request from /reset")

    return jsonify({
        "status": "ok",
        "message": "Database wiped and recreated.",
        "backup": backup,
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _backup_db():
    """Copy the SQLite .db file to a timestamped backup file.

    Returns the backup path on success, or None if the database is not a
    SQLite file (e.g. in-memory or PostgreSQL).
    """
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if not uri.startswith("sqlite:///") or uri == "sqlite:///:memory:":
        return None

    db_path = uri[len("sqlite:///"):]
    if not os.path.isabs(db_path):
        db_path = os.path.join(current_app.root_path, db_path)

    if not os.path.exists(db_path):
        return None

    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"fhir_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    logger.info("Created backup: %s", backup_path)

    # Rolling window — drop anything beyond the most recent MAX_BACKUPS
    all_backups = sorted(glob.glob(os.path.join(backup_dir, "fhir_*.db")))
    for stale in all_backups[:-MAX_BACKUPS]:
        os.remove(stale)
        logger.info("Removed old backup: %s", stale)

    return backup_path
