"""Bulk Data Export processor.

Implements the FHIR Bulk Data Export pattern:
  1. Kick-off: POST returns 202 + Content-Location
  2. Poll: GET status endpoint → 202 (in-progress) or 200 (complete with download links)
  3. Download: GET ndjson file content
"""

import json
import uuid
import threading
import logging
from datetime import datetime, timezone

from app.models.resource import ResourceEntity
from app.utils.fhir_types import SUPPORTED_RESOURCE_TYPES

logger = logging.getLogger("fhir.bulk_export")


class BulkExportProcessor:
    """Manages bulk export jobs."""

    def __init__(self):
        self._jobs = {}  # job_id -> job state
        self._lock = threading.Lock()

    def kick_off(self, export_type="system", type_filter=None, since=None, patient_ids=None):
        """Start a bulk export job.

        Args:
            export_type: "system" or "patient"
            type_filter: comma-separated resource types to include
            since: ISO datetime — only resources updated after this
            patient_ids: list of patient IDs for Patient-level export

        Returns:
            job_id
        """
        job_id = str(uuid.uuid4())

        job = {
            "id": job_id,
            "status": "in-progress",
            "export_type": export_type,
            "type_filter": type_filter,
            "since": since,
            "patient_ids": patient_ids,
            "request_time": datetime.now(timezone.utc).isoformat(),
            "output": [],
            "error": [],
        }

        with self._lock:
            self._jobs[job_id] = job

        return job_id

    def process(self, job_id, app):
        """Process a bulk export job (run in app context).

        Generates ndjson data for each resource type.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

        try:
            with app.app_context():
                self._do_export(job)
        except Exception as e:
            logger.error("Bulk export job %s failed: %s", job_id, str(e))
            with self._lock:
                job["status"] = "error"
                job["error"].append({
                    "type": "OperationOutcome",
                    "url": "",
                    "diagnostics": str(e),
                })

    def _do_export(self, job):
        """Perform the actual export."""
        export_type = job["export_type"]
        type_filter = job.get("type_filter")
        since = job.get("since")
        patient_ids = job.get("patient_ids")

        # Determine resource types to export
        if type_filter:
            resource_types = [t.strip() for t in type_filter.split(",")]
        elif export_type == "patient":
            # Patient-level export: Patient and related types
            resource_types = [
                "Patient", "Observation", "Condition", "Procedure",
                "Encounter", "MedicationRequest", "AllergyIntolerance",
                "DiagnosticReport", "Immunization", "ServiceRequest",
            ]
        else:
            resource_types = sorted(SUPPORTED_RESOURCE_TYPES)

        output_files = []

        for res_type in resource_types:
            if res_type not in SUPPORTED_RESOURCE_TYPES:
                continue

            query = ResourceEntity.query.filter_by(
                res_type=res_type, is_deleted=False
            )

            if since:
                from app.utils.datetime_utils import parse_fhir_date_to_range
                since_dt, _ = parse_fhir_date_to_range(since)
                if since_dt:
                    query = query.filter(ResourceEntity.last_updated >= since_dt)

            # For patient-level export, filter by patient references
            if export_type == "patient" and patient_ids and res_type != "Patient":
                from app.models.resource_link import ResourceLink
                patient_linked = (
                    ResourceEntity.query
                    .join(ResourceLink, ResourceLink.src_resource_id == ResourceEntity.id)
                    .filter(
                        ResourceEntity.res_type == res_type,
                        ResourceEntity.is_deleted == False,  # noqa: E712
                        ResourceLink.target_resource_type == "Patient",
                        ResourceLink.target_fhir_id.in_(patient_ids),
                    )
                )
                if since:
                    from app.utils.datetime_utils import parse_fhir_date_to_range
                    since_dt, _ = parse_fhir_date_to_range(since)
                    if since_dt:
                        patient_linked = patient_linked.filter(
                            ResourceEntity.last_updated >= since_dt
                        )
                entities = patient_linked.all()
            elif export_type == "patient" and patient_ids and res_type == "Patient":
                entities = query.filter(
                    ResourceEntity.fhir_id.in_(patient_ids)
                ).all()
            else:
                entities = query.all()

            if not entities:
                continue

            # Build ndjson content
            lines = []
            for entity in entities:
                lines.append(entity.res_text)

            ndjson_content = "\n".join(lines)

            output_files.append({
                "type": res_type,
                "count": len(entities),
                "ndjson": ndjson_content,
            })

        with self._lock:
            job["output"] = output_files
            job["status"] = "complete"
            job["transaction_time"] = datetime.now(timezone.utc).isoformat()

    def get_status(self, job_id):
        """Get the status of a bulk export job."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_output(self, job_id, file_index):
        """Get a specific output file from a completed job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["status"] != "complete":
                return None
            if file_index < 0 or file_index >= len(job["output"]):
                return None
            return job["output"][file_index]

    def delete_job(self, job_id):
        """Delete a completed export job."""
        with self._lock:
            self._jobs.pop(job_id, None)


bulk_export_processor = BulkExportProcessor()
