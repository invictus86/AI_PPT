"""File-only character coverage before WPS launch; never infer visual approval."""
from __future__ import annotations

import io
import os
from pathlib import Path
import posixpath
import unicodedata
import zipfile

from fontTools.ttLib import TTFont, TTCollection
from lxml import etree

from .embedded_fonts import decode_font
from .file_hashing import file_sha256

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def _mapping(font):
    glyphs = set(font.getGlyphOrder())
    return {cp for cp, glyph in (font.getBestCmap() or {}).items()
            if glyph != '.notdef' and glyph in glyphs}


def _variant(font):
    flags = font['OS/2'].fsSelection if 'OS/2' in font else 0
    return 'boldItalic' if flags & 32 and flags & 1 else 'bold' if flags & 32 else 'italic' if flags & 1 else 'regular'


def _installed_index():
    from .font_repair import system_font_roots
    paths = {p for root in system_font_roots() if root.is_dir() for p in root.rglob('*')
             if p.suffix.lower() in {'.ttf', '.otf', '.ttc', '.otc'} and p.is_file()}
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                    for n in range(winreg.QueryInfoKey(key)[1]):
                        value = winreg.EnumValue(key, n)[1]
                        if isinstance(value, str) and Path(value).is_absolute() and Path(value).is_file():
                            paths.add(Path(value))
            except OSError:
                pass
    index = {}
    for path in sorted(paths):
        fonts = []; collection = None
        try:
            if path.suffix.lower() in {'.ttc', '.otc'}:
                collection = TTCollection(path, lazy=True); fonts = collection.fonts
            else:
                fonts = [TTFont(path, lazy=True)]
            for n, font in enumerate(fonts):
                for name in font['name'].names:
                    if name.nameID in {1, 4, 6, 16}:
                        index.setdefault((name.toUnicode().casefold(), _variant(font)), (path, n))
        except Exception:
            continue
        finally:
            for font in fonts:
                font.close()
            if collection:
                collection.close()
    return index


def _owner(node):
    for parent in node.iterancestors():
        if parent.tag in {P+'sp', P+'graphicFrame', P+'cxnSp'}:
            return parent
    return node.getparent()


def _full_text(owner):
    paragraphs = owner.findall('.//'+A+'p')
    return '\n'.join(''.join('\v' if n.tag == A+'br' else n.text or ''
                            for n in para.iter() if n.tag in {A+'t', A+'br'}) for para in paragraphs)


def _properties(node):
    """Resolve local run/paragraph/body defaults. Unknown theme inheritance stays pending."""
    chain = []
    props = node.getparent().find(A+'rPr')
    if props is not None:
        chain.append(props)
    para = next((p for p in node.iterancestors() if p.tag == A+'p'), None)
    if para is not None:
        props = para.find(A+'pPr/'+A+'defRPr')
        if props is not None:
            chain.append(props)
        body = para.getparent()
        level = int(para.find(A+'pPr').get('lvl', '0')) if para.find(A+'pPr') is not None else 0
        for tag in (f'lvl{level+1}pPr', 'defPPr'):
            props = body.find(A+'lstStyle/'+A+tag+'/'+A+'defRPr')
            if props is not None:
                chain.append(props)
    return chain


