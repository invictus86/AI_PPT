#!/usr/bin/env python3
"""Two-way, source-only Git synchronization for a portable PPT workspace."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'scripts'))
from portable_bootstrap import configure
configure(SKILL)
sys.path.insert(0, str(SKILL / 'scripts' / 'runtime'))
from ppt_skill_v3.package_skill import _collect_files

REPOSITORY = 'https://github.com/invictus86/AI_PPT.git'
BRANCH = 'main'
LOCAL = SKILL / '_local'


class SyncError(RuntimeError):
    pass


def git_executable():
    portable = LOCAL / 'git' / 'cmd' / 'git.exe'
    return str(portable) if portable.is_file() else shutil.which('git') or 'git'


def git(*args, root=SKILL, check=True, capture=True, input=None):
    env = dict(os.environ, GIT_EDITOR='true', GIT_MERGE_AUTOEDIT='no')
    proc = subprocess.run([git_executable(), '-C', str(root), *args], input=input,
                          capture_output=capture, text=True, encoding='utf-8',
                          errors='replace', env=env)
    if check and proc.returncode:
        # Git output may contain authenticated URLs; never print credential values.
        raise SyncError(f'Git 操作失败：{args[0]}。本机修改已保留；请检查网络、登录或冲突。')
    return proc


def allowed_files(root=SKILL):
    return set(_collect_files(Path(root)))


def check_index(root=SKILL):
    allowed = allowed_files(root)
    tracked = git('ls-files', '-z', root=root).stdout.split('\0')
    forbidden = [p for p in tracked if p and p not in allowed and (Path(root) / p).exists()]
    if forbidden:
        raise SyncError('暂存/跟踪范围包含非发布文件：' + '、'.join(forbidden[:8]))
    config = Path(root) / '_local' / 'private' / 'image_api_key'
    key = config.read_bytes().strip() if config.is_file() else os.environ.get('PPT_IMAGE_API_KEY', '').encode()
    if key:
        for name in tracked:
            if not name:
                continue
            proc = git('show', ':' + name, root=root, check=False)
            if proc.returncode == 0 and key in proc.stdout.encode('utf-8'):
                raise SyncError('检测到生图密钥进入暂存内容；停止提交。')


def normalize_install_status(root=SKILL):
    """Keep substantive edits; remove machine-generated installation stamp drift."""
    path = Path(root) / 'docs' / '维护说明.md'
    before = git('show', 'HEAD:docs/维护说明.md', root=root, check=False)
    if before.returncode or not path.exists():
        return
    pattern = r'<!-- PPT_SKILL_INSTALL_STATUS_BEGIN -->.*?<!-- PPT_SKILL_INSTALL_STATUS_END -->'
    original = re.search(pattern, before.stdout, re.S)
    if original:
        text = path.read_text(encoding='utf-8')
        new = re.sub(pattern, lambda _: original.group(), text, count=1, flags=re.S)
        if new != text:
            path.write_text(new, encoding='utf-8', newline='\n')


def assert_quiet():
    # The shared runtime database is read-only here. Do not create it just to sync.
    import sqlite3
    runtime = Path(os.environ.get('PPT_SKILL_RUNTIME_DIR') or
                   (Path(os.environ.get('LOCALAPPDATA', Path.home() / '.cache')) / 'ppt-skill-v3' / 'runtime'))
    db = runtime / 'resources.sqlite3'
    if db.is_file():
        from ppt_skill_v3.resources import _alive
        with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
            rows = connection.execute("SELECT pid FROM jobs WHERE state IN ('waiting','running')").fetchall()
            leases = connection.execute('SELECT COUNT(*) FROM leases').fetchone()[0]
        if any(_alive(pid) for (pid,) in rows) or leases:
            raise SyncError('仍有 PPT 运行任务或外部交易租约；先收口任务再同步。')


@contextlib.contextmanager
def sync_lock():
    LOCAL.mkdir(parents=True, exist_ok=True)
    path = LOCAL / 'sync.lock'
    try:
        with path.open('x', encoding='utf-8') as out:
            out.write(str(os.getpid()))
    except FileExistsError:
        raise SyncError('另一个同步操作尚未结束。若上次异常中断，请先核对后处理 _local/sync.lock。')
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def init_repository():
    if not (SKILL / '.git').exists():
        git('init', '-b', BRANCH)
    git('config', 'core.autocrlf', 'false')
    git('config', 'core.quotepath', 'false')
    git('config', 'merge.autoStash', 'false')
    if git('remote', 'get-url', 'origin', check=False).returncode:
        git('remote', 'add', 'origin', REPOSITORY)
    elif git('remote', 'get-url', 'origin').stdout.strip() != REPOSITORY:
        raise SyncError('origin 与指定的 AI_PPT 仓库不一致；保留现有设置，停止同步。')
    # This address is derived from the verified GitHub owner ID, scoped to this repo.
    if git('config', '--get', 'user.name', check=False).returncode:
        git('config', 'user.name', 'invictus86')
    if git('config', '--get', 'user.email', check=False).returncode:
        git('config', 'user.email', '38399660+invictus86@users.noreply.github.com')


def assert_branch(root=SKILL):
    if git('symbolic-ref', '--short', 'HEAD', root=root).stdout.strip() != BRANCH:
        raise SyncError('当前不在 main 分支；停止自动同步，保留分支现场。')
    if git('ls-files', '-u', root=root).stdout.strip():
        raise SyncError('存在未解决的合并冲突。先在 Codex 中解决冲突，再重新同步。')
    for name in ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD'):
        if (Path(root) / '.git' / name).exists():
            raise SyncError('上次合并尚未结束。请先完成或取消该操作。')


def commit_changes(root=SKILL):
    normalize_install_status(root)
    allowed = allowed_files(root)
    tracked = {p for p in git('ls-files', '-z', root=root).stdout.split('\0') if p}
    forbidden = {p for p in tracked if p not in allowed and (Path(root) / p).exists()}
    if forbidden:
        raise SyncError('Git 跟踪了发布范围外的文件；停止自动提交。')
    paths = sorted(allowed | {p for p in tracked if not (Path(root) / p).exists()})
    # NUL-delimited pathspec handles Chinese, spaces, and command-line length.
    git('add', '--all', '--pathspec-from-file=-', '--pathspec-file-nul', root=root,
        input=''.join(p + '\0' for p in paths))
    check_index(root)
    if git('diff', '--cached', '--quiet', root=root, check=False).returncode:
        version = read_version(Path(root))
        stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
        git('commit', '-m', f'Sync PPT Skill {version} at {stamp}', root=root)
        return True
    return False


def read_version(root=SKILL):
    text = (Path(root) / 'scripts/runtime/ppt_skill_v3/__init__.py').read_text(encoding='utf-8')
    return re.search(r'__version__\s*=\s*[\"\']([^\"\']+)', text).group(1)


def merge_remote(root=SKILL):
    proc = git('merge', '--no-edit', 'origin/' + BRANCH, root=root, check=False)
    if proc.returncode:
        conflicts = git('diff', '--name-only', '--diff-filter=U', root=root).stdout.strip()
        if conflicts:
            raise SyncError('双方修改发生冲突；本机和远端提交均已保留。请在 Codex 中解决这些文件：\n' + conflicts)
        raise SyncError('合并未完成；本机提交和备份均已保留。')


def backup():
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y%m%d-%H%M%S-%f')
    out = LOCAL / 'backups' / stamp
    out.mkdir(parents=True)
    with zipfile.ZipFile(out / 'source.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(allowed_files()):
            archive.write(SKILL / rel, rel)
    if git('rev-parse', '--verify', 'HEAD', check=False).returncode == 0:
        git('bundle', 'create', str(out / 'history.bundle'), '--all')
    return out


def do_sync(push=True):
    with sync_lock():
        assert_quiet()
        init_repository()
        assert_branch()
        out = backup()
        print('已备份当前源码。')
        commit_changes()
        print('正在下载另一台电脑的更新……')
        git('fetch', 'origin')
        remote = git('rev-parse', '--verify', 'origin/' + BRANCH, check=False)
        if remote.returncode == 0:
            merge_remote()
        ensure_dependencies()
        if push:
            print('正在上传本机版本；首次上传可能要求 GitHub 登录……')
            git('push', '-u', 'origin', BRANCH, capture=False)
        install_entry()
        print('同步完成。版本：' + read_version() + '；提交：' + git('rev-parse', '--short', 'HEAD').stdout.strip())
        print('更新前备份：' + str(out))


def ensure_dependencies():
    req = SKILL / 'scripts' / 'portable-requirements.txt'
    if not req.exists():
        raise SyncError('当前版本缺少依赖清单。')
    import importlib.metadata as metadata
    from pip._vendor.packaging.requirements import Requirement
    missing = []
    for raw in req.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            if not requirement.specifier.contains(metadata.version(requirement.name)):
                missing.append(line)
        except metadata.PackageNotFoundError:
            missing.append(line)
    if missing:
        print('当前版本新增或调整了依赖，正在安装到便携环境……')
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(req)])
        if result.returncode:
            raise SyncError('依赖安装未完成；源码修改和历史仍保留。')


def install_entry():
    result = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts/pptctl.py'),
                             'install-profile', '--target', 'codex'], capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise SyncError('工作区入口生成失败。')
    # Installation stamps are local facts, not source changes to synchronize.
    normalize_install_status()
    entry = SKILL.parent / 'AGENTS.md'
    text = entry.read_text(encoding='utf-8')
    hint = '\n## 本机便携运行环境\n\n运行脚本优先使用 `.skill/_local/python/python.exe`；该解释器自动加载本机生图配置和 Poppler。不要将 `_local/`、密钥、输入输出资料提交到 GitHub。修改 Skill 前后使用 `.skill/scripts/双向同步.cmd` 同步；冲突必须保留双方提交并实际解决。\n'
    entry.write_text(text + hint, encoding='utf-8', newline='\n')


def environment_check():
    import importlib
    for name in ('PIL', 'docx', 'pptx', 'lxml.etree', 'fontTools.ttLib', 'pypdf', 'reportlab'):
        importlib.import_module(name)
    from ppt_skill_v3.image_api import image_api_key_status
    from ppt_skill_v3.verification_environment import verification_capability
    key = image_api_key_status()
    caps = {kind: verification_capability(kind) for kind in ('docx', 'pdf', 'pptx')}
    print('Python 和脚本依赖：可用')
    print('生图密钥：' + ('已配置（未调用生图服务）' if key['status'] == 'configured' else '缺失'))
    for name, cap in caps.items():
        print(name.upper() + ' 后台验证：' + ('环境可用，尚未实际渲染' if cap['available'] else '缺少 ' + '、'.join(cap['missing'])))
    if key['status'] != 'configured':
        raise SyncError('生图密钥未迁移完成。')


def publish_version():
    do_sync()
    tag = 'v' + read_version()
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise SyncError('发布版本应为数字三段版本号。')
    existing = git('ls-remote', '--tags', 'origin', 'refs/tags/' + tag).stdout.strip()
    if existing:
        raise SyncError('这个版本标签已经发布；请先更新版本号和 CHANGELOG 后再发布新版本。')
    if git('rev-parse', '--verify', tag, check=False).returncode:
        git('tag', '-a', tag, '-m', 'PPT Skill ' + read_version())
    else:
        target = git('rev-list', '-n', '1', tag).stdout.strip()
        if target != git('rev-parse', 'HEAD').stdout.strip():
            raise SyncError('本机已有同名版本标签指向其他提交；保留标签并停止上传。')
    git('push', 'origin', 'refs/tags/' + tag, capture=False)
    print('正式版本已标记：' + tag)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 'check', 'sync', 'receive', 'save', 'release'])
    args = parser.parse_args()
    if args.action == 'setup':
        init_repository()
        install_entry()
        environment_check()
        print('准备完成。请在 Codex 中打开工作区：' + str(SKILL.parent))
    elif args.action == 'check':
        environment_check()
    elif args.action == 'release':
        publish_version()
    elif args.action == 'save':
        with sync_lock():
            init_repository()
            assert_branch()
            check_index()
            commit_changes()
    else:
        do_sync(push=args.action == 'sync')


if __name__ == '__main__':
    try:
        main()
    except (SyncError, OSError) as exc:
        print('操作已停止：' + str(exc), file=sys.stderr)
        raise SystemExit(1)
