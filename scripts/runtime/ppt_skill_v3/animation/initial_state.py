"""Source-based first-frame checks; never infer teaching quality from object counts."""
from __future__ import annotations

import posixpath
import re
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from ..validation import ValidationError

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P, "a": A, "r": R}
_FALSE = {"0", "false", "off"}
_SOLE_STATIC_REASONS = {"完整阅读", "方便书写", "无需分步", "保持静态", "整页静态"}


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def _related(parts, part, kind):
    rel = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    if rel not in parts:
        return None
    for item in ET.fromstring(parts[rel]):
        if item.get("TargetMode") != "External" and item.get("Type", "").endswith("/" + kind):
            target = unquote(item.get("Target", "").split("#", 1)[0])
            resolved = posixpath.normpath(target.lstrip("/") if target.startswith("/") else
                                         posixpath.join(posixpath.dirname(part), target))
            if resolved in parts:
                return resolved
    return None


def _rect(node):
    transform = node.find("p:grpSpPr/a:xfrm", NS) if node.tag == f"{{{P}}}grpSp" else node.find("p:spPr/a:xfrm", NS)
    if transform is None:
        transform = node.find("p:xfrm", NS)
    if transform is None:
        return None
    off, ext = transform.find("a:off", NS), transform.find("a:ext", NS)
    if off is None or ext is None:
        return None
    try:
        return tuple(int(v) for v in (off.get("x"), off.get("y"), ext.get("cx"), ext.get("cy")))
    except (TypeError, ValueError):
        return None


def _on_canvas(node, size):
    transform = node.find(".//a:xfrm", NS)
    if transform is not None and transform.get("rot", "0") != "0":
        return None  # Rotation makes this bounding-box-only check inconclusive; inspect a preview.
    rect = _rect(node)
    if rect is None or not size:
        return None
    x, y, width, height = rect
    return width > 0 and height > 0 and x < size[0] and y < size[1] and x + width > 0 and y + height > 0


def _text_visible(node):
    # A transparent rectangle can still contain visible text. Inspect text runs, not every alpha in the shape.
    for paragraph in node.findall(".//a:p", NS):
        for run in paragraph:
            text = "".join(t.text or "" for t in run.findall(".//a:t", NS)).strip()
            if not text:
                continue
            props = run.find("a:rPr", NS)
            if props is not None and props.find("a:noFill", NS) is not None:
                continue
            alpha = props.findall("a:solidFill/*/a:alpha", NS) if props is not None else []
            if not alpha or any(a.get("val") != "0" for a in alpha):
                return True
    return False


def _kind(node, size, *, inherited=False):
    props = node.find("*/p:cNvPr", NS)
    if props is not None and props.get("hidden", "0") not in _FALSE:
        return None
    placeholder = node.find("*/p:nvPr/p:ph", NS)
    # Layout/master placeholder prompt text is not a visible slide title. Footer placeholders are not context.
    if placeholder is not None and (inherited or placeholder.get("type") in {"dt", "ftr", "hdr", "sldNum"}):
        return None
    if node.find(".//a:fld[@type='slidenum']", NS) is not None:
        return None
    on_canvas = _on_canvas(node, size)
    if on_canvas is False:
        return None
    kind = node.tag.rsplit("}", 1)[-1]
    if kind == "grpSp":
        members = [_kind(child, None, inherited=inherited) for child in node
                   if child.tag.rsplit("}", 1)[-1] in {"sp", "pic", "grpSp", "graphicFrame"}]
        result = "text" if "text" in members else "visual" if any(members) else None
    elif _text_visible(node):
        result = "text"
    elif kind == "pic" and node.find(".//a:blip", NS) is not None:
        alpha = node.findall(".//a:alphaModFix", NS)
        result = None if any(a.get("amt") == "0" for a in alpha) else "visual"
    elif kind == "graphicFrame":
        result = "visual"
    else:
        # Blank fills, connectors and decorative autoshapes do not establish readable context.
        return None
    return "visual" if result and on_canvas is None else result


