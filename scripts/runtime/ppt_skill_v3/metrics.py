"""Recorded spans and provider usage stay separate; absent data stays unknown."""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path

from .json_io import read_json, write_json
from .resources import path_identity, resource_slot
from .time_utils import now_iso
from .validation import ValidationError


def record_measurement(root, measurement: dict) -> dict:
    if not isinstance(measurement, dict) or measurement.get('source') not in {'codex', 'image_api', 'manual', 'runtime'}:
        raise ValidationError('measurement.source must be codex, image_api, manual or runtime')
    for key in ('record_id', 'stage', 'operation'):
        if not isinstance(measurement.get(key), str) or not measurement[key].strip():
            raise ValidationError('measurement needs ' + key)
    allowed = {'source','record_id','stage','operation','turn_id','started_at','completed_at','activity_seconds',
               'queue_seconds','execution_seconds','api_wait_seconds','manual_seconds','input_tokens','cached_input_tokens',
               'output_tokens','total_tokens','usage','status','rework_category','notes','duration_lower_bound'}
    if set(measurement) - allowed:
        raise ValidationError('measurement contains unsupported fields; do not record credentials or remote URLs')
    for key in allowed - {'source','record_id','stage','operation','turn_id','started_at','completed_at','usage','status','rework_category','notes','duration_lower_bound'}:
        value = measurement.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int,float)) or value < 0):
            raise ValidationError('measurement values must be nonnegative numbers or null: ' + key)
    if measurement.get('cached_input_tokens') is not None and measurement.get('input_tokens') is not None and measurement['cached_input_tokens'] > measurement['input_tokens']:
        raise ValidationError('cached input is a subset of input, not an additional token count')
    file = Path(root)/'_state/metrics/measurements.json'
    with resource_slot('metrics:' + path_identity(file)):
        records = read_json(file) if file.exists() else {}
        key = measurement['source'] + ':' + measurement['record_id']
        if key in records and records[key] != measurement:
            raise ValidationError('measurement id already exists with different values')
        records[key] = measurement
        write_json(file, records)
    return measurement


@contextmanager
def operation_span(root, operation, *, stage='unknown'):
    import uuid
    start = time.monotonic()
    record = {'source':'runtime', 'record_id':uuid.uuid4().hex, 'stage':stage,
              'operation':operation, 'started_at':now_iso(), 'status':'completed'}
    try:
        yield record
    except BaseException:
        record['status'] = 'failed'
        raise
    finally:
        record.update(completed_at=now_iso(), activity_seconds=round(time.monotonic()-start,3))
        # Spans overlap with nested API/renderer records. Never sum them as serial wall time.
        record_measurement(root, record)


def metrics_summary(root):
    file = Path(root)/'_state/metrics/measurements.json'
    records = list(read_json(file).values()) if file.exists() else []
    sources = {}
    for item in records:
        bucket = sources.setdefault(item['source'], {'records':0, 'missing_duration':0, 'missing_usage':0})
        bucket['records'] += 1
        bucket['missing_duration'] += item.get('activity_seconds') is None
        bucket['missing_usage'] += not any(item.get(k) is not None for k in ('usage','input_tokens','output_tokens','total_tokens'))
    return {'sources':sources, 'records':records, 'notice':'嵌套/并行时段不相加为用户耗时；缓存包含在输入；中转与Codex分别列账；缺测不填0。'}
