"""Cross-process queues and durable external leases; never control a desktop."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .validation import ValidationError

_local = threading.local()


def identity(value) -> str:
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def path_identity(path) -> str:
    return identity(os.path.normcase(str(Path(path).resolve())))


def runtime_dir() -> Path:
    explicit = os.environ.get('PPT_SKILL_RUNTIME_DIR')
    base = Path(explicit) if explicit else Path(os.environ.get('LOCALAPPDATA', Path.home() / '.cache')) / 'ppt-skill-v3' / 'runtime'
    base.mkdir(parents=True, exist_ok=True)
    return base


@contextmanager
def _connect():
    db = sqlite3.connect(runtime_dir() / 'resources.sqlite3', timeout=30)
    db.execute('PRAGMA busy_timeout=30000')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
          ticket INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE,
          resource TEXT, capacity INTEGER, pid INTEGER, state TEXT, created REAL, heartbeat REAL);
        CREATE INDEX IF NOT EXISTS job_resource ON jobs(resource,state,ticket);
        CREATE TABLE IF NOT EXISTS leases (
          resource TEXT PRIMARY KEY, owner TEXT, token TEXT, created REAL);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def _alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # access denied is not proof of death
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextmanager
def resource_slot(resource: str, *, capacity: int = 1, timeout: float | None = None):
    """FIFO grants across processes. Expiry alone never evicts a live owner."""
    if capacity < 1:
        raise ValidationError('resource capacity must be positive')
    timeout = float(os.environ.get('PPT_SKILL_QUEUE_TIMEOUT', '3600')) if timeout is None else timeout
    if resource == 'office-background':
        with _connect() as db:
            if db.execute('SELECT 1 FROM leases WHERE resource=\'office-background:uncertain\'').fetchone():
                raise ValidationError('后台Office前次任务未确认清理；禁止盲目重开或前台恢复，请查看resource-status')
    held = getattr(_local, 'held', None)
    if held is None:
        held = _local.held = {}
    if resource in held:
        yield held[resource]
        return
    token = uuid.uuid4().hex
    began = time.monotonic()
    stop = threading.Event()
    with _connect() as db:
        db.execute('INSERT INTO jobs(token,resource,capacity,pid,state,created,heartbeat) VALUES(?,?,?,?,?,?,?)',
                   (token, resource, capacity, os.getpid(), 'waiting', time.time(), time.time()))
    heartbeat_thread = None
    try:
        while True:
            office_abandoned = False
            with _connect() as db:
                db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT token,pid,state FROM jobs WHERE resource=? AND state IN (\'waiting\',\'running\')', (resource,)).fetchall()
                for old_token, pid, old_state in rows:
                    if not _alive(pid):
                        if resource == 'office-background' and old_state == 'running':
                            db.execute('INSERT OR IGNORE INTO leases VALUES(?,?,?,?)',
                                       ('office-background:uncertain',str(pid),uuid.uuid4().hex,time.time()))
                            office_abandoned = True
                        db.execute('UPDATE jobs SET state=\'abandoned\' WHERE token=?', (old_token,))
                if resource == 'office-background' and db.execute('SELECT 1 FROM leases WHERE resource=\'office-background:uncertain\'').fetchone():
                    office_abandoned = True
                limit = db.execute('SELECT MIN(capacity) FROM jobs WHERE resource=? AND state IN (\'waiting\',\'running\')', (resource,)).fetchone()[0]
                active = db.execute('SELECT COUNT(*) FROM jobs WHERE resource=? AND state=\'running\'', (resource,)).fetchone()[0]
                first = db.execute('SELECT token FROM jobs WHERE resource=? AND state=\'waiting\' ORDER BY ticket LIMIT 1', (resource,)).fetchone()
                granted = not office_abandoned and first and first[0] == token and active < limit
                db.execute('UPDATE jobs SET state=?,heartbeat=? WHERE token=?', ('running' if granted else 'waiting', time.time(), token))
            if office_abandoned:
                raise ValidationError('后台Office执行进程中断，需确认任务文稿/字体清理后恢复')
            if granted:
                break
            if time.monotonic() - began >= timeout:
                raise ValidationError('资源排队超时；未执行操作，请查看 resource-status 后恢复')
            stop.wait(.1)
        info = {'resource': resource, 'queue_seconds': round(time.monotonic() - began, 3)}
        held[resource] = info
        def heartbeat():
            while not stop.wait(5):
                try:
                    with _connect() as db:
                        db.execute('UPDATE jobs SET heartbeat=? WHERE token=?', (time.time(), token))
                except sqlite3.Error:
                    pass
        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        yield info
    finally:
        held.pop(resource, None)
        stop.set()
        if heartbeat_thread:
            heartbeat_thread.join(timeout=6)
        with _connect() as db:
            db.execute('UPDATE jobs SET state=\'finished\',heartbeat=? WHERE token=?', (time.time(), token))
            db.execute('DELETE FROM jobs WHERE state IN (\'finished\',\'abandoned\') AND heartbeat<?', (time.time()-86400,))


def project_lock(root):
    return resource_slot('project:' + path_identity(root))


def mark_office_uncertain(owner):
    with _connect() as db:
        db.execute('INSERT OR IGNORE INTO leases VALUES(?,?,?,?)',
                   ('office-background:uncertain',str(owner),uuid.uuid4().hex,time.time()))


def resolve_office_recovery(evidence):
    if not isinstance(evidence,dict) or evidence.get('controller_reviewed') is not True or evidence.get('worker_stopped_confirmed') is not True or evidence.get('task_documents_and_fonts_cleared') is not True or not evidence.get('reason'):
        raise ValidationError('必须实际确认后台worker已停止且仅任务所属文稿/字体已清理；不得终止用户软件')
    with _connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for pid,state in db.execute('SELECT pid,state FROM jobs WHERE resource=\'office-background\' AND state IN (\'waiting\',\'running\')'):
            if state == 'running' and _alive(pid):
                raise ValidationError('仍有活动后台Office任务，不能清理租约')
        db.execute('UPDATE jobs SET state=\'abandoned\' WHERE resource=\'office-background\' AND state=\'running\'')
        db.execute('DELETE FROM leases WHERE resource=\'office-background:uncertain\'')


def project_mutation(function):
    from functools import wraps
    @wraps(function)
    def wrapped(run_dir, *args, **kwargs):
        with project_lock(run_dir):
            return function(run_dir, *args, **kwargs)
    return wrapped


def claim_external(resource: str, owner: str, *, token: str | None = None) -> str:
    """Canva leases survive CLI exit; no timeout can prove a remote transaction ended."""
    with _connect() as db:
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT owner,token FROM leases WHERE resource=?', (resource,)).fetchone()
        if prior:
            if token and prior == (owner, token):
                return token
            raise ValidationError('该外部资源已有未收口租约；核对保存/取消结果后再释放，禁止跨窗口编辑')
        if token:
            raise ValidationError('外部租约已失效；请重新领取')
        token = uuid.uuid4().hex
        db.execute('INSERT INTO leases VALUES(?,?,?,?)', (resource, owner, token, time.time()))
        return token


def require_external(resource: str, owner: str, token: str):
    with _connect() as db:
        row = db.execute('SELECT owner,token FROM leases WHERE resource=?', (resource,)).fetchone()
    if row != (owner, token):
        raise ValidationError('外部资源租约缺失或属于另一个窗口')


def release_external(resource: str, owner: str, token: str):
    with _connect() as db:
        changed = db.execute('DELETE FROM leases WHERE resource=? AND owner=? AND token=?', (resource, owner, token)).rowcount
    if changed != 1:
        raise ValidationError('不能释放其他窗口的外部租约')


def resource_status() -> dict:
    with _connect() as db:
        jobs = db.execute('SELECT resource,capacity,pid,state,created,heartbeat FROM jobs WHERE state IN (\'waiting\',\'running\') ORDER BY ticket').fetchall()
        leases = db.execute('SELECT resource,owner,created FROM leases').fetchall()
    return {'jobs': [dict(zip(('resource','capacity','pid','state','created','heartbeat'), r)) for r in jobs],
            'external_leases': [dict(zip(('resource','owner','created'), r)) for r in leases]}
