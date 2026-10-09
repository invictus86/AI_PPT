"""Read-only local font inventory; candidates do not determine visual similarity."""
from pathlib import Path
import os

from .font_repair import COMMON_FONT_FAMILIES, system_font_roots, is_installed_font


def common_font_candidates(text):
    from fontTools.ttLib import TTFont, TTCollection
    paths = set()
    for root in system_font_roots():
        if root.is_dir():
            paths.update(p.resolve() for p in root.rglob('*') if p.suffix.lower() in {'.ttf', '.otf', '.ttc', '.otc'})
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                    for index in range(winreg.QueryInfoKey(key)[1]):
                        value = winreg.EnumValue(key, index)[1]
                        if isinstance(value, str) and Path(value).is_absolute():
                            paths.add(Path(value).resolve())
            except OSError:
                continue
    allowed = {x.casefold() for x in COMMON_FONT_FAMILIES}
    result, unreadable = [], 0
    for path in sorted(paths):
        if not path.is_file() or not is_installed_font(path):
            continue
        fonts = []
        try:
            if path.suffix.lower() in {'.ttc', '.otc'}:
                collection = TTCollection(path, lazy=True)
                fonts = collection.fonts
            else:
                fonts = [TTFont(path, lazy=True)]
            for index, font in enumerate(fonts):
                names = sorted({n.toUnicode() for n in font['name'].names if n.nameID in {1, 16}})
                families = [n for n in names if n.casefold() in allowed]
                if not families:
                    continue
                cmap = font.getBestCmap() or {}
                missing = ''.join(sorted({c for c in text if not c.isspace() and ord(c) not in cmap}))
                if missing:
                    continue
                advances = font['hmtx'].metrics
                units = font['head'].unitsPerEm
                width = sum(advances.get(cmap.get(ord(c)), (0, 0))[0] for c in text if not c.isspace()) / units
                result.append({'target_font': families[0], 'family_aliases': families,
                               'font_file': str(path), 'font_face_index': index, 'non_premium': True,
                               'weight': int(font['OS/2'].usWeightClass), 'text_width_em': round(width, 3)})
        except Exception:
            unreadable += 1
        finally:
            for font in fonts:
                font.close()
    return {'candidates': result, 'unreadable_font_files': unreadable,
            'notice': 'Only installed common families covering this text. Controller must compare original glyphs, weight, widths and actual rendered samples; no automatic similarity verdict.'}
