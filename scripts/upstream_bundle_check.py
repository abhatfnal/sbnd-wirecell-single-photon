#!/usr/bin/env python
"""Validate the STRUCTURE of a filled frozen-bundle manifest from Aurora (configs/frozen_bundle_manifest.template.yaml). Exit 1 and list problems if anything is missing / inconsistent with
configs/upstream_release.yaml. Evaluates nothing; does not authorise anything (authorisation is the evaluation_guard, filled by a named person).

    python scripts/upstream_bundle_check.py BUNDLE.yaml
"""
import sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import upstream_scores as US

if __name__ == "__main__":
    problems = US.validate_frozen_bundle(yaml.safe_load(Path(sys.argv[1]).read_text()))
    print("\n".join(problems) if problems else "bundle manifest structurally complete (NOT an authorisation to evaluate)"); sys.exit(1 if problems else 0)
