"""Terminology service for CodeSystem/$lookup and ValueSet/$validate-code."""

import json
from app.models.resource import ResourceEntity


class TerminologyService:
    """Queries stored CodeSystem and ValueSet resources for terminology operations."""

    def lookup(self, system=None, code=None, version=None):
        """CodeSystem/$lookup — find a code in a stored CodeSystem.

        Returns an OperationOutcome-style Parameters resource or None.
        """
        if not system and not code:
            return None

        # Find the CodeSystem by URL
        query = ResourceEntity.query.filter_by(
            res_type="CodeSystem", is_deleted=False
        )

        cs_entities = query.all()
        for entity in cs_entities:
            cs = json.loads(entity.res_text)
            cs_url = cs.get("url", "")

            if system and cs_url != system:
                continue
            if version and cs.get("version") != version:
                continue

            # Search concepts
            match = self._find_concept(cs.get("concept", []), code)
            if match:
                return {
                    "resourceType": "Parameters",
                    "parameter": [
                        {"name": "name", "valueString": cs.get("name", cs_url)},
                        {"name": "version", "valueString": cs.get("version", "")},
                        {"name": "display", "valueString": match.get("display", "")},
                        {"name": "code", "valueCode": match.get("code", code)},
                        {"name": "system", "valueUri": cs_url},
                    ],
                }

        return None

    def validate_code(self, url=None, system=None, code=None, display=None):
        """ValueSet/$validate-code — check if a code is in a ValueSet.

        Returns a Parameters resource with result boolean.
        """
        if not url and not system:
            return self._validation_result(False, "No url or system provided")

        # Find the ValueSet by URL
        vs_entities = ResourceEntity.query.filter_by(
            res_type="ValueSet", is_deleted=False
        ).all()

        for entity in vs_entities:
            vs = json.loads(entity.res_text)
            if url and vs.get("url") != url:
                continue

            # Check compose.include
            for include in vs.get("compose", {}).get("include", []):
                inc_system = include.get("system", "")
                if system and inc_system != system:
                    continue

                # If there's a concept list, check it
                concepts = include.get("concept", [])
                if concepts:
                    for concept in concepts:
                        if concept.get("code") == code:
                            return self._validation_result(
                                True, concept.get("display", ""),
                                display_match=(display == concept.get("display")) if display else True,
                            )
                else:
                    # No concept list means all codes from system are included
                    # Try to look up in the CodeSystem
                    result = self.lookup(system=inc_system, code=code)
                    if result:
                        return self._validation_result(True, "Code found in included system")

            # Check expansion
            for contains in vs.get("expansion", {}).get("contains", []):
                if system and contains.get("system") != system:
                    continue
                if contains.get("code") == code:
                    return self._validation_result(True, contains.get("display", ""))

        return self._validation_result(False, "Code not found in ValueSet")

    def _find_concept(self, concepts, code):
        """Recursively search for a code in a concept hierarchy."""
        for concept in concepts:
            if concept.get("code") == code:
                return concept
            # Check nested concepts
            nested = concept.get("concept", [])
            if nested:
                result = self._find_concept(nested, code)
                if result:
                    return result
        return None

    def _validation_result(self, result, message, display_match=True):
        """Build a Parameters resource for validation result."""
        params = [
            {"name": "result", "valueBoolean": result},
        ]
        if message:
            params.append({"name": "message", "valueString": message})
        if result and not display_match:
            params.append({"name": "display", "valueString": "Display mismatch"})
        return {
            "resourceType": "Parameters",
            "parameter": params,
        }


terminology_service = TerminologyService()
