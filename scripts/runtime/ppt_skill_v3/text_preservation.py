"""Separate strict input/output text preservation from stage1 display equivalence."""
from pathlib import Path
from collections import Counter
import re
from zipfile import ZipFile
from lxml import etree
from .json_io import read_json
from .file_hashing import file_sha256
from .validation import ValidationError
from .teaching_animation import slide_parts


def verify_source_text_unchanged(source, output):
    """Check literal text and explicit breaks independently of font run splits.

    No normalization: source spaces, punctuation, numbers, fields and paragraphs
    stay exact. Full package comparison separately protects geometry and media.
    """
    parts = slide_parts(source)
    if parts != slide_parts(output):
        raise ValidationError('字体/动画修复改变了原稿页序')
    a = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    def units(data):
        tree = etree.fromstring(data)
        return [''.join('\v' if n.tag == a+'br' else (n.text or '')
                        for n in p.iter() if n.tag in {a+'t', a+'br'}) for p in tree.iter(a+'p')]
    with ZipFile(source) as before, ZipFile(output) as after:
        for page, part in enumerate(parts, 1):
            if units(before.read(part)) != units(after.read(part)):
                raise ValidationError(f'第{page}页原稿文字、空格、标点或显式换行发生变化')
    return {'verified': True, 'literal_source_text_unchanged': True,
            'source_sha256': file_sha256(source), 'output_sha256': file_sha256(output),
            'pages_checked': len(parts), 'normalization': 'none'}


def verify_stage1_text(root, input_pptx, *, mapping_document=None):
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
    with ZipFile(source) as package:
        for slide,part in zip(slides,parts):
            tree=etree.fromstring(package.read(part))
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
                if Counter(actual_units) != Counter(expected_units):
                    from .text_mapping_review import load_mapping_review, check_mapped_page
                    if mapping is None:
                        mapping = load_mapping_review(root, source, authority, mapping_document)
                    candidates = [p for p in mapping['pages'] if p['slide_index'] == slide['slide_index']] if mapping else []
                    if len(candidates) != 1:
                        raise ValidationError(f"第{slide['slide_index']}页文字与阶段1不一致；停止字体/动画后续，不自动改写正文")
                    check_mapped_page(candidates[0], actual_units, expected_units)
                    match_method = 'controller_reviewed_display_mapping'
                else:
                    match_method = 'exact_paragraph_units_independent_of_shape_storage_order'
            pages.append({'slide_index':slide['slide_index'],'editable_text_matches_stage1':True,'match_method':match_method})
    return {'status':'editable_text_matches_stage1','authority':str(authority),'authority_sha256':file_sha256(authority),
            'input':str(source),'input_sha256':file_sha256(source),'pages':pages,
            'scope':'阶段1与导出PPTX的转换对照；可编辑文字精确匹配，正常分段、排版空格、图形箭头、装饰及填空横线可凭原版和当前同页图片登记显示等价映射。图形横线不要求成为可编辑文字，不回写输入；专项保全基准是最终输入PPTX，输入与成品仍独立逐字检查且不归一化。视觉阅读顺序、图片内烘焙字及外部图表文字仍需实际图片审阅，不据XML宣称这些项目通过。'}
