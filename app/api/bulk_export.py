"""Bulk Data Export endpoints.

Implements:
  GET /fhir/$export           — System-level export kick-off
  GET /fhir/Patient/$export   — Patient-level export kick-off
  GET /fhir/$export-poll-status?job=<id>  — Poll for export status
  GET /fhir/$export-download?job=<id>&file=<index>  — Download ndjson
  DELETE /fhir/$export-poll-status?job=<id>  — Cancel/delete export
"""

from flask import Blueprint, request, Response, current_app

from app.api.content_negotiation import fhir_response
from app.api.errors import BadRequestError, ResourceNotFoundError
from app.fhir.bulk_export import bulk_export_processor

bulk_export_bp = Blueprint("bulk_export", __name__, url_prefix="/fhir")


@bulk_export_bp.route("/$export", methods=["GET"])
def system_export():
    """System-level bulk export: GET /fhir/$export"""
    accept = request.headers.get("Accept", "")
    prefer = request.headers.get("Prefer", "")

    type_filter = request.args.get("_type")
    since = request.args.get("_since")

    job_id = bulk_export_processor.kick_off(
        export_type="system",
        type_filter=type_filter,
        since=since,
    )

    # Process synchronously for simplicity (async pattern would use background thread)
    bulk_export_processor.process(job_id, current_app._get_current_object())

    base_url = request.host_url.rstrip("/") + "/fhir"
    poll_url = f"{base_url}/$export-poll-status?job={job_id}"

    return Response(
        status=202,
        headers={
            "Content-Location": poll_url,
        },
    )


@bulk_export_bp.route("/Patient/$export", methods=["GET"])
def patient_export():
    """Patient-level bulk export: GET /fhir/Patient/$export"""
    type_filter = request.args.get("_type")
    since = request.args.get("_since")
    patient_param = request.args.get("patient")  # comma-separated patient IDs

    patient_ids = None
    if patient_param:
        patient_ids = [p.strip() for p in patient_param.split(",")]

    job_id = bulk_export_processor.kick_off(
        export_type="patient",
        type_filter=type_filter,
        since=since,
        patient_ids=patient_ids,
    )

    # Process synchronously
    bulk_export_processor.process(job_id, current_app._get_current_object())

    base_url = request.host_url.rstrip("/") + "/fhir"
    poll_url = f"{base_url}/$export-poll-status?job={job_id}"

    return Response(
        status=202,
        headers={
            "Content-Location": poll_url,
        },
    )


@bulk_export_bp.route("/$export-poll-status", methods=["GET"])
def export_poll_status():
    """Poll export job status: GET /fhir/$export-poll-status?job=<id>"""
    job_id = request.args.get("job")
    if not job_id:
        raise BadRequestError("Missing 'job' parameter")

    job = bulk_export_processor.get_status(job_id)
    if job is None:
        raise ResourceNotFoundError("BulkExportJob", job_id)

    if job["status"] == "in-progress":
        return Response(
            status=202,
            headers={"X-Progress": "in-progress"},
        )

    if job["status"] == "error":
        return fhir_response(
            {
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "exception",
                           "diagnostics": "Export failed"}],
            },
            status_code=500,
        )

    # Complete — return manifest
    base_url = request.host_url.rstrip("/") + "/fhir"
    output = []
    for i, file_info in enumerate(job.get("output", [])):
        output.append({
            "type": file_info["type"],
            "count": file_info["count"],
            "url": f"{base_url}/$export-download?job={job_id}&file={i}",
        })

    manifest = {
        "transactionTime": job.get("transaction_time", job.get("request_time")),
        "request": f"{base_url}/$export",
        "requiresAccessToken": False,
        "output": output,
        "error": job.get("error", []),
    }

    return fhir_response(manifest)


@bulk_export_bp.route("/$export-download", methods=["GET"])
def export_download():
    """Download an export file: GET /fhir/$export-download?job=<id>&file=<index>"""
    job_id = request.args.get("job")
    file_index = request.args.get("file", type=int)

    if not job_id or file_index is None:
        raise BadRequestError("Missing 'job' or 'file' parameter")

    file_info = bulk_export_processor.get_output(job_id, file_index)
    if file_info is None:
        raise ResourceNotFoundError("ExportFile", f"{job_id}/{file_index}")

    return Response(
        file_info["ndjson"],
        mimetype="application/fhir+ndjson",
        headers={
            "Content-Type": "application/fhir+ndjson",
        },
    )


@bulk_export_bp.route("/$export-poll-status", methods=["DELETE"])
def export_delete():
    """Delete/cancel an export job: DELETE /fhir/$export-poll-status?job=<id>"""
    job_id = request.args.get("job")
    if not job_id:
        raise BadRequestError("Missing 'job' parameter")

    bulk_export_processor.delete_job(job_id)
    return Response(status=202)
