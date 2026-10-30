"""Follow only verified timing-only revisions; editing exclusions survive renames."""
from pathlib import Path

from ..file_hashing import file_sha256
from ..json_io import read_json
from .plan import plan_signature, require
from .reader import read_package
from .verify import content_snapshot, verify_file


def matches_revision(root, source, digest, original, original_hashes):
    root=Path(root);original=Path(original).resolve()
    hashes=set(filter(None,original_hashes))
    pending=[(Path(source).resolve(),digest,Path(source))];seen=set()
    records=list((root/'_state/工具任务/animation').glob('*/task.json'))
    while pending:
        logical,current,physical=pending.pop()
        key=(logical,current)
        if key in seen:continue
        seen.add(key)
        if logical==original and current in hashes:return True
        for path in records:
            try:item=read_json(path)
            except (ValueError,OSError):continue
            if (item.get('status')!='applied' or not item.get('output')
                    or Path(item['output']).resolve()!=logical or item.get('after_sha256')!=current):continue
            folder=path.parent;snapshot=Path(item.get('snapshot',''))
            require(snapshot.resolve().is_relative_to(root.resolve()/'_state/阶段5/originals'), 'Animation lineage snapshot escaped project')
            require(file_sha256(physical)==current and file_sha256(snapshot)==item['before_sha256'], 'Animation lineage revision changed')
            plan=read_json(folder/'plan.json');baseline=read_json(folder/'baseline.json')
            require(plan_signature(plan)==item.get('plan_signature') and plan['source']['sha256']==item['before_sha256']
                    and Path(plan['source']['path']).resolve()==Path(item['source']).resolve(), 'Animation lineage plan changed')
            before=content_snapshot(read_package(snapshot),{p['part'] for p in plan['pages']})
            require(before==baseline,'Animation lineage baseline changed')
            verify_file(physical,baseline,plan)
            pending.append((Path(item['source']).resolve(),item['before_sha256'],snapshot))
    return False


def editable_matches(root,source,digest,task):
    original=task.get('output') or task.get('original_input') or task.get('input')
    return bool(task.get('operation')=='editable' and original and matches_revision(
        root,source,digest,original,{task.get('input_sha256'),task.get('output_sha256')}))


def result_view(root,task):
    """Validate active files, permitting only a proven animation handoff to replace output."""
    view=dict(task);output=task.get('output');handed_off=False
    if output and (not Path(output).is_file() or file_sha256(output)!=task.get('output_sha256')):
        if task.get('status')=='executing' and Path(output).is_file() and file_sha256(output)==task.get('input_sha256'):
            require(file_sha256(task['editable_candidate'])==task['output_sha256'],'Editable candidate changed')
        else:
            for path in (Path(root)/'_state/工具任务/animation').glob('*/task.json'):
                item=read_json(path);candidate=Path(item.get('output',''))
                if (item.get('status')=='applied' and candidate.is_file() and file_sha256(candidate)==item.get('after_sha256')
                        and matches_revision(root,candidate,item['after_sha256'],output,{task.get('output_sha256')})):
                    snapshot=Path(task.get('editable_result_snapshot',''))
                    require(snapshot.is_file() and file_sha256(snapshot)==task['output_sha256'],'Editable result snapshot changed')
                    view['output']=str(snapshot);handed_off=True;break
            require(handed_off,'Editable output missing or changed without a verified animation handoff')
    source=Path(task.get('input',''))
    if handed_off and output and source.resolve()==Path(output).resolve() and task['input_sha256']==task['output_sha256']:
        view['input']=view['output'];source=Path(view['input'])
    require(source.is_file() and file_sha256(source)==task.get('input_sha256'),'Editable input missing or changed')
    if output and task.get('status')!='executing':
        require(Path(view['output']).is_file() and file_sha256(view['output'])==task['output_sha256'],'Editable result changed')
    return view
