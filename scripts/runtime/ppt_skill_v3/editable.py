"""Existing text/font contracts, executed before the independent lightweight animation route."""
from pathlib import Path
import os
import tempfile

from .file_hashing import file_sha256
from .json_io import read_json, write_json
from .state import read_state, write_state
from .validation import ValidationError


def inspect(run_dir, source, evidence, *, optimize_text=False, repair_fonts=False, match_reference_fonts=False):
    from .teaching_animation import start_animation
    result=start_animation(run_dir,source,evidence,optimize_text=optimize_text,
                           repair_fonts=repair_fonts,match_reference_fonts=match_reference_fonts)
    state=read_state(run_dir)
    state['stage5_animation']['operation']='editable'
    write_state(run_dir,state)
    return result


def _previews(root, task):
    from .teaching_animation import _require_previews
    _require_previews(root,task)
    manifest=read_json(root/'_state/阶段5/preview_manifest.json')
    if manifest.get('method')=='verification_skipped':
        raise ValidationError('Editable changes require actual diagnostic previews; preserve fonts/text without evidence')
    return manifest


def record_plan(run_dir, plan):
    from .teaching_animation import (_bind_font_evidence, _require_reference_authorization,
                                    _validate_pending_text, slide_parts)
    from .text_mapping_review import require_task_mapping
    from .text_optimization import validate_optimizations
    from .font_repair import validate_repairs, _expanded_repairs
    from .font_handoff import validate_handoff_resolutions
    root=Path(run_dir);state=read_state(root);task=state['stage5_animation']
    if task.get('operation')!='editable' or task['status'] not in {'planning','plan_ready','needs_manual_adjustment'}:
        raise ValidationError('Inspect the editable input first')
    if file_sha256(task['input'])!=task['input_sha256'] or plan.get('input_sha256')!=task['input_sha256']:
        raise ValidationError('Editable input changed; inspect again')
    if plan.get('controller_reviewed') is not True or not plan.get('preview_review_evidence'):
        raise ValidationError('Actual page review evidence is required')
    manifest=_previews(root,task)
    info=read_json(root/'_state/阶段5/inspection.json')
    pages=plan.get('pages',[])
    if len(pages)!=len(info['pages']) or {p.get('page') for p in pages}!={p['page'] for p in info['pages']}:
        raise ValidationError('Review every editable page')
    if not plan.get('font_review_evidence') or any(not p.get('font_observation') for p in pages):
        raise ValidationError('Record actual font/layout observations, including unchanged pages')
    repairs=plan.get('font_repairs',[]);optimizations=plan.get('text_optimizations',[])
    if repairs and not task.get('font_repair_enabled') or optimizations and not task.get('text_optimization_enabled'):
        raise ValidationError('Changes exceed the actual editing authorization')
    # Internal adapter only for the preserved copy/handoff contracts, never an animation plan.
    result=dict(plan, slides=[dict(p,effects=[],replace_targets=[],manual_issues=p.get('manual_issues',[])) for p in pages])
    if any(p.get('effects') or p.get('replace_targets') for p in pages):
        raise ValidationError('Editable optimization cannot introduce timing; use animation after review')
    validate_optimizations(task['input'],optimizations,root=root,bind=True)
    validate_repairs(task['input'],slide_parts(task['input']),repairs)
    if {(e['page'],e['shape_id']) for e in optimizations}.intersection((r['page'],r['shape_id']) for r in _expanded_repairs(repairs)):
        raise ValidationError('Use one optimization entry per object; do not overlap font repair ranges')
    verification=require_task_mapping(root,task,optimizations)
    pending=_validate_pending_text(root,task,result,verification,bind=True)
    _require_reference_authorization(task,repairs)
    _bind_font_evidence(root,repairs,bind=True)
    _bind_font_evidence(root,result.get('font_handoff_resolutions',[]),bind=True)
    validate_handoff_resolutions(root,task,result,info)
    manual_pages={p['page'] for p in result['slides'] if p['manual_issues']}
    if manual_pages.intersection(e['page'] for e in repairs+optimizations):
        raise ValidationError('Unresolved editing pages must remain unchanged; continue other safe pages')
    path=root/'_state/阶段5/editable_plan.json';write_json(path,result)
    task.update(status='plan_ready',plan=path.relative_to(root).as_posix(),plan_sha256=file_sha256(path),
                preview_manifest_sha256=file_sha256(root/'_state/阶段5/preview_manifest.json'),pending_text_issues=pending,
                editable_manual_pages=sorted(manual_pages))
    write_state(root,state)
    return result


