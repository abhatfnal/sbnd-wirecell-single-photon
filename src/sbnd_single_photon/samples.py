"""Sample registry (configs/samples.yaml) and file manifests (manifests/*.tsv.gz)."""
from __future__ import annotations

import gzip
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLES_YAML = REPO_ROOT / "configs" / "samples.yaml"


@dataclass(frozen=True)
class Sample:
    name: str
    status: str                       # "available" | "wc_merged_caf_pending" | "remains_on_aurora"
    role: str = ""                    # background_evaluation | data_validation | signal_evaluation | training_development ...
    may_train: Optional[bool] = None
    may_evaluate: Optional[bool] = None
    is_mc: Optional[bool] = None
    label: str = ""
    production: str = ""
    schema_md5: Optional[str] = None
    manifest: Optional[str] = None
    n_files_listed: Optional[int] = None
    n_caf_events: Optional[int] = None
    n_wc_valid_events: Optional[int] = None
    extra: dict = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.status == "available"


def load_samples(path: Path | str = DEFAULT_SAMPLES_YAML) -> dict[str, Sample]:
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    known = {"status", "is_mc", "label", "production", "schema_md5", "manifest",
             "n_files_listed", "n_caf_events", "n_wc_valid_events", "role", "may_train", "may_evaluate"}
    out = {}
    for name, d in raw["samples"].items():
        kw = {k: d[k] for k in known if k in d}
        kw.setdefault("status", "available")
        extra = {k: v for k, v in d.items() if k not in known}
        out[name] = Sample(name=name, extra=extra, **kw)
    return out


def read_manifest(path: Path | str) -> list[dict]:
    """Rows of ``index, pnfs_path, xrootd_url`` in the ORIGINAL list order."""
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    opener = gzip.open if p.suffix == ".gz" else open
    rows = []
    with opener(p, "rt") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip() or line.startswith("index\t"):
                continue
            i, pnfs, url = line.rstrip("\n").split("\t")
            rows.append({"index": int(i), "pnfs_path": pnfs, "url": url})
    return rows


def manifest_urls(sample: Sample, start: int = 0, stop: Optional[int] = None) -> list[str]:
    if not sample.available or not sample.manifest:
        raise ValueError(f"sample {sample.name!r} has no usable manifest (status={sample.status})")
    rows = read_manifest(sample.manifest)
    return [r["url"] for r in rows[start:stop]]


def iter_manifest_urls(sample: Sample) -> Iterator[str]:
    yield from manifest_urls(sample)
