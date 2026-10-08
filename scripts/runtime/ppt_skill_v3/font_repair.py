"""Deterministic, reviewed sentence/title repairs; never a global font replacement.

Offsets are Python Unicode character offsets in the object's text: paragraph
boundaries are '\n', explicit soft breaks '\v'. Visual diagnosis and semantic
sentence boundaries belong to the controller, not the execution script.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import zipfile

from lxml import etree

from .validation import ValidationError

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
TARGET_FONT = "微软雅黑"
FONT_SLOTS = ("latin", "ea", "cs", "sym")


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


def validate_repairs(source: Path, parts: list[str], repairs: list[dict]) -> None:
    if not isinstance(repairs, list):
        raise ValidationError("font_repairs must be a list")
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
            if repair["unit_kind"] == "title" and (start != 0 or end != len(text)):
                raise ValidationError("a title repair must cover the complete title object")
            # Hard boundary guard catches character-only repairs. Paragraph boundaries
            # are candidates, not proof of a sentence; soft breaks never end a unit.
            if repair["unit_kind"] == "sentence":
                endings = "。！？!?；;\n"
                if (start and text[start - 1] not in endings) or (end < len(text) and text[end - 1] not in endings):
                    raise ValidationError("range cuts inside a sentence; include all soft/wrapped lines")
            if type(repair.get("bold")) is not bool:
                raise ValidationError("each unit needs an explicit visually judged bold choice")
            for key in ("reason", "bold_reason", "visual_evidence", "single_font_intent_evidence", "boundary_reason"):
                if not isinstance(repair.get(key), str) or not repair[key].strip():
                    raise ValidationError(f"font repair needs {key}")
            if repair.get("target_font", TARGET_FONT) != TARGET_FONT:
                raise ValidationError("compatibility repairs use Microsoft YaHei only")
            for node, _, offset, token in _tokens(shape):
                if offset < end and offset + len(token) > start and node is not None and node.tag == A + "fld":
                    raise ValidationError("text fields need manual font repair; do not rebuild them")
            key = (page, shape_id)
            if any(start < other_end and end > other_start for other_start, other_end in seen.get(key, [])):
                raise ValidationError("overlapping font repair units")
            seen.setdefault(key, []).append((start, end))


def _set_font(run, bold):
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
        font.set("typeface", TARGET_FONT)


def patch_font_tree(tree, repairs):
    """Keep boxes/paragraphs and all other run properties; split only internal runs."""
    shapes = _shapes(tree)
    by_shape = {}
    for repair in repairs:
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
                _set_font(node, matches[0]["bold"])
                continue
            position = paragraph.index(node)
            paragraph.remove(node)
            for index, (left, right) in enumerate(zip(cuts, cuts[1:])):
                segment = deepcopy(node)
                segment.find(A + "t").text = text[left:right]
                unit = next((r for r in matches if r["start"] <= offset + left < r["end"]), None)
                if unit is not None:
                    _set_font(segment, unit["bold"])
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
