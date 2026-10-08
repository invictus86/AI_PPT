"""Recover one logical request without limiting independent image batches."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from .file_hashing import file_sha256
from .image_geometry import read_image_dimensions
from .image_prompt_docs import require_current_image_style
from .json_io import read_json, write_json
from .metrics import record_measurement
from .resources import identity, path_identity, resource_slot
from .time_utils import now_iso
from .validation import ValidationError


def logical_request_key(packet, config, *, force=False):
    from .image_api import _request_options
    value = {'target':(packet['slide_index'], packet.get('option_id'), packet.get('purpose')),
             'basis':packet.get('generation_basis'), 'prompt':packet['prompt'],
             'input':packet.get('image_api_input'), 'options':_request_options(config, packet.get('image_api_input', {})),
             'account':identity(config.base_url.rstrip('/') + '|' + config.api_key)}
    if force:
        value['explicit_new_attempt'] = packet['generation_request_id']
    return identity(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _recovered_item(root, receipt):
    evidence_path = root/receipt.get('api_evidence_path','__missing__')
    if not evidence_path.is_file():
        return None
    evidence = read_json(evidence_path)
    path = root/evidence.get('output_image_path','__missing__')
    if not path.is_file() or file_sha256(path) != evidence.get('image_sha256'):
        return None
    try:
        read_image_dimensions(path)
    except (OSError,ValidationError):
        return None
    packet_path = root/evidence['packet_path']
    require_current_image_style(root, read_json(packet_path))
    return {'status':'api_completed', 'api_evidence_path':str(evidence_path.relative_to(root)),
            **{k:evidence.get(k) for k in ('packet_id','packet_path','output_image_path','api_call_id',
              'image_api_result_id','request_id','api_endpoint','model','response_format','image_sha256','provider_image_url')}}


def run_packet_job(root, packet_path, packet, config, *, force=False):
    from .image_api import _request_packet_image, _write_api_output, _api_evidence_path
    root = Path(root).resolve()
    key = logical_request_key(packet, config, force=force)
    receipt_path = root/'_state/阶段2/request_results'/f'{key}.json'
    with resource_slot('image-target:' + path_identity(root) + ':' + key):
        receipt = read_json(receipt_path) if receipt_path.exists() else {}
        recovered = _recovered_item(root, receipt)
        if recovered:
            recovered['api_submitted'] = False
            return recovered  # Re-register evidence/QA if needed; do not declare visual pass.
        if receipt.get('status') in {'submitted','unknown','completed','returned_unusable'}:
            raise ValidationError(f'请求结果未知或返回文件不可用；禁止盲目重复付费：{key}，先核对证据并使用 resolve-image-request')
        evidence = _api_evidence_path(root, packet)
        receipt = {'status':'queued', 'request_key':key, 'packet_path':str(Path(packet_path).resolve().relative_to(root)),
                   'api_evidence_path':str(evidence.relative_to(root)), 'created_at':now_iso()}
        write_json(receipt_path, receipt)
        # The caller owns its batch-local thread pool (up to six). There is no
        # account semaphore, global image lock, or shared rate-limit cooldown.
        # This per-project request key only deduplicates the exact same job.
        require_current_image_style(root, packet)
        receipt.update(status='submitted', submitted_at=now_iso(), attempt_id=uuid.uuid4().hex)
        write_json(receipt_path, receipt)
        start = time.monotonic()
        response = None
        try:
            response = _request_packet_image(root, packet_path, packet, config)
            item = _write_api_output(root, packet_path, packet, response, config)
            read_image_dimensions(root/item['output_image_path'])
        except BaseException as exc:
            from .image_api import ImageApiHTTPError
            rejected = isinstance(exc, ImageApiHTTPError) and exc.http_status in {400,401,403,404,405,413,415,422,429}
            status = 'rejected' if rejected else ('returned_unusable' if response is not None else 'unknown')
            receipt.update(status=status, interrupted_at=now_iso(), http_status=getattr(exc,'http_status',None))
            write_json(receipt_path, receipt)
            record_measurement(root, {'source':'image_api','record_id':'attempt:'+receipt['attempt_id'],
                'stage':'stage2','operation':packet.get('purpose','image'),'started_at':receipt['submitted_at'],
                'completed_at':receipt['interrupted_at'],'activity_seconds':round(time.monotonic()-start,3),
                'usage':response.usage if response is not None else None,'status':status,
                'rework_category':'technical_failure','notes':'技术失败；未据HTTP状态推断费用；request_key='+key})
            raise
        receipt.update(status='completed', completed_at=now_iso())
        write_json(receipt_path, receipt)
        record_measurement(root, {'source':'image_api', 'record_id':item['api_call_id'], 'stage':'stage2',
            'operation':packet.get('purpose','image'), 'started_at':receipt['submitted_at'], 'completed_at':receipt['completed_at'],
            'activity_seconds':round(time.monotonic()-start,3),
            'api_wait_seconds':response.elapsed_seconds, 'usage':response.usage, 'status':'completed'})
        item['api_submitted'] = True
        return item


def resolve_image_request(root, request_key: str, evidence: dict):
    if len(request_key) != 64 or any(c not in '0123456789abcdef' for c in request_key):
        raise ValidationError('invalid request key')
    if evidence.get('controller_reviewed') is not True or evidence.get('resolution') != 'confirmed_no_result' or not evidence.get('reason'):
        raise ValidationError('必须核实该请求无可恢复返回并记录原因；未知请求不能仅因过期重试')
    root = Path(root).resolve()
    path = root/'_state/阶段2/request_results'/f'{request_key}.json'
    with resource_slot('image-target:' + path_identity(root) + ':' + request_key):
        receipt = read_json(path)
        if _recovered_item(root, receipt):
            raise ValidationError('已存在可恢复返回，必须补登记而不是再生图')
        receipt.update(status='retry_authorized', resolution_evidence=evidence, resolved_at=now_iso())
        write_json(path, receipt)
    return receipt