def audit_pptx_fonts(source):
    from .teaching_animation import slide_parts
    source = Path(source)
    report = {'method': 'file_only_sfnt_cmap_and_actual_glyph_mapping', 'before_render': True,
              'input_sha256': file_sha256(source), 'visual_verified': False, 'fonts': [], 'objects': [],
              'notice': '文件覆盖检查不代表WPS实际选字、字体外观或版面通过；未知继承/回退逐项待审阅。'}
    installed = _installed_index(); maps = {}; embedded = {}; installed_maps = {}
    with zipfile.ZipFile(source) as z:
        pres = etree.fromstring(z.read('ppt/presentation.xml'))
        rels = {n.get('Id'): n.get('Target') for n in etree.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
        for entry in pres.findall('.//'+P+'embeddedFont'):
            meta = entry.find(P+'font'); family = meta.get('typeface') if meta is not None else ''
            for variant in entry:
                rid = variant.get(R+'id')
                if not rid:
                    continue
                target = rels.get(rid, '')
                part = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('ppt', target))
                key = (family.casefold(), etree.QName(variant).localname)
                record = {'font': family, 'variant': key[1], 'part': part}
                embedded[key] = record
                try:
                    data, info = decode_font(z.read(part))
                    with TTFont(io.BytesIO(data)) as font:
                        maps[key] = _mapping(font)
                    record.update(status='decoded', mapped_characters=len(maps[key]), details=info)
                except Exception as exc:
                    record.update(status='unverified', reason=str(exc))
                report['fonts'].append(record)
        for page, part in enumerate(slide_parts(source), 1):
            tree = etree.fromstring(z.read(part)); objects = {}
            for node in tree.iter(A+'t'):
                text = node.text or ''
                if not text.strip():
                    continue
                owner = _owner(node); nv = next(owner.iter(P+'cNvPr'), None)
                object_key = tree.getroottree().getpath(owner)
                obj = objects.setdefault(object_key, {'page': page, 'part': part,
                    'shape_id': int(nv.get('id')) if nv is not None else None, 'object_path': object_key,
                    'full_text': _full_text(owner), 'runs': []})
                props = _properties(node)
                bold = next((p.get('b') for p in props if p.get('b') is not None), '0') in {'1', 'true'}
                italic = next((p.get('i') for p in props if p.get('i') is not None), '0') in {'1', 'true'}
                variant = 'boldItalic' if bold and italic else 'bold' if bold else 'italic' if italic else 'regular'
                groups = {}
                for char in text:
                    if char.isspace() or unicodedata.category(char) == 'Cf':
                        continue
                    slot = 'ea' if unicodedata.east_asian_width(char) in {'W', 'F'} else 'cs' if unicodedata.bidirectional(char) in {'AL', 'R', 'AN'} else 'latin'
                    family = next((p.find(A+slot).get('typeface') for p in props if p.find(A+slot) is not None), None)
                    groups.setdefault((slot, family), set()).add(char)
                for (slot, family), chars in groups.items():
                    key = ((family or '').casefold(), variant); selected_key = key
                    origin = 'embedded_subset'; cmap = maps.get(key); font_file = None; face_index = None
                    risks = []
                    if key not in embedded and (key[0], 'regular') in embedded:
                        selected_key = (key[0], 'regular'); cmap = maps.get(selected_key)
                        risks.append('requested_style_not_embedded_synthesis_or_fallback_possible')
                    if selected_key not in embedded:
                        origin = 'installed'; location = installed.get(key)
                        if location is None and (key[0], 'regular') in installed:
                            location = installed[key[0], 'regular']
                            if variant != 'regular':
                                risks.append('requested_style_not_installed_synthesis_possible')
                        if location:
                            font_file, face_index = location
                            if location not in installed_maps:
                                try:
                                    with TTFont(font_file, fontNumber=face_index) as font:
                                        installed_maps[location] = _mapping(font)
                                except Exception:
                                    installed_maps[location] = None
                            cmap = installed_maps[location]
                    if cmap is None:
                        origin = 'unresolved'; risks.append('font_unavailable_or_inheritance_unresolved')
                    missing = ''.join(sorted(c for c in chars if cmap is not None and ord(c) not in cmap))
                    if missing:
                        risks.append('missing_or_invalid_glyph_mapping')
                    obj['runs'].append({'text': text, 'font_slot': slot, 'font': family, 'variant': variant,
                        'source': origin, 'font_file': str(font_file) if font_file else None, 'font_face_index': face_index,
                        'missing_characters': missing, 'unverified_characters': ''.join(sorted(chars)) if cmap is None else '',
                        'risks': risks, 'coverage_verified': cmap is not None and not missing})
            for obj in objects.values():
                obj['file_coverage_pass'] = all(r['coverage_verified'] for r in obj['runs'])
                obj['pending'] = any(r['risks'] for r in obj['runs'])
                report['objects'].append(obj)
    report['objects_checked'] = len(report['objects'])
    report['pending_objects'] = sum(o['pending'] for o in report['objects'])
    report['coverage_pass'] = all(o['file_coverage_pass'] for o in report['objects']) and all(f['status']=='decoded' for f in report['fonts'])
    return report
