"""Data / blinding gate of the purity + data/MC package. A beam-on sample can be plotted only if ``configs/data_policy.yaml`` allows its stage kind;
the signal region (final frozen selection) additionally needs a named approver. The gate raises: a plot can never silently become an unblinding."""
from __future__ import annotations
from pathlib import Path
import yaml

STAGE_KINDS = ("preselection", "sideband", "signal_region")
POLICY_FILE = Path(__file__).resolve().parents[2] / "configs" / "data_policy.yaml"


class PolicyError(RuntimeError):
    pass


def load_policy(path: Path | None = None) -> dict:
    return yaml.safe_load(Path(path or POLICY_FILE).read_text())


def check(sample: str, stage_kind: str, policy: dict | None = None) -> None:
    """Raise PolicyError unless ``sample`` data may be shown at ``stage_kind``. MC samples are never gated."""
    if stage_kind not in STAGE_KINDS:
        raise ValueError(f"unknown stage kind {stage_kind!r}")
    p = policy or load_policy()
    if sample not in p["samples"]:
        raise PolicyError(f"data sample {sample!r} has no entry in the data policy: blocked")
    s = p["samples"][sample]
    if stage_kind not in s["allowed_stage_kinds"]:
        raise PolicyError(f"{sample}: stage kind {stage_kind!r} is not allowed by the data policy (allowed: {s['allowed_stage_kinds']})")
    if stage_kind == "signal_region" and sample != "beam_off":
        sr = p.get("signal_region", {})
        if not (str(sr.get("approved_by", "")).strip() and str(sr.get("approved_date", "")).strip()):
            raise PolicyError("signal-region beam-on data are blocked: signal_region.approved_by / approved_date are empty in the data policy")


def allowed(sample: str, stage_kind: str, policy: dict | None = None) -> bool:
    try:
        check(sample, stage_kind, policy); return True
    except PolicyError:
        return False
