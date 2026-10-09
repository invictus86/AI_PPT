"""Compare editable visible text with the sole stage1 per-page text authority."""
from pathlib import Path
from collections import Counter
import re
from zipfile import ZipFile
from lxml import etree
from .json_io import read_json
from .file_hashing import file_sha256
from .validation import ValidationError
from .teaching_animation import slide_parts


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
            'scope':'可编辑文字逐字核对；XML对象存储顺序不同可按完全相同的段落及出现次数匹配。视觉阅读顺序、图片内烘焙字及外部图表文字仍需实际图片审阅，不据XML宣称这些项目通过。'}
