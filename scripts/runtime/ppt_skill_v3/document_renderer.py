"""Read-only DOCX renderer selection: native WPS COM first, Word if absent."""
from __future__ import annotations

import os
from pathlib import Path


RENDERERS = {
    'wps': 'WPS Writer hidden ExportAsFixedFormat + pdftoppm',
    'word': 'Microsoft Word hidden ExportAsFixedFormat + pdftoppm',
}


def _registered_application(provider):
    import winreg
    progid = 'KWPS.Application' if provider == 'wps' else 'Word.Application'
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, 'Software\\Classes\\'+progid+'\\CLSID',
                                    0, winreg.KEY_READ | view) as key:
                    clsid = winreg.QueryValueEx(key, '')[0]
                # COM class and ProgID can legitimately live in different hives.
                for server_hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                    for server_view in (view, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
                        try:
                            with winreg.OpenKey(server_hive, 'Software\\Classes\\CLSID\\'+clsid+'\\LocalServer32',
                                                0, winreg.KEY_READ | server_view) as key:
                                command = winreg.QueryValueEx(key, '')[0]
                            # Paths may be quoted or use the historical unquoted Office registration.
                            end = command.lower().find('.exe')
                            if end < 0:
                                continue
                            path = Path(os.path.expandvars(command[:end+4].strip('" ')))
                            expected = 'wps.exe' if provider == 'wps' else 'winword.exe'
                            if path.is_file() and path.name.lower() == expected:
                                return {'provider': provider, 'progid': progid, 'executable': str(path),
                                        'renderer': RENDERERS[provider]}
                        except OSError:
                            pass
            except OSError:
                pass
    return None


def select_document_renderer():
    if os.name != 'nt':
        return None
    return _registered_application('wps') or _registered_application('word')
