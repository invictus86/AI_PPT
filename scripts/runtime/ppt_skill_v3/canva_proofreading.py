"""Source-bound Canva copy diagnostics and local repair planning; no network edits.

Language judgement belongs to the controller. The small hint list only raises
candidates, including when the approved source and converted text agree.
"""
from difflib import SequenceMatcher
import hashlib
import json
import re
import unicodedata

from .text_optimization import layout_text
from .validation import ValidationError

COMMON_HINTS = {
    '再接再励': '再接再厉', '厉兵株马': '厉兵秣马', '迫不急待': '迫不及待',
    '按步就班': '按部就班', '一愁莫展': '一筹莫展', '谈笑风声': '谈笑风生',
    '相形见拙': '相形见绌', '穿流不息': '川流不息',
}


def _require(condition, message):
    if not condition:
        raise ValidationError('Canva文字校对：' + message)


def _digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def copy_difference_summary(actual, expected):
    before, after = layout_text(''.join(actual)), layout_text(''.join(expected))
    changes = [f'当前“{before[a:b]}”→原稿“{after[c:d]}”'
               for tag, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if tag != 'equal']
    return '；'.join(changes[:5])


def _objects(values):
    _require(isinstance(values, list), 'objects须为实际回读的文字对象列表')
    result = {}
    for item in values:
        _require(isinstance(item, dict), '文字对象须为对象')
        identity, text = item.get('element_id'), item.get('text')
        _require(isinstance(identity, str) and bool(identity.strip()) and identity not in result, '对象ID缺失或重复')
        _require(isinstance(text, str), '对象text须为实际纯文字，不能填richtext/fill载荷')
        result[identity] = text
    return result


def _layout_map(text):
    """Keep raw Unicode offsets while applying the existing layout tolerance."""
    positions = list(range(len(text)))
    for pattern in (r'(?:^|(?<=[\n\r\v]))[ \t\u3000]+(?=[\u3400-\u9fff])',
                    r'(?<=[\u3400-\u9fff])[ \t\u3000]+(?=[\u3400-\u9fff])', r'[\n\r\v]'):
        removed = {i for match in re.finditer(pattern, text) for i in range(match.start(), match.end())}
        positions = [p for i, p in enumerate(positions) if i not in removed]
        text = ''.join(c for i, c in enumerate(text) if i not in removed)
    return text, positions


def _language(expected, review):
    hints = []
    for unit, text in enumerate(expected):
        for wrong, correct in COMMON_HINTS.items():
            for match in re.finditer(re.escape(wrong), text):
                hints.append({'unit_index': unit, 'start': match.start(), 'end': match.end(),
                              'current_text': wrong, 'suggested_text': correct, 'category': 'typo',
                              'reason': '常见词形疑误，须结合上下文判断，可能是引文或故意展示的错误例句', 'origin': 'hint'})
    if review is None:
        return hints, False
    _require(isinstance(review, dict) and review.get('controller_reviewed') is True, '语言校对须由主控实际审阅')
    units = review.get('reviewed_unit_indices')
    _require(isinstance(units, list) and all(type(x) is int for x in units)
             and len(units) == len(expected) and set(units) == set(range(len(expected))), '语言审阅须覆盖全部批准文字单位')
    _require(isinstance(review.get('review_evidence'), str) and bool(review['review_evidence'].strip()), '须说明语言审阅依据')
    dismissed = review.get('dismissed_hints', [])
    _require(isinstance(dismissed, list), 'dismissed_hints须为列表')
    for item in dismissed:
        _require(isinstance(item, dict) and isinstance(item.get('reason'), str) and bool(item['reason'].strip()), '排除词形候选须给出上下文理由')
        matches = [h for h in hints if all(h[k] == item.get(k) for k in ('unit_index', 'start', 'end'))]
        _require(len(matches) == 1, '被排除候选不存在或重复')
        hints.remove(matches[0])
    issues = review.get('issues', [])
    _require(isinstance(issues, list), '语言疑误须为列表')
    for item in issues:
        _require(isinstance(item, dict), '语言疑误须为对象')
        unit, start, end = item.get('unit_index'), item.get('start'), item.get('end')
        _require(type(unit) is int and 0 <= unit < len(expected) and type(start) is int and type(end) is int
                 and 0 <= start <= end <= len(expected[unit]), '原稿疑误位置无效')
        _require(item.get('current_text') == expected[unit][start:end], '原稿疑误必须对应批准原文，不能伪造原文')
        _require(isinstance(item.get('suggested_text'), str) and item['suggested_text'] != item['current_text'], '须给出不同的疑误建议')
        _require(item.get('category') in {'typo', 'wording', 'repeated_word', 'punctuation', 'number', 'unit', 'name', 'term', 'quote'}, '语言疑误分类无效')
        _require(isinstance(item.get('reason'), str) and bool(item['reason'].strip()), '语言疑误须写具体语境或来源依据')
        hints = [h for h in hints if (h['unit_index'], h['start'], h['end']) != (unit, start, end)]
        hints.append({k: item[k] for k in ('unit_index', 'start', 'end', 'current_text', 'suggested_text', 'category', 'reason')} | {'origin': 'controller'})
    return hints, True


