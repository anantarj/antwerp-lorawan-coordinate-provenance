"""Post-association registry and lineage checks. Never used to choose a link."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import copy
import numpy as np
from identity_core import ContractError, RowHandle


def registry_sidecar(association: dict, registry: Mapping[str,dict], required: Sequence[str]) -> list[dict]:
    rows=[]
    for result in association['features']:
        name=result['feature'];identity=association['mapping'].get(name)
        attributes=registry.get(identity) if identity is not None else None
        missing=[k for k in required if attributes is None or attributes.get(k) is None]
        rows.append({'feature':name,'association_status':result['status'],'identifier':identity,
                     'registry_entry_present':attributes is not None,'missing_attributes':missing,
                     'metadata_available':identity is not None and not missing,
                     'attributes':copy.deepcopy(attributes)})
    return rows


def verify_partition(rows: Sequence[RowHandle], source_sha: str, source_x: np.ndarray, source_y: np.ndarray,
                     source_hdop: np.ndarray, x: np.ndarray, y: np.ndarray, hdop: np.ndarray,
                     expected_order: Sequence[RowHandle] | None = None) -> None:
    if len(rows)!=len(set(rows)):raise ContractError('duplicate_partition_handles',len(rows))
    if any(h.payload_sha256!=source_sha for h in rows):raise ContractError('wrong_partition_payload',source_sha)
    if expected_order is not None and tuple(rows)!=tuple(expected_order):
        raise ContractError('partition_order_changed','Ordered row identities differ')
    indices=np.array([h.source_row_index0 for h in rows],dtype=np.int64)
    if (indices<0).any() or (indices>=len(source_x)).any():raise ContractError('partition_index_out_of_bounds',len(source_x))
    for name,full,actual in [('features',source_x,x),('targets',source_y,y),('HDOP',source_hdop,hdop)]:
        if not np.array_equal(full[indices],actual,equal_nan=True):
            raise ContractError('partition_values_misaligned',name)
