"""Check content preservation separately from reviewed text presentation changes."""
from pathlib import Path
from collections import Counter
import re
from zipfile import ZipFile
from lxml import etree
from .json_io import read_json
from .file_hashing import file_sha256
from .validation import ValidationError
from .teaching_animation import slide_parts


def verify_source_text_unchanged(source, output, *, text_optimizations=None, root=None):
    """Keep literal text exact outside declared optimization objects.

    Edited objects must match their reviewed restoration/layout plan. Full
    package comparison separately protects all undeclared XML properties/media.
    """
    parts = slide_parts(source)
    if parts != slide_parts(output):
        raise ValidationError('字体/动画修复改变了原稿页序')
    a = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    def units(data):
        tree = etree.fromstring(data)
        return [''.join('\v' if n.tag == a+'br' else (n.text or '')
                        for n in p.iter() if n.tag in {a+'t', a+'br'}) for p in tree.iter(a+'p')]
    edits = text_optimizations or []
    if edits:
        from .text_optimization import validate_optimizations, layout_text
        from .font_repair import _shapes, _text
        validate_optimizations(source, edits, root=root)
    with ZipFile(source) as before, ZipFile(output) as after:
        for page, part in enumerate(parts, 1):
            page_edits = {e['shape_id']: e for e in edits if e['page'] == page}
            if page_edits:
                original = _shapes(etree.fromstring(before.read(part)))
                final = _shapes(etree.fromstring(after.read(part)))
                if set(original) != set(final):
                    raise ValidationError('文字优化改变了文本对象身份')
                for identity, shape in original.items():
                    expected = page_edits.get(identity, {}).get('after_text', _text(shape))
                    actual = _text(final[identity])
                    same = layout_text(expected) == layout_text(actual) if identity in page_edits else expected == actual
                    if not same:
                        raise ValidationError(f'第{page}页正文变化超出已审阅的原稿还原或排版清单')
            elif units(before.read(part)) != units(after.read(part)):
                raise ValidationError(f'第{page}页原稿文字、空格、标点或显式换行发生变化')
    return {'verified': True, 'literal_source_text_unchanged': not edits,
            'content_preserved_with_reviewed_optimizations': bool(edits),
            'source_sha256': file_sha256(source), 'output_sha256': file_sha256(output),
            'pages_checked': len(parts), 'normalization': 'declared_layout_only' if edits else 'none'}


def verify_stage1_text(root, input_pptx, *, mapping_document=None, text_optimizations=None, collect_differences=False):
    root=Path(root)
    source=Path(input_pptx).resolve()
    authority=root/'_state/阶段1/content.json'
    content=read_json(authority)
    parts=slide_parts(source)
    slides=sorted(content['slides'],key=lambda item:item['slide_index'])
    if len(parts)!=len(slides):
        raise ValidationError('转换后页数与阶段1逐页文字不一致')
    pages=[]
    mapping = None
    edits = text_optimizations or []
    if edits:
        from .text_optimization import validate_optimizations, patch_text_tree
        validate_optimizations(source, edits, root=root)
    with ZipFile(source) as package:
        for slide,part in zip(slides,parts):
            tree=etree.fromstring(package.read(part))
            if edits:
                patch_text_tree(tree, [e for e in edits if e['page'] == slide['slide_index']])
            actual=tree.xpath('//a:t/text()',namespaces={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'})
            expected=''.join(slide['final_visible_text'])
            # Run/paragraph segmentation is formatting; actual characters are not cleaned.
            match_method = 'xml_text_order_exact'
            if ''.join(actual)!=expected:
                # Shape order in OOXML is stacking order, not visual reading order.
                # Match exact paragraph units and their multiplicity; never sort
                # individual characters or remove spaces/punctuation to make a pass.
                ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
                a = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
                actual_units = [part for paragraph in tree.xpath('//a:p', namespaces=ns)
                                for part in re.split('[\n\v]', ''.join('\v' if node.tag == a+'br' else (node.text or '')
                                    for node in paragraph.iter() if node.tag in {a+'t', a+'br'})) if part != '']
                expected_units = [part for item in slide['final_visible_text'] for part in re.split('[\n\v]', item) if part != '']
                from .text_optimization import page_text_equal
                has_mapping = mapping_document is not None or (root / '_state/阶段5/editable_text_mapping_review.json').is_file()
                if not has_mapping and page_text_equal(actual, slide['final_visible_text']):
                    match_method = 'content_equal_with_layout_variation'
                elif Counter(actual_units) != Counter(expected_units):
                    from .text_mapping_review import load_mapping_review, check_mapped_page
                    if mapping is None:
                        mapping = load_mapping_review(root, source, authority, mapping_document)
                    candidates = [p for p in mapping['pages'] if p['slide_index'] == slide['slide_index']] if mapping else []
                    if len(candidates) != 1:
                        if collect_differences:
                            pages.append({'slide_index': slide['slide_index'], 'editable_text_matches_stage1': False,
                                          'match_method': 'requires_original_comparison',
                                          'expected_text': slide['final_visible_text'], 'actual_text': actual_units})
                            continue
                        raise ValidationError(f"第{slide['slide_index']}页需对照原稿：排版或图像文字可登记显示映射；明确转换错误可登记原稿还原，无法确定的正文差异保留待处理")
                    check_mapped_page(candidates[0], actual_units, expected_units)
                    match_method = 'controller_reviewed_display_mapping'
                else:
                    match_method = 'exact_paragraph_units_independent_of_shape_storage_order'
            pages.append({'slide_index':slide['slide_index'],'editable_text_matches_stage1':True,'match_method':match_method})
    return {'status': 'requires_original_comparison' if any(not p['editable_text_matches_stage1'] for p in pages) else 'editable_text_matches_stage1',
            'authority':str(authority),'authority_sha256':file_sha256(authority),
            'input':str(source),'input_sha256':file_sha256(source),'pages':pages,
            'scope':'正文保真：自动接受断行及明确中文排版空格；图形箭头、装饰、填空横线及原图文字凭同页证据登记显示映射；计划内有原稿依据的转换错误可还原。字词、数字、答案、含义标点及英文/公式空格保持。输入与成品独立按授权清单核验，不回写输入；图片字与阅读顺序仍需实际图片审阅，不据XML宣称通过。'}
