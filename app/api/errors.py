from flask import jsonify


class FHIRError(Exception):
    """Base FHIR error that produces an OperationOutcome."""

    def __init__(self, status_code, severity, code, diagnostics):
        self.status_code = status_code
        self.severity = severity
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(diagnostics)


class ResourceNotFoundError(FHIRError):
    def __init__(self, resource_type, fhir_id):
        super().__init__(
            404, "error", "not-found",
            f"{resource_type}/{fhir_id} not found",
        )


class ResourceGoneError(FHIRError):
    def __init__(self, resource_type, fhir_id):
        super().__init__(
            410, "error", "deleted",
            f"{resource_type}/{fhir_id} has been deleted",
        )


class ValidationError(FHIRError):
    def __init__(self, diagnostics):
        super().__init__(400, "error", "invalid", diagnostics)


class BadRequestError(FHIRError):
    def __init__(self, diagnostics):
        super().__init__(400, "error", "invalid", diagnostics)


class UnsupportedResourceError(FHIRError):
    def __init__(self, resource_type):
        super().__init__(
            404, "error", "not-supported",
            f"Resource type '{resource_type}' is not supported",
        )


class PreconditionFailedError(FHIRError):
    def __init__(self, diagnostics="Multiple matches found for conditional operation"):
        super().__init__(412, "error", "multiple-matches", diagnostics)


def make_operation_outcome(severity, code, diagnostics):
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "diagnostics": diagnostics,
            }
        ],
    }


def register_error_handlers(app):
    @app.errorhandler(FHIRError)
    def handle_fhir_error(e):
        body = make_operation_outcome(e.severity, e.code, e.diagnostics)
        return jsonify(body), e.status_code

    @app.errorhandler(404)
    def handle_404(e):
        body = make_operation_outcome("error", "not-found", "Endpoint not found")
        return jsonify(body), 404

    @app.errorhandler(405)
    def handle_405(e):
        body = make_operation_outcome(
            "error", "not-supported", "Method not allowed"
        )
        return jsonify(body), 405

    @app.errorhandler(500)
    def handle_500(e):
        body = make_operation_outcome(
            "fatal", "exception", "Internal server error"
        )
        return jsonify(body), 500
