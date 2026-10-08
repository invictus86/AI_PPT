"""Read-only capability checks; absence is a skip, an execution failure is not."""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from .file_hashing import file_sha256
from .time_utils import now_iso


def verification_capability(kind):
    if kind not in {'docx', 'pdf', 'pptx'}:
        raise ValueError('Unsupported verification artifact kind')
    missing = []
    if kind in {'docx', 'pptx'}:
        if os.name != 'nt':
            missing.append('Windows')
        if not (shutil.which('pwsh') or shutil.which('powershell')):
            missing.append('PowerShell')
        found = False
        if os.name == 'nt':
            import winreg
            app = 'WINWORD.EXE' if kind == 'docx' else 'POWERPNT.EXE'
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for view in (0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, 'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\'+app,
                                            0, winreg.KEY_READ | view) as key:
                            path = Path(winreg.QueryValueEx(key, '')[0].strip('"'))
                            found |= path.is_file() and 'microsoft office' in str(path).lower()
                    except OSError:
                        pass
        if not found:
            missing.append('Microsoft Word' if kind == 'docx' else 'Microsoft PowerPoint')
    if kind in {'docx', 'pdf'}:
        from .pdf_page_images import find_pdftoppm
        if not find_pdftoppm():
            missing.append('pdftoppm')
    return {'kind': kind, 'available': not missing, 'missing': missing,
            'policy': '缺环境不验证；有环境必须验证；执行失败不等于缺环境；禁止前台备用'}


def skipped_verification(source, capability):
    if capability.get('available') is not False or not capability.get('missing'):
        raise ValueError('Only confirmed missing dependencies can skip verification')
    source = Path(source).resolve()
    return {'method': 'verification_skipped', 'status': 'skipped_no_environment',
            'input': str(source), 'input_sha256': file_sha256(source),
            'capability': capability, 'reason': '缺少：'+', '.join(capability['missing']),
            'foreground_opened': False, 'verified': False, 'images': [], 'created_at': now_iso(),
            'notice': '仅记录环境缺失，未作视觉/分页/字体验收，不表示检查通过。'}
