"""Check declared teaching relationships; never guess roles from text or geometry."""
from __future__ import annotations


def check_relations(plan, inventory=None):
    from .plan import keys, require

    pages = {p['slide_index']: p for p in plan['pages']}
    rows = {p['slide_index']: p for p in inventory['pages']} if inventory else {}
    refs = {}
    for ref in plan.get('question_refs', []):
        keys(ref, {'question_id', 'slide_index', 'targets', 'evidence', 'visual_checked'},
             {'question_id', 'slide_index', 'targets', 'evidence'})
        qid, index, targets = ref['question_id'], ref['slide_index'], ref['targets']
        require(isinstance(qid, str) and bool(qid.strip()) and qid not in refs, 'Duplicate/invalid question reference')
        require(type(index) is int and index > 0, 'Invalid question reference page')
        require(isinstance(targets, list) and targets and all(type(t) is int and t > 0 for t in targets)
                and len(targets) == len(set(targets)), 'Invalid question reference targets')
        require(isinstance(ref['evidence'], str) and bool(ref['evidence'].strip()), 'Question reference needs actual matching evidence')
        require('visual_checked' not in ref or type(ref['visual_checked']) is bool, 'visual_checked must be boolean')
        if inventory:
            require(index in rows and set(targets) <= {o['id'] for o in rows[index]['objects']},
                    'Question reference contains missing page/targets')
            if rows[index]['has_visual_content']:
                require(ref.get('visual_checked') is True, 'Referenced question contains graphics: review its actual materials')
        if index in pages:
            anchors = [u for u in pages[index]['units'] if set(u['targets']) & set(targets)]
            require(any(u['role'] == 'question' for u in anchors), 'Question reference must include a real question unit, not a title')
            require(all(u.get('question_id') == qid and u['role'] in {'question', 'given', 'options'}
                        and not u.get('is_title') and u['click'] == 0 for u in anchors),
                    'Question reference targets must be initially visible question/material units')
        refs[qid] = ref

    titles, question_groups = [], {}
    for index, page in pages.items():
        units = {u['id']: u for u in page['units']}
        for unit in page['units']:
            if unit.get('is_title'):
                require(unit['role'] in {'content', 'answer'}, 'A page title cannot impersonate a question/given/options unit')
                reason = unit.get('title_exception_reason', '')
                bodies = [u for u in page['units'] if u.get('title_id') == unit['id']]
                require(bodies, 'Declared page title needs its corresponding body units')
                late = [u['id'] for u in bodies if u['click'] < unit['click']]
                require(not late or bool(reason.strip()),
                        f'Page {index}: body appears before title; replan or record the actual teaching exception')
                titles.append({'page': index, 'title': unit['id'], 'late_to': late,
                               'exception_reason': reason, 'order': 'reviewed_exception' if late else 'title_first_or_together'})
            if unit.get('title_id') is not None:
                title = units.get(unit['title_id'])
                require(title is not None and title is not unit and title.get('is_title') is True,
                        'title_id must bind a separate declared page title in the same page')
            qid, role = unit.get('question_id'), unit['role']
            if role not in {'question', 'given', 'options', 'answer', 'answer_marker', 'explanation'}:
                continue
            # Old same-page IDs stay page-scoped. Only explicit refs join pages.
            key = ('ref', qid) if qid in refs else (index, qid)
            group = question_groups.setdefault(key, {'question': [], 'answer': [], 'other': [], 'qid': qid})
            group['question' if role == 'question' else 'answer' if role == 'answer' else 'other'].append((index, unit))
            if qid in refs:
                source_page = refs[qid]['slide_index']
                require(index >= source_page, f'Question {qid}: answer/material appears before its question page')
                if role == 'question':
                    require(index == source_page, 'Question reference has ambiguous repeated question pages')
                    require(set(unit['targets']) <= set(refs[qid]['targets']), 'Question reference omits part of its question')

    links = []
    for key, group in question_groups.items():
        qid = group['qid']
        ref = refs.get(qid) if key[0] == 'ref' else None
        require(ref is not None or group['question'], 'Unknown question_id: bind a real question or explicit cross-page reference')
        answer_positions = {(i, u['click']) for i, u in group['answer']}
        require(len(answer_positions) <= 1, 'Answer must bind one question and one synchronized page/step')
        answer_position = next(iter(answer_positions), None)
        for index, unit in group['other']:
            role = unit['role']
            if role in {'given', 'options'} and answer_position is not None:
                require((index, unit['click']) < answer_position,
                        'Necessary conditions/options must appear before the corresponding answer')
            if role in {'answer_marker', 'explanation'}:
                require(answer_position is not None, 'Marker/explanation requires its answer in this plan')
                position = (index, unit['click'])
                require(position == answer_position if role == 'answer_marker' else position > answer_position,
                        'Marker must reveal with answer; explanation requires a later manual click or later page')
        links.append({'question_id': qid, 'question_page': ref['slide_index'] if ref else group['question'][0][0],
                      'question_targets': ref['targets'] if ref else [t for _, u in group['question'] for t in u['targets']],
                      'answer_position': list(answer_position) if answer_position else None,
                      'evidence': ref['evidence'] if ref else 'same-page declared question units'})
    require(all(('ref', qid) in question_groups for qid in refs), 'Unused question reference')
    return {'title_order_checks': titles, 'question_links': links,
            'undeclared_title_pages': sorted(i for i, p in pages.items() if not any(u.get('is_title') for u in p['units'])),
            'content_roles_and_relationship_evidence': 'controller_review_required'}
