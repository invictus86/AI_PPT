"""Reviewed, local text presentation changes and source-backed restorations.

The controller judges visual quality and mildness. This module applies only
declared properties to existing text objects and preserves unrelated package parts.
"""
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
import math
import re
import zipfile

from lxml import etree

from .file_hashing import file_sha256
from .font_repair import A, P, _shapes, _text
from .json_io import read_json
from .validation import ValidationError

RUN_KEYS = {'font_family', 'font_size', 'bold', 'italic', 'underline', 'character_spacing', 'color'}
PARAGRAPH_KEYS = {'alignment', 'line_spacing_percent', 'line_spacing_points',
                  'space_before', 'space_after', 'indent', 'margin_left'}
BOX_KEYS = {'left', 'top', 'width', 'height', 'margin_left', 'margin_right',
            'margin_top', 'margin_bottom', 'vertical_anchor'}


def layout_text(text):
    """Ignore text line wrapping and unambiguous Chinese layout spacing only.

    English word spaces, digits, punctuation, formulas and all actual letters
    remain. No bag-of-characters, punctuation cleaning or fuzzy semantic match.
    """
    text = re.sub(r'(^|[\n\r\v])[ \t\u3000]+(?=[\u3400-\u9fff])', r'\1', text)
    text = re.sub(r'(?<=[\u3400-\u9fff])[ \t\u3000]+(?=[\u3400-\u9fff])', '', text)
    return text.replace('\r', '').replace('\n', '').replace('\v', '')


def page_text_equal(actual, expected):
    return layout_text(''.join(actual)) == layout_text(''.join(expected))


def _require(condition, message):
    if not condition:
        raise ValidationError('text optimization: ' + message)


def _evidence(root, entry, key, bind):
    value = entry.get(key)
    _require(isinstance(value, str) and value and '://' not in value, 'needs local ' + key)
    path = Path(value)
    path = path if path.is_absolute() else root / path
    _require(path.is_file() and path.resolve().is_relative_to(root.resolve()), 'evidence must be inside project')
    digest = file_sha256(path)
    if bind:
        entry[key + '_sha256'] = digest
    else:
        _require(entry.get(key + '_sha256') == digest, 'evidence changed: ' + key)
    return path


