"""Render cache keys include the source, renderer and installed font environment."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .file_hashing import file_sha256
from .image_geometry import read_image_dimensions
from .resources import identity


def environment_fingerprint(renderer_files):
    paths = [Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts',
             Path(os.environ.get('LOCALAPPDATA', Path.home()))/'Microsoft/Windows/Fonts']
    fonts = []
    for directory in paths:
        if directory.is_dir():
            for file in sorted(directory.iterdir()):
                if file.is_file():
                    stat = file.stat()
                    fonts.append((str(file), stat.st_size, stat.st_mtime_ns))
    app_files = []
    if os.name == 'nt':
        import winreg
        for app in ('POWERPNT.EXE','WINWORD.EXE'):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, 'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + app) as key:
                        file = Path(winreg.QueryValueEx(key, '')[0].strip('"'))
                        stat = file.stat()
                        app_files.append((str(file),stat.st_size,stat.st_mtime_ns))
                except (OSError, ValueError):
                    pass
    return identity(json.dumps({'fonts':fonts, 'apps':app_files,
        'renderers':[(str(p),file_sha256(p)) for p in renderer_files],
        'configured_font':os.environ.get('PPT_SKILL_CJK_FONT'), 'extra_environment':os.environ.get('PPT_SKILL_RENDER_ENV_VERSION','')}, sort_keys=True))


def valid_cache(source, manifest, environment, *, expected_pages=None):
    if manifest.get('input_sha256') != file_sha256(source) or manifest.get('environment_fingerprint') != environment:
        return False
    images = manifest.get('images', [])
    if not images or (expected_pages is not None and len(images) != expected_pages):
        return False
    try:
        if [i['page'] for i in images] != list(range(1,len(images)+1)):
            return False
        for image in images:
            if file_sha256(image['path']) != image['sha256']:
                return False
            read_image_dimensions(image['path'])
    except (OSError, ValueError, KeyError):
        return False
    return True
