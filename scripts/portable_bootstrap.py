"""Load per-workspace portable paths without changing user-level settings."""
from pathlib import Path
import json
import os


def configure(skill_dir):
    local = Path(skill_dir) / '_local'
    key = local / 'private' / 'image_api_key'
    if key.is_file():
        os.environ['PPT_IMAGE_API_KEY_FILE'] = str(key)
        os.environ.pop('PPT_IMAGE_API_KEY', None)
    settings = local / 'private' / 'settings.json'
    if settings.is_file():
        data = json.loads(settings.read_text(encoding='utf-8'))
        for name in ('PPT_IMAGE_API_BASE_URL', 'PPT_IMAGE_API_SIZE', 'PPT_IMAGE_API_QUALITY',
                     'PPT_IMAGE_API_RESPONSE_FORMAT'):
            if name in data:
                os.environ[name] = data[name]
    renderer = local / 'poppler' / 'Library' / 'bin' / 'pdftoppm.exe'
    if renderer.is_file():
        os.environ['PPT_SKILL_PDFTOPPM'] = str(renderer)
    python = local / 'python'
    if (python / 'python.exe').is_file():
        os.environ['PATH'] = str(python) + os.pathsep + os.environ.get('PATH', '')
        os.environ['PPTCTL_NO_BUNDLED_PYTHON'] = '1'