def apply(run_dir):
    from .resources import resource_slot, path_identity
    task=read_state(run_dir)['stage5_animation']
    with resource_slot('editable-file:' + path_identity(task.get('output',task['input']))):
        return _apply(run_dir)


def _apply(run_dir):
    from .teaching_animation import verify_animation_only, slide_parts, _bind_font_evidence
    from .font_repair import apply_font_repairs
    from .text_optimization import apply_text_optimizations, validate_optimizations
    from .text_mapping_review import require_task_mapping
    from .font_handoff import validate_handoff_resolutions
    from .animation.task import _locked_conflict
    from .animation_storage import make_snapshot
    root=Path(run_dir);state=read_state(root);task=state['stage5_animation']
    if task.get('operation')!='editable':
        raise ValidationError('Not an editable optimization task')
    plan=read_json(root/task['plan'])
    if file_sha256(root/task['plan'])!=task['plan_sha256']:
        raise ValidationError('Editable plan changed')
    if task.get('editable_candidate'):
        source=Path(task['input']);output=Path(task['output']);candidate=Path(task['editable_candidate'])
        if not output.is_file():
            raise ValidationError('Editable output disappeared')
        if file_sha256(output)!=task['output_sha256']:
            if file_sha256(output)!=task['input_sha256'] or not candidate.is_file() or file_sha256(candidate)!=task['output_sha256']:
                raise ValidationError('Editable commit changed externally')
            os.replace(candidate,output)
        return verify_animation_only(source,output,set(),plan.get('font_repairs',[]),plan.get('text_optimizations',[]),root=root)
    if task['status']!='plan_ready' or file_sha256(task['input'])!=task['input_sha256']:
        raise ValidationError('Inspect and record the current editable plan')
    source=Path(task['input']).resolve();_locked_conflict(root,source)
    _previews(root,task)
    if file_sha256(root/'_state/阶段5/preview_manifest.json')!=task['preview_manifest_sha256']:
        raise ValidationError('Editable preview evidence changed')
    repairs=plan.get('font_repairs',[]);opts=plan.get('text_optimizations',[])
    validate_optimizations(source,opts,root=root)
    require_task_mapping(root,task,opts)
    validate_handoff_resolutions(root,task,plan,read_json(root/'_state/阶段5/inspection.json'))
    _bind_font_evidence(root,repairs,bind=False)
    _bind_font_evidence(root,plan.get('font_handoff_resolutions',[]),bind=False)
    snapshot=make_snapshot(root,source,task['input_sha256'])
    with tempfile.TemporaryDirectory(prefix='ppt_editable_') as tmp:
        baseline=source
        if repairs:
            baseline=Path(tmp)/'fonts.pptx';apply_font_repairs(source,source,baseline,slide_parts(source),repairs)
        if opts:
            optimized=Path(tmp)/'optimized.pptx';apply_text_optimizations(source,baseline,optimized,opts,root=root);baseline=optimized
        report=verify_animation_only(source,baseline,set(),repairs,opts,root=root)
        fd,name=tempfile.mkstemp(prefix='.ppt-editable-',suffix='.tmp',dir=source.parent)
        import shutil
        with os.fdopen(fd,'wb') as out,baseline.open('rb') as incoming:
            shutil.copyfileobj(incoming,out);out.flush();os.fsync(out.fileno())
        candidate=Path(name)
        if file_sha256(source)!=task['input_sha256']:
            candidate.unlink();raise ValidationError('Editable source changed concurrently')
        task.update(input=str(snapshot),output=str(source),original_input=str(source),
                    editable_candidate=str(candidate),output_sha256=file_sha256(candidate),
                    status='executing',editable_review_accepted=False)
        write_state(root,state)
        os.replace(candidate,source)
    task.update(status='waiting_background_review',file_verification='_state/阶段5/editable_verification.json')
    task['editable_result_snapshot']=str(make_snapshot(root,source,task['output_sha256']))
    write_json(root/task['file_verification'],report);write_state(root,state)
    return dict(report,output=str(source),next='editable previews-output; editable review')


