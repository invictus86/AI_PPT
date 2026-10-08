"""Publish a generated manifest only after checking the current project revision."""
from pathlib import Path
from .resources import project_lock
from .state import read_state, write_state
from .json_io import write_json
from .validation import ValidationError
from .file_hashing import file_sha256


def commit_project_artifact(root, expected_state, relative_path, artifact):
    root = Path(root).resolve()
    target = (root/relative_path).resolve()
    target.relative_to(root)
    with project_lock(root):
        current = read_state(root)
        if current.get('revision', 0) != expected_state.get('revision', 0):
            raise ValidationError('另一窗口已更新项目；未发布旧清单，请重新读取后继续')
        from .validation import validate_project_state
        validate_project_state(expected_state)
        write_json(target, artifact)
        task = expected_state.get('stage5_animation',{})
        if task.get('background_manifest') == relative_path:
            task['background_manifest_sha256'] = file_sha256(target)
        write_state(root, expected_state)
    return artifact
