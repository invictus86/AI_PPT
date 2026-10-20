"""Hand confirmed relay failures to the host image tool without regenerating plans."""
from __future__ import annotations

from copy import deepcopy
from contextlib import ExitStack
import hashlib
from pathlib import Path

from .image_routes import (
    IMAGE_ROUTE_CODEX_IMAGE_GEN, IMAGE_ROUTE_OPENAI_IMAGE_API,
    image_size_contract, normalize_image_generation_route, route_tool, route_tool_function,
)
from .json_io import read_json, write_json
from .resources import project_mutation, resource_slot
from .time_utils import now_iso
from .validation import ValidationError


def _path(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root / '_state'):
        raise ValidationError('生图备用证据与任务必须位于项目_state内')
    return path


def _hash(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def _receipts(root, source):
    rows = []
    for path in (root / '_state/阶段2/request_results').glob('*.json'):
        receipt = read_json(path)
        value = receipt.get('packet_path')
        if not value:
            continue
        packet = read_json(_path(root, value))
        fields = ('packet_id', 'prompt', 'generation_basis', 'image_api_input')
        if all(packet.get(k) == source.get(k) for k in fields):
            rows.append(receipt)
    return rows


def _reason(root, source, evidence):
    from .image_jobs import _recovered_item
    rows = _receipts(root, source)
    if any(r.get('failure_category') == 'content_policy' for r in rows):
        return None, '内容安全拒绝不能切换渠道规避'
    for receipt in rows:
        if _recovered_item(root, receipt):
            return None, '存在可恢复结果，先补登记'
        if receipt.get('status') in {'queued', 'submitted', 'unknown', 'completed', 'returned_unusable'}:
            return None, '原请求在途、结果未知或返回不可用，先使用resolve-image-request核实'
    if rows and all(r.get('native_fallback_allowed') is True or r.get('status') == 'retry_authorized' for r in rows):
        return {'kind': 'confirmed_relay_failure', 'receipts': [r['request_key'] for r in rows]}, None
    if evidence and evidence.get('controller_reviewed') is True and evidence.get('relay_unavailable') is True and evidence.get('resolution') == 'confirmed_no_result' and evidence.get('reason'):
        return deepcopy(evidence), None
    return None, '没有明确中转故障及无可恢复结果的证据'


def _usable_result(root, source):
    from .image_style import result_is_current
    from .image_results import _result_path
    path = _result_path(root, 'stage2', source.get('purpose', 'full_slide'), source['slide_index'], source.get('option_id'))
    if not path.is_file():
        return False
    result = read_json(path)
    return result.get('prompt_hash') == source.get('prompt_hash') and result_is_current(root, result)


def _source_options(root, source, evidence=None):
    from .image_api import ImageApiConfig, _request_options
    rows = sorted(_receipts(root, source), key=lambda r: r.get('submitted_at', ''))
    options = rows[-1].get('request_options') if rows else None
    if not options and evidence:
        options = evidence.get('request_options_by_packet', {}).get(source['packet_id'])
    config = ImageApiConfig(api_key='not-used-for-transport')
    if options:
        config = ImageApiConfig(api_key='not-used-for-transport', size=options['size'], size_override=True,
                                quality=options['quality'], model=options['model'], output_format=options['output_format'],
                                response_format=options['response_format'], response_format_override=True)
    return _request_options(config, source.get('image_api_input', {}))


@project_mutation
def prepare_native_fallback(run_dir, batch_file, *, evidence=None):
    """Create/reuse native packets only for missing, safely resolved source images."""
    from .image_jobs import image_route_target
    root = Path(run_dir).resolve()
    batch_path = _path(root, batch_file)
    batch = read_json(batch_path)
    packets = [read_json(_path(root, value)) for value in batch['packet_paths']]
    with ExitStack() as stack:
        for key in sorted({image_route_target(root, packet) for packet in packets}):
            stack.enter_context(resource_slot(key))
        return _prepare_native_fallback(root, batch_path, evidence=evidence)


def _prepare_native_fallback(run_dir, batch_file, *, evidence=None):
    from .image_batches import create_image_generation_batch
    from .image_prompt_docs import require_current_image_style
    root = Path(run_dir).resolve()
    source_path = _path(root, batch_file)
    batch = read_json(source_path)
    if normalize_image_generation_route(batch.get('image_generation_route')) != IMAGE_ROUTE_OPENAI_IMAGE_API or batch.get('stage') != 'stage2':
        raise ValidationError('备用路线只能接续阶段2中转生图批次')
    mapping = batch.setdefault('native_fallback_packets', {})
    pending, reused, blocked, skipped = [], [], [], []
    for value in batch['packet_paths']:
        path = _path(root, value)
        source = read_json(path)
        require_current_image_style(root, source)
        if _usable_result(root, source):
            skipped.append(source['packet_id'])
            continue
        if source['packet_id'] in mapping:
            native_path = _path(root, mapping[source['packet_id']])
            validate_native_fallback(root, read_json(native_path))
            reused.append(native_path)
            continue
        reason, error = _reason(root, source, evidence)
        if not reason:
            blocked.append({'packet_id': source['packet_id'], 'reason': error})
            continue
        api = source.get('image_api_input', {})
        options = _source_options(root, source, reason)
        if api.get('urls'):
            blocked.append({'packet_id': source['packet_id'], 'reason': '原请求使用远程图片，须先保存并核对同一参考图，不可丢弃后切换'})
            continue
        native = deepcopy(source)
        for key in ('image_api_input', 'generation_request_id', 'generation_batch_path', 'original_packet_path'):
            native.pop(key, None)
        native.update(image_generation_route=IMAGE_ROUTE_CODEX_IMAGE_GEN,
                      execution_tool=route_tool(IMAGE_ROUTE_CODEX_IMAGE_GEN))
        native['image_gen_input'] = {
            'tool': 'image_gen.imagegen', 'mode': 'edit' if api.get('endpoint') == '/v1/images/edits' else 'generate',
            'size': options['size'], 'quality': options['quality'], 'output_format': options['output_format'],
            'project_bound': True, 'referenced_image_paths': deepcopy(api.get('referenced_image_paths', [])),
            'requested_parameters_only': True,
            **{k: deepcopy(source[k]) for k in image_size_contract() if k in source},
        }
        native['native_fallback'] = {
            'source_packet_path': path.relative_to(root).as_posix(), 'source_packet_sha256': _hash(path),
            'source_batch_path': source_path.relative_to(root).as_posix(),
            'reason': reason, 'requested_parameters': options, 'created_at': now_iso(),
        }
        pending.append(native)
    if pending:
        digest = hashlib.sha256('|'.join(x['native_fallback']['source_packet_sha256'] for x in pending).encode()).hexdigest()[:16]
        group_id = str(batch['execution_group_id']) + '-native-' + digest
        paths = []
        for index, native in enumerate(pending, 1):
            fn = route_tool_function(IMAGE_ROUTE_CODEX_IMAGE_GEN, edit=native['image_gen_input']['mode'] == 'edit')
            native['execution_tool_function'] = fn
            native['execution_group'] = {
                'group_id': group_id, 'image_generation_route': IMAGE_ROUTE_CODEX_IMAGE_GEN,
                'required_tool': route_tool(IMAGE_ROUTE_CODEX_IMAGE_GEN),
                'tool_call': fn, 'mode': 'parallel_required', 'parallel_required': True,
                'packet_index': index, 'total_packets': len(pending),
                'max_parallel': min(6, batch['max_parallel'], len(pending)),
            }
            path = root / '_state/阶段2/native_fallback' / group_id / (native['packet_id'] + '.json')
            write_json(path, native)
            paths.append(path)
        native_batch = create_image_generation_batch(root, pending[0]['execution_group'], paths,
                                                     stage='stage2', purpose=batch['purpose'], route=IMAGE_ROUTE_CODEX_IMAGE_GEN)
        frozen = read_json(native_batch)['packet_paths']
        for native, value in zip(pending, frozen):
            mapping[native['packet_id']] = value
            reused.append(_path(root, value))
        write_json(source_path, batch)
    return {
        'status': 'awaiting_native_image_generation' if reused else 'no_safe_native_fallback',
        'packet_paths': [p.relative_to(root).as_posix() for p in reused],
        'skipped_packets': skipped, 'blocked_packets': blocked,
        'next_required_action': '主控逐图执行prepare-image-request，再调用返回的image_gen.imagegen工具参数；实际看图后按原质量标准登记，保留原用户确认节点。' if reused else '先恢复未知请求或核对中转故障证据，不重复生图。',
    }


def validate_native_fallback(run_dir, packet):
    """The native exception cannot change the frozen relay prompt or quality contract."""
    root = Path(run_dir).resolve()
    proof = packet.get('native_fallback')
    if not isinstance(proof, dict) or not proof.get('reason'):
        raise ValidationError('原生生图只允许从已核实中转故障的备用任务接续')
    path = _path(root, proof['source_packet_path'])
    if _hash(path) != proof.get('source_packet_sha256'):
        raise ValidationError('备用生图对应的中转请求快照已变化')
    source = read_json(path)
    if normalize_image_generation_route(source.get('image_generation_route')) != IMAGE_ROUTE_OPENAI_IMAGE_API:
        raise ValidationError('备用源必须是中转生图请求')
    reason, error = _reason(root, source, proof['reason'])
    if not reason:
        raise ValidationError(error)
    fields = ('stage', 'purpose', 'slide_index', 'option_id', 'prompt', 'prompt_hash', 'generation_basis',
              'asset_hashes', 'image_style_snapshot', 'expected_output_relpath', *image_size_contract())
    if any(packet.get(k) != source.get(k) for k in fields):
        raise ValidationError('切换渠道不得更改提示词、正文依据、参考风格或尺寸合同')
    options = _source_options(root, source, proof['reason'])
    native = packet.get('image_gen_input', {})
    if any(native.get(k) != options[k] for k in ('size', 'quality', 'output_format')):
        raise ValidationError('原生备用不得降低原尺寸、高质量或PNG要求')
    original_refs = source.get('image_api_input', {}).get('referenced_image_paths', [])
    refs = native.get('referenced_image_paths', [])
    archived = {x['archived_path']: x['original_path'] for x in packet.get('input_image_snapshots', [])}
    if [archived.get(p, p) for p in refs] != original_refs:
        # Relay snapshots can already contain the same archived input paths.
        if refs != original_refs:
            raise ValidationError('备用路线必须保留原图片输入及顺序')


def native_tool_request(run_dir, packet):
    validate_native_fallback(run_dir, packet)
    root = Path(run_dir).resolve()
    refs = packet['image_gen_input'].get('referenced_image_paths', [])
    args = {'prompt': packet['prompt'], 'transparent_background': False}
    if refs:
        args['referenced_image_paths'] = [str((root / p).resolve()) for p in refs]
    return {
        'tool_name': 'image_gen.imagegen', 'tool_arguments': args,
        'requested_parameters': packet['native_fallback']['requested_parameters'],
        'unexposed_tool_parameters': ['model', 'size', 'quality', 'output_format'],
        'reference_review_required': bool(refs),
        'parameter_note': 'size/high/PNG是沿用的要求，未作为该原生工具未开放的参数提交；必须实际核对成图。',
    }
