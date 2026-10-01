"""Small reader-facing contracts; no receiver fitting or optimizer code.

These checks make source, row-order, receiver-order and coordinate availability
explicit. A passed contract proves only its stated invariant.
"""
from __future__ import annotations
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import math
from pathlib import Path
import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def require_rows(actual: Sequence[int], expected: Sequence[int]) -> None:
    a, b = list(actual), list(expected)
    if len(a) != len(set(a)):
        raise ValueError('Duplicate CSV source-row identities')
    if a != b:
        raise ValueError('Source-row membership/order differs; equal counts are insufficient')


def require_source(actual_sha: str, expected_sha: str) -> None:
    if actual_sha != expected_sha:
        raise ValueError('Source payload differs; zero-based row IDs are not portable between payloads')


def require_multiplicity(csv_keys: Iterable, json_keys: Iterable) -> None:
    c, j = Counter(csv_keys), Counter(json_keys)
    if any(count > j[key] for key, count in c.items()):
        raise ValueError('CSV occurrence count exceeds matching JSON occurrences')


def require_same_group_maps(maps: Sequence[Mapping[str, float]]) -> None:
    if maps and any(dict(m) != dict(maps[0]) for m in maps[1:]):
        raise ValueError('Serialization key is ambiguous: gateway/RSSI maps disagree')


def require_unique_linkage(mapping: Mapping[str, str]) -> None:
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Two active receiver columns map to one identifier')
    if not all(isinstance(k, str) and isinstance(v, str) and v for k, v in mapping.items()):
        raise ValueError('Receiver/gateway identifiers must remain strings')


def select_receptions(receptions: Mapping[str, float], roster: set[str]) -> list[tuple[str, float]]:
    """Declared baseline rule: numerical BS order, stable descending raw RSSI, k<=10."""
    good = [(b, float(receptions[b])) for b in sorted(roster, key=int)
            if b in receptions and math.isfinite(float(receptions[b]))
            and -150 <= float(receptions[b]) <= -20]
    good.sort(key=lambda pair: -pair[1])
    return good[:10]


def centroid(selected: Sequence[tuple[str, float]], coords: Mapping[str, Sequence[float]]) -> np.ndarray:
    if not selected:
        raise ValueError('No selected observations')
    if any(b not in coords or coords[b] is None for b, _ in selected):
        raise ValueError('A selected receiver lacks coordinates; no implicit imputation or reselection')
    xy = np.asarray([coords[b] for b, _ in selected], dtype=float)
    r = np.asarray([v for _, v in selected], dtype=float)
    if xy.shape != (len(selected), 2) or not np.isfinite(xy).all():
        raise ValueError('Invalid coordinate array')
    w = np.power(10., (r - r.max()) / 10.)
    return (xy * w[:, None]).sum(axis=0) / w.sum()
