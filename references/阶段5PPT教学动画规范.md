# 可编辑文字字体排版修订（保留阶段5内部目录） · 1.3.38

本文件保留本地文字字体修复详细合同。新动画已整体切换《PPT动画轻量规范》，不再按旧阶段5动画长计划执行。完整衔接、修订命令与审阅字段见[可编辑后续一体化规范](可编辑后续一体化规范.md)；用户提示词统一见assets/templates/可编辑优化与教学动画提示词.txt。基础三步、目录命名及人工PDF转换保持，Canva保存后由当前连接器自动导出下载。

## 修改边界

**专项以最终输入PPTX为保全基准，正文内容保持；有明确原稿依据的转换错误允许自动还原。** 已授权可编辑文字优化按[可编辑文字优化规范](可编辑文字优化规范.md)执行，可轻微调整字体、粗细、字号、颜色、间距、断行和文本框位置尺寸，主控连续修复并统一验收，无需逐句或逐页再确认。字词、数字、答案和影响含义的标点仍保护；英文/公式空格不全局清洗。纯动画或原窄范围字体请求保留原严格限制，阶段1正文母版和基础配套不改。

默认纯动画只改p:timing。用户请求优化可编辑文字/排版时用editable inspect --optimize-text，字体兼容与原版相近匹配纳入同次授权；否则按原--repair-fonts/--match-reference-fonts范围执行。基础项目转换对照先自动接受正文相同的断行和明确中文排版空格；其他正常显示差异由主控登记同页证据映射。明确转换错误可在text_optimizations计划登记原稿还原后继续；无法确定的正文差异列pending_text_issues并保持受影响页原样且不新增动画，其余安全页继续，不把待办当通过。

Canva导出可能将完整句子拆成段落、用空格对齐、将箭头或填空横线保留为图形，或把原插画中的独立问号转为文本。主控实际对照原版同页图片及当前输入后台预览，确认显示等价后登记，不因这些正常差异要求用户改课件或再确认。用`record-animation-text-mapping --run-dir <项目> --input-pptx <文件> --review <JSON>`保存`_state/阶段5/editable_text_mapping_review.json`，然后重新核验。JSON含controller_reviewed、review_evidence、input_sha256、stage1_content_sha256及pages；每个差异页含slide_index、observation、reference_visual/export_visual及各自_sha256、units和decorations。units逐项覆盖批准正文按换行拆出的单位（authority_unit_index、expected_text、reason）；sources逐个写实际段落index/text，排版空格仅通过remove_spaces列明字符位置，跨段joins仅允许空串或显式已审阅箭头（graphic_connectors_reviewed=true）。decorations仅能登记原版同位置的独立问号/感叹号/勾号，写index/text/reason和original_decoration_confirmed=true。每个实际段落恰好使用一次；除明确登记的图形占位范围外，重组后须逐字等于批准文字。主控负责视觉判断，脚本只核对合同。禁止全局删除空格/标点、按字符计数放行、忽略新增文案或改课件来凑通过；输入、正文或图片变化后须重新审阅。

图形填空横线沿用unit.graphic_spans的fill_line精确范围合同；图片中的原版文字使用retained_text。无需转成可编辑字符，不补写、不遮盖；仍逐项核对原版与当前同页画面，全部实际可编辑正文恰好消费一次。

有效显示映射按输入、批准正文和同页图片指纹复用，不重复视觉逐句对照。新文字优化的输入/成品检查允许计划内排版与有依据的原稿还原，并独立核对其余实际正文；纯动画及旧窄范围任务保留逐字保护。证据变化只复核受影响部分。

原窄范围字体修复保留compatibility和reference_match模式及其独立授权语义。已授权文字优化的--optimize-text同时覆盖两者，不要求重复授权；仍从真实本机常见非会员字体中选择相近候选，不全稿替换。

