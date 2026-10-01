"""Exact association for declared, compatible observation representations.

No source schema, radio constants, registry, location labels, outcome or training
model enters this module. Integers are canonical tokens, not measured accuracy.
Conditional correspondence is not authentication of the underlying observations.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Hashable, Sequence
import math
import re
import numpy as np


class ContractError(ValueError):
    """A refused input/association with a machine-readable reason."""
    def __init__(self, code: str, detail: object):
        self.code, self.detail = code, detail
        super().__init__(f'{code}: {detail}')


def _valid_key(key: Hashable) -> bool:
    if isinstance(key, tuple):
        return all(_valid_key(x) for x in key)
    return type(key) in (str, int, bytes) or (type(key) is float and math.isfinite(key))


@dataclass(frozen=True, order=True)
class RowHandle:
    payload_sha256: str
    source_row_index0: int

    def __post_init__(self):
        if not isinstance(self.payload_sha256, str) or not re.fullmatch('[0-9a-f]{64}', self.payload_sha256):
            raise ContractError('invalid_payload_handle', self.payload_sha256)
        if type(self.source_row_index0) is not int or self.source_row_index0 < 0:
            raise ContractError('invalid_row_index', self.source_row_index0)


@dataclass(frozen=True)
class Observations:
    rows: tuple[RowHandle, ...]
    keys: tuple[Hashable, ...]
    features: tuple[str, ...]
    values: np.ndarray
    present: np.ndarray

    def __post_init__(self):
        if len(self.rows) != len(set(self.rows)):
            raise ContractError('duplicate_row_handles', 'Physical duplicates require distinct source row handles')
        if not all(isinstance(h, RowHandle) for h in self.rows):
            raise ContractError('missing_lineage', 'RowHandle objects required')
        if len(self.keys) != len(self.rows) or not all(_valid_key(k) for k in self.keys):
            raise ContractError('invalid_record_keys', 'Use finite, explicitly canonical structured keys')
        if len(self.features) != len(set(self.features)) or not all(type(x) is str and x for x in self.features):
            raise ContractError('invalid_feature_handles', 'Distinct nonempty strings required')
        expected = (len(self.rows), len(self.features))
        if self.values.shape != expected or self.present.shape != expected:
            raise ContractError('shape_mismatch', expected)
        if self.values.dtype != np.dtype('int64') or self.present.dtype != np.dtype('bool'):
            raise ContractError('noncanonical_array', 'Expected exact int64 tokens and bool presence')
        if np.any(self.values[~self.present] != 0):
            raise ContractError('noncanonical_absence', 'Absent payload must be zero; presence distinguishes real zero')
        # Owning, read-only copies prevent an adapter's later writes altering a run.
        for name in ('values', 'present'):
            a = np.array(getattr(self, name), copy=True, order='C'); a.flags.writeable = False
            object.__setattr__(self, name, a)


@dataclass(frozen=True)
class Alignment:
    primary: Observations
    secondary: Observations
    secondary_indices: np.ndarray
    group_sizes: tuple[int, ...]
    surplus_rows: tuple[RowHandle, ...]
    duplicate_group_count: int
    complete_occurrence_equivalence: bool


def reconcile(primary: Observations, secondary: Observations) -> Alignment:
    """Keep all primary rows. Indistinguishable groups use source-order representatives.

    Any ambiguous secondary group or deficient multiplicity refuses this whole
    alignment. A surplus is reported without adding it to the primary population.
    """
    groups: dict[Hashable, list[int]] = defaultdict(list)
    for i, k in enumerate(secondary.keys):
        groups[k].append(i)
    for k, ids in groups.items():
        ids.sort(key=lambda i: secondary.rows[i])
        first = ids[0]
        for j in ids[1:]:
            if not (np.array_equal(secondary.present[first], secondary.present[j]) and
                    np.array_equal(secondary.values[first], secondary.values[j])):
                raise ContractError('conflicting_secondary_group', {
                    'key': repr(k), 'secondary_rows': [secondary.rows[x].source_row_index0 for x in ids]})
    counts = Counter(primary.keys)
    for k, count in counts.items():
        if count > len(groups.get(k, [])):
            raise ContractError('insufficient_secondary_multiplicity', {
                'key': repr(k), 'primary': count, 'secondary': len(groups.get(k, []))})
    # Stable occurrence association independent of derivative row-view order.
    primary_groups: dict[Hashable, list[int]] = defaultdict(list)
    for i, k in enumerate(primary.keys):
        primary_groups[k].append(i)
    aligned = np.empty(len(primary.rows), dtype=np.int64)
    sizes = np.empty(len(primary.rows), dtype=np.int64)
    used: set[int] = set()
    for k, ids in primary_groups.items():
        ids.sort(key=lambda i: primary.rows[i])
        for i, j in zip(ids, groups[k]):
            aligned[i] = j; sizes[i] = len(groups[k]); used.add(j)
    surplus = tuple(sorted(secondary.rows[i] for i in range(len(secondary.rows)) if i not in used))
    aligned.flags.writeable = False
    return Alignment(primary, secondary, aligned, tuple(map(int, sizes)), surplus,
                     sum(len(v) > 1 for v in groups.values()), not surplus)


def _signature(values: np.ndarray, present: np.ndarray) -> bytes:
    a = np.empty(len(values), dtype=[('present', 'u1'), ('value', '<i8')])
    a['present'] = present; a['value'] = values
    return a.tobytes()


def associate(alignment: Alignment, recovery_rows: Sequence[RowHandle] | None = None,
              digest: Callable[[bytes], str] = lambda b: sha256(b).hexdigest()) -> dict:
    """Hash proposals followed by exact comparisons; never break an ambiguous tie.

    recovery_rows controls signature evidence only. Alignment preconditions are
    checked on the full passed representations. Report the two scopes separately.
    """
    p, s = alignment.primary, alignment.secondary
    recover = tuple(p.rows if recovery_rows is None else recovery_rows)
    if len(recover) != len(set(recover)):
        raise ContractError('repeated_recovery_handles', len(recover))
    lookup = {h: i for i, h in enumerate(p.rows)}
    if any(h not in lookup for h in recover):
        raise ContractError('unknown_recovery_handle', 'Recovery must be an explicit primary-row subset')
    ri = np.array([lookup[h] for h in recover], dtype=np.int64)
    si = alignment.secondary_indices[ri]
    bv, bp = s.values[si], s.present[si]
    buckets: dict[str, list[int]] = defaultdict(list)
    for j in range(len(s.features)):
        buckets[digest(_signature(bv[:, j], bp[:, j]))].append(j)
    rows = []
    for c, name in enumerate(p.features):
        present = p.present[ri, c]; values = p.values[ri, c]
        support = int(present.sum())
        candidates = []
        if support:
            for j in buckets.get(digest(_signature(values, present)), []):
                if np.array_equal(present, bp[:, j]) and np.array_equal(values, bv[:, j]):
                    candidates.append(s.features[j])
        candidates.sort()
        status = ('unsupported' if support == 0 else 'unmatched' if not candidates else
                  'unique' if len(candidates) == 1 else 'ambiguous')
        rows.append({'feature': name, 'support': support, 'status': status, 'candidates': candidates})
    # Even unique local candidates cannot certify an impossible many-to-one map.
    targets = Counter(r['candidates'][0] for r in rows if r['status'] == 'unique')
    for r in rows:
        if r['status'] == 'unique' and targets[r['candidates'][0]] > 1:
            r['status'] = 'noninjective'
    mapping = {r['feature']: r['candidates'][0] for r in rows if r['status'] == 'unique'}
    supported = [r for r in rows if r['support']]
    return {
        'scope': 'Exact association under declared record alignment and canonicalization, not physical authentication',
        'alignment_rows': len(p.rows), 'recovery_rows': len(recover),
        'mapping': mapping, 'features': rows,
        'all_supported_uniquely_resolved': bool(supported) and all(r['status'] == 'unique' for r in supported),
        'complete_occurrence_equivalence': alignment.complete_occurrence_equivalence,
        'surplus_count': len(alignment.surplus_rows),
    }


def positions_for_handles(observations: Observations, ordered_handles: Sequence[RowHandle]) -> list[int]:
    """Recover a declared partition's order from a derived view with explicit lineage."""
    if len(set(ordered_handles)) != len(ordered_handles):
        raise ContractError('duplicate_partition_handles', 'Partitions require explicit unique source rows')
    ix = {h: i for i, h in enumerate(observations.rows)}
    try:
        return [ix[h] for h in ordered_handles]
    except KeyError as e:
        raise ContractError('missing_partition_lineage', str(e)) from e