def validate_optimizations(source, entries, *, root, bind=False):
    from .teaching_animation import slide_parts
    root = Path(root)
    _require(isinstance(entries, list), 'text_optimizations must be a list')
    parts = slide_parts(source)
    seen = set()
    with zipfile.ZipFile(source) as package:
        for entry in entries:
            _require(isinstance(entry, dict), 'entry must be an object')
            page, identity = entry.get('page'), entry.get('shape_id')
            _require(type(page) is int and 1 <= page <= len(parts), 'invalid page')
            shapes = _shapes(etree.fromstring(package.read(parts[page - 1])))
            _require(type(identity) is int and identity in shapes and (page, identity) not in seen,
                     'use one entry for each existing text object')
            seen.add((page, identity))
            shape = shapes[identity]
            _require(entry.get('before_text') == _text(shape), 'source text changed')
            _require(entry.get('controller_reviewed') is True and entry.get('mild_adjustment_confirmed') is True,
                     'controller must review the local adjustment and page hierarchy')
            _require(isinstance(entry.get('reason'), str) and entry['reason'].strip(), 'needs adjustment reason')
            _evidence(root, entry, 'visual_evidence', bind)
            changes = False
            for name, allowed in [('run_format', RUN_KEYS), ('paragraph_format', PARAGRAPH_KEYS), ('text_box', BOX_KEYS)]:
                values = entry.get(name, {})
                _require(isinstance(values, dict) and not set(values) - allowed, 'unsupported ' + name)
                changes |= bool(values)
                for key, value in values.items():
                    if key == 'font_family':
                        from .font_repair import validate_reference_font
                        _require(isinstance(value, str) and type(values.get('bold')) is bool,
                                 'font replacement needs a family and visually chosen bold flag')
                        font_entry = {**entry, 'target_font': value, 'text': entry.get('after_text', entry['before_text'])}
                        validate_reference_font(font_entry)
                        path = Path(entry['font_file'])
                        if bind:
                            entry['font_file_sha256'] = file_sha256(path)
                        else:
                            _require(entry.get('font_file_sha256') == file_sha256(path), 'installed font changed')
                    elif key in {'bold', 'italic', 'underline'}:
                        _require(type(value) is bool, 'style flags must be boolean')
                    elif key == 'color':
                        _require(isinstance(value, str) and re.fullmatch('[0-9a-fA-F]{6}', value), 'use RGB hex color')
                    elif key == 'alignment':
                        _require(value in {'left', 'center', 'right', 'justify'}, 'unknown alignment')
                    elif key == 'vertical_anchor':
                        _require(value in {'top', 'middle', 'bottom'}, 'unknown vertical anchor')
                    else:
                        _require(type(value) in {int, float} and math.isfinite(value), 'use finite numeric properties')
                        if key not in {'left', 'top', 'indent', 'character_spacing'}:
                            _require(value >= 0, 'negative size or spacing')
                        if key in {'font_size', 'width', 'height', 'line_spacing_percent', 'line_spacing_points'}:
                            _require(value > 0, 'size and line spacing must be positive')
                if name == 'paragraph_format':
                    _require(not {'line_spacing_percent', 'line_spacing_points'} <= set(values), 'choose one line spacing mode')
            after = entry.get('after_text', entry['before_text'])
            _require(isinstance(after, str), 'after_text must be text')
            if after != entry['before_text']:
                _require(not any(n.tag == A + 'fld' for n in shape.iter()), 'preserve dynamic text fields')
                changes = True
                mode = entry.get('text_change', 'layout')
                if mode == 'layout':
                    _require(layout_text(after) == layout_text(entry['before_text']), 'layout edit changes actual content')
                else:
                    _require(mode == 'reference_restoration', 'only layout or source-backed restoration is allowed')
                    _require(entry.get('reference_restoration_confirmed') is True, 'confirm original source restoration')
                    visual = _evidence(root, entry, 'reference_visual', bind)
                    canonical = root / f'阶段2_图片版PPT/img/slide_{page:03d}.png'
                    if canonical.is_file():
                        _require(visual.resolve() == canonical.resolve(), 'restoration must use the original same-page image')
                    authority = root / '_state/阶段1/content.json'
                    if authority.is_file():
                        approved = next((s['final_visible_text'] for s in read_json(authority)['slides']
                                         if s['slide_index'] == page), None)
                        # Conversion may merge several original text units into
                        # one existing textbox. Preserve complete units in their
                        # original order rather than forcing the user to split it.
                        matches = False
                        if approved is not None:
                            for start in range(len(approved)):
                                joined = ''
                                for unit in approved[start:]:
                                    joined += unit
                                    if layout_text(after) == layout_text(joined):
                                        matches = True
                                        break
                                if matches:
                                    break
                        _require(matches, 'restored whole object must equal complete approved original units in order')
                        if bind:
                            entry['authority_sha256'] = file_sha256(authority)
                        else:
                            _require(entry.get('authority_sha256') == file_sha256(authority), 'original approved text changed')
                    else:
                        path = _evidence(root, entry, 'reference_text_file', bind)
                        _require(after in path.read_text(encoding='utf-8-sig'), 'restoration must come from the original transcript')
            _require(changes, 'entry has no adjustment')
            if entry.get('text_box') and set(entry['text_box']) & {'left', 'top', 'width', 'height'}:
                _require(shape.find(P + 'spPr/' + A + 'xfrm') is not None,
                         'textbox geometry is inherited; preserve it rather than invent coordinates')
    return entries


def _properties(parent, tag, first=False):
    node = parent.find(A + tag)
    if node is None:
        node = etree.Element(A + tag)
        if first:
            parent.insert(0, node)
        else:
            parent.append(node)
    return node


def _reflow(shape, text):
    from .font_repair import _tokens
    body = shape.find(P + 'txBody')
    originals = body.findall(A + 'p')
    paragraphs = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    original_text = _text(shape)
    styles = [(node, paragraph) for node, paragraph, _, token in _tokens(shape) for _ in token]
    mapped = []
    for kind, i, end, j, stop in SequenceMatcher(None, original_text, normalized, autojunk=False).get_opcodes():
        for offset in range(stop - j):
            position = i + offset if kind == 'equal' else min(i + offset, max(i, end - 1))
            mapped.append(styles[min(position, len(styles) - 1)] if styles else (None, originals[0]))
    fallback = next((n for p in originals for n in p if n.tag == A + 'r'), None)
    position = 0
    for paragraph in originals:
        body.remove(paragraph)
    for index, value in enumerate(paragraphs):
        old = mapped[position][1] if position < len(mapped) else originals[min(index, len(originals) - 1)]
        paragraph = deepcopy(old)
        for node in list(paragraph):
            if node.tag in {A + 'r', A + 'br', A + 'fld'}:
                paragraph.remove(node)
        end = paragraph.find(A + 'endParaRPr')
        insert_at = paragraph.index(end) if end is not None else len(paragraph)
        for part_index, chunk in enumerate(value.split('\v')):
            if part_index:
                paragraph.insert(insert_at, etree.Element(A + 'br')); insert_at += 1; position += 1
            segments = []
            for character in chunk:
                template = mapped[position][0] if position < len(mapped) else fallback
                if template is None or template.tag != A + 'r':
                    template = fallback
                if segments and segments[-1][0] is template:
                    segments[-1][1] += character
                else:
                    segments.append([template, character])
                position += 1
            if not segments:
                segments = [[fallback, '']]
            for template, content in segments:
                run = deepcopy(template) if template is not None else etree.Element(A + 'r')
                node = run.find(A + 't')
                if node is None:
                    node = etree.SubElement(run, A + 't')
                node.text = content
                paragraph.insert(insert_at, run); insert_at += 1
        body.append(paragraph)
        position += 1


