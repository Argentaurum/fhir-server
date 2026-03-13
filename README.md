<div align="center">

<img src="logo.svg" width="110" alt="OpenEpic — cute robot doctor mascot"/>

# OpenEpic

**A lightweight, open-source FHIR R4 server — healthcare interoperability without the enterprise overhead.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://python.org)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-e8491d)](https://www.hl7.org/fhir/R4/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black?logo=flask)](https://flask.palletsprojects.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-d71f00)](https://sqlalchemy.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/yourname/openepic/pulls)

*The FHIR server you actually want to run locally.*

</div>

---

OpenEpic is a fully spec-compliant **FHIR R4** REST server built on Python, Flask, and SQLAlchemy. It speaks the same language as Epic, Cerner, and other major EHR systems — without the six-figure license. Spin it up in minutes, seed it with synthetic data, and start building healthcare integrations right away.

## Features

- **21 FHIR Resource Types** — Patient, Encounter, Observation, Condition, Procedure, and more
- **Full CRUD + Version History** — create, read, update, delete, vread, soft deletes, and audit trail
- **Transaction & Batch Bundles** — atomic multi-resource operations in a single request
- **Advanced Search** — 50+ search parameters with string, token, date, quantity, and reference modifiers
- **Bulk Data Export** — FHIR `$export` for large-scale data pulls
- **Subscriptions** — event-driven notifications when resources change
- **Terminology Services** — CodeSystem and ValueSet with `$lookup` and `$expand`
- **Conditional Operations** — conditional create, update, and delete
- **`_include` / `_revinclude`** — fetch related resources in a single query
- **`_summary` / `_elements`** — field-level response filtering
- **CapabilityStatement** — machine-readable server capability declaration at `/fhir/metadata`

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourname/openepic.git
cd openepic
pip install -e ".[dev]"

# 2. Start the server
python run.py
# → Running on http://localhost:5000

# 3. Verify it's alive
curl http://localhost:5000/fhir/metadata | python -m json.tool
```

That's it. The server initializes a fresh SQLite database on first run. Seed it with sample data:

```bash
python -m scripts.seed_data
```

## Installation

OpenEpic requires **Python 3.11+**.

```bash
# Standard install
pip install -e .

# With development and test dependencies
pip install -e ".[dev]"
```

All dependencies are declared in `pyproject.toml`. Key libraries:

| Library | Purpose |
|---|---|
| `flask` | HTTP server and routing |
| `flask-sqlalchemy` | ORM and database integration |
| `sqlalchemy` | SQL query building |
| `fhir.resources` | FHIR R4 schema validation |
| `flask-cors` | CORS headers for browser clients |

## Configuration

Switch environments with the `FLASK_CONFIG` environment variable:

| Environment | Value | Database | Notes |
|---|---|---|---|
| Development | `dev` *(default)* | `fhir.db` (SQLite) | Debug mode on |
| Testing | `test` | `:memory:` (SQLite) | In-memory, no persistence |
| Production | `prod` | `$DATABASE_URL` | Any SQLAlchemy-compatible DB |

```bash
# Use PostgreSQL in production
export FLASK_CONFIG=prod
export DATABASE_URL=postgresql://user:pass@localhost/fhir
python run.py
```

**Optional flags:**

| Env Var | Default | Description |
|---|---|---|
| `FHIR_VALIDATE_ON_WRITE` | `true` | Validate resources against FHIR R4 schema on create/update |

## API Reference

All FHIR endpoints are mounted under `/fhir`.

### CRUD Operations

| Method | Path | Description |
|---|---|---|
| `POST` | `/fhir/{ResourceType}` | Create a resource |
| `GET` | `/fhir/{ResourceType}/{id}` | Read a resource |
| `PUT` | `/fhir/{ResourceType}/{id}` | Update (full replace) |
| `PATCH` | `/fhir/{ResourceType}/{id}` | Patch a resource |
| `DELETE` | `/fhir/{ResourceType}/{id}` | Delete a resource |
| `GET` | `/fhir/{ResourceType}/{id}/_history` | Version history |
| `GET` | `/fhir/{ResourceType}/{id}/_history/{vid}` | Read a specific version |

### Search

```
GET /fhir/Patient?name=Smith&birthdate=1990-01-15
GET /fhir/Observation?subject=Patient/123&code=8867-4
GET /fhir/Encounter?_include=Encounter:patient&status=finished
```

### System Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/fhir/metadata` | CapabilityStatement |
| `POST` | `/fhir` | Batch / transaction bundle |
| `GET` | `/fhir/$export` | Bulk data export |
| `GET` | `/fhir/_history` | System-wide history |

### Example: Create a Patient

```bash
curl -X POST http://localhost:5000/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Patient",
    "name": [{"family": "Smith", "given": ["Jane"]}],
    "gender": "female",
    "birthDate": "1990-06-15"
  }'
```

## Supported Resource Types

| | | | |
|---|---|---|---|
| AllergyIntolerance | CodeSystem | Condition | DiagnosticReport |
| DocumentReference | Encounter | Immunization | Location |
| Medication | MedicationRequest | Observation | Organization |
| Patient | Practitioner | PractitionerRole | Procedure |
| ServiceRequest | Subscription | ValueSet | |

## Scripts

Scripts live in `scripts/` and run as modules from the project root:

```bash
# Seed the database with sample patients and observations
python -m scripts.seed_data

# Load Synthea-generated synthetic FHIR bundles
python -m scripts.load_synthea /path/to/synthea/output/fhir/

# Load SNOMED CT / LOINC terminology data
python -m scripts.load_terminology
```

> **Why `-m scripts.seed_data`?** Running as a module lets Python resolve imports correctly without any `sys.path` hacks.

## Testing

The test suite uses `pytest` against an in-memory SQLite database — no setup required.

```bash
# Run all tests
pytest

# Run a specific file
pytest tests/test_search.py

# Verbose output
pytest -v

# With coverage
pytest --cov=app
```

## Architecture

```
HTTP Request
    │
    ▼
Middleware Chain
(Logging → Validation → Subscription handling)
    │
    ▼
API Blueprints
(metadata · operations · bulk_export · fhir · batch)
    │
    ▼
Resource DAO
(CRUD, versioning, conditional ops, bundle processing)
    │
    ▼
Search Engine
(query building, parameter parsing, _include/_revinclude)
    │
    ▼
SQLAlchemy Models
(ResourceEntity · SearchIndex · ResourceHistory · ResourceLink)
    │
    ▼
SQLite / PostgreSQL
```

## Contributing

Contributions are very welcome. This is an intentionally small, readable codebase — a great place to learn how FHIR servers work under the hood.

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests alongside your changes
4. Open a pull request

Please keep PRs focused. Bug fixes and spec-compliance improvements are especially appreciated.

## License

MIT

---

<div align="center">

Built with care for the people who build healthcare software.<br/>
<sub>Not affiliated with Epic Systems Corporation.</sub>

</div>
