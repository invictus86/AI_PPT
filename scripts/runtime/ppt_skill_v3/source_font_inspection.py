"""Source-reading copies only. Never called by animation/finished-deck checks."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import posixpath
import struct
import zipfile
from lxml import etree

from .embedded_fonts import decode_font, FontReadError, decoder_files, node_runtime
from .file_hashing import file_sha256
from .json_io import write_json

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


@lru_cache(maxsize=1)
def installed_faces():
    from .font_repair import system_font_roots
    from fontTools.ttLib import TTFont, TTCollection
    faces = {}
    for root in system_font_roots():
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if path.suffix.lower() not in ('.ttf', '.otf', '.ttc', '.otc'):
                continue
            fonts = []; collection = None
            try:
                if path.suffix.lower() in ('.ttc', '.otc'):
                    collection = TTCollection(path, lazy=True); fonts = collection.fonts
                else:
                    fonts = [TTFont(path, lazy=True)]
                for font in fonts:
                    for name in font['name'].names:
                        if name.nameID in (1, 4, 6, 16):
                            faces.setdefault(name.toUnicode().casefold(), str(path))
            except Exception:
                continue
            finally:
                for font in fonts:
                    font.close()
                if collection:
                    collection.close()
    return faces


def prepare_source_copy(source, directory, *, force_fallback=False):
    """Prepare a persistent internal copy, with original package parts preserved."""
    source = Path(source).resolve(); directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory/'source_reading_copy.pptx'
    if target == source:
        raise ValueError('source copy must not overwrite input')
    original = file_sha256(source)
    from .render_cache import environment_fingerprint
    node = node_runtime()
    fingerprint = environment_fingerprint(decoder_files()+([Path(node)] if node else []))
    previous = directory/'font_recovery.json'
    if previous.is_file() and target.is_file():
        import json
        try:
            cached = json.loads(previous.read_text(encoding='utf-8'))
            if (cached.get('preparation_fingerprint')==fingerprint and cached.get('source_path')==str(source)
                    and cached.get('source_sha256')==original and cached.get('forced_fallback')==force_fallback
                    and cached.get('copy_sha256')==file_sha256(target)):
                return target, cached
        except (ValueError, OSError):
            pass
    faces = installed_faces()
    report = {'source_path': str(source), 'source_sha256': original, 'fonts': [],
              'issues': [], 'changes': [], 'visual_review_accepted': False,
              'decoder': {'name': 'mtx-decompressor', 'version': '1.8.0', 'node_runtime': node,
                          'timeout_seconds': 90, 'heap_limit_mb': 1024},
              'purpose': 'source_content_inspection', 'original_font_appearance_verified': False,
              'forced_fallback': force_fallback, 'preparation_fingerprint': fingerprint}
    updates = {}; embedded_faces = set(); failed_faces = set()
    with zipfile.ZipFile(source) as z:
        pres = etree.fromstring(z.read('ppt/presentation.xml'))
        rels = {x.get('Id'): x.get('Target') for x in etree.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
        for entry in pres.findall('.//'+P+'embeddedFont'):
            meta = entry.find(P+'font'); face = meta.get('typeface') if meta is not None else ''
            embedded_faces.add(face)
            for variant in entry:
                rid = variant.get(R+'id')
                if not rid:
                    continue
                part = rels.get(rid, '')
                part = part.lstrip('/') if part.startswith('/') else posixpath.normpath(posixpath.join('ppt', part))
                record = {'face': face, 'variant': etree.QName(variant).localname, 'part': part}
                try:
                    raw = z.read(part)
                    record['container_format'] = 'mtx_eot' if len(raw)>=16 and struct.unpack_from('<I',raw,12)[0] & 4 else 'uncompressed_or_unknown_eot'
                    data, info = decode_font(raw)
                    record.update(info, status='decoded')
                    if info['format'] == 'mtx_eot':
                        size = struct.unpack_from('<I', raw, 4)[0]
                        header = bytearray(raw[:-size])
                        struct.pack_into('<I', header, 0, len(header)+len(data))
                        struct.pack_into('<I', header, 4, len(data))
                        struct.pack_into('<I', header, 12, struct.unpack_from('<I', header, 12)[0] & ~4)
                        updates[part] = bytes(header)+data
                        report['changes'].append({'part': part, 'action': 'mtx_to_sfnt'})
                except (KeyError, FontReadError) as exc:
                    code = exc.code if isinstance(exc, FontReadError) else 'embedded_font_missing'
                    record.update(status='failed', code=code, reason=str(exc))
                    failed_faces.add(face)
                report['fonts'].append(record)
        failed_faces.update(embedded_faces if force_fallback else ())
        fallback = next((f for f in ('Microsoft YaHei', '微软雅黑', 'Noto Sans CJK SC', 'PingFang SC', 'SimHei', 'Arial') if f.casefold() in faces), None)
        report['fallback_family'] = fallback
        if failed_faces:
            report['issues'].append({'code': 'embedded_font_recovery_failed', 'faces': sorted(failed_faces)})
        for item in z.infolist():
            if not item.filename.endswith('.xml'):
                continue
            tree = etree.fromstring(z.read(item.filename)); changed = False
            # Preserve good embedded entries; unsupported faces use only the inspection fallback.
            if item.filename == 'ppt/presentation.xml':
                for entry in list(tree.findall('.//'+P+'embeddedFont')):
                    meta = entry.find(P+'font')
                    if meta is not None and meta.get('typeface') in failed_faces:
                        entry.getparent().remove(entry); changed = True
            # Specific demonstrated mismatch: Wingdings + a Unicode bullet.
            for props in tree.iter():
                bullet = props.find(A+'buChar'); font = props.find(A+'buFont')
                if bullet is not None and font is not None and bullet.get('char') in ('•', '●', '·') and font.get('typeface', '').casefold() in ('wingdings', 'webdings', 'wingdings 2', 'wingdings 3'):
                    report['issues'].append({'code': 'bullet_font_mismatch', 'part': item.filename, 'char': bullet.get('char')})
                    if 'arial' in faces:
                        font.set('typeface', 'Arial'); changed = True
                        report['changes'].append({'part': item.filename, 'action': 'unicode_bullet_font_to_Arial', 'char': bullet.get('char')})
            for node in tree.iter():
                face = node.get('typeface')
                if not face or face.startswith('+'):
                    continue
                missing = face not in embedded_faces and face.casefold() not in faces
                if missing:
                    issue = {'code': 'font_not_installed', 'face': face}
                    if issue not in report['issues']:
                        report['issues'].append(issue)
                if (face in failed_faces or missing) and fallback:
                    node.set('typeface', fallback); changed = True
                    action = {'part': item.filename, 'from': face, 'to': fallback, 'action': 'inspection_font_substitution'}
                    if action not in report['changes']:
                        report['changes'].append(action)
            if changed:
                updates[item.filename] = etree.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
        with zipfile.ZipFile(target, 'w') as out:
            for item in z.infolist():
                out.writestr(item, updates.get(item.filename, z.read(item.filename)))
    report['copy_path'] = str(target); report['copy_sha256'] = file_sha256(target)
    report['content_only'] = any(c['action'] != 'mtx_to_sfnt' for c in report['changes']) or bool(failed_faces) or any(i['code']=='font_not_installed' for i in report['issues'])
    report['notice'] = '核对副本仅用于读取内容；须结合原稿对象文字、备注、媒体和配套资料逐页检查。替代可能改变断行和布局，导出成功不代表原字体外观或视觉验收通过。'
    if file_sha256(source) != original:
        raise ValueError('source changed during font preparation')
    write_json(directory/'font_recovery.json', report)
    return target, report
