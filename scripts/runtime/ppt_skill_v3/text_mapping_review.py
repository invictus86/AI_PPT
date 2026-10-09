"""Evidence-bound display mappings; never rewrite or globally normalize copy."""
from pathlib import Path

from .file_hashing import file_sha256
from .json_io import read_json, write_json
from .validation import ValidationError

REVIEW = Path('_state/阶段5/editable_text_mapping_review.json')
CONNECTORS = {'→', ' → ', '←', ' ← ', '↓', ' ↓ ', '↑', ' ↑ '}
DECORATIONS = {'?', '？', '!', '！', '✓', '✔'}


def _require(condition, message):
    if not condition:
        raise ValidationError('editable text mapping: ' + message)


def _reason(item, key='reason'):
    _require(isinstance(item.get(key), str) and bool(item[key].strip()), 'needs ' + key)


def _visual(root, page, key):
    from PIL import Image
    value = page.get(key)
    _require(isinstance(value, str) and bool(value) and '://' not in value, 'needs local ' + key)
    path = Path(value)
    path = path if path.is_absolute() else root / path
    _require(path.resolve().is_relative_to(root.resolve()) and path.is_file(), 'visual must be inside project')
    _require(page.get(key + '_sha256') == file_sha256(path), 'visual changed: ' + key)
    try:
        with Image.open(path) as img:
            _require(img.width >= 100 and img.height >= 100, 'visual is too small')
            img.verify()
    except (OSError, ValueError) as exc:
        raise ValidationError('mapping needs actual page image evidence') from exc


def load_mapping_review(root, source, authority, document=None):
    root = Path(root)
    if document is None:
        if not (root / REVIEW).is_file():
            return None
        document = read_json(root / REVIEW)
    _require(isinstance(document, dict) and document.get('controller_reviewed') is True,
             'requires actual controller review')
    _require(document.get('input_sha256') == file_sha256(source), 'PPTX changed; review again')
    _require(document.get('stage1_content_sha256') == file_sha256(authority), 'approved copy changed')
    _reason(document, 'review_evidence')
    pages = document.get('pages')
    _require(isinstance(pages, list) and bool(pages), 'needs reviewed differing pages')
    seen = set()
    for page in pages:
        _require(isinstance(page, dict), 'page must be an object')
        n = page.get('slide_index')
        _require(type(n) is int and n > 0 and n not in seen, 'invalid or duplicate page')
        seen.add(n)
        _reason(page, 'observation')
        _visual(root, page, 'reference_visual')
        _visual(root, page, 'export_visual')
        canonical = root / f'阶段2_图片版PPT/img/slide_{n:03d}.png'
        if canonical.is_file():
            reference = Path(page['reference_visual'])
            reference = reference if reference.is_absolute() else root / reference
            _require(reference.resolve() == canonical.resolve(), 'reference must be the original same-page image')
            export = Path(page['export_visual'])
            export = export if export.is_absolute() else root / export
            manifests = [export.parent / 'render_manifest.json', root / '_state/阶段5/preview_manifest.json']
            matched = False
            for path in manifests:
                if not path.is_file():
                    continue
                manifest = read_json(path)
                if manifest.get('input_sha256') != file_sha256(source):
                    continue
                for image in manifest.get('images', []):
                    image_path = Path(image.get('path', ''))
                    image_path = image_path if image_path.is_absolute() else root / image_path
                    if image.get('page') == n and image_path.resolve() == export.resolve() and image.get('sha256') == page['export_visual_sha256']:
                        matched = True
            _require(matched, 'export visual must belong to a current input background render of this page')
    return document


def check_mapped_page(page, actual_units, expected_units):
    """Every source/approved unit is consumed once; only declared spaces/arrows differ."""
    units = page.get('units')
    _require(isinstance(units, list) and len(units) == len(expected_units), 'map every approved unit')
    consumed, expected_seen = set(), set()
    for unit in units:
        _require(isinstance(unit, dict), 'unit must be an object')
        i = unit.get('authority_unit_index')
        _require(type(i) is int and 0 <= i < len(expected_units) and i not in expected_seen,
                 'invalid or duplicate approved unit')
        expected_seen.add(i)
        _require(unit.get('expected_text') == expected_units[i], 'approved text differs')
        _reason(unit)
        sources = unit.get('sources')
        _require(isinstance(sources, list) and bool(sources), 'needs exact source paragraphs')
        chunks = []
        for src in sources:
            _require(isinstance(src, dict), 'source must be an object')
            index = src.get('index')
            _require(type(index) is int and 0 <= index < len(actual_units) and index not in consumed,
                     'missing, reused or invalid source paragraph')
            consumed.add(index)
            text = actual_units[index]
            _require(src.get('text') == text, 'source paragraph changed')
            spaces = src.get('remove_spaces', [])
            _require(isinstance(spaces, list) and all(type(pos) is int for pos in spaces)
                     and len(spaces) == len(set(spaces)), 'invalid spacing positions')
            _require(all(0 <= pos < len(text) and text[pos] in ' \t\u3000' for pos in spaces),
                     'only explicitly reviewed layout spaces may be removed')
            chunks.append(''.join(c for pos, c in enumerate(text) if pos not in spaces))
        joins = unit.get('joins', [''] * (len(chunks) - 1))
        _require(isinstance(joins, list) and len(joins) == len(chunks) - 1
                 and all(isinstance(j, str) and (j == '' or j in CONNECTORS) for j in joins),
                 'joins may only be empty or an explicit graphic arrow')
        if any(joins):
            _require(unit.get('graphic_connectors_reviewed') is True, 'review graphic connectors')
        reconstructed = chunks[0] + ''.join(j + c for j, c in zip(joins, chunks[1:]))
        _require(reconstructed == expected_units[i], 'word, punctuation, number or spacing mismatch')
    decorations = page.get('decorations', [])
    _require(isinstance(decorations, list), 'decorations must be a list')
    for item in decorations:
        _require(isinstance(item, dict), 'decoration must be an object')
        i = item.get('index')
        _require(type(i) is int and 0 <= i < len(actual_units) and i not in consumed, 'invalid decoration index')
        _require(item.get('text') == actual_units[i] and actual_units[i] in DECORATIONS,
                 'only reviewed original standalone decoration symbols can be excluded')
        _require(item.get('original_decoration_confirmed') is True, 'confirm original decoration')
        _reason(item)
        consumed.add(i)
    _require(consumed == set(range(len(actual_units))), 'extra or unaccounted editable text')


def record_mapping_review(root, source, document):
    from .text_preservation import verify_stage1_text
    result = verify_stage1_text(root, source, mapping_document=document)
    used = {p['slide_index'] for p in result['pages'] if p['match_method'] == 'controller_reviewed_display_mapping'}
    _require(used == {p['slide_index'] for p in document['pages']}, 'review only the actual differing pages')
    write_json(Path(root) / REVIEW, document)
    return {'status': 'recorded', 'review': str(Path(root) / REVIEW), 'mapped_pages': sorted(used),
            'review_sha256': file_sha256(Path(root) / REVIEW), 'input_unchanged': True}


def require_task_mapping(root, task):
    authority = task.get('approved_text_authority')
    if authority:
        _require(file_sha256(Path(root) / authority) == task.get('approved_text_authority_sha256'),
                 'approved original text changed after inspection')
    path = task.get('text_mapping_review')
    if path:
        _require(file_sha256(Path(root) / path) == task.get('text_mapping_review_sha256'),
                 'mapping review changed after inspection')
    if path or authority:
        from .text_preservation import verify_stage1_text
        return verify_stage1_text(root, task['input'])
