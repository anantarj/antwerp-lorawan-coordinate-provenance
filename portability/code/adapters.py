"""Two declared schemas around the same exact correspondence core.

Antwerp canonicalization intentionally preserves existing source conventions.
SyntheticExplicit is an alternate integer-token schema, not a field dataset.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd
from identity_core import ContractError, Observations, RowHandle


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def exact_integer(x, *, lo=-(2**63), hi=2**63-1) -> int:
    """No string/bool coercion; reject floats beyond their exact integer range."""
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ContractError('invalid_integer_token', repr(x))
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(float(x)) or not float(x).is_integer() or abs(float(x)) > 2**53:
            raise ContractError('nonexact_integer_token', repr(x))
    v = int(x)
    if v < lo or v > hi: raise ContractError('integer_overflow', repr(x))
    return v


def _id(x) -> str:
    if type(x) is not str or not x: raise ContractError('invalid_identifier', repr(x))
    return x


def _antwerp_hdop(x) -> float:
    if isinstance(x, bool): raise ContractError('invalid_hdop', x)
    v = float(x)
    if not math.isfinite(v): raise ContractError('invalid_hdop', repr(x))
    return round(v, 2)


def antwerp_frames(frame: pd.DataFrame, messages: list[dict], csv_sha: str, json_sha: str):
    cols = tuple(sorted((c for c in frame if re.fullmatch(r'BS\s+\d+', c)),
                        key=lambda x: int(x.split()[-1])))
    if not cols: raise ContractError('no_receiver_columns', 'Expected BS-number fields in Antwerp adapter')
    if len({int(c.split()[-1]) for c in cols}) != len(cols):
        raise ContractError('duplicate_receiver_numbers', cols)
    raw = frame[list(cols)].to_numpy()
    # Integral int16-compatible scientific RSSI tokens; reject BEFORE casting.
    if raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all() or not np.equal(raw, np.rint(raw)).all():
        raise ContractError('invalid_antwerp_rssi', 'Nonfinite/nonintegral/nonnumeric value')
    if (raw < -200).any() or (raw > 32767).any():
        raise ContractError('invalid_antwerp_rssi_range', 'Would violate source sentinel or int16 representation')
    values = raw.astype(np.int64); present = values != -200
    values[~present] = 0
    keys = tuple((str(t), exact_integer(sf), _antwerp_hdop(h), tuple(sorted(map(int, values[i, present[i]]))))
                 for i, (t, sf, h) in enumerate(frame[['RX Time','SF','HDOP']].itertuples(index=False, name=None)))
    primary = Observations(tuple(RowHandle(csv_sha, i) for i in range(len(frame))), keys, cols, values, present)
    ids = tuple(sorted({_id(g['id']) for m in messages for g in m['gateways']}))
    id_index = {g: i for i, g in enumerate(ids)}
    v = np.zeros((len(messages), len(ids)), dtype=np.int64); seen = np.zeros(v.shape, dtype=bool); jkeys=[]
    for i, m in enumerate(messages):
        gw=m['gateways']
        if not gw: raise ContractError('empty_gateway_list', i)
        for g in gw:
            name=_id(g['id']); j=id_index[name]
            if seen[i,j]: raise ContractError('duplicate_gateway_in_event', {'row':i,'id':name})
            value=exact_integer(g['rssi'],lo=-199,hi=32767)
            v[i,j]=value;seen[i,j]=True
        jkeys.append((str(gw[0]['rx_time']['time']), exact_integer(m['sf']), _antwerp_hdop(m['hdop']),
                      tuple(sorted(map(int,v[i,seen[i]])))))
    secondary=Observations(tuple(RowHandle(json_sha,i) for i in range(len(messages))),tuple(jkeys),ids,v,seen)
    return primary,secondary


def load_antwerp(csv_path: Path, json_path: Path):
    head = pd.read_csv(csv_path, nrows=0)
    cols = [c for c in head if re.fullmatch(r'BS\s+\d+', c)]
    # Positions, target labels and outcome fields are not even loaded from CSV.
    frame = pd.read_csv(csv_path, usecols=cols+['RX Time','SF','HDOP'])
    messages = json.loads(json_path.read_text())
    return antwerp_frames(frame,messages,file_hash(csv_path),file_hash(json_path))


def synthetic_explicit(primary_rows: list[dict], secondary_events: list[dict], channels: list[str],
                       primary_sha: str, secondary_sha: str):
    """Wide channels with explicit presence; secondary long-form integer events.

    The caller supplies original source indices. Row order is a view, not lineage.
    Unknown scalar unit conversions are not inferred. Values use exact int64 tokens.
    """
    channels=tuple(channels)
    values=np.zeros((len(primary_rows),len(channels)),dtype=np.int64)
    present=np.zeros(values.shape,dtype=bool)
    for i,row in enumerate(primary_rows):
        if set(row['signals'])!=set(channels):raise ContractError('synthetic_channel_schema',i)
        for j,c in enumerate(channels):
            pair=row['signals'][c]
            if type(pair['present']) is not bool:raise ContractError('invalid_presence_tag',pair)
            present[i,j]=pair['present']
            if pair['present']:values[i,j]=exact_integer(pair['value'])
            elif pair.get('value') is not None:raise ContractError('absent_value_not_null',pair)
    p=Observations(tuple(RowHandle(primary_sha,r['source_index']) for r in primary_rows),
                   tuple(r['event_key'] for r in primary_rows),channels,values,present)
    ids=tuple(sorted({_id(g['sensor']) for e in secondary_events for g in e['readings']}));ix={g:i for i,g in enumerate(ids)}
    v=np.zeros((len(secondary_events),len(ids)),dtype=np.int64);m=np.zeros(v.shape,dtype=bool)
    for i,event in enumerate(secondary_events):
        for reading in event['readings']:
            j=ix[_id(reading['sensor'])]
            if m[i,j]:raise ContractError('duplicate_gateway_in_event',i)
            m[i,j]=True;v[i,j]=exact_integer(reading['token'])
    s=Observations(tuple(RowHandle(secondary_sha,e['source_index']) for e in secondary_events),
                   tuple(e['event_key'] for e in secondary_events),ids,v,m)
    return p,s
