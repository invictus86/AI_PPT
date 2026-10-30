"""Download an actual connector export. Signed URLs are stdin-only and never persisted."""
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

from .json_io import write_json, read_json
from .validation import ValidationError


def _url(value):
    parsed = urllib.parse.urlsplit(value)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None,443) or not (
            host == 'export-download.canva.com' or host.endswith('.canva.com')):
        raise ValidationError('Only an HTTPS Canva export URL is accepted')
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)):
        raise ValidationError('Export host must resolve to public addresses')
    return value


class _Redirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req,fp,code,msg,headers,_url(newurl))


def download_pptx(run_dir, task_id, design_id, expected_pages, url):
    from .animation.task import guard_run_dir
    root = guard_run_dir(run_dir)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',task_id) or not re.fullmatch(r'D[A-Za-z0-9_-]+',design_id):
        raise ValidationError('Invalid task/design identity')
    if type(expected_pages) is not int or expected_pages < 1:
        raise ValidationError('Use the actual positive page count returned by Canva')
    folder = root/'_state/工具任务/canva'/task_id/'downloads'
    if not folder.resolve().is_relative_to(root):
        raise ValidationError('Download path escapes project')
    folder.mkdir(parents=True,exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='.download-',suffix='.part',dir=folder)
    temporary=Path(name)
    try:
        with os.fdopen(handle,'wb') as out:
            try:
                deadline=time.monotonic()+300
                response=urllib.request.build_opener(_Redirect()).open(_url(url.strip()),timeout=30)
                with response:
                    total=0
                    read=getattr(response,'read1',response.read)
                    while chunk:=read(64*1024):
                        if time.monotonic()>deadline:
                            raise ValidationError('Canva export download exceeded five minutes; obtain a fresh export URL')
                        total+=len(chunk)
                        if total>512*1024*1024:
                            raise ValidationError('PPTX export exceeds 512 MiB')
                        out.write(chunk)
            except (urllib.error.URLError, OSError) as exc:
                # urllib errors can contain signed request URLs; disclose only their type.
                raise ValidationError('Canva export download failed: '+type(exc).__name__) from None
            out.flush();os.fsync(out.fileno())
        with zipfile.ZipFile(temporary) as package:
            if package.testzip() is not None:
                raise ValidationError('Incomplete PPTX ZIP')
            presentation=ET.fromstring(package.read('ppt/presentation.xml'))
            ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
            count=len(presentation.findall('p:sldIdLst/p:sldId',ns))
            if count!=expected_pages:
                raise ValidationError('Export page count differs from the selected Canva design')
        digest=hashlib.sha256(temporary.read_bytes()).hexdigest()
        target=folder/(digest+'.pptx')
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
                raise ValidationError('Existing downloaded evidence changed')
        else:
            os.link(temporary,target)
        manifest={'design_id':design_id,'format':'pptx','pages':count,'sha256':'sha256:'+digest,
                  'file':target.relative_to(root).as_posix(),'editable_objects_verified':False,
                  'status':'downloaded','bytes':target.stat().st_size}
        write_json(folder/'download_manifest.json',manifest)
        return manifest
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise ValidationError('Export is not a valid PowerPoint presentation') from None
    finally:
        temporary.unlink(missing_ok=True)


def prepare_input(run_dir, downloaded_file, target):
    """Place verified bytes in the existing delivery directory without overwriting a current deck."""
    from .animation.task import guard_run_dir
    import shutil
    root=guard_run_dir(run_dir)
    source=Path(downloaded_file).resolve();target=Path(target).resolve()
    if not source.is_relative_to(root/'_state/工具任务/canva') or not target.is_relative_to(root):
        raise ValidationError('Use the current project download and delivery directory')
    if target.is_relative_to(root/'_state') or target.suffix.lower()!='.pptx':
        raise ValidationError('Working input must be a PPTX in the project delivery directory')
    if target.exists():
        raise ValidationError('Current deliverable exists; archive a confirmed prior file before replacing it')
    manifest=read_json(source.parent/'download_manifest.json')
    digest='sha256:'+hashlib.sha256(source.read_bytes()).hexdigest()
    if manifest.get('sha256')!=digest or manifest.get('file')!=source.relative_to(root).as_posix():
        raise ValidationError('Downloaded source differs from its verified manifest')
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.editable-input-',suffix='.tmp',dir=target.parent)
    temporary=Path(name)
    try:
        with source.open('rb') as incoming,os.fdopen(fd,'wb') as out:
            shutil.copyfileobj(incoming,out);out.flush();os.fsync(out.fileno())
        if 'sha256:'+hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:
            raise ValidationError('Working input copy is incomplete')
        os.link(temporary,target)
    finally:
        temporary.unlink(missing_ok=True)
    return {'input':str(target),'sha256':digest}
