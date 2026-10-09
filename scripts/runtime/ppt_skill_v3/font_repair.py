"""Deterministic, reviewed sentence/title repairs; never a global font replacement.

Offsets are Python Unicode character offsets in the object's text: paragraph
boundaries are '\n', explicit soft breaks '\v'. Visual diagnosis and semantic
sentence boundaries belong to the controller, not the execution script.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
import unicodedata
import zipfile

from lxml import etree

from .validation import ValidationError

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
TARGET_FONT = "微软雅黑"
FONT_SLOTS = ("latin", "ea", "cs", "sym")
COMMON_FONT_FAMILIES = {
    '微软雅黑', 'Microsoft YaHei', 'Microsoft YaHei UI', '宋体', 'SimSun', '新宋体', 'NSimSun',
    '黑体', 'SimHei', '楷体', 'KaiTi', '仿宋', 'FangSong', '幼圆', 'YouYuan', '等线', 'DengXian',
    '思源黑体', '思源宋体', 'Source Han Sans SC', 'Source Han Serif SC',
    'Source Han Sans CN', 'Source Han Serif CN', 'Noto Sans CJK SC', 'Noto Serif CJK SC',
    'Noto Sans SC', 'Noto Serif SC', '文泉驿微米黑', 'WenQuanYi Micro Hei',
    '文泉驿正黑', 'WenQuanYi Zen Hei', 'Heiti SC', 'STHeiti', 'Songti SC', 'STSong',
    'Kaiti SC', 'STKaiti', 'Arial', 'Calibri', 'Aptos', 'Times New Roman'
}


def system_font_roots():
    return [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
            Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Microsoft/Windows/Fonts',
            Path('/Library/Fonts'), Path('/System/Library/Fonts'), Path.home() / 'Library/Fonts',
            Path('/usr/share/fonts'), Path('/usr/local/share/fonts'),
            Path.home() / '.fonts', Path.home() / '.local/share/fonts']


def is_installed_font(path: Path) -> bool:
    """Require a system/user font location or an actual Windows font registration."""
    path = path.resolve()
    roots = system_font_roots()
    if any(path.is_relative_to(root.resolve()) for root in roots):
        return True
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                    for index in range(winreg.QueryInfoKey(key)[1]):
                        value = winreg.EnumValue(key, index)[1]
                        if isinstance(value, str) and Path(value).is_absolute() and Path(value).resolve() == path:
                            return True
            except OSError:
                continue
    return False


def validate_reference_font(repair):
    from fontTools.ttLib import TTFont
    if repair.get('non_premium') is not True or repair.get('target_font', '').casefold() not in {f.casefold() for f in COMMON_FONT_FAMILIES}:
        raise ValidationError('choose a common installed non-premium font; paid/member/custom families are excluded')
    path = Path(repair.get('font_file', ''))
    if not path.is_absolute() or not path.is_file() or not is_installed_font(path):
        raise ValidationError('reference font must exist and be installed on this computer')
    index = repair.get('font_face_index', 0)
    if type(index) is not int or index < 0:
        raise ValidationError('invalid collection font face index')
    try:
        with TTFont(path, fontNumber=index) as font:
            names = {n.toUnicode().casefold() for n in font['name'].names if n.nameID in {1, 16}}
            if repair['target_font'].casefold() not in names:
                raise ValidationError('target font does not match the installed font file family')
            cmap = font.getBestCmap() or {}
            missing = {c for c in repair['text'] if not c.isspace()
                       and unicodedata.category(c) != 'Cf' and ord(c) not in cmap}
            if missing:
                raise ValidationError('reference font lacks required glyphs: ' + ''.join(sorted(missing)))
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError('cannot inspect reference font file') from exc


def _body(shape):
    return shape.find(f"{P}txBody")


def _tokens(shape):
    """Return all text-bearing runs/breaks, including otherwise unsupported fields."""
    offset = 0
    paragraphs = _body(shape).findall(f"{A}p")
    for p_index, paragraph in enumerate(paragraphs):
        for node in paragraph:
            if node.tag == A + "br":
                text = "\v"
            elif node.tag in {A + "r", A + "fld"}:
                text = node.findtext(A + "t", default="")
            else:
                continue
            yield node, paragraph, offset, text
            offset += len(text)
        if p_index + 1 < len(paragraphs):
            yield None, paragraph, offset, "\n"
            offset += 1


def _text(shape):
    return "".join(t[3] for t in _tokens(shape))


def _shapes(tree):
    result = {}
    for shape in tree.iter(P + "sp"):
        if _body(shape) is None:
            continue
        identity = shape.find(f"{P}nvSpPr/{P}cNvPr")
        if identity is None or not identity.get("id", "").isdigit():
            raise ValidationError("text object has no stable identity")
        shape_id = int(identity.get("id"))
        if shape_id in result:
            raise ValidationError("duplicate text object identity")
        result[shape_id] = shape
    return result


def inspect_text_objects(tree):
    """Include nested group text and raw properties; inheritance needs visual review."""
    objects = []
    for shape_id, shape in _shapes(tree).items():
        runs = []
        for node, _, offset, text in _tokens(shape):
            if node is None or node.tag != A + "r":
                continue
            properties = node.find(A + "rPr")
            runs.append({"start": offset, "end": offset + len(text), "text": text,
                         "properties": dict(properties.attrib) if properties is not None else {},
                         "font_slots": {slot: dict(font.attrib) for slot in FONT_SLOTS
                             if properties is not None and (font := properties.find(A + slot)) is not None}})
        objects.append({"shape_id": shape_id, "text": _text(shape), "runs": runs,
                        "has_fields": any(n.tag == A + "fld" for n in shape.iter())})
    return objects


def _expanded_repairs(repairs):
    """Expand a reviewed semantic group into narrow existing-object ranges.

    Group validation happens before expansion. No textbox or text is rebuilt.
    Internal flags cannot be supplied by a plan to bypass boundary checks.
    """
    result = []
    for repair in repairs:
        if not isinstance(repair, dict) or any(k.startswith('_group_') for k in repair):
            raise ValidationError('invalid font repair or reserved group flag')
        if 'segments' not in repair:
            result.append(repair)
            continue
        for segment in repair['segments']:
            entry = {k: v for k, v in repair.items() if k not in {'segments', 'text', 'shape_id', 'start', 'end', 'bold', 'bold_reason'}}
            entry.update(segment)
            entry['_group_validated'] = True
            result.append(entry)
    return result


def _validate_groups(source, parts, repairs):
    with zipfile.ZipFile(source) as package:
        for repair in repairs:
            if not isinstance(repair, dict) or 'segments' not in repair:
                continue
            page, segments = repair.get('page'), repair.get('segments')
            if type(page) is not int or not 1 <= page <= len(parts):
                raise ValidationError('font group needs an actual page')
            if not isinstance(segments, list) or len(segments) < 2:
                raise ValidationError('cross-object group needs at least two complete linked ranges')
            if repair.get('whole_unit_confirmed') is not True or repair.get('unit_kind') not in {'sentence', 'title'}:
                raise ValidationError('confirm the complete cross-object sentence/title')
            if not isinstance(repair.get('mapping_reason'), str) or not repair['mapping_reason'].strip():
                raise ValidationError('cross-object group needs reviewed reading order and boundary evidence')
            if any(k in repair for k in ('shape_id', 'start', 'end', 'bold')):
                raise ValidationError('group ranges and visually judged bold belong to segments')
            if repair.get('mode') not in {'compatibility', 'reference_match'}:
                raise ValidationError('cross-object group requires an explicit authorized repair mode')
            shapes = _shapes(etree.fromstring(package.read(parts[page - 1])))
            consumed, chunks = set(), []
            for index, segment in enumerate(segments):
                if not isinstance(segment, dict) or set(segment) != {'shape_id', 'start', 'end', 'text', 'bold', 'bold_reason'}:
                    raise ValidationError('group segment allows only an exact range and its bold decision')
                identity = segment['shape_id']
                if type(identity) is not int or identity not in shapes or identity in consumed:
                    raise ValidationError('group needs distinct existing text objects on the same page')
                consumed.add(identity)
                text = _text(shapes[identity])
                start, end = segment['start'], segment['end']
                if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                    raise ValidationError('invalid group range')
                if segment['text'] != text[start:end]:
                    raise ValidationError('cross-object source text changed')
                # Intermediate boundaries must consume the entire remainder/start
                # of their objects. Only outer boundaries can end a sentence.
                if index and start != 0 or index < len(segments)-1 and end != len(text):
                    raise ValidationError('cross-object group leaves an interior fragment unaccounted')
                endings = '。！？!?；;\n'
                if repair['unit_kind'] == 'title':
                    if start != 0 or end != len(text):
                        raise ValidationError('cross-object title must cover every complete title object')
                elif (index == 0 and start and text[start-1] not in endings or
                      index == len(segments)-1 and end < len(text) and text[end-1] not in endings):
                    raise ValidationError('cross-object group cuts inside an outer sentence')
                chunks.append(segment['text'])
            if not chunks or ''.join(chunks) != repair.get('text'):
                raise ValidationError('cross-object whole text must equal exact ordered source fragments; no normalization or inserted copy')


def validate_repairs(source: Path, parts: list[str], repairs: list[dict]) -> None:
    if not isinstance(repairs, list):
        raise ValidationError("font_repairs must be a list")
    _validate_groups(source, parts, repairs)
    repairs = _expanded_repairs(repairs)
    seen = {}
    with zipfile.ZipFile(source) as package:
        trees = {}
        for repair in repairs:
            if not isinstance(repair, dict):
                raise ValidationError("font repair must be an object")
            page, shape_id = repair.get("page"), repair.get("shape_id")
            if type(page) is not int or not 1 <= page <= len(parts) or type(shape_id) is not int:
                raise ValidationError("font repair needs an actual page and shape_id")
            if page not in trees:
                trees[page] = _shapes(etree.fromstring(package.read(parts[page - 1])))
            shape = trees[page].get(shape_id)
            if shape is None:
                raise ValidationError("font repair target is not an editable text object")
            text = _text(shape)
            start, end = repair.get("start"), repair.get("end")
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                raise ValidationError("invalid sentence/title range")
            if repair.get("text") != text[start:end] or not text[start:end].strip():
                raise ValidationError("font repair text no longer matches the source")
            if repair.get("unit_kind") not in {"sentence", "title"} or repair.get("whole_unit_confirmed") is not True:
                raise ValidationError("repair the entire reviewed sentence/title, not isolated missing glyphs")
            if repair["unit_kind"] == "title" and not repair.get('_group_validated') and (start != 0 or end != len(text)):
                raise ValidationError("a title repair must cover the complete title object")
            # Hard boundary guard catches character-only repairs. Paragraph boundaries
            # are candidates, not proof of a sentence; soft breaks never end a unit.
            if repair["unit_kind"] == "sentence" and not repair.get('_group_validated'):
                endings = "。！？!?；;\n"
                if (start and text[start - 1] not in endings) or (end < len(text) and text[end - 1] not in endings):
                    raise ValidationError("range cuts inside a sentence; include all soft/wrapped lines")
            if type(repair.get("bold")) is not bool:
                raise ValidationError("each unit needs an explicit visually judged bold choice")
            for key in ("reason", "bold_reason", "visual_evidence", "single_font_intent_evidence", "boundary_reason"):
                if not isinstance(repair.get(key), str) or not repair[key].strip():
                    raise ValidationError(f"font repair needs {key}")
            mode = repair.get('mode', 'compatibility')
            if mode not in {'compatibility', 'reference_match'}:
                raise ValidationError('unknown font repair mode')
            # Existing narrow YaHei plans remain readable. Newly recorded explicit modes
            # choose a reviewed common font; YaHei is a candidate, not a forced target.
            if 'mode' in repair or repair.get('target_font', TARGET_FONT) != TARGET_FONT:
                for field in ('target_font', 'font_match_reason', 'sample_review_evidence'):
                    if not isinstance(repair.get(field), str) or not repair[field].strip():
                        raise ValidationError('common font matching needs ' + field)
                candidates = repair.get('candidate_fonts')
                if not isinstance(candidates, list) or not candidates or not all(isinstance(f, str) and f.strip() for f in candidates):
                    raise ValidationError('record actual reference font candidates')
                if any(f.casefold() not in {n.casefold() for n in COMMON_FONT_FAMILIES} for f in candidates):
                    raise ValidationError('exclude paid/member/unknown families from font candidates')
                if repair['target_font'] not in candidates:
                    raise ValidationError('chosen reference font must be among reviewed candidates')
                validate_reference_font(repair)
            if 'mode' in repair and (not isinstance(repair.get('reference_visual'), str) or not repair['reference_visual'].strip()):
                raise ValidationError('font repair needs original same-page visual evidence in both modes')
            for node, _, offset, token in _tokens(shape):
                if offset < end and offset + len(token) > start and node is not None and node.tag == A + "fld":
                    raise ValidationError("text fields need manual font repair; do not rebuild them")
            key = (page, shape_id)
            if any(start < other_end and end > other_start for other_start, other_end in seen.get(key, [])):
                raise ValidationError("overlapping font repair units")
            seen.setdefault(key, []).append((start, end))


def _set_font(run, bold, target_font=TARGET_FONT):
    properties = run.find(A + "rPr")
    if properties is None:
        properties = etree.Element(A + "rPr")
        run.insert(0, properties)
    properties.set("b", "1" if bold else "0")
    order = (*FONT_SLOTS, "hlinkClick", "hlinkMouseOver", "rtl", "extLst")
    for index, slot in enumerate(FONT_SLOTS):
        font = properties.find(A + slot)
        if font is None:
            font = etree.Element(A + slot)
            later = {A + name for name in order[index + 1:]}
            insert_at = next((i for i, n in enumerate(properties) if n.tag in later), len(properties))
            properties.insert(insert_at, font)
        font.set("typeface", target_font)


def patch_font_tree(tree, repairs):
    """Keep boxes/paragraphs and all other run properties; split only internal runs."""
    shapes = _shapes(tree)
    by_shape = {}
    for repair in _expanded_repairs(repairs):
        by_shape.setdefault(repair["shape_id"], []).append(repair)
    for shape_id, units in by_shape.items():
        shape = shapes[shape_id]
        for node, paragraph, offset, text in list(_tokens(shape)):
            if node is None or node.tag != A + "r" or not text:
                continue
            matches = [r for r in units if offset < r["end"] and offset + len(text) > r["start"]]
            if not matches:
                continue
            cuts = sorted({0, len(text), *(max(0, r["start"] - offset) for r in matches),
                           *(min(len(text), r["end"] - offset) for r in matches)})
            if cuts == [0, len(text)]:
                _set_font(node, matches[0]["bold"], matches[0].get('target_font', TARGET_FONT))
                continue
            position = paragraph.index(node)
            paragraph.remove(node)
            for index, (left, right) in enumerate(zip(cuts, cuts[1:])):
                segment = deepcopy(node)
                segment.find(A + "t").text = text[left:right]
                unit = next((r for r in matches if r["start"] <= offset + left < r["end"]), None)
                if unit is not None:
                    _set_font(segment, unit["bold"], unit.get('target_font', TARGET_FONT))
                paragraph.insert(position + index, segment)
    return tree


def apply_font_repairs(source: Path, baseline: Path, output: Path, parts: list[str], repairs: list[dict]):
    validate_repairs(source, parts, repairs)
    by_part = {}
    for repair in repairs:
        by_part.setdefault(parts[repair["page"] - 1], []).append(repair)
    if output.resolve() in {source.resolve(), baseline.resolve()}:
        raise ValidationError("font repair must preserve the source and animation baseline")
    with zipfile.ZipFile(baseline) as package, zipfile.ZipFile(output, "w") as target:
        for item in package.infolist():
            data = package.read(item.filename)
            if item.filename in by_part:
                tree = patch_font_tree(etree.fromstring(data), by_part[item.filename])
                data = etree.tostring(tree, encoding="UTF-8", xml_declaration=True, standalone=True)
            target.writestr(item, data)
