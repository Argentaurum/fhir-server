#!/usr/bin/env python3
"""Load Synthea transaction bundles into the FHIR server.

Usage:
    python -m scripts.load_synthea <path_to_synthea_output_dir>

Synthea generates one JSON file per patient, each containing a
transaction Bundle with Patient, Encounters, Observations, etc.
"""

import sys
import os
import json
import glob

from app import create_app
from app.fhir.bundle_processor import bundle_processor


def load_synthea(directory):
    app = create_app()

    json_files = glob.glob(os.path.join(directory, "*.json"))
    if not json_files:
        print(f"No JSON files found in {directory}")
        return

    print(f"Found {len(json_files)} Synthea bundle files")

    with app.app_context():
        loaded = 0
        errors = 0
        for filepath in json_files:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r") as f:
                    bundle = json.load(f)

                if bundle.get("resourceType") != "Bundle":
                    print(f"  Skipping {filename}: not a Bundle")
                    continue

                result = bundle_processor.process(bundle)
                entry_count = len(result.get("entry", []))
                print(f"  Loaded {filename}: {entry_count} entries")
                loaded += 1

            except Exception as e:
                print(f"  ERROR loading {filename}: {e}")
                errors += 1

        print(f"\nDone: {loaded} bundles loaded, {errors} errors")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.load_synthea <path_to_synthea_fhir_output>")
        sys.exit(1)

    load_synthea(sys.argv[1])
