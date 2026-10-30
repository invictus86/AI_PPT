"""Explicit recovery boundary for the historical detailed animation contract."""
from pathlib import Path

from .file_hashing import file_sha256
from .json_io import read_json
from .state import read_state
from .validation import ValidationError


def require_legacy_task(run_dir,*,source=None):
    root=Path(run_dir);task=read_state(root)['stage5_animation']
    if task.get('operation')=='editable' or task.get('status') in {'not_started','waiting_valid_input'}:
        raise ValidationError('旧动画命令仅供已有旧任务恢复；新任务使用 animation inspect，文字字体排版使用 editable inspect')
    inspection=root/task.get('inspection','_state/阶段5/inspection.json')
    if not inspection.is_file() or not task.get('input_sha256') or not task.get('authorization_evidence'):
        raise ValidationError('缺少真实旧任务检查记录；请使用 animation 或 editable')
    info=read_json(inspection)
    if info.get('source_sha256')!=task['input_sha256'] or not info.get('pages'):
        raise ValidationError('旧任务检查记录失效')
    original=Path(task.get('input',''))
    if not original.is_file() or file_sha256(original)!=task['input_sha256']:
        raise ValidationError('旧任务原稿已变；先恢复内部快照或使用新路线重新检查')
    if source is not None:
        current=Path(source).resolve()
        allowed={Path(task[k]).resolve() for k in ('input','original_input','output') if task.get(k)}
        if current not in allowed or not current.is_file() or file_sha256(current) not in {task['input_sha256'],task.get('output_sha256')}:
            raise ValidationError('旧入口不能启动另一文件或新版本；使用 animation / editable 重新检查')
    return task
