"""R3 reconstruction: dependency consistency without labels, plus offline audit.

This is a newly reconstructed interface, not byte recovery of the failed R2 code.
No authentication of a model implementation, physical truth, or sampling law is
provided by a matching declaration. The caller must supply a trusted manifest.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

FIELDS = ("source_payload", "feature_schema", "position_model", "error_model",
          "coordinate_metric", "error_units", "calibration_role", "calibration_state",
          "score_kind", "population", "ordered_row_handles")


def _schema_errors(record: Mapping[str, Any], prefix: str) -> list[str]:
    if not isinstance(record, dict):
        return [prefix + ':not_object']
    errors=[]
    for key in FIELDS:
        if key not in record:
            errors.append(prefix + ':missing:' + key)
    for key in set(record)-set(FIELDS):
        errors.append(prefix + ':unexpected:' + key)
    for key in FIELDS:
        if key not in record:
            continue
        value=record[key]
        if key in ('feature_schema','ordered_row_handles'):
            if not isinstance(value,list) or not value or any(not isinstance(x,str) or not x for x in value):
                errors.append(prefix + ':invalid:' + key)
            elif len(set(value))!=len(value):
                errors.append(prefix + ':duplicate:' + key)
        elif not isinstance(value,str) or not value:
            errors.append(prefix + ':invalid:' + key)
    return sorted(errors)


def validate_dependencies(trusted: dict, received: dict) -> dict:
    """Check only declared identities, roles and ordering. Takes no labels."""
    errors=_schema_errors(trusted,'trusted')+_schema_errors(received,'received')
    if errors:
        return {'state':'unsupported_comparison','violations':sorted(errors)}
    mismatches=[k+':mismatch' for k in FIELDS if trusted[k] != received[k]]
    return {'state':'equivalent_continuation' if not mismatches else 'unsupported_comparison',
            'violations':mismatches}


def conventional_reference(trusted: dict, received: dict) -> dict:
    """Independent explicit comparisons of the same declared contract.

    This is an equally informed reference, not a deliberately weaker detector.
    """
    errors=[]
    for prefix,rec in [('trusted',trusted),('received',received)]:
        if type(rec) is not dict:
            errors.append(prefix+':not_object'); continue
        for key in FIELDS:
            if key not in rec: errors.append(prefix+':missing:'+key);continue
            val=rec[key]
            if key in ('feature_schema','ordered_row_handles'):
                if type(val) is not list or len(val)==0 or any(type(t) is not str or len(t)==0 for t in val):
                    errors.append(prefix+':invalid:'+key)
                elif any(val[i] in val[:i] for i in range(len(val))):
                    errors.append(prefix+':duplicate:'+key)
            elif type(val) is not str or len(val)==0:
                errors.append(prefix+':invalid:'+key)
        errors.extend(prefix+':unexpected:'+key for key in rec if key not in FIELDS)
    if errors:return {'state':'unsupported_comparison','violations':sorted(errors)}
    mismatches=[]
    for key in FIELDS:
        a,b=trusted[key],received[key]
        if isinstance(a,list):
            same=len(a)==len(b) and all(x==y for x,y in zip(a,b))
        else:same=(a==b)
        if not same:mismatches.append(key+':mismatch')
    return {'state':'equivalent_continuation' if len(mismatches)==0 else 'unsupported_comparison',
            'violations':mismatches}


def audit_derived_quantities(actual_errors: Sequence[float], estimates: Sequence[float],
                             claimed_signed: Sequence[float], *, atol: float=1e-8) -> dict:
    """Offline comparison to scalar e-h; actual errors require labelled evaluation.

    This does not recover error from coordinates: that metric is separately verified
    in the protected execution archives. Current labels are not available to the
    dependency interface.
    """
    if not math.isfinite(atol) or atol<0:raise ValueError('Invalid tolerance')
    if not (len(actual_errors)==len(estimates)==len(claimed_signed)):
        raise ValueError('Array lengths differ')
    max_diff=0.; count=0
    for e,h,s in zip(actual_errors,estimates,claimed_signed):
        e,h,s=float(e),float(h),float(s)
        if not all(math.isfinite(x) for x in (e,h,s)) or e<0 or h<0:
            raise ValueError('Finite, nonnegative errors/estimates required')
        diff=abs((e-h)-s);max_diff=max(max_diff,diff);count+=int(diff>atol)
    return {'requires_labels':True,'n':len(actual_errors),'mismatched_records':count,
            'maximum_difference':max_diff,'formula':'actual_error_minus_point_error_estimate',
            'state':'agrees' if count==0 else 'numerical_discrepancy'}