def inspect_copy(expected, payload):
    """Map approved units to reviewed object spans, then diagnose exact changes."""
    _require(isinstance(expected, list) and all(isinstance(t, str) for t in expected), '批准文字须为字符串列表')
    _require(isinstance(payload, dict) and payload.get('mapping_reviewed') is True, '先实际确认文字对象的阅读关系')
    _require(type(payload.get('slide_index')) is int and payload['slide_index'] > 0
             and isinstance(payload.get('canva_page_id'), str) and bool(payload['canva_page_id'].strip()), '报告须绑定实际页码及Canva页面ID')
    objects = _objects(payload.get('objects'))
    compared = list(expected)
    if payload.get('copy_check') is not None:
        from .canva_task import _validate_copy_check
        from .text_mapping_review import _editable_expected
        copy = _validate_copy_check(payload['copy_check'], expected_text=expected)
        for item in copy.get('graphic_spans', []):
            compared[item['unit_index']] = _editable_expected(item, expected[item['unit_index']])
        if copy.get('mode') == 'retained_artwork':
            for token in copy['artwork_text_tokens']:
                compared = [text.replace(' ' + token + ' ', '').replace(token, '') for text in compared]
    mappings = payload.get('mappings')
    _require(isinstance(mappings, list) and len(mappings) == len(expected), '每个批准文字单位须有映射，包括缺失单位')
    source_issues, reviewed = _language(expected, payload.get('language_review'))
    suspect_units = {i['unit_index'] for i in source_issues}
    used, seen, differences, changes = {k: set() for k in objects}, set(), [], {}
    for entry in mappings:
        unit = entry.get('unit_index') if isinstance(entry, dict) else None
        _require(type(unit) is int and 0 <= unit < len(expected) and unit not in seen, '映射单位缺失、重复或越界')
        seen.add(unit)
        segments = entry.get('segments')
        _require(isinstance(segments, list), 'segments须为按实际阅读顺序排列的对象片段')
        actual, locations = '', []
        for segment in segments:
            _require(isinstance(segment, dict), '映射片段须为对象')
            identity, start, end = segment.get('element_id'), segment.get('start'), segment.get('end')
            _require(isinstance(identity, str) and identity in objects and type(start) is int and type(end) is int and 0 <= start <= end <= len(objects[identity]), '对象片段定位无效')
            span = set(range(start, end))
            _require(not used[identity].intersection(span), '同一实际文字片段不得重复对应批准正文')
            used[identity].update(span)
            actual += objects[identity][start:end]
            locations.extend((identity, i) for i in range(start, end))
        norm, offsets = _layout_map(actual)
        target = layout_text(compared[unit])
        for tag, a0, a1, b0, b1 in SequenceMatcher(None, norm, target, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            left = offsets[a0] if a0 < len(offsets) else len(actual)
            right = offsets[a1 - 1] + 1 if a1 > a0 else left
            affected = locations[left:right]
            if not affected and locations:
                anchor = locations[left] if left < len(locations) else (locations[-1][0], locations[-1][1] + 1)
                affected = [anchor]
            if not affected and len(segments) == 1:
                affected = [(segments[0]['element_id'], segments[0]['start'])]
            identities = list(dict.fromkeys(p[0] for p in affected))
            contiguous = len(identities) == 1 and (right == left or [p[1] for p in affected] == list(range(affected[0][1], affected[-1][1] + 1)))
            if right == left and 0 < left < len(locations) and locations[left - 1][0] != locations[left][0]:
                contiguous = False
            before, after = actual[left:right], target[b0:b1]
            category = 'missing_text' if tag == 'insert' else 'extra_text' if tag == 'delete' else 'typo'
            if tag == 'replace' and any(c.isdigit() for c in before + after):
                category = 'number'
            elif tag == 'replace' and all(unicodedata.category(c).startswith('P') for c in before + after):
                category = 'punctuation'
            reason = 'source_suspect' if unit in suspect_units else 'language_review_pending' if not reviewed else 'cross_object_or_missing_target' if not contiguous else None
            difference = {'unit_index': unit, 'category': category, 'current_text': before, 'expected_text': after,
                          'element_ids': identities, 'context': actual[max(0, left - 12):right + 12],
                          'start': affected[0][1] if contiguous else None,
                          'end': (affected[-1][1] + 1 if right > left else affected[0][1]) if contiguous else None,
                          'critical': any(c.isdigit() or c in '不未无勿否' for c in before + after), 'blocked_reason': reason}
            differences.append(difference)
            if reason is None:
                identity = identities[0]
                start = affected[0][1]
                end = affected[-1][1] + 1 if right > left else start
                changes.setdefault(identity, []).append((start, end, after))
    for identity, text in objects.items():
        missing = [i for i in range(len(text)) if i not in used[identity]]
        if set(missing).intersection(_layout_map(text)[1]):
            differences.append({'category': 'unmapped_text', 'element_ids': [identity],
                                'current_text': ''.join(text[i] for i in missing), 'blocked_reason': 'review_object_mapping'})
    operations, results = [], dict(objects)
    for identity, edits in changes.items():
        text = objects[identity]
        edits.sort()
        _require(all(a[1] <= b[0] and a[0] != b[0] for a, b in zip(edits, edits[1:])), '修复片段重叠，需重新定位')
        start, end = edits[0][0], max(e[1] for e in edits)
        for padding in range(len(text) + 1):
            left, right = max(0, start - padding), min(len(text), end + padding)
            find = text[left:right]
            if find and len(list(re.finditer('(?=' + re.escape(find) + ')', text))) == 1:
                break
        else:
            for d in differences:
                if d.get('element_ids') == [identity]: d['blocked_reason'] = 'no_unique_context'
            continue
        replacement = find
        for a, b, value in reversed(edits):
            replacement = replacement[:a-left] + value + replacement[b-left:]
        operations.append({'type': 'find_and_replace_text', 'element_id': identity, 'find_text': find, 'replace_text': replacement})
        results[identity] = text[:left] + replacement + text[right:]
    for issue in source_issues:
        issue.update(status='suspected_source', auto_repair=False)
    return {'schema_version': '1.0', 'authority_sha256': _digest(expected), 'input': payload,
            'language_reviewed': reviewed, 'source_issues': source_issues, 'differences': differences,
            'operations': operations, 'expected_objects': results}


def _rebuild(report, expected):
    _require(isinstance(report, dict) and report.get('authority_sha256') == _digest(expected), '批准正文已变化，须重新校对')
    rebuilt = inspect_copy(expected, report.get('input'))
    _require(report == rebuilt, '校对报告或修复目标被改写，须重新生成')
    return rebuilt


def prepare_repairs(report, expected, live_objects):
    rebuilt = _rebuild(report, expected)
    _require(rebuilt['language_reviewed'], '语言审阅未完成，不派发文字替换')
    _require(_objects(live_objects) == _objects(report['input']['objects']), '实际对象已变化或缺失，须重新读取与定位')
    return rebuilt['operations']


def verify_repairs(report, expected, live_objects):
    rebuilt = _rebuild(report, expected)
    _require(rebuilt['language_reviewed'], '语言审阅未完成，不能记为修复核验通过')
    _require(not any(d.get('blocked_reason') for d in rebuilt['differences']), '仍有未定位或未解决文字差异，不能记为整页修复通过')
    actual = _objects(live_objects)
    _require(set(actual) == set(rebuilt['expected_objects']), '修复后对象增删或遗漏，不能通过')
    for identity, text in rebuilt['expected_objects'].items():
        _require(layout_text(actual[identity]) == layout_text(text), '修复后对象' + identity + '与计划不一致，或正常文字被连带改动')
    return {'verified': True, 'source_issues': rebuilt['source_issues'], 'objects_checked': len(actual)}


def check_task_text(run_dir, task_id, payload, mode='inspect'):
    """Read-only internal helper inside an existing Canva batch, never a stage writer."""
    from pathlib import Path
    from .json_io import read_json
    from .canva_task import CANVA_TASKS_REL, STAGE1_CONTENT_REL, _normal_task_id, _assert_safe_task_value
    root = Path(run_dir)
    directory = root / CANVA_TASKS_REL / _normal_task_id(task_id)
    task = read_json(directory / 'task.json')
    _require(isinstance(payload, dict), '输入须为JSON对象')
    _assert_safe_task_value(payload)
    current = read_json(root / STAGE1_CONTENT_REL)
    reference = read_json(directory / 'reference_text_by_slide.json')
    index = lambda doc: {p['slide_index']: p['final_visible_text'] for p in doc['slides']}
    authority = index(current)
    _require(authority == index(reference), '阶段1已变化，旧Canva参考失效')
    page = payload.get('slide_index')
    _require(type(page) is int and page in authority, '实际页码不在批准正文中')
    if mode == 'inspect':
        if payload.get('copy_check', {}).get('graphic_spans'):
            from .canva_task import _validate_graphic_copy_evidence
            _validate_graphic_copy_evidence(root, payload)
        return inspect_copy(authority[page], payload)
    report = payload.get('report')
    _require(isinstance(report, dict) and report.get('input', {}).get('slide_index') == page, '报告页码与本次实际操作页不一致')
    if isinstance(report, dict) and report.get('input', {}).get('copy_check', {}).get('graphic_spans'):
        from .canva_task import _validate_graphic_copy_evidence
        _validate_graphic_copy_evidence(root, report['input'])
    if mode == 'prepare':
        _require(task.get('text_policy') == 'authorized_reference_repair'
                 and 'find_and_replace_text' in task.get('repair_authorization', {}).get('allowed_operations', []), '本任务未授权精准文字替换')
        return {'operations': prepare_repairs(report, authority[page], payload.get('live_objects'))}
    _require(mode == 'verify', '未知校对模式')
    return verify_repairs(report, authority[page], payload.get('live_objects'))
