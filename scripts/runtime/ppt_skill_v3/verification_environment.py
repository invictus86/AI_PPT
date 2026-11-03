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
        if kind == 'docx':
            from .document_renderer import select_document_renderer
            found = select_document_renderer() is not None
        elif os.name == 'nt':
            from .presentation_renderer import select_presentation_renderer
            found = select_presentation_renderer() is not None
        if not found:
            missing.append('WPS Writer 或 Microsoft Word（后台 COM）' if kind == 'docx' else 'WPS 演示（原生 KWPP.Application 后台 COM）')
    if kind in {'docx', 'pdf'}:
        from .pdf_page_images import find_pdftoppm
        if not find_pdftoppm():
            missing.append('pdftoppm')
    result = {'kind': kind, 'available': not missing, 'missing': missing,
            'policy': '缺环境不验证；有环境必须验证；执行失败不等于缺环境；禁止前台备用'}
    if kind == 'pptx':
        from .presentation_renderer import select_presentation_renderer
        result['renderer_selection'] = select_presentation_renderer()
        result['probe_scope'] = 'read_only_registration_and_files_not_actual_render_or_visual_acceptance'
    return result


def skipped_verification(source, capability):
    if capability.get('available') is not False or not capability.get('missing'):
        raise ValueError('Only confirmed missing dependencies can skip verification')
    source = Path(source).resolve()
    return {'method': 'verification_skipped', 'status': 'skipped_no_environment',
            'input': str(source), 'input_sha256': file_sha256(source),
            'capability': capability, 'reason': '缺少：'+', '.join(capability['missing']),
            'foreground_opened': False, 'verified': False, 'images': [], 'created_at': now_iso(),
            'notice': '仅记录环境缺失，未作视觉/分页/字体验收，不表示检查通过。'}