def output_previews(run_dir):
    from .background_ppt import render_hidden
    root=Path(run_dir);state=read_state(root);task=state['stage5_animation']
    if task.get('operation')!='editable' or file_sha256(task['output'])!=task['output_sha256']:
        raise ValidationError('Current editable result is required')
    result=render_hidden(task['output'],root.resolve()/'_state/阶段5/editable_output_previews'/task['output_sha256'].split(':')[1][:12])
    result['plan_sha256']=task['plan_sha256']
    write_json(root/'_state/阶段5/editable_output_manifest.json',result)
    return result


def review(run_dir, document, *, persist=True, _task=None):
    from .teaching_animation import verify_animation_only
    root=Path(run_dir);state=read_state(root);task=_task or state['stage5_animation']
    manifest_path=root/'_state/阶段5/editable_output_manifest.json';manifest=read_json(manifest_path)
    if task.get('operation')!='editable' or document.get('controller_reviewed') is not True:
        raise ValidationError('Actual editable result review required')
    for key in ('input_sha256','output_sha256','plan_sha256'):
        if document.get(key)!=task[key]:raise ValidationError('Editable review fingerprints changed')
    if document.get('manifest_sha256')!=file_sha256(manifest_path) or manifest['input_sha256']!=task['output_sha256']:
        raise ValidationError('Editable output preview changed')
    from .background_ppt import RENDERER
    proof=manifest.get('render_proof',{})
    if (manifest.get('renderer')!=RENDERER or manifest.get('foreground_opened') is not False or
            proof.get('with_window') is not False or type(proof.get('windows_before')) is not int or
            proof.get('windows_before')!=proof.get('windows_during') or
            proof.get('slides_exported')!=len(manifest.get('images',[])) or not manifest.get('images')):
        raise ValidationError('Actual hidden-rendered editable output pages are required')
    if file_sha256(task['input'])!=task['input_sha256'] or file_sha256(task['output'])!=task['output_sha256'] or file_sha256(root/task['plan'])!=task['plan_sha256']:
        raise ValidationError('Editable source/output/plan changed')
    pages=document.get('pages',[]);images={i['page']:i for i in manifest.get('images',[])}
    if len(pages)!=len(images) or {p.get('page') for p in pages}!=set(images) or document.get('unresolved_issues'):
        raise ValidationError('Review all output pages and disclose unresolved issues')
    for p in pages:
        image=images[p['page']];path=Path(image['path']);path=path if path.is_absolute() else root/path
        if p.get('pass') is not True or p.get('image_sha256')!=image['sha256'] or file_sha256(path)!=image['sha256']:
            raise ValidationError('Unreviewed or changed editable page')
        if any(not isinstance(p.get(k),str) or not p[k].strip() for k in ('font_observation','layout_observation','text_quality_observation','original_comparison_observation')):
            raise ValidationError('Record actual text/font/layout and original comparison observations')
    plan=read_json(root/task['plan'])
    verify_animation_only(Path(task['input']),Path(task['output']),set(),plan.get('font_repairs',[]),plan.get('text_optimizations',[]),root=root)
    if not persist:
        return {'valid':True,'editable_review_accepted':True}
    write_json(root/'_state/阶段5/editable_review.json',document)
    write_json(root/'_state/阶段5/font_handoff_results.json',{'input_sha256':task['input_sha256'],'output_sha256':task['output_sha256'],
        'items':plan.get('font_handoff_resolutions',[]),'pptx_only':True,'canva_online_changed':False})
    _previews(root,task)
    if file_sha256(root/'_state/阶段5/preview_manifest.json')!=task['preview_manifest_sha256']:
        raise ValidationError('Original editable preview evidence changed')
    task.update(status='needs_manual_adjustment' if task.get('pending_text_issues') or task.get('editable_manual_pages') else 'completed',
                editable_review_accepted=True,font_review_accepted=True,background_accepted=False,
                execution_mode='background_only',editable_review='_state/阶段5/editable_review.json',
                editable_review_sha256=file_sha256(root/'_state/阶段5/editable_review.json'))
    if state['workflow']['mode']=='animation_only' and task['status']=='completed':
        state.update(status='completed',required_actor='none',next_required_action='可按独立授权继续轻量动画')
    write_state(root,state)
    return {'status':task['status'],'output':task['output'],'editable_review_accepted':True,'animation_added':False,
            'pending_text_issues':task.get('pending_text_issues',[])}