**两种模式都从本机已安装、完整覆盖待修文字的常见非会员字体中选相近字体，不再固定替换成微软雅黑。** 微软雅黑、黑体、宋体、楷体、仿宋、幼圆、等线及已安装的思源/Noto CJK等是候选；具体允许家族以执行器COMMON_FONT_FAMILIES为准，禁用苹方、付费/会员专用及未知自定义字体。系统常见字体供本机使用，Skill不打包或上传字体文件；开源候选来源见[思源黑体](https://github.com/adobe-fonts/source-han-sans)、[Noto CJK](https://github.com/notofonts/noto-cjk)。本机可用不等于另一台电脑或Canva导入后可用，换电脑须重新检查。

主控按同页原版的笔画、圆润程度、字面宽度、粗细与标题/正文层级比较候选，不由名字或宽度数值自动判相似。先用长标题、密集正文、特殊符号等代表页试修，在临时副本后台渲染，实际看图后记录样本证据。按异常整句话或完整标题处理，正常其他文字保留；禁止全稿替换或只修几个字留下混用。原本的装饰/手写风格不因特殊被视为异常；字体名称、bold元数据只作线索，正文不自动加粗。

内部保存原稿快照，保留未列入优化清单的内容、格式、媒体、背景、页序和切换。已授权文字优化允许受影响文字和文本框的轻微呈现调整；不用拆框、覆盖图片或重建页面修文字。仅字体兼容或纯动画任务仍保留字号、间距、颜色、位置和尺寸；原跨框整句字体修复合同保留。

显示映射的remove_spaces仍只用于匹配，不回写输入；基础项目reference_visual绑定原版同页图，export_visual绑定当前输入后台同页渲染。graphic_spans可用retained_text登记原版和当前均完整显示的模块序号或其他图片文字，写精确文字范围、两图确认与visual_location；不能凭声明忽略真实缺字，具体见可编辑文字优化规范。

### 字体清单契约

plan顶层`font_repairs`为清单。单对象项记录实际`page`、`shape_id`、完整单元`unit_kind`（sentence/title）、`start`/`end`、逐字相同的`text`、`whole_unit_confirmed=true`、`boundary_reason`、`single_font_intent_evidence`、`reason`、`bold`（明确布尔）、`bold_reason`、`visual_evidence`（真实本地预览或详细观察记录）。新计划明确`mode`（compatibility/reference_match）、`target_font`（所选常见字体）、`candidate_fonts`、`non_premium=true`、`font_file`（本机实际已安装文件绝对路径）、`font_face_index`（集合索引，默认0）、`font_match_reason`、`sample_review_evidence`（已查看试修页面/观察记录）；两种模式均必需`reference_visual`，与原版同页实际比较，基础项目绑定阶段2同页图。字体文件、样本、原版与诊断证据在登记和执行时绑定指纹；执行器核查常见家族、安装位置、字体内部家族名及完整字形覆盖。历史未标mode的窄范围微软雅黑计划保留原执行语义，不用于生成新的相近字体计划。

跨框项沿用上述证据/字体字段，将顶层shape_id/start/end/bold/bold_reason改为segments及mapping_reason。segments按主控实际看图确认的阅读顺序列出同页至少两个不同文本对象，每段仅含shape_id/start/end/text/bold/bold_reason；整组text须逐字等于各源范围原样串接，不插字、不删空格、不改变换行。中间段须覆盖完整对象，首尾范围只能在完整语义外边界截取；标题组覆盖每个完整标题对象。整组只用一种选定字体，每段粗体按原有标签/正文层级分别判断，不自动加粗正文；组内正常其他句子的原字体保留。所有段验证成功后在临时成品一次应用并整体核验，失败不交付半组修复文件。

### Canva字体交接

editable inspect自动读取项目内各Canva任务的font_handoff.json，核对正文和同页视觉指纹，在`_state/阶段5/font_handoff_import.json`记录页码、完整文字、候选PPTX对象及是否有歧义。记录候选不是确认映射；用户未授权原版匹配时只留待办，不执行该类替换。

启用原版匹配后，plan需`font_handoff_resolutions`逐项覆盖全部handoff_id，status为replace/no_change/blocked，并写reason。replace/no_change需实际page、shape_id（单对象）或按实际阅读顺序排列的shape_ids（跨框组）、mapping_reason与visual_evidence；replace对应带同handoff_id的一条font_repairs或一组完整text_optimizations（run_format.font_family），两条路径不重复执行，完整文字及对象组顺序一致；no_change说明导出后已合格且不执行修复。能完整定位的跨框文字使用segments组继续，不要求用户合框。重复标题、图中文字或其他不能可靠定位的情况记blocked及页面manual_issues，不按Canva对象ID猜测。修订结果后台页面审阅通过后生成`font_handoff_results.json`，明确仅修复PPTX、Canva在线设计未改变。正文、参考图、交接文件、PPTX或字体文件变化均需重新定位与审阅，不能复用旧映射或写成已通过。

偏移是源对象完整文字中的Unicode字符索引，左闭右开；段落之间为`\n`，显式软换行为`\v`，视觉自动换行不新增字符。标题覆盖完整标题对象；句子不切入语义内部，脚本边界保护不能代替主控整句判断。多句同run可以在原框内分run，正常句子的原字体及全部属性保留。所有计划以当前源文本定位，不以替换后文本回推。


## 执行与验收

新修订使用editable inspect/previews/plan/apply/previews-output/review。本文历史字段中的plan/阶段5指内部修订合同，不要求新动画填写。文字和字体清单、输入/输出/字体/原版证据指纹、正文独立核验与XML属性允许清单保留；检查最终保存的实际页面、字形、层级、断行、溢出、遮挡及原版比较。仅修订不写动画，不为了审阅修订强制渲染已有动画全部点击状态。

有明确原稿依据才还原转换错误；无法确定的正文页保持原样并列pending_text_issues，其他安全页继续，后续动画排除待办页。缺环境不虚构诊断或看图，实际失败与已知问题不能冒称缺环境。后台运行、不前台打开Office/WPS或放映。

修订完成以后重新animation inspect，默认按外部轻量规则添加动画。已有动画按外部reject/任务复用/明确限定替换规则处理。最终文件和原稿历史收拢严格沿用交付文件命名规范。
