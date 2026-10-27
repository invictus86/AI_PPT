"""In-place animation publication with an immutable input and a recoverable journal."""
import os
from pathlib import Path
import re
import shutil
import tempfile

from .file_hashing import file_sha256
from .json_io import read_json, write_json
from .validation import ValidationError


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def animation_output_path(source):
    source = Path(source).absolute()
    stem = source.stem
    # Remove only recognized trailing conversion/output wrappers, never title text.
    while True:
        clean = re.sub(r'_可编辑动画版(?:_v[0-9]+)?$', '', stem)
        clean = re.sub(r'[｜|]图片版PPT(?:\.pdf)?$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\.pdf$', '', clean, flags=re.IGNORECASE)
        if clean == stem:
            break
        stem = clean
    _require(bool(stem.strip()), '清理转换后缀后主题名为空，不能自动改名')
    return source.with_name(stem + '_可编辑动画版.pptx')


def _check_target(source, target):
    _require(source.parent.resolve() == target.parent.resolve(), '动画改名必须留在实际输入目录')
    if target != source and os.path.lexists(target):
        raise ValidationError('动画目标名称已被其他文件占用，不覆盖、不递增版本：' + str(target))


def make_snapshot(root, source, digest):
    root, source = Path(root).resolve(), Path(source).resolve()
    directory = root / '_state/阶段5/originals' / digest.split(':')[1]
    _require(directory.resolve().is_relative_to(root), '原稿快照目录越出当前项目')
    _require(not source.is_relative_to((root / '_state/阶段5/originals').resolve()), '不能把内部原稿快照作为原位修改目标')
    _require(file_sha256(source) == digest, '原PPT已变化，须重新检查当前输入')
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / 'original.pptx'
    if not snapshot.exists():
        try:
            with snapshot.open('xb') as out, source.open('rb') as incoming:
                shutil.copyfileobj(incoming, out)
                out.flush(); os.fsync(out.fileno())
        except Exception:
            # Never reuse a partial snapshot; leave it for explicit diagnosis.
            raise
    _require(file_sha256(snapshot) == digest and file_sha256(source) == digest, '原稿快照不完整或输入在备份期间发生变化')
    return snapshot


def prepare_commit(root, source, snapshot, staged, before_sha256, plan_sha256, *, input_sha256=None):
    source = Path(source).resolve()
    target = animation_output_path(source)
    _check_target(source, target)
    input_sha256 = input_sha256 or before_sha256
    _require(file_sha256(source) == before_sha256 and file_sha256(snapshot) == input_sha256, '提交前原稿或快照已变化')
    descriptor, name = tempfile.mkstemp(prefix='.ppt-animation-', suffix='.tmp', dir=source.parent)
    candidate = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as out, Path(staged).open('rb') as incoming:
            shutil.copyfileobj(incoming, out)
            out.flush(); os.fsync(out.fileno())
        digest = file_sha256(candidate)
        _require(digest == file_sha256(staged), '待写回文件不完整')
        stat = source.stat()
        os.chmod(candidate, stat.st_mode & 0o777)
        journal = Path(root).resolve() / '_state/阶段5/in_place_commit.json'
        record = {'schema_version': '1.0', 'phase': 'prepared', 'source': str(source), 'target': str(target),
                  'snapshot': str(Path(snapshot).resolve()), 'candidate': str(candidate),
                  'before_sha256': before_sha256, 'input_sha256': input_sha256,
                  'after_sha256': digest, 'plan_sha256': plan_sha256}
        write_json(journal, record)
        return journal, record
    except Exception:
        candidate.unlink(missing_ok=True)
        raise


def finish_commit(root, task):
    """Complete an owned publication; never infer ownership from matching bytes alone."""
    root = Path(root).resolve()
    journal = root / task['in_place_commit']
    _require(journal.resolve().is_relative_to(root), '动画提交记录越出当前项目')
    record = read_json(journal)
    source, target, snapshot, candidate = (Path(record[k]) for k in ('source', 'target', 'snapshot', 'candidate'))
    _require(source == Path(task['original_input']) and target == Path(task['output'])
             and snapshot == Path(task['input']) and target == animation_output_path(source)
             and record['plan_sha256'] == task['plan_sha256'] and record['input_sha256'] == task['input_sha256']
             and record['before_sha256'] == task.get('working_input_sha256', task['input_sha256'])
             and record['after_sha256'] == task['output_sha256'], '动画提交记录与本次输入/计划/成品不一致')
    _require(candidate.parent == source.parent and candidate.name.startswith('.ppt-animation-')
             and candidate.suffix == '.tmp', '动画临时文件路径不属于实际输入目录')
    _require(snapshot.resolve().is_relative_to(root) and file_sha256(snapshot) == record['input_sha256'], '原稿快照缺失或变化，不能恢复')
    _require(file_sha256(root / task['plan']) == record['plan_sha256'], '动画计划变化，不能恢复写回')
    after, before = record['after_sha256'], record['before_sha256']
    if record['phase'] == 'committed':
        _require(target.is_file() and file_sha256(target) == after, '已保存PPT发生变化，不能按旧结果恢复')
        if candidate.exists():
            _require(os.path.samefile(candidate, target) and file_sha256(candidate) == after, '临时文件已变化，不自动删除')
            candidate.unlink()
        return target
    _require(record['phase'] in {'prepared', 'published'}, '未知动画提交状态')
    if target == source:
        if source.is_file() and file_sha256(source) == after and not candidate.exists():
            pass  # Atomic replacement finished before the journal update.
        else:
            _require(source.is_file() and file_sha256(source) == before, '原PPT发生变化，停止原位写回')
            _require(candidate.is_file() and file_sha256(candidate) == after, '待写回文件缺失或变化')
            os.replace(candidate, source)
    else:
        _require(candidate.is_file() and file_sha256(candidate) == after, '待改名文件缺失或变化')
        if os.path.lexists(target):
            _require(os.path.samefile(candidate, target), '改名目标被其他文件占用，不覆盖')
        else:
            _require(source.is_file() and file_sha256(source) == before, '原PPT发生变化，停止改名')
            # Atomic no-clobber publication. A crash leaves an owned link that
            # can be recognized using file identity, not just content hashes.
            os.link(candidate, target)
        record['phase'] = 'published'
        write_json(journal, record)
        try:
            if source.exists():
                _require(file_sha256(source) == before, '原PPT在写回期间变化，不移除原名称')
                source.unlink()
        except Exception:
            # If the original cannot be renamed/removed (e.g. Office lock),
            # undo only our own published link and keep the original intact.
            if target.exists() and os.path.samefile(candidate, target):
                target.unlink()
            record['phase'] = 'prepared'
            write_json(journal, record)
            raise
    _require(target.is_file() and file_sha256(target) == after, '原位保存结果与已核验文件不一致')
    record['phase'] = 'committed'
    write_json(journal, record)
    if candidate.exists():
        candidate.unlink()
    return target