def patch_text_tree(tree, entries):
    shapes = _shapes(tree)
    for entry in entries:
        shape = shapes[entry['shape_id']]
        after = entry.get('after_text', entry['before_text'])
        if after != entry['before_text']:
            _reflow(shape, after)
        for paragraph in shape.find(P + 'txBody').findall(A + 'p'):
            for run in paragraph:
                if run.tag != A + 'r':
                    continue
                fmt = entry.get('run_format', {})
                if not fmt:
                    continue
                props = _properties(run, 'rPr', True)
                for key, value in fmt.items():
                    if key == 'font_family':
                        from .font_repair import _set_font
                        _set_font(run, fmt['bold'], value)
                    elif key == 'color':
                        for fill in list(props):
                            if fill.tag in {A + t for t in ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill')}:
                                props.remove(fill)
                        fill = etree.Element(A + 'solidFill')
                        etree.SubElement(fill, A + 'srgbClr').set('val', value.upper())
                        # Fill precedes effects, underline and font slots in CT_TextCharacterProperties.
                        later = {A + t for t in ('effectLst', 'effectDag', 'highlight', 'uLnTx', 'uLn',
                                                 'uFillTx', 'uFill', 'latin', 'ea', 'cs', 'sym', 'hlinkClick', 'hlinkMouseOver', 'rtl', 'extLst')}
                        props.insert(next((i for i, n in enumerate(props) if n.tag in later), len(props)), fill)
                    else:
                        attr = {'font_size': 'sz', 'bold': 'b', 'italic': 'i', 'underline': 'u', 'character_spacing': 'spc'}[key]
                        props.set(attr, ('sng' if value else 'none') if key == 'underline' else
                                  ('1' if value else '0') if type(value) is bool else str(round(value * 100)))
            fmt = entry.get('paragraph_format', {})
            if fmt:
                props = _properties(paragraph, 'pPr', True)
                for key, value in fmt.items():
                    if key == 'alignment':
                        props.set('algn', {'left': 'l', 'center': 'ctr', 'right': 'r', 'justify': 'just'}[value])
                    elif key in {'indent', 'margin_left'}:
                        props.set('indent' if key == 'indent' else 'marL', str(round(value * 12700)))
                    else:
                        tag = {'line_spacing_percent': 'lnSpc', 'line_spacing_points': 'lnSpc',
                               'space_before': 'spcBef', 'space_after': 'spcAft'}[key]
                        node = props.find(A + tag)
                        if node is not None:
                            props.remove(node)
                        node = etree.Element(A + tag)
                        etree.SubElement(node, A + ('spcPct' if key == 'line_spacing_percent' else 'spcPts')).set(
                            'val', str(round(value * (1000 if key == 'line_spacing_percent' else 100))))
                        order = ['lnSpc', 'spcBef', 'spcAft']
                        rank = order.index(tag)
                        props.insert(next((i for i, n in enumerate(props)
                                           if n.tag not in {A + t for t in order[:rank]}), len(props)), node)
        fmt = entry.get('text_box', {})
        for key, value in fmt.items():
            if key in {'left', 'top', 'width', 'height'}:
                xfrm = shape.find(P + 'spPr/' + A + 'xfrm')
                node = xfrm.find(A + ('off' if key in {'left', 'top'} else 'ext'))
                _require(node is not None, 'textbox transform is incomplete')
                node.set({'left': 'x', 'top': 'y', 'width': 'cx', 'height': 'cy'}[key], str(round(value * 12700)))
            else:
                props = shape.find(P + 'txBody/' + A + 'bodyPr')
                if key == 'vertical_anchor':
                    props.set('anchor', {'top': 't', 'middle': 'ctr', 'bottom': 'b'}[value])
                else:
                    props.set({'margin_left': 'lIns', 'margin_right': 'rIns', 'margin_top': 'tIns', 'margin_bottom': 'bIns'}[key],
                              str(round(value * 12700)))
    return tree


def apply_text_optimizations(source, baseline, output, entries, *, root):
    from .teaching_animation import slide_parts
    validate_optimizations(source, entries, root=root)
    _require(Path(output).resolve() not in {Path(source).resolve(), Path(baseline).resolve()}, 'preserve source and baseline')
    parts = slide_parts(source)
    by_part = {part: [e for e in entries if parts[e['page'] - 1] == part] for part in parts}
    with zipfile.ZipFile(baseline) as package, zipfile.ZipFile(output, 'w') as target:
        for item in package.infolist():
            data = package.read(item.filename)
            if by_part.get(item.filename):
                tree = patch_text_tree(etree.fromstring(data), by_part[item.filename])
                data = etree.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
            target.writestr(item, data)
