"""Real DOCX layout evidence and all-page PDF review; no foreground fallback."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .file_hashing import file_sha256
from .json_io import read_json, write_json
from .pdf_page_images import render_pdf_pages_to_png, find_pdftoppm
from .document_rendering import pdf_page_count
from .render_cache import environment_fingerprint, valid_cache
from .resources import resource_slot, path_identity, project_lock
from .time_utils import now_iso
from .validation import ValidationError


def render_document(source, directory, *, timeout=600):
    source = Path(source).resolve(); directory = Path(directory).resolve()
    if not source.is_file() or source.suffix.lower() not in {'.docx','.pdf'}:
        raise ValidationError('document rendering accepts an existing DOCX or PDF')
    from .verification_environment import verification_capability, skipped_verification
    capability = verification_capability(source.suffix.lower()[1:])
    if not capability['available']:
        manifest = skipped_verification(source, capability)
        with resource_slot('render-output:' + path_identity(directory)):
            write_json(directory/'document_manifest.json', manifest)
        return manifest
    poppler = find_pdftoppm()
    if not poppler:
        raise ValidationError('缺少pdftoppm；文档布局验收阻断，不使用前台备用')
    fingerprint = environment_fingerprint([Path(__file__),Path(__file__).with_name('background_word.ps1'),Path(poppler)])
    with resource_slot('render-output:' + path_identity(directory)):
        manifest_path = directory/'document_manifest.json'
        if manifest_path.is_file():
            manifest = read_json(manifest_path)
            pdf = Path(manifest.get('layout_pdf','__missing__'))
            proof = manifest.get('render_proof',{})
            hidden = source.suffix.lower()=='.pdf' or (manifest.get('renderer')=='Microsoft Word hidden ExportAsFixedFormat + pdftoppm' and proof.get('visible') is False and proof.get('read_only') is True and proof.get('document_pages')==manifest.get('pages'))
            if hidden and pdf.is_file() and file_sha256(pdf)==manifest.get('layout_pdf_sha256') and valid_cache(source,manifest,fingerprint) and manifest.get('foreground_opened') is False:
                return manifest
        digest = file_sha256(source)
        directory.mkdir(parents=True,exist_ok=True)
        proof = {'foreground_opened':False}
        queue_seconds = 0
        if source.suffix.lower() == '.docx':
            if os.name != 'nt':
                raise ValidationError('DOCX真实后台排版当前需要Windows/Microsoft Word；不启用WPS或前台备用')
            shell = shutil.which('pwsh') or shutil.which('powershell')
            if not shell:
                raise ValidationError('缺少后台PowerShell')
            with resource_slot('office-background') as slot:
                queue_seconds = slot['queue_seconds']
                with tempfile.TemporaryDirectory(prefix='ppt_word_background_') as tmp:
                    pdf = Path(tmp)/'layout.pdf'; evidence = Path(tmp)/'evidence.json'
                    try:
                        process = subprocess.run([shell,'-NoProfile','-NonInteractive','-File',str(Path(__file__).with_name('background_word.ps1')),
                            '-InputDocx',str(source),'-OutputPdf',str(pdf),'-EvidenceJson',str(evidence)],
                            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                    except subprocess.TimeoutExpired as exc:
                        from .resources import mark_office_uncertain
                        mark_office_uncertain(directory)
                        raise ValidationError('DOCX后台导出超时，需核对任务资源清理；禁止前台恢复') from exc
                    if process.returncode:
                        raise ValidationError('DOCX后台排版失败，未启用前台备用：'+(process.stderr or process.stdout)[-1500:])
                    proof = json.loads(evidence.read_text(encoding='utf-8-sig'))
                    if proof.get('visible') is not False or proof.get('read_only') is not True or proof.get('open_after_export') is not False:
                        raise ValidationError('Word后台证据不符合隐藏只读导出合同')
                    layout_pdf = directory/'docx_layout.pdf'
                    shutil.copy2(pdf,layout_pdf)
            renderer = 'Microsoft Word hidden ExportAsFixedFormat + pdftoppm'
        else:
            layout_pdf = source
            renderer = 'pdftoppm'
        result = render_pdf_pages_to_png(layout_pdf,directory/'pages')
        images = result['images']
        count = pdf_page_count(layout_pdf)
        if not count or len(images) != count or (source.suffix.lower()=='.docx' and proof.get('document_pages') != count):
            raise ValidationError('后台文档页数证据或全页导出不一致')
        if file_sha256(source) != digest or environment_fingerprint([Path(__file__),Path(__file__).with_name('background_word.ps1'),Path(poppler)]) != fingerprint:
            raise ValidationError('文档或渲染环境变化，须重新渲染')
        manifest = {'method':'background_document_pages','input':str(source),'input_sha256':digest,
                    'environment_fingerprint':fingerprint,'renderer':renderer,'foreground_opened':False,
                    'render_proof':proof,'pages':count,'images':images,'queue_seconds':queue_seconds,
                    'layout_pdf':str(layout_pdf),'layout_pdf_sha256':file_sha256(layout_pdf),'created_at':now_iso(),
                    'notice':'实际全页图片仍需主控审阅；未自动通过'}
        write_json(manifest_path,manifest)
        return manifest


def _validate_review(root, review):
    from .image_geometry import read_image_dimensions
    if review.get('method') == 'verification_skipped':
        from .verification_environment import verification_capability
        source = Path(review['input']).resolve()
        source.relative_to(root.resolve())
        if file_sha256(source) != review.get('input_sha256') or review.get('verified') is not False:
            raise ValidationError('缺环境记录必须绑定真实文件，不能冒充验收')
        capability = verification_capability(source.suffix.lower()[1:])
        if capability['available']:
            raise ValidationError('当前验证环境已具备，必须实际验证，不能继续沿用缺环境记录')
        return review
    if review.get('controller_reviewed') is not True or review.get('method') != 'background_document_pages' or review.get('unresolved_issues') != []:
        raise ValidationError('document review needs actual all-page observations and no unresolved issues')
    manifest_path = Path(review['manifest'])
    if not manifest_path.is_absolute():
        manifest_path = root/manifest_path
    manifest_path.resolve().relative_to(root.resolve())
    if file_sha256(manifest_path) != review.get('manifest_sha256'):
        raise ValidationError('document render manifest changed')
    manifest = read_json(manifest_path)
    source = Path(manifest['input']); source.resolve().relative_to(root.resolve())
    if file_sha256(source) != review.get('input_sha256') or manifest['input_sha256'] != review['input_sha256'] or manifest.get('foreground_opened') is not False:
        raise ValidationError('document review is stale or not background evidence')
    if manifest.get('renderer') not in {'pdftoppm','Microsoft Word hidden ExportAsFixedFormat + pdftoppm'}:
        raise ValidationError('unsupported document renderer')
    poppler = find_pdftoppm()
    if not poppler or manifest.get('environment_fingerprint') != environment_fingerprint([Path(__file__),Path(__file__).with_name('background_word.ps1'),Path(poppler)]):
        raise ValidationError('文档渲染环境已变化，必须重新渲染及审阅')
    if source.suffix.lower()=='.docx':
        proof = manifest.get('render_proof',{})
        if manifest['renderer'] != 'Microsoft Word hidden ExportAsFixedFormat + pdftoppm' or proof.get('visible') is not False or proof.get('read_only') is not True or proof.get('open_after_export') is not False or proof.get('document_pages') != manifest.get('pages'):
            raise ValidationError('DOCX layout cannot be proven by independently generated PDF')
    if file_sha256(manifest['layout_pdf']) != manifest['layout_pdf_sha256']:
        raise ValidationError('layout PDF changed')
    if pdf_page_count(Path(manifest['layout_pdf'])) != manifest['pages']:
        raise ValidationError('document manifest does not match the actual layout PDF page count')
    observations = review.get('pages',[]); images = manifest['images']
    if len(images) != manifest['pages'] or [x['page'] for x in images] != list(range(1,manifest['pages']+1)):
        raise ValidationError('document manifest omits or duplicates pages')
    if len(observations) != len(images) or {x.get('page') for x in observations} != {x['page'] for x in images}:
        raise ValidationError('document review must cover every actual page')
    by_page = {x['page']:x for x in observations}
    for image in images:
        Path(image['path']).resolve().relative_to(root.resolve())
        item = by_page[image['page']]
        if item.get('pass') is not True or item.get('image_sha256') != image['sha256'] or file_sha256(image['path']) != image['sha256']:
            raise ValidationError('document page failed or image changed')
        read_image_dimensions(image['path'])
        for key in ('text_observation','font_observation','layout_observation'):
            if not isinstance(item.get(key),str) or not item[key].strip():
                raise ValidationError('document review needs ' + key)
    return manifest


def record_document_review(root, review):
    root = Path(root)
    with project_lock(root):
        manifest = _validate_review(root,review)
        target = root/'_state/document_reviews'/(manifest['input_sha256'].split(':')[-1]+'.json')
        write_json(target,review)
    return {'status':'document_layout_reviewed','review':str(target)}


def require_package_document_reviews(root):
    root = Path(root)
    for name in ('speaker_script','lesson_plan'):
        manifest = read_json(root/f'_state/阶段3/{name}_manifest.json')
        for file in manifest['files']:
            artifact = root/file['path']
            if artifact.suffix.lower() not in {'.docx','.pdf'}:
                continue
            digest = file_sha256(artifact)
            review_path = root/'_state/document_reviews'/(digest.split(':')[-1]+'.json')
            from .verification_environment import verification_capability, skipped_verification
            capability = verification_capability(artifact.suffix.lower()[1:])
            if not capability['available']:
                if review_path.is_file():
                    prior = read_json(review_path)
                    if prior.get('unresolved_issues') or any(page.get('pass') is False for page in prior.get('pages', [])):
                        raise ValidationError('已记录的文档问题仍需处理，不能用缺环境覆盖失败：'+file['path'])
                # Environment absence is recorded, never as a successful review.
                skipped = skipped_verification(artifact, capability)
                if not review_path.is_file() or read_json(review_path).get('method') != 'verification_skipped':
                    write_json(review_path, skipped)
                _validate_review(root, read_json(review_path))
                continue
            if not review_path.is_file():
                raise ValidationError('配套文档缺少真实后台全页布局审阅：'+file['path'])
            review = read_json(review_path)
            if review.get('input_sha256') != digest:
                raise ValidationError('配套文档布局审阅指纹不一致')
            _validate_review(root,review)
