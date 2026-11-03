"""Read-only native WPS Presentation discovery; no Office aliases or fallback."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .file_hashing import file_sha256
from .resources import identity

RENDERER = 'WPS Presentation native KWPP hidden Slide.Export + temporary embedded fonts'
PROGID = 'KWPP.Application'


def _presentation_server(command):
    """WPS ships either wpp.exe or the unified wps.exe /wpp launcher."""
    end = command.lower().find('.exe')
    if end < 0:
        return None
    path = Path(os.path.expandvars(command[:end + 4].strip('" ')))
    arguments = command[end + 4:].strip('" ').lower().split()
    if (path.name.lower() == 'wpp.exe' or
            (path.name.lower() == 'wps.exe' and '/wpp' in arguments)) and path.is_file():
        return path.resolve()
    return None


def _registered_presentation():
    import winreg
    hives = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    views = (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)
    for hive in hives:
        for view in views:
            try:
                with winreg.OpenKey(hive, 'Software\\Classes\\' + PROGID + '\\CLSID',
                                    0, winreg.KEY_READ | view) as key:
                    clsid = winreg.QueryValueEx(key, '')[0]
            except OSError:
                continue
            for server_hive in hives:
                for server_view in views:
                    try:
                        with winreg.OpenKey(server_hive, 'Software\\Classes\\CLSID\\' + clsid + '\\LocalServer32',
                                            0, winreg.KEY_READ | server_view) as key:
                            command = winreg.QueryValueEx(key, '')[0]
                        path = _presentation_server(command)
                        if path:
                            return {'provider': 'wps', 'progid': PROGID, 'executable': str(path),
                                    'renderer': RENDERER, 'registration_command': command}
                    except OSError:
                        pass
    return None


def select_presentation_renderer():
    return _registered_presentation() if os.name == 'nt' else None


def _registered_fonts_fingerprint():
    if os.name != 'nt':
        return []
    import winreg
    result = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                for n in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, n)
                    path = Path(value) if isinstance(value, str) else None
                    stat = path.stat() if path and path.is_absolute() and path.is_file() else None
                    result.append((str(hive), name, str(value), (stat.st_size, stat.st_mtime_ns) if stat else None))
        except OSError:
            pass
    return sorted(result)


def render_environment():
    """One cache contract for source, editable and optional click-state previews."""
    from .embedded_fonts import decoder_files, node_runtime
    from .render_cache import environment_fingerprint
    selected = select_presentation_renderer()
    root = Path(__file__).parent
    files = [root/'background_ppt.py', root/'background_render.ps1', Path(__file__),
             root/'pptx_font_preflight.py', root/'verification_environment.py', root/'render_cache.py',
             *decoder_files()]
    node = node_runtime()
    if node:
        files.append(Path(node))
    if selected:
        executable = Path(selected['executable'])
        # WPS application/version and the presentation engine must invalidate together.
        files.extend(p for p in (executable, executable.parent/'wpp.exe',
                                 executable.parent/'wppcore.dll', executable.parent/'wppmain.dll') if p.is_file())
    return identity(json.dumps({'selection': selected, 'environment': environment_fingerprint(files),
                                'registered_fonts': _registered_fonts_fingerprint()}, sort_keys=True))


def proof_valid(proof, selected, pages, font_count):
    if not selected:
        return False
    executable = Path(selected['executable']).resolve()
    return (proof.get('renderer_provider') == 'wps' and proof.get('com_progid') == PROGID
            and Path(proof.get('application_executable', '')).resolve() == executable
            and Path(proof.get('application_path', '')).resolve() == executable.parent
            and proof.get('application_executable_sha256') == file_sha256(executable)
            and bool(proof.get('application_version')) and bool(proof.get('application_file_version'))
            and proof.get('with_window') is False and proof.get('read_only') is True
            and proof.get('windows_before') == proof.get('windows_during') == proof.get('windows_after')
            and type(proof.get('windows_before')) is int and proof['windows_before'] >= 0
            and proof.get('slides_exported') == pages
            and proof.get('fonts_registered') == proof.get('fonts_unloaded') == font_count
            and proof.get('cleanup_complete') is True and proof.get('status') == 'exported')
