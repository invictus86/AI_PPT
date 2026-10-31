"""Order complete reveal blocks, with declared teaching dependencies taking precedence.

Geometry supplies a default, never a content role. This module checks a plan;
it does not change click numbers or the presentation's objects.
"""
from __future__ import annotations

from .plan import keys, require


def _box(obj):
    if 'bounds' in obj:
        return obj['bounds']
    # Earlier inventories store the outer xfrm first. Never use a child transform
    # to estimate a group's position when the outer transform is absent.
    geom = obj.get('geometry', [])
    if len(geom) >= 2 and {'x', 'y'} <= geom[0].keys() and {'cx', 'cy'} <= geom[1].keys():
        return [int(geom[0]['x']), int(geom[0]['y']), int(geom[1]['cx']), int(geom[1]['cy'])]
    return None


def _unit_box(unit, objects):
    targets = [unit['order_anchor']] if 'order_anchor' in unit else unit['targets']
    boxes = [_box(objects[t]) for t in targets]
    if not boxes or any(b is None or b[2] <= 0 or b[3] <= 0 for b in boxes):
        return None
    left, top = min(b[0] for b in boxes), min(b[1] for b in boxes)
    return [left, top, max(b[0]+b[2] for b in boxes)-left, max(b[1]+b[3] for b in boxes)-top]


def _geometric_order(nodes, boxes):
    """Top-to-bottom bands; within a near-aligned band, left-to-right.

    Band membership is relative to its first item, not transitively chained.
    The quarter-height tolerance accommodates text/image alignment jitter.
    """
    pending = sorted(nodes, key=lambda n: (boxes[n][1], boxes[n][0], n))
    result = []
    while pending:
        first = pending[0]
        row = [n for n in pending if abs(boxes[n][1]-boxes[first][1]) <= min(boxes[n][3], boxes[first][3]) * .25]
        result.extend(sorted(row, key=lambda n: (boxes[n][0], boxes[n][1], n)))
        pending = [n for n in pending if n not in row]
    return result


def check_ordering(plan, inventory, dependencies):
    if plan['schema_version'] != '1.1':
        return {'status': 'legacy_not_checked', 'pages': []}
    rows = {p['slide_index']: p for p in inventory['pages']} if inventory else {}
    reports = []
    for page in plan['pages']:
        index = page['slide_index']
        units = {u['id']: u for u in page['units']}
        parent = {name: name for name in units}

        def root(name):
            while parent[name] != name:
                name = parent[name]
            return name

        def join(a, b):
            require(units[a]['click'] == units[b]['click'], f'Page {index}: bound members must reveal together: {a}, {b}')
            parent[root(b)] = root(a)

        bindings, answers = {}, {}
        for unit in units.values():
            if 'order_anchor' in unit:
                require(type(unit['order_anchor']) is int and unit['order_anchor'] in unit['targets'], 'order_anchor must be an owned top-level target')
            if 'binding_id' in unit:
                value = unit['binding_id']
                require(isinstance(value, str) and bool(value.strip()), 'Invalid binding_id')
                if value in bindings:
                    join(bindings[value], unit['id'])
                bindings[value] = unit['id']
            if unit['role'] in {'answer', 'answer_marker'}:
                qid = unit['question_id']
                if qid in answers:
                    join(answers[qid], unit['id'])
                answers[qid] = unit['id']
        groups = {}
        for name in units:
            groups.setdefault(root(name), []).append(name)

        edges = [(a, b, strict) for p, a, b, strict in dependencies if p == index]
        constraints = page.get('order_constraints', [])
        require(isinstance(constraints, list), 'order_constraints must be a list')
        for edge in constraints:
            keys(edge, {'before', 'after', 'reason'}, {'before', 'after', 'reason'})
            a, b = edge['before'], edge['after']
            require(isinstance(a, str) and isinstance(b, str) and a in units and b in units and a != b, 'Order constraint needs distinct existing units on this page')
            require(isinstance(edge['reason'], str) and bool(edge['reason'].strip()), 'Order constraint needs concrete teaching evidence')
            edges.append((a, b, True))
        graph = {g: set() for g in groups}
        for a, b, strict in edges:
            ra, rb = root(a), root(b)
            require(ra != rb or not strict, f'Page {index}: binding conflicts with required before/after order; reclassify or report needs_layering')
            if ra != rb:
                graph[ra].add(rb)
            require(units[a]['click'] < units[b]['click'] if strict else units[a]['click'] <= units[b]['click'],
                    f'Page {index}: dependency violated: {a} before {b}')

        # Validate the whole graph, including initial units, even without geometry.
        remaining = set(graph)
        while remaining:
            ready = {n for n in remaining if not any(n in graph[p] for p in remaining)}
            require(ready, f'Page {index}: cyclic teaching dependencies')
            remaining -= ready

        dynamic = [g for g, names in groups.items() if units[names[0]]['click'] > 0]
        dynamic_names = {name for g in dynamic for name in groups[g]}
        explicit = page.get('reading_order')
        if explicit is not None:
            require(isinstance(explicit, list) and all(isinstance(n, str) for n in explicit)
                    and len(explicit) == len(set(explicit)) and set(explicit) == dynamic_names,
                    'reading_order must list every dynamic unit exactly once, excluding initial units')
            require(isinstance(page.get('reading_order_reason'), str) and bool(page['reading_order_reason'].strip()),
                    'Non-default reading order needs current layout evidence')
            baseline = list(dict.fromkeys(root(n) for n in explicit))
        else:
            require('reading_order_reason' not in page, 'reading_order_reason requires reading_order')
            baseline = None
            if index in rows:
                objects = {o['id']: o for o in rows[index]['objects']}
                boxes = {}
                for g in dynamic:
                    members = [_unit_box(units[n], objects) for n in groups[g]]
                    require(all(b is not None for b in members), f'Page {index}: missing block position; declare reviewed reading_order and reason')
                    left, top = min(b[0] for b in members), min(b[1] for b in members)
                    boxes[g] = [left, top, max(b[0]+b[2] for b in members)-left, max(b[1]+b[3] for b in members)-top]
                baseline = _geometric_order(dynamic, boxes)
        if baseline is None:
            reports.append({'page': index, 'status': 'requires_inventory', 'bindings': list(groups.values())})
            continue
        # Stable topological order: dependency edges win; free blocks keep the
        # reviewed/default reading order. S0 is already visible, not a late block.
        remaining, resolved = set(dynamic), []
        while remaining:
            ready = [n for n in baseline if n in remaining and not any(n in graph[p] for p in remaining)]
            require(ready, f'Page {index}: cyclic dynamic ordering')
            chosen = ready[0]
            remaining.remove(chosen)
            resolved.append(chosen)
        clicks = [units[groups[g][0]]['click'] for g in resolved]
        require(clicks == sorted(clicks), f'Page {index}: reading order inverted; expected blocks { [groups[g] for g in resolved] }. Use a justified dependency/layout order, not arbitrary click numbers')
        reports.append({'page': index, 'status': 'checked', 'basis': 'reviewed_layout' if explicit is not None else 'top_to_bottom_left_to_right',
                        'baseline': [groups[g] for g in baseline], 'resolved': [groups[g] for g in resolved],
                        'bindings': list(groups.values()), 'constraints': constraints})
    return {'status': 'checked' if inventory else 'structural_only', 'pages': reports,
            'semantic_review': 'controller_required'}
