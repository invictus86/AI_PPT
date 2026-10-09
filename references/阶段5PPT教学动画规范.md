# 阶段5：PPT教学动画与常见相近字体修复 · 1.3.10

用户明确请求并提供最终可编辑PPTX才启动。基础交付之后由用户手动转换，可选Canva修改；专项不重跑阶段0—4，不撤销基础完成事实。单独PPTX用`init --animation-only`；已有项目使用独立`stage5_animation`。

全程遵守[后台执行与验收规范](后台执行与验收规范.md)：不前台打开Office/WPS、不启动放映、不抢焦点。

## 修改边界

**专项以最终输入PPTX为保全基准，正文内容保持；有明确原稿依据的转换错误允许自动还原。** 已授权可编辑文字优化按[可编辑文字优化规范](可编辑文字优化规范.md)执行，可轻微调整字体、粗细、字号、颜色、间距、断行和文本框位置尺寸，主控连续修复并统一验收，无需逐句或逐页再确认。字词、数字、答案和影响含义的标点仍保护；英文/公式空格不全局清洗。纯动画或原窄范围字体请求保留原严格限制，阶段1正文母版和基础配套不改。

默认纯动画只改p:timing。用户请求优化可编辑文字/排版时用inspect-animation --optimize-text，字体兼容与原版相近匹配纳入同次授权；否则按原--repair-fonts/--match-reference-fonts范围执行。基础项目转换对照先自动接受正文相同的断行和明确中文排版空格；其他正常显示差异由主控登记同页证据映射。明确转换错误可在text_optimizations计划登记原稿还原后继续；无法确定的正文差异列pending_text_issues并保持受影响页原样且不新增动画，其余安全页继续，不把待办当通过。

Canva导出可能将完整句子拆成段落、用空格对齐、将箭头或填空横线保留为图形，或把原插画中的独立问号转为文本。主控实际对照原版同页图片及当前输入后台预览，确认显示等价后登记，不因这些正常差异要求用户改课件或再确认。用`record-animation-text-mapping --run-dir <项目> --input-pptx <文件> --review <JSON>`保存`_state/阶段5/editable_text_mapping_review.json`，然后重新核验。JSON含controller_reviewed、review_evidence、input_sha256、stage1_content_sha256及pages；每个差异页含slide_index、observation、reference_visual/export_visual及各自_sha256、units和decorations。units逐项覆盖批准正文按换行拆出的单位（authority_unit_index、expected_text、reason）；sources逐个写实际段落index/text，排版空格仅通过remove_spaces列明字符位置，跨段joins仅允许空串或显式已审阅箭头（graphic_connectors_reviewed=true）。decorations仅能登记原版同位置的独立问号/感叹号/勾号，写index/text/reason和original_decoration_confirmed=true。每个实际段落恰好使用一次；除明确登记的图形占位范围外，重组后须逐字等于批准文字。主控负责视觉判断，脚本只核对合同。禁止全局删除空格/标点、按字符计数放行、忽略新增文案或改课件来凑通过；输入、正文或图片变化后须重新审阅。

图形填空横线沿用unit.graphic_spans的fill_line精确范围合同；图片中的原版文字使用retained_text。无需转成可编辑字符，不补写、不遮盖；仍逐项核对原版与当前同页画面，全部实际可编辑正文恰好消费一次。

有效显示映射按输入、批准正文和同页图片指纹复用，不重复视觉逐句对照。新文字优化的输入/成品检查允许计划内排版与有依据的原稿还原，并独立核对其余实际正文；纯动画及旧窄范围任务保留逐字保护。证据变化只复核受影响部分。

原窄范围字体修复保留compatibility和reference_match模式及其独立授权语义。已授权文字优化的--optimize-text同时覆盖两者，不要求重复授权；仍从真实本机常见非会员字体中选择相近候选，不全稿替换。