def _background_image(parts, background, master_part):
    if background.find(".//a:blip", NS) is not None:
        return True
    reference = background.find("p:bgRef", NS)
    theme_part = _related(parts, master_part, "theme") if master_part else None
    if reference is None or theme_part is None:
        return False
    try:
        index = int(reference.get("idx", "0"))
    except ValueError:
        return False
    theme = ET.fromstring(parts[theme_part])
    listing = theme.find("a:themeElements/a:fmtScheme/" +
                         ("a:bgFillStyleLst" if index >= 1001 else "a:fillStyleLst"), NS)
    position = index - 1001 if index >= 1001 else index - 1
    return listing is not None and 0 <= position < len(listing) and listing[position].find(".//a:blip", NS) is not None


def describe_initial_context(parts, part, slide, size):
    """Only read actual source parts. A solid background or unused master never qualifies."""
    slide_size = (int(size.get("cx", 0)), int(size.get("cy", 0))) if size is not None else None
    context = {"text_ids": [], "visual_ids": [], "inherited": []}
    for node in slide.findall("p:cSld/p:spTree/*", NS):
        props = node.find(".//p:cNvPr", NS)
        kind = _kind(node, slide_size)
        if props is not None and kind:
            context[kind + "_ids"].append(int(props.get("id")))
    layout_part = _related(parts, part, "slideLayout")
    master_part = _related(parts, layout_part, "slideMaster") if layout_part else None
    layers = [(part, slide)] + [(p, ET.fromstring(parts[p])) for p in (layout_part, master_part) if p]
    for source, root in layers:
        background = root.find("p:cSld/p:bg", NS)
        if background is not None:
            # Nearest explicit background overrides ancestor backgrounds, even when it is a plain solid fill.
            if _background_image(parts, background, master_part):
                context["inherited"].append({"part": source, "kind": "visual", "source": "background_image"})
            break
    # showMasterSp controls inherited non-placeholder graphics (ISO/IEC 29500, 19.3.1).
    if slide.get("showMasterSp", "1") not in _FALSE:
        for source, root in layers[1:]:
            if source == master_part and any(r.get("showMasterSp", "1") in _FALSE for _, r in layers[:-1]):
                continue
            # Inherited timing is not compiled by this task. Do not assume its targeted shapes are visible.
            timed_ids = {n.get("spid") for n in root.findall("p:timing//p:spTgt", NS)}
            for node in root.findall("p:cSld/p:spTree/*", NS):
                if any(n.get("id") in timed_ids for n in node.findall(".//p:cNvPr", NS)):
                    continue
                kind = _kind(node, slide_size, inherited=True)
                if kind:
                    props = node.find(".//p:cNvPr", NS)
                    context["inherited"].append({"part": source, "kind": kind, "source": "inherited_shape",
                                                 "id": int(props.get("id")) if props is not None else None})
    return context


def check_initial_state(page, row):
    index = page["slide_index"]
    visible = {i for u in page["units"] if u["click"] == 0 for i in u["targets"]}
    context = row.get("initial_context")
    _require(context is not None, f"Page {index}: initial context missing; inspect current source again")
    inherited = context["inherited"]
    local_text = visible.intersection(context["text_ids"])
    text = local_text or any(x["kind"] == "text" for x in inherited)
    visual = visible.intersection(context["visual_ids"]) or any(x["kind"] == "visual" for x in inherited)
    _require(text or visual, f"Page {index}: blank initial state; keep readable context visible and replan animation")
    if not local_text:
        _require(page.get("visual_checked") is True,
                 f"Page {index}: image-only or inherited initial context needs current preview review (visual_checked)")
    animated = any(u["click"] > 0 for u in page["units"])
    reason = page.get("static_reason", "").strip()
    _require(not animated or not reason, f"Page {index}: static_reason belongs only to a static exception")
    if not animated:
        _require(reason, f"Page {index}: static exception requires a concrete static_reason; do not remove animation to fix blank starts")
        terms = set(filter(None, re.split(r"[\s，,；;。.!！、/]+", reason)))
        _require(not terms <= _SOLE_STATIC_REASONS,
                 f"Page {index}: reading/writing/no-split alone is not a static exception")
    return {"slide_index": index, "visible_ids": sorted(visible), "image_only": not bool(text),
            "visual_review_declared": page.get("visual_checked") is True, "inherited_context": inherited,
            "animated": animated, "static_reason": reason or None,
            "semantic_review": "controller_required", "native_playback_verified": False}
