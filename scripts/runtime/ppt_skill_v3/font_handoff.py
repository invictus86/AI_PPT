"""Reference font handoff; recorded observations never imply an executed repair."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .file_hashing import file_sha256
from .json_io import read_json, write_json
from .time_utils import now_iso
from .validation import ValidationError

TASKS = Path('_state/工具任务/canva')
CONTENT = Path('_state/阶段1/content.json')


def normalized_text(text):
    # Matching only: never write normalized text back into a presentation.
    return ''.join(text.split())


def _text(value, key):
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValidationError('font handoff needs ' + key)
    return result


def local_evidence(root, value):
    if not isinstance(value, str) or not value or '://' in value:
        raise ValidationError('font evidence must be a real local file, not a remote URL')
    path = Path(value)
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file():
        raise ValidationError('font evidence file is missing: ' + str(path))
    return path


def record_font_handoff(run_dir, task_id, document):
    root = Path(run_dir)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
        raise ValidationError('invalid Canva task id')
    directory = root / TASKS / task_id
    task = read_json(directory / 'task.json')
    if task.get('status') != 'completed':
        raise ValidationError('record final font handoff after Canva save/readback completes')
    if not isinstance(document, dict) or document.get('controller_reviewed') is not True:
        raise ValidationError('font handoff requires actual controller review')
    content = read_json(root / CONTENT)
    authority = {s['slide_index']: s for s in content['slides']}
    reference_path = directory / 'reference_text_by_slide.json'
    if reference_path.is_file():
        reference = read_json(reference_path)
        if {s['slide_index']: s['final_visible_text'] for s in reference['slides']} != {
                n: s['final_visible_text'] for n, s in authority.items()}:
            raise ValidationError('Canva reference copy changed; review the task before font handoff')
    items = document.get('items')
    if not isinstance(items, list):
        raise ValidationError('font handoff items must be a list (empty if no pending issues)')
    checked, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError('font handoff item must be an object')
        page = item.get('slide_index')
        if type(page) is not int or page not in authority:
            raise ValidationError('font handoff page is not in approved content')
        slide = authority[page]
        text = _text(item, 'text')
        kind = item.get('unit_kind')
        if kind not in {'sentence', 'title'}:
            raise ValidationError('handoff must identify a complete sentence or title')
        if kind == 'title' and text != slide['title']:
            raise ValidationError('handoff title must equal the complete approved title')
        if kind == 'sentence' and not any(text in t for t in slide['final_visible_text']):
            raise ValidationError('handoff sentence must come from approved visible text')
        if item.get('whole_unit_confirmed') is not True:
            raise ValidationError('confirm the complete sentence/title, not isolated glyphs')
        identity = f'{task_id}:{page}:{kind}:{text}'
        if identity in seen:
            raise ValidationError('duplicate font handoff item')
        seen.add(identity)
        entry = {'handoff_id': hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20],
                 'slide_index': page, 'page_title': slide['title'], 'text': text,
                 'unit_kind': kind, 'whole_unit_confirmed': True,
                 'reason': _text(item, 'reason'), 'status': 'pending_pptx_review',
                 'target_font': None, 'canva_font_changed': False}
        for key in ('reference_visual', 'canva_preview'):
            path = local_evidence(root, item.get(key))
            try:
                entry[key] = path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                raise ValidationError('copy font reference evidence into the project first')
            entry[key + '_sha256'] = file_sha256(path)
        checked.append(entry)
    record = {'schema_version': '1.0', 'task_id': task_id,
              'stage1_content_sha256': file_sha256(root / CONTENT),
              'controller_reviewed': True, 'created_at': now_iso(), 'items': checked}
    path = directory / 'font_handoff.json'
    write_json(path, record)
    lines = ['# Canva → PPTX 字体交接清单', '', '待办仅用于后续定位；未在Canva更换字体，未授权或执行PPTX修复。', '']
    for entry in checked:
        lines.append(f"- 第{entry['slide_index']}页｜{entry['text']}｜{entry['reason']}｜待PPTX复核")
    if not checked:
        lines.append('本次检查没有待交接的字体事项。')
    path.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return record


def import_font_handoffs(root, inspection, *, strict=True):
    root = Path(root)
    imports, items, warnings = [], [], []
    for path in sorted((root / TASKS).glob('*/font_handoff.json')):
        document = read_json(path)
        content_stale = document.get('stage1_content_sha256') != file_sha256(root / CONTENT)
        if content_stale:
            if strict:
                raise ValidationError('font handoff approved content changed; review handoff again')
            warnings.append('Stale font handoff retained without authorization: ' + path.relative_to(root).as_posix())
        imports.append({'path': path.relative_to(root).as_posix(), 'sha256': file_sha256(path)})
        for item in document['items']:
            for key in ('reference_visual', 'canva_preview'):
                if strict and file_sha256(local_evidence(root, item[key])) != item[key + '_sha256']:
                    raise ValidationError('font handoff visual evidence changed')
            matches = []
            for page in inspection['pages']:
                for obj in page['text_objects']:
                    if normalized_text(item['text']) in normalized_text(obj['text']):
                        matches.append({'page': page['page'], 'shape_id': obj['shape_id'],
                                        'text': obj['text'], 'has_fields': obj['has_fields']})
            items.append({**item, 'candidate_objects': matches,
                          'mapping_status': 'stale' if content_stale else 'needs_controller_review' if len(matches) == 1 else 'ambiguous_or_missing'})
    result = {'input_sha256': inspection['source_sha256'], 'sources': imports, 'items': items, 'warnings': warnings}
    write_json(root / '_state/阶段5/font_handoff_import.json', result)
    return result


def validate_handoff_resolutions(root, task, plan, inspection):
    if not task.get('reference_font_matching_enabled'):
        return
    path = Path(root) / '_state/阶段5/font_handoff_import.json'
    imported = read_json(path)
    if file_sha256(path) != task['font_handoff_import_sha256']:
        raise ValidationError('font handoff mapping changed; inspect again')
    for source in imported['sources']:
        if file_sha256(Path(root) / source['path']) != source['sha256']:
            raise ValidationError('Canva font handoff changed; inspect again')
        if read_json(Path(root) / source['path'])['stage1_content_sha256'] != file_sha256(Path(root) / CONTENT):
            raise ValidationError('approved text changed after font handoff import')
    items = {x['handoff_id']: x for x in imported['items']}
    for item in items.values():
        for key in ('reference_visual', 'canva_preview'):
            if file_sha256(local_evidence(root, item[key])) != item[key + '_sha256']:
                raise ValidationError('font handoff reference pixels changed; inspect again')
    resolutions = plan.get('font_handoff_resolutions', [])
    if not isinstance(resolutions, list) or len(resolutions) != len(items):
        raise ValidationError('account for every imported font handoff item')
    seen = set()
    for resolution in resolutions:
        if not isinstance(resolution, dict):
            raise ValidationError('font handoff resolution must be an object')
        identity = resolution.get('handoff_id')
        if identity not in items or identity in seen:
            raise ValidationError('unknown or duplicate font handoff resolution')
        seen.add(identity)
        item = items[identity]
        _text(resolution, 'reason')
        status = resolution.get('status')
        if status == 'blocked':
            if not any(s['manual_issues'] for s in plan['slides']):
                raise ValidationError('blocked handoff requires a manual issue in animation plan')
            continue
        if status not in {'replace', 'no_change'}:
            raise ValidationError('handoff resolution must be replace, no_change or blocked')
        page, shape = resolution.get('page'), resolution.get('shape_id')
        objects = [o for p in inspection['pages'] if p['page'] == page
                   for o in p['text_objects'] if o['shape_id'] == shape]
        if len(objects) != 1 or normalized_text(item['text']) not in normalized_text(objects[0]['text']):
            raise ValidationError('handoff mapping does not match actual PPTX text')
        _text(resolution, 'mapping_reason')
        local_evidence(root, resolution.get('visual_evidence'))
        repairs = [r for r in plan.get('font_repairs', []) if r.get('handoff_id') == identity]
        if status == 'replace':
            if len(repairs) != 1 or (repairs[0]['page'], repairs[0]['shape_id']) != (page, shape):
                raise ValidationError('replacement needs exactly one mapped font repair')
            if normalized_text(repairs[0]['text']) != normalized_text(item['text']):
                raise ValidationError('font repair must cover the handed-off complete text')
        elif repairs:
            raise ValidationError('no_change handoff must not execute a font repair')
    for repair in plan.get('font_repairs', []):
        if repair.get('handoff_id') and repair['handoff_id'] not in items:
            raise ValidationError('font repair refers to an unknown handoff')