**两种模式都从本机已安装、完整覆盖待修文字的常见非会员字体中选相近字体，不再固定替换成微软雅黑。** 微软雅黑、黑体、宋体、楷体、仿宋、幼圆、等线及已安装的思源/Noto CJK等是候选；具体允许家族以执行器COMMON_FONT_FAMILIES为准，禁用苹方、付费/会员专用及未知自定义字体。系统常见字体供本机使用，Skill不打包或上传字体文件；开源候选来源见[思源黑体](https://github.com/adobe-fonts/source-han-sans)、[Noto CJK](https://github.com/notofonts/noto-cjk)。本机可用不等于另一台电脑或Canva导入后可用，换电脑须重新检查。

主控按同页原版的笔画、圆润程度、字面宽度、粗细与标题/正文层级比较候选，不由名字或宽度数值自动判相似。先用长标题、密集正文、特殊符号等代表页试修，在临时副本后台渲染，实际看图后记录样本证据。按异常整句话或完整标题处理，正常其他文字保留；禁止全稿替换或只修几个字留下混用。原本的装饰/手写风格不因特殊被视为异常；字体名称、bold元数据只作线索，正文不自动加粗。

保留原文件及未列入优化清单的内容、格式、媒体、背景、页序和切换。已授权文字优化允许受影响文字和文本框的轻微呈现调整；不用拆框、覆盖图片或重建页面修文字。仅字体兼容或纯动画任务仍保留字号、间距、颜色、位置和尺寸；原跨框整句字体修复合同保留。

显示映射的remove_spaces仍只用于匹配，不回写输入；基础项目reference_visual绑定原版同页图，export_visual绑定当前输入后台同页渲染。graphic_spans可用retained_text登记原版和当前均完整显示的模块序号或其他图片文字，写精确文字范围、两图确认与visual_location；不能凭声明忽略真实缺字，具体见可编辑文字优化规范。

成品直接保存到实际输入PPTX父目录：`<原名>_可编辑动画版.pptx`，同名递增`_v2`、`_v3`，不覆盖旧文件，不创建用户可见阶段5文件夹。所有预览、计划、差异和验收证据在项目内部`_state/阶段5/`。

## 检查与计划

1. `inspect-animation --run-dir <项目绝对路径> --input-pptx <文件> --evidence <真实授权原话> [--repair-fonts]`保存实际presentation页序、顶层对象/组合、嵌套文字、原文字片段属性及已有动画。随后`export-animation-previews`后台导出全部页面并绑定输入/图片指纹。主控实际逐页看图，不能用XML或关键词代替视觉诊断。
2. 字体诊断结合后台原稿预览及嵌入字体字形、原对象字体及可取得的字体缺字证据。`list-font-candidates --text-file <待修完整文字UTF-8文件>`只读列出本机常见非会员候选、文件/集合索引、字形覆盖、字重和文字宽度，不自动选字体。候选须实际存在、已安装、家族匹配且覆盖整段中文/标点/数字；换电脑不能复用旧font_file指纹。缺字体、缺字、错误回退、局部粗细突变为线索；未能确认时保留并列问题。所选字体不可用、替换后溢出/遮挡或仍异常时尝试其他已审阅候选；没有合格候选则阻断相应修复，已授权文字优化可先尝试小幅调整文本框、间距或字号改善显示；窄范围字体任务仍不改这些属性。不将后台渲染通过写成PowerPoint/WPS实际播放兼容通过。
3. 每页动画plan写`teaching_reason`、`initial_state`、`final_state`、`manual_issues`、`effects`和`replace_targets`。按教学任务逐步揭示提问、分析、例证、结论和方法；同组同步，标题背景装饰默认静态，默认0.45秒淡入。不逐字播放、不凑数量、不新增切换；零效果写理由。effect包含真实`shape/shape_id`、`role/reason`、`trigger`（click/with_previous）、`click_group`、`duration`及`separable=true`。
4. 已有动画默认保留，不重复叠加。确需调整的顶层对象列`replace_targets`并提供新效果；仅支持可完整解析的整对象淡入，按原点击顺序保留其他对象并追加新组；不能空删除。复杂/交互/退出/运动/分段动画、音视频或未知依赖为阻断，不能近似后通过。题干答案同框、底图答案、不可独立控制组合列`manual_issues`，不拆、不遮、不重建。
5. plan绑定`input_sha256`、`controller_reviewed=true`及实际`preview_review_evidence`，覆盖全部页。字体修复启用时还需总`font_review_evidence`及每页`font_observation`，正常页也说明检查结果；环境具备时`font_repairs=[]`表示检查后无须修复，不表示跳过检查；缺环境时保存未验证原因并保持字体，不能填写虚构font_observation。未解决`manual_issues`不能执行。每页还需`content_roles_reviewed=true`及`visibility_rules`，逐个记录题目/答案对象与实际reveal_click，不能由关键词自动放行。

### 字体清单契约

plan顶层`font_repairs`为清单。单对象项记录实际`page`、`shape_id`、完整单元`unit_kind`（sentence/title）、`start`/`end`、逐字相同的`text`、`whole_unit_confirmed=true`、`boundary_reason`、`single_font_intent_evidence`、`reason`、`bold`（明确布尔）、`bold_reason`、`visual_evidence`（真实本地预览或详细观察记录）。新计划明确`mode`（compatibility/reference_match）、`target_font`（所选常见字体）、`candidate_fonts`、`non_premium=true`、`font_file`（本机实际已安装文件绝对路径）、`font_face_index`（集合索引，默认0）、`font_match_reason`、`sample_review_evidence`（已查看试修页面/观察记录）；两种模式均必需`reference_visual`，与原版同页实际比较，基础项目绑定阶段2同页图。字体文件、样本、原版与诊断证据在登记和执行时绑定指纹；执行器核查常见家族、安装位置、字体内部家族名及完整字形覆盖。历史未标mode的窄范围微软雅黑计划保留原执行语义，不用于生成新的相近字体计划。

跨框项沿用上述证据/字体字段，将顶层shape_id/start/end/bold/bold_reason改为segments及mapping_reason。segments按主控实际看图确认的阅读顺序列出同页至少两个不同文本对象，每段仅含shape_id/start/end/text/bold/bold_reason；整组text须逐字等于各源范围原样串接，不插字、不删空格、不改变换行。中间段须覆盖完整对象，首尾范围只能在完整语义外边界截取；标题组覆盖每个完整标题对象。整组只用一种选定字体，每段粗体按原有标签/正文层级分别判断，不自动加粗正文；组内正常其他句子的原字体保留。所有段验证成功后在临时成品一次应用并整体核验，失败不交付半组修复文件。

### Canva字体交接

inspect-animation自动读取项目内各Canva任务的font_handoff.json，核对正文和同页视觉指纹，在`_state/阶段5/font_handoff_import.json`记录页码、完整文字、候选PPTX对象及是否有歧义。记录候选不是确认映射；用户未授权原版匹配时只留待办，不执行该类替换。

启用原版匹配后，plan需`font_handoff_resolutions`逐项覆盖全部handoff_id，status为replace/no_change/blocked，并写reason。replace/no_change需实际page、shape_id（单对象）或按实际阅读顺序排列的shape_ids（跨框组）、mapping_reason与visual_evidence；replace对应带同handoff_id的一条font_repairs或一组完整text_optimizations（run_format.font_family），两条路径不重复执行，完整文字及对象组顺序一致；no_change说明导出后已合格且不执行修复。能完整定位的跨框文字使用segments组继续，不要求用户合框。重复标题、图中文字或其他不能可靠定位的情况记blocked及页面manual_issues，不按Canva对象ID猜测。全状态后台验收通过后生成`font_handoff_results.json`，明确仅修复PPTX、Canva在线设计未改变。正文、参考图、交接文件、PPTX或字体文件变化均需重新定位与审阅，不能复用旧映射或写成已通过。

偏移是源对象完整文字中的Unicode字符索引，左闭右开；段落之间为`\n`，显式软换行为`\v`，视觉自动换行不新增字符。标题覆盖完整标题对象；句子不切入语义内部，脚本边界保护不能代替主控整句判断。多句同run可以在原框内分run，正常句子的原字体及全部属性保留。所有计划以当前源文本定位，不以替换后文本回推。

## 执行与三个核验

`record-animation-plan --plan <文件>`后`apply-teaching-animation`。直接写入源包副本的p:timing；字体按授权清单准确修复，不调用Office写动画。失败标failed，基础完成事实保持。

1. **文件差异核验**：只允许计划内timing、原font_repairs及新text_optimizations声明属性/原稿还原；正文独立检查与XML属性允许清单分别执行，未授权文字、媒体、背景、对象身份及其余包文件变化仍拒绝。纯动画和窄范围字体任务保留原严格检查。
2. **成品时间轴核验**：读取最终成品的完整时间树，核对对象、触发、同步组、时长及题目/答案可见性契约。未知语义阻断；支持完整顶层对象短淡入、click及with_previous。
3. **后台逐点击视觉核验**：`export-animation-states`生成每页初始及全部点击完成画面；临时状态PPTX中的未出现对象真实移除，仅用于后台渲染，正式成品不变。主控实际审阅全部图，检查题目/答案顺序、底图残影、图文同步、中文字体、粗细、断行、溢出、遮挡和最终完整性。未做字体/文字呈现调整的页面仍与原稿预览逐像素一致；优化页按实际正文、字形、层级、断行和留白检查，全部状态写text_quality_observation。

主控使用`record-animation-background-review --review <文件>`登记全部状态；输入/输出/计划/manifest/状态图绑定指纹，具体契约见后台规范。method只能为background_click_states。启用字体检查时，此次逐状态审阅包含全页字体和排版，分别保留background_review与font_review；不能只检查修复页。

新字体清单完成后，每一页最终状态还需original_comparison_observation，记录实际与原版同页/输入预览的文字、字形、粗细及排版比较。不能只确认文字数量或记录“看起来正常”；可恢复的映射或跨框差异由主控完成核对并继续，真实内容差异、证据不足、图片文字不可编辑及未解决视觉问题仍不得宣布专项完成。

环境具备时，状态为waiting_background_review直到完整后台审阅通过，无正文待办则completed；存在pending_text_issues时仍为needs_manual_adjustment，报告已完成范围与待办；缺环境按后台规范记录verification_skipped/background_accepted=false并交付已结构核验文件，不伪造审阅通过。不运行前台放映，不能伪称目标播放器实际放映已验证；后台状态只保证支持范围内的初始/点击完成画面和语义顺序。默认不改基础逐字稿；用户要求点击提示时另出对应版本。

## 标准用户提示词

以下文字可直接用于飞书命令词的动画段；它明确同时授权动画与受限字体修复。保留其他基础制作/Canva命令词。

```plaintext
我已提供最终可编辑PPTX，授权教学动画和轻微文字优化，包括字体、粗细、格式排版及Canva字体交接；文字内容保持，有明确原稿依据的转换错误可自行还原。
请读取 PPT Skill 规范，以PPT成品质量为主，连续完成独立教学动画与文字优化。

要求：
1. 实际查看全部页面、对象、文字显示及已有动画，结合页面任务和已有配套资料制定逐页教学动画计划和字体修复清单；默认保留有效动画，只按明确计划新增或调整，不重复叠加。
2. 提问、分析、结论和方法步骤按教学需要逐步揭示，同一教学组同步出现；不需要动画的页面保持静态，不逐字播放、不凑效果数量、不新增页面切换。
3. 不统一替换全稿字体。修复实际确认的字体显示异常，以及明确交接的原版风格差异；从本机可用且覆盖完整文字的常见非会员字体中选择相近字体，不固定改成微软雅黑，不使用付费/会员专用字体。先比较候选并在代表页试修看图。异常句子整句处理，标题按完整标题处理；换行仍属同一句时一并处理，同框正常其他句子保留原字体，不能仅换几个字。故意的装饰、点字或手写风格不能仅因特殊就替换。
4. 是否加粗参考原字体实际笔画粗细、正常邻字及标题/正文层级，不能只看字体名或bold标志，正文不自动加粗。清单记录页码、对象、整句范围、原字体线索、替代字体/粗体、视觉证据和判断原因；不能可靠判断的列为问题。
5. 允许轻微调整受影响文字的字体、粗细、字号、颜色、字距、行距、段距、对齐、缩进及文本框位置尺寸，修复孤字、断行、溢出与遮挡，保持原页面风格和信息层级。正文、数字、单位、答案与结论不改写；有明确原稿依据的转换错误可自行还原并记录。不全稿重排、不动背景、插画、页序和基础配套。
6. 成品直接保存到输入PPTX所在目录，命名为<原名>_可编辑动画版.pptx；同名已存在时递增为<原名>_可编辑动画版_v2.pptx、_v3.pptx，不覆盖已有文件，不创建用户可见的阶段5文件夹。预览、计划及核验记录放在项目内部_state中。
7. 题干与答案同框、烘焙图片、动态字段等对象无法独立揭示或安全修字体时，列出受影响页面和人工调整要求，不拆框、不遮挡、不重建；未解决的阻断项不能作为可完整执行的计划。
8. 全部步骤只通过文件读取、API或后台隐藏文稿渲染执行，不前台打开Office/WPS、不启动放映、不抢焦点。读取成品时间轴并后台渲染每页初始及每次点击完成画面，逐张核对答案显示、背景残影、字体和排版；文件差异只允许计划timing、授权字体和轻微文字优化/原稿还原清单，未支持或未通过项目明确阻断；缺少验证环境则不执行对应视觉/字体检查，列明缺项与未验证范围，结构核验仍做，不编造通过。不将后台结果伪称目标播放器实际播放兼容通过。
9. 本专项单独交付，不重跑阶段0—4，不影响已完成的基础交付。已授权后连续执行，无须逐句再确认；关键阻断如实说明。
10. 自动读取已有Canva字体交接清单，核对页码、完整文字及PPTX实际对象后逐项判断替换、无需修改或阻断。不得沿用Canva对象ID；修复与验收针对PPTX，不记录成Canva在线设计已同步修改。
```
