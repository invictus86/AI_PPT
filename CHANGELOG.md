# Changelog

## 1.3.8 - 2026-10-09

- 明确动画/字体专项正文不可改写，修复前后与原版批准文字及同页画面核对；新增独立输入/成品逐页原文检查，字、数字、标点、空格与显式换行必须完全一致，正常文字和版式仍由整包差异核验保护。
- 显示映射允许按精确位置登记全角缩进，仅用于匹配，不回写PPTX；基础项目的参考须为原版同页图片，导出证据须属于当前输入的同页后台渲染。计划、执行及最终后台验收再次核对批准正文和证据指纹，真实错漏字不放行。
- 字体修复支持跨文本框完整句子/标题的segments组；按明确阅读顺序覆盖所有范围，同字体、分段视觉判断粗体，不拆框、不合框、不遮挡、不改变文字。Canva交接支持对应shape_ids组，缺字字段、范围遗漏/重叠、未知或会员字体仍阻断。
- 两种新字体修复模式都需原版同页参考；最终全页状态新增原版文字/字形/排版对照观察。针对跨框保真、错误正文/范围/字重、映射证据及完整后台验收进行回归；合成测试不冒充实际课件或目标播放器验收。

## 1.3.7 - 2026-10-09

- 修正Canva导出拆行、排版空格、图形箭头和原版装饰符号触发文字误判的问题。默认逐字检查保留；差异页必须逐项登记完整文字映射、精确段落及空格位置，绑定批准正文、PPTX和已实际审阅的原版/导出同页图片。
- 新命令record-animation-text-mapping；入口、计划和执行复核映射及证据指纹，不全局去空格/标点，不按字符数量放行，不修改PPTX正文或基础content.json。错字、漏字、数字/标点变化、额外正文、重复消费及证据变化仍阻断。
- 验证入口：文字映射守卫回归、既有逐字保真回归、完整unittest及Skill quick_validate；合成图片仅用于合同测试，不冒充真实视觉审阅。

## 1.3.6 - 2026-10-09

- Canva字体族能力不足时登记完整字体交接清单，保存含封面页码、完整文字、原版及保存后插件预览指纹，待办不冒称已修复。阶段5自动导入并按PPTX实际对象重新定位，歧义/拆分/烘焙文字明确阻断，在线Canva设计不回写。
- 阶段5分compatibility与经单独授权的reference_match两种模式；兼容修复也改为常见相近非会员字体，不固定微软雅黑。新增本机候选查询、常见家族白名单、真实安装/家族/完整字形覆盖校验、字体文件及试修/原版证据指纹，保留整句/完整标题和禁止全稿替换边界。
- 新命令record-canva-font-handoff、list-font-candidates；inspect-animation新增--match-reference-fonts。交接逐项replace/no_change/blocked，全状态后台验收后单独记录PPTX结果；原有窄范围微软雅黑计划不自动扩大授权。
- 验证入口：字体与交接契约回归、完整unittest、JSON schema、skill-creator quick_validate、inspect-installation、发布包范围核对。合成测试不冒充真实课件或目标播放器视觉验收。

## 1.3.5 - 2026-10-08

- 新建项目从原始主题文件夹继承明确编号、前导零及分隔形式；对话中指定的编号优先，年份/日期/页码/素材号及资料类型目录号不作为主题编号，无可靠依据不编造。
- 编号仅用于项目目录管理；移除阶段2/3交付文件名和阶段4主题子目录自动附加项目编号的行为，主题兜底也去掉目录管理编号。批准封面主题与已有交付文件名保持原样。
- 已有项目目录重命名须经用户授权并同步当前路径记录，不重新生成课件、不重置授权或验收。
- 验证入口：编号目录与纯主题交付命名回归、完整 unittest 回归、skill-creator quick_validate、inspect-installation。结构回归不代表课件内容或播放器视觉验收。

## 1.3.4 - 2026-10-08

- 双向同步在合并远端后再次核对跟踪文件范围和本机生图密钥，检查通过后才继续依赖检查与上传，防止未经同步入口提交的非发布文件进入下一次自动上传。
- 首次便携交付固定本机库路径，隔离用户级 Python 包；发布包绑定当前 Git 提交，私用凭据附件不进入公开代码与版本标签。

## 1.3.3 - 2026-10-08

- 增加 Windows 便携运行与 GitHub 双向源码同步：本机修改先提交，再合并远端并上传；源码与历史在同步前备份，同处冲突保留双方提交并停止，不强推、不自动舍弃修改。
- 私用便携包携带独立 Python、运行依赖、Git、Poppler 与已有生图配置；本机 `_local/`、凭据和输入输出不进入公开仓库或普通 Skill 发布包。
- 增加锁定依赖清单、双击入口及本机环境检查；PPT 制作阶段、模型、质量门槛和业务授权边界保持原口径。
- GitHub 仓库主体即 `.skill/`；克隆和更新保持工作区外壳独立。安装状态块由双向同步剔除机器时间差异，实质维护文字仍纳入版本管理。

## 1.3.2 - 2026-10-07

- 修复Canva默认字体粗细限制覆盖用户明确修订范围的问题：新增authorize-canva-repair登记真实授权，支持按批准正文修复转换错字、标点以及格式/位置/尺寸，不改写教学内容或基础配套。
- 插件仅返回图片链接时继续参考驱动修订与直接保存，readback_only明确verified=false；不下载图片绕过展示限制、不切Computer Use、不伪造视觉通过。文字回读失败、已知错误及保存失败仍须处理。
- 批次提交校验最新回读审计，不要求修复前草稿先通过；保留无文本层的原图页明确未文字核验。授权范围、正文指纹、真实交易终态和同设计租约持续保护。
- 维护与测试记录见docs/current/2026-10-07_1.3.2_canva；Skill调用名、包名和schema id不变，历史授权不自动扩大。

## 1.3.1 - 2026-10-07

- 对齐四封面独立媒介/质感规范，所有生图文字必须来自阶段1本页final_visible_text；页码不再按页序自动生成，画面计划不得另加文字。
- 正式请求强制high、无损PNG及原清晰度/比例合同，阻止参数/环境变量/请求包降质；保留实际整页QA。
- PDF手动转可编辑、Canva和动画不改文字；新增可编辑文字逐页核对，Canva仅改已授权字体/粗细，旧文字参考变化阻断；基础配套正文保留。
- 按用户要求缺环境不验证：只读探测依赖、保存未验证记录并允许其他步骤继续；已有环境仍验证，已发现问题/执行失败仍阻断。动画结构/包保真仍核验，不伪造视觉通过。
- 明确HTTP拒绝可同路线重试；超时未知及返回损坏仍先核对证据，每次失败独立计量。新增原Canva失败交易真实终态证据恢复，不伪造取消批次。
- 慢预览与点击状态先核对revision，再发布manifest和state；过期窗口不能覆盖新清单。生图仍每batch/run最多6，多窗口独立、不设账号队列或全局生图互斥。

验证记录在docs/current/2026-10-07_1.3.1；本次测试不使用付费生图、不启动前台Office/WPS，未声称验证真实生图质量或WPS播放器兼容。旧课件/输入保留，Skill调用名、包名和schema id不变。

## 1.3.0 - 2026-10-06

- 保留原三步流程、整步授权与两个用户暂停节点、content.json唯一正文、固定gpt-image-2.5/high、基础交付、手动可编辑转换、Canva5页及全部动画点击状态验收。
- 统一旧生图路线/OCR/候选风格冲突；四封面按候选独立媒介、质感或视觉表达继承，选择后才统一内页。新增生成前文字/关系/情境检查、整页修复副作用QA及图片完整解码。
- 生图保持原规则：单个batch/run最多6并发，多窗口独立批次不共享额度，不增加全局生图互斥、账号许可池或共享限流退避。跨进程保护项目写状态、输出预留和Office后台操作；state revision防止旧窗口覆盖。Canva同设计持久租约随commit/cancel收口，失败/未知不自动释放。
- 相同批次重派保留结果，同逻辑生图请求在途去重，返回逐个持久化并登记；结果未知先核对，不盲目重复付费。原高质量参数与正式路线保持。
- 后台预览缓存绑定来源、实现、字体/Office环境和实际图片指纹；后台Word真实排版＋PDF全页审阅增加配套质量门禁，不增加用户审批。Office异常清理不明时阻断，无前台或WPS别名回退。
- 新增source/record_id去重计量，Codex/API/人工/runtime分别记录，缓存包含在输入、未知不填0、并行/嵌套时间不重复相加。恢复摘要增加版本、revision和源SHA，减少重复上下文。

验证入口：`python -m unittest discover -s .skill/tests -v`、skill-creator `quick_validate.py .skill`、runtime compileall、JSON Schema自检、`inspect-installation`及新CLI帮助。多进程使用模拟API，无付费生图；真实后台样本证据单独保存在docs/current及本机审计目录，排除发布包。旧项目及已交付课件不自动重写；未验证WPS后台适配器不声称支持。

本文件记录 PPT Skill 的仓库发布版本。稳定调用名仍是 `ppt-skill-v3`，runtime package 仍是 `ppt_skill_v3`；这里的版本号只用于同步、发布和变更说明。

历史条目只记录当时版本事实。若旧条目与最新版本口径冲突，以最高版本条目、`.skill/SKILL.md` 和正式 references 为准。

## 1.2.5 - 2026-10-04

- 全流程后台执行：原PPTX预览复用隐藏窗口渲染器，不打开前台Office/WPS或放映，不抢焦点；嵌入字体临时加载并卸载，串行渲染。声明字体名与内部字体名不一致时，仅在渲染副本使用原字形别名，正式字体不改。
- 教学动画直接写入OOXML；解析最终成品时间轴生成全部点击状态包，不依赖PowerPoint写动画或前台截图。支持完整对象短淡入，复杂/交互/音视频效果明确阻断。
- 新增extract-ppt-background、render-ppt-background、export-animation-states、record-animation-background-review；验收绑定原稿预览、成品、计划、manifest及全部状态图片，强制检查答案、残影、字体与排版，核对隐藏窗口与全量导出证据。支持范围和目标播放器实测分开记录。
- 删除旧Office动画写入和预览脚本；旧状态不自动迁移，不修改已交付PPTX。

验证：65项回归；真实3页原稿后台导出，9状态复现并拦截插画底图残影，修正方案6状态全部审阅通过，3页最终画面与原稿逐像素一致，doctor通过。结构测试不等于任意播放器实测；过程证据保存在docs/current/background_validation_1_2_5，发布包排除该目录。

## 1.2.4 - 2026-10-03

- 按用户要求，正式生图强制限定为中转 API 的 `gpt-image-2.5`，禁止其他模型/分组；不可用或失败时停止并报告，只可在同一分组内检查或重试，不得自行启用备用中转站或内置生图路线。
- 配置加载、批次预检、请求准备及发送参数校验拒绝非许可模型；命令行 `--model` 只接受 `gpt-image-2.5`。环境变量、项目请求包和直接构造配置都不能绕过限制。
- 同步入口、核心不变量、生图证据链及封面规范；已有项目与历史成功/失败证据保持原值。

验收命令：模型限制回归、`unittest discover`、runtime compileall、skill-creator quick_validate、`inspect-installation`。回归不调用付费生图服务。

## 1.2.3 - 2026-10-03

- 教学动画新增经授权的字体兼容检查与修复：仅处理真实显示异常所在整句话或完整标题，统一用微软雅黑；按实际笔画粗细与文字层级决定加粗，正常文字保留原字体。不做全稿替换或单独缺字替换。
- `inspect-animation --repair-fonts`启用该范围；计划保存全部页字体观察与整句修复清单，实际视觉证据绑定指纹。明确纯动画任务仍禁止字体变更。
- 在原XML上执行清单内字体/粗体修复，允许内部run分割以保留同框正常句子；差异核验只允许计划timing和清单字体/粗体，保留所有其他内容与属性。大文件指纹改为流式计算。
- 新增`record-animation-font-review`；全页字体显示/排版与真实放映分别登记，两者均通过才完成。记录实际检查应用，不将PowerPoint检查冒充WPS验收。
- 同步阶段5规范、入口、核心不变量与标准用户提示词；不修改已交付PPTX、不迁移旧项目状态。版本名、包名、输出位置和递增命名不变。

验收命令：`python -X utf8 -m unittest discover -s .skill/tests -v`、runtime compileall、skill-creator quick_validate、`inspect-installation`。字体回归覆盖跨run整句、跨软换行、同框正常句子保留、非字体差异拒绝、证据漂移与双核验门禁；技术测试不替代目标应用实际显示检查。

## 1.2.2 - 2026-10-02

- 按用户要求，将新动画成品后缀由`_教学动画版.pptx`改为`_可编辑动画版.pptx`，同步Skill、正式规范、执行脚本和回归用例。
- 同目录保存和同名版本保留规则继续生效；冲突时递增为`_可编辑动画版_v2.pptx`、`_v3.pptx`。已有成品不自动重命名。

验收命令：`python -m unittest discover -s .skill/tests -v`、`python -X utf8 <skill-creator>/scripts/quick_validate.py .skill`、runtime compileall。

## 1.2.1 - 2026-10-02

- 教学动画成品直接保存到实际输入PPTX同目录，命名为`<原名>_教学动画版.pptx`；已有同名成品保留，后续递增`_v2`、`_v3`。
- 独立动画项目初始化与动画执行均不再创建`阶段5_PPT教学动画/`；预览、计划和验收证据仍保存在项目内部`_state/阶段5/`。
- 保留`stage5_animation`状态与只合并timing、实际放映验收规则；已有项目、旧成品和目录不自动搬迁或删除。

验收命令：`python -m unittest discover -s .skill/tests -v`、runtime compileall、inspect-installation、skill-creator quick_validate。回归覆盖独立项目初始化、输入位于项目外的同目录输出、同名版本保留、带timing合并的基础完成项目输出及状态/核验路径一致性。

## 1.2.0 - 2026-10-02

面向精品主题班会与家长会深度增强二创升级，稳定Skill name和runtime包名不变。

- 三步基础流程：资料+规划+四封面、前5页试样、全稿+真实验收+配套+整理；用户授权、实际确认与主控验收分别入账。
- 当前目标与来源分开，四项常改输入保留；通用版一套，配套提供少量年级替代活动。
- 规划、实际全稿和配套新增内容深度审阅与指纹校验；教育价值靠主控判断，不采用字数/关键词评分。
- 班会必交班会教案，家长会专门生成会议实施方案；逐字稿口播、操作、可能回应及年级替代分开，页码标题与母版一致。
- 基础产物保持图片版PDF和Word/PDF，转换PPTX仍由用户手动。Canva在转换之后、动画之前。
- 独立stage5动画：真实页序/对象映射、已有动画保留或实际替换、仅合并timing、非动画包差异核验；实际放映验收独立。
- 按用户要求不维护旧项目兼容或自动迁移。旧用户项目与参考动画项目未修改。

验证命令：compileall、unittest discover、inspect-installation、quick_validate、schema自检和严格白名单打包。合成样稿验证三学段两场景配套渲染；动画用真实PowerPoint合成副本验证，不将技术回归等同实际授课效果。

## 1.1.0 - 2026-09-18

本次将当前工作区已完成的阶段1/2、资料登记和国际版 Canva 辅助编辑改造合并为正式发布版本；稳定调用名仍是 `ppt-skill-v3`，runtime package 仍是 `ppt_skill_v3`。

新增与调整：

- 阶段1以 `content.json` 作为正文权威来源，同步规划、逐页稿和提示词简报；图片请求按页冻结、结果保留不可变 SHA 证据，活动 work packet 改为轻量指针。
- `drift-check` 按具体动作收窄检查范围，`resume-brief`、`next-action` 和漂移检查默认即时返回，只有显式 `--persist` 才写控制快照。
- 资料登记同时维护项目内部归档与 `输入资料/<项目名>/` 用户入口副本，并在索引和资料清单中保留两条路径。
- 国际版 Canva 辅助编辑建立宿主/执行器、页级权威文案与视觉审计、敏感值拒绝记录和阶段外状态边界；允许范围内默认每批 5 页，经主控回读通过后直接提交。

兼容与发布边界：

- 历史项目、旧 task schema、旧派生材料和历史成功记录保持只读兼容；不自动迁移、删除或改写用户项目。
- GitHub 与发布包只纳入入口、正式规范、模板、runtime、schema、维护说明和 changelog；测试、过程文档、`输入资料/`、`PPT输出/`、构建产物及本机开发目录不随发布提交。

验收：

- 运行安装检查、模板/K12 校验、全量单测、runtime 编译、Skill 快检与发布包 manifest 审计。

## 1.0.12 - 2026-09-18

本次按最新执行口径收紧 Canva 批次策略：允许范围内的 Canva 辅助编辑默认 5 页一批，AI 主控回读文案与预览通过后直接提交，不等待用户确认。

调整：

- 正式 Canva 规范将“每批默认 3 到 5 页，复杂页 1 到 2 页”改为“每批默认 5 页，最后不足 5 页按剩余页处理”。
- 复杂页不再自动拆成 1 到 2 页，也不因此引入用户确认门禁；工具限制、预览异常、回读失败或视觉未闭环时仍必须 cancel。
- 新建 task 的 `commit_policy` 新增 `default_batch_page_count=5`，workflow 同步提示默认 5 页一批并直接提交。
- Skill 入口、维护说明、agent 默认提示和本地任务卡同步为默认 5 页批次策略。

验收：

- `test_canva_task.py` 增加默认批次页数断言。
- 本次不触碰真实 Canva 设计、不写项目阶段 state。

## 1.0.11 - 2026-09-18

本次补充国际版 Canva 辅助编辑的 AI 主控口径：逐页文案与视觉校验不是纯机械字段检查，而是由主控理解页面角色、权威文案和阶段2视觉意图后，再留下可回读证据并提交允许范围内的修订。

调整：

- 正式 Canva 规范改为“AI 主控的逐页文案与视觉校验”，明确 `page_audit.json` 是主控判断后的证据，不替代主控的页面理解和审美判断。
- 每页视觉校验要求结合页面角色、信息重点和阶段2参考，说明为什么已贴近参考或为什么只能转人工。
- Skill 入口、阶段流程、维护说明、agent 默认提示和新建 task brief workflow 均同步为“AI 主控判断 + runtime 证据门禁”。
- 直接 commit、`pre_authorized`、controller-reviewed preview、文案回读、视觉闭环、人工待办范围和阶段外边界保持不变。

验收：

- 本次仅收口规范与 brief 语义，不触碰真实 Canva 设计、不写项目阶段 state。
- 相关验证命令见当前任务卡 TC-08 与 TC-06 回写。

## 1.0.10 - 2026-09-18

本次把国际版 Canva 双宿主辅助编辑收敛为可由 AI 实际执行和验证的页级合同。WorkBuddy 仍使用 Canva MCP，Codex 仍使用 Canva 插件；两者在允许范围内均不再等待用户逐批确认，而是在 AI 回读通过后直接提交。

调整：

- 每页审计强制记录权威文字、修改前文字、修改后回读文字、发现项、拟执行操作和逐项视觉检查；通过的 `post_edit_text` 必须与同页 `content.json.final_visible_text` 精确一致。
- 视觉检查逐项覆盖文字角色与层级、字号、粗细、颜色、对齐、行高、列表、位置、尺寸、溢出、遮挡、断行；未闭环的 `needs_edit`/`blocked` 禁止 commit。
- 新建 task 升为 schema v1.2，写入 `direct_commit_after_controller_qa`；新批次在控制器审核预览、页级文案和视觉校验通过后，以 `pre_authorized` 直接 commit，保存后必须重新只读回读。
- schema v1.1 的确认式记录保持只读兼容；新 v1.2 task 不允许进入 `waiting_batch_confirmation`，也不允许将 `confirmed` 作为新提交授权。
- 直接提交没有放宽边界：Magic Layers、字体族、背景、复杂图形、增删内容/页面、换图和主动重排仍由人工处理，Canva 导出稿仍须用户确认才可作为阶段3外部锁定稿。

验收：

- `test_canva_task.py` 覆盖未审核预览、文案回读不匹配、未闭环视觉项、旧确认式授权与 v1.2 直接授权边界。
- 完整安装、模板、单测、编译、Skill 快检、打包和包内容检查命令见本次任务卡的 TC-06 回写。

## 1.0.9 - 2026-09-18

本次在不改变“内容确认 → 4 张封面 → 封面确认 → 5 页试样 → 试样确认 → 剩余页 → 最终 PDF 确认 → Stage 3 全格式 → Stage 4 整理交付”流程的前提下，收紧事实来源并去除内部重复写入。

调整：

- `content.json` 成为 Stage 1 正文唯一权威来源；页面规划、逐页稿和 prompt brief 的文字字段按来源摘要同步，旧项目保持兼容读取。
- 4 封面、5 页试样和内部生图登记使用动作相关严格检查，不扫描无关的后续阶段；最终 PDF、Stage 3/4 收口、手动 doctor 与异常恢复仍完整检查。
- Stage 2 成图按 SHA 保存一份不可变内部证据图，页面入口优先硬链接；冻结请求、提供方证据、正式结果和轻量尝试记录各自只保存本职事实，停止新写 `result_receipts`。
- 每个 batch 仅保留一份当前权威 manifest；提示词 Markdown 只在封面、试样、剩余页完成和显式刷新/导出时完整重建。
- 完整 work packet 仍归档，活动文件改为轻指针；`resume-brief`、`next-action`、`drift-check` 默认即时返回，只有 `--persist` 才保存控制快照。
- 外部锁定稿进入 Stage 3 时要求存在、声明 SHA 匹配和明确确认依据；标准路线仍必须先确认 Stage 2 图片版 PDF，外部模式不伪造 Stage 2 确认。

兼容：

- 旧 Stage 1 派生材料、完整活动包、控制快照、batch history 和提示词台账继续只读兼容；不自动迁移、删除或压缩真实项目。

验收：

- 全量单测 `274/274` 通过。
- `inspect-installation`、风格模板、K12 模板、runtime 编译、Skill 快检、打包全部通过。
- 已生成 `.skill/dist/ppt-skill-v3.zip` 与 manifest；过程文档和测试仍不进入发布包。

## 1.0.8 - 2026-09-18

本次完成国际版 Canva 双宿主阶段外辅助编辑收口：WorkBuddy 使用已授权的 Canva MCP，Codex 使用 Canva 插件；两者共享逐页权威文案校验、小批预览、用户确认与 commit/cancel 纪律。

调整：

- `/canva`、`/可画` 均固定表示国际版 Canva；runtime task v1.1 显式记录 provider、宿主和执行器，不再从 profile 猜测 MCP 可用性。
- 新增逐页审计、批次状态机、人工待办投影和受限导出记录；批次必须从 `draft` 收口，commit 必须记录“预览已展示 + 用户确认”。
- 恢复摘要以只读 sidecar 展示 Canva 任务、执行器、最后批次和人工待办，不影响项目阶段、next action 或 decision。
- 记录拒绝 token、签名 URL 和本机路径；`manual_handoff` 被明确标为 connector 阻断，不能冒充编辑完成。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 -m compileall -q .skill/scripts/runtime/ppt_skill_v3`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`

真实 WorkBuddy MCP 与 Codex 插件事务仍需在用户指定的非生产国际版 Canva 设计上分别完成“审计 -> 预览 -> 用户确认 -> commit”验收；该外部验收不由本地单测替代。

## 1.0.7 - 2026-09-18

本次精准收口阶段2独立生图提示词：每份新请求固定使用“画面文字、页面设计、视觉风格、关键约束”四段。AI 主控负责按页选择、归并和表达PPT版式一致性与图片风格继承，runtime 不再把上游自然语言规则重新扩写进 prompt。

调整：

- `image_prompt_plan` 保持既有字段和来源摘要，但登记时不再自动追加 `PPT一致性.md`、共享组件、安全区或风格禁用项。
- `current_plan` 保留正文、来源摘要和冻结请求的确定性校验，不再要求上游每条自然语言规则逐条出现在计划中。
- 编译器将文字角色、版式规则、构图和页码自然归入 `【页面设计】`，将图片继承归入 `【视觉风格】`，将文字边界与本页高风险问题归入 `【关键约束】`。
- 正式规范与阶段1模板明确：页面设计继承PPT版式，视觉风格继承图片表现；不增加字数、规则数量或视觉质量硬门禁。
- 提示词格式版本升为3；待发送的旧格式请求须由主控重新整理并派发，历史成功提示词和图片保持不变。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `python3 -m compileall -q .skill/scripts/runtime/ppt_skill_v3`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`

## 1.0.6 - 2026-09-13

本次完成阶段2提示词按页编译与普通页标题改造：解决 `PPT一致性.md` 整章注入、普通页默认带章节标签、跨页映射进入 prompt、Markdown 残留和重复禁用项稀释本页重点的问题。

调整：

- 普通内容页默认只使用页面标题组件，不自动生成章节标签、眉题或模块导航条。
- `PPT一致性.md` 解析改为按页过滤：普通页、模块页、封面、目录、结束页和页码范围例外只返回当前页有效规则。
- 新增提示词规则清洗工具，统一处理 Markdown 标记、文档说明、跨页映射、未启用章节标签、未绑定 `chapter_tag` 安全区和同义禁用项归并。
- `image_prompt_plan` 只注入当前页有效规则；`current_plan` 改为语义类别覆盖校验，不再要求一致性原文逐条存在。
- final prompt 跨字段使用语义 key 去重，避免照片/3D、未批准文字、温暖积极等要求重复输出。
- doctor 增加新待发 prompt 污染检查；旧成功提示词文档仅 warning，不自动改写历史证据。
- 正式规范和阶段1模板同步：章节标签必须显式 opt-in；没有章节标签不再被 QA 误判为缺失。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `python3 -m compileall -q .skill/scripts/runtime/ppt_skill_v3`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`
- `python3 .skill/scripts/package_skill.py --output-dir .skill/dist`

## 1.0.5 - 2026-09-12

本次是 GitHub 发布后的维护入口精简：去掉重复维护文档，只保留一个用户和维护者都能看懂的维护说明。

调整：

- 将 `docs/维护规划.md` 的发布边界、GitHub 上传边界和维护原则合并进 `docs/维护说明.md`。
- 删除 `docs/维护规划.md`，正式包只保留 `docs/维护说明.md` 一个维护入口。
- 打包白名单改为只允许 `docs/维护说明.md` 进入包，继续排除测试、过程文档、归档文档、输入输出和 dist 产物。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`
- `PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 .skill/scripts/package_skill.py --output-dir .skill/dist`

## 1.0.4 - 2026-09-12

本次是 GitHub 同步前的发布打包收口，重点处理普通用户包的边界和维护入口。

调整：

- 新增 `docs/维护规划.md`，作为 GitHub 和分发包中的发布维护规划入口。
- 打包白名单补充 `docs/维护规划.md`，并继续排除 `tests/`、`docs/current/`、`docs/archive/`、`输入资料/`、`PPT输出/`、旧 `inputs/outputs/tmp`、缓存和 zip。
- 更新 package 测试，明确维护说明和维护规划都进入包，过程文档和测试不进入包。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`
- `PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 .skill/scripts/package_skill.py --output-dir .skill/dist`

## 1.0.3 - 2026-09-12

本次完成深度体检后的当前口径收敛：让 AI 主控保留判断权，runtime 只做确定性检查，并清理旧入口、旧说明文件和重复 reference。

调整：

- 阶段2A封面候选不再被正式全量图片结果缺失提前硬拦；完整图片版 PDF 确认阶段仍要求正式图片、PDF、hash 和 manifest 证据。
- 删除 `/文件整理`、`/整理` 作为用户快捷指令入口；`organize-deliverables` 保留为阶段4内部整理动作。
- 不再恢复或要求 `封面风格选择说明.md`、`阶段2_确认说明.md`、`讲稿生成说明.md`、`教案生成说明.md`。
- K12 教案 schema/runtime 降低机械质量门槛，只硬查结构、路径、manifest、文件和安全事实；教学质量交回主控判断。
- `视觉系统统一规范.md`、`阶段2审美QA规范.md` 和 `版本与兼容说明.md` 已合并进对应正式文档后移除。
- 阶段2提示词、图片风格、封面候选和生图证据链重新串联到 `PPT一致性.md` 与 `图片风格.md` 的当前项目来源。
- 中转站默认 base URL 对齐为 `http://direct-api.cangyuansuanli.cn/`，并补充 `direct-api` / `cangyuan` 路线别名。
- Canva 规范保留为唯一阶段外辅助编辑文档；风格模板规范只负责模板触发、注册和维护。
- 删除无引用的通用用户确认说明模板，并把阶段1总览模板改为“不是额外确认文件”的辅助模板。
- `make-decision` 生成的 `allowed_actions` 改用当前 CLI/drift 动作名；历史图片记录动作名和旧 packets 动作名只作为兼容别名识别。

验收：

- `python3 .skill/scripts/pptctl.py inspect-installation`
- `python3 .skill/scripts/pptctl.py validate-style-templates`
- `python3 .skill/scripts/pptctl.py validate-k12-subject-profiles`
- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .skill`
- `PYTHONPATH=.skill/scripts/runtime:.skill/tests python3 -m unittest discover -s .skill/tests -v`
- `python3 .skill/scripts/package_skill.py --output-dir .skill/dist`

## 1.0.2 - 2026-09-12

阶段2所有新请求统一使用主控整理的图片风格与画面计划。移除尺寸和流程说明，保留批准正文、独立参数及实际宽高/比例验收。

- 新增读取来源和登记画面计划命令；封面、5页试样、全量及返工使用同一编译器。
- 当前风格、完整禁用项和适用页面组件进入计划；标题/章节文字显式引用批准正文，页码单独控制。
- 新请求在提交前复核来源、版本及实际提示词；旧成功记录和在途请求保留原文，失败请求不进入用户文档。
- 编辑图片的本地输入与提示词一起冻结；修复编辑端点成功结果无法登记、来源编辑中导致在途结果无法回收的问题。
- 实际图片增加16:9比例检查，默认相对容差2%，与像素尺寸检查独立；不拉伸、不裁切原图。
- 参考说明保留在代码块外，修正重复“借鉴”文案；提示词文档支持成功记录重建和附件导出。
- 正文区只含批准原文，标题/章节用途在正文区外按段引用，避免用途标签被画入图片。
- 修复合法已决策返工被旧依据检查阻断；未授权过期、缺图与hash损坏仍阻断。

## 1.0.1 - 2026-09-12

本次把阶段2默认生图路线切换为苍原国内直连中转站，并补齐 OpenAI-compatible 生成请求与证据链。

调整：

- 新项目阶段2A封面候选、阶段2B试样和剩余整页图片默认走 `openai_image_api`。
- 默认中转配置统一为 `http://direct-api.cangyuansuanli.cn/`、`/v1/images/generations`、`gpt-image-2.5`、`1672x941`、`response_format=b64_json`。
- `run-image-api-batch` 支持 `--response-format`，packet、dry-run、batch report 和 API evidence 均记录响应格式。
- URL 图片下载失败会给出明确 HTTP 状态，避免把 provider URL 403 误判为普通生成失败。
- `make-decision` 阶段2默认生图决策会同时写入 `basis/execution.image_generation_route=openai_image_api`，并自动开放 `run_image_api_batch`。
- 主控决策校验会阻断中转 API 路线缺少 `run_image_api_batch`、官方 `codex_image_gen` 路线误写 `run_image_api_batch` 等路线和动作不一致问题。
- 新 `/v1/images/generations` 正式结果必须记录 `response_format`；旧 Grsai `/v1/draw/completions` 历史结果可继续读取。
- API 主请求连接失败、无效 `b64_json` 和 provider URL 下载网络错误会抛出更明确的 `ValidationError`。
- `codex_image_gen` 保留为显式备用路线；旧 Grsai `/v1/draw/completions` 解析能力只作为 legacy 兼容保留。

## 1.0.0 - 2026-09-12

本次确立 PPT Skill v3 的正式 1.0.0 版本口径，并进入目录隔离、Codex/WorkBuddy 双主体适配和跨平台中文路径兼容的落地改造阶段。

规划：

- 根目录目标收敛为入口文档、`输入资料/`、`PPT输出/` 和 `.skill/` 四项。
- Skill 主体后续迁入 `.skill/`，项目输入和输出明确放在 Skill 外部。
- Codex 形态使用根入口 `AGENTS.md`；WorkBuddy 形态使用根入口 `CODEBUDDY.md`。
- 新项目输出目标调整为 `PPT输出/<中文项目名>/`，不再嵌套 `projects`。
- `.skill/docs/维护说明.md` 将记录当前主体、版本号、安装方式、路径规则和 Windows/macOS 中文兼容检查。

兼容性：

- 稳定 Skill 调用名仍是 `ppt-skill-v3`，Python package 名仍是 `ppt_skill_v3`。
- 旧 `outputs/projects` 项目路径仅作为历史项目恢复和迁移线索，不作为新项目正式路径。
- 当前条目只确立版本和实施任务卡，目录迁移与 runtime 改造需按任务卡分阶段落地。

## 0.4.0 - 2026-09-12

本次重构阶段模型：旧可编辑 PPT 路线移出正式流程，阶段3改为逐字稿与 K12 教案输出，阶段4改为文件整理交付。

调整：

- 正式阶段骨架改为：阶段0资料整理 -> 阶段1规划确认 -> 阶段2图片版 PPT -> 阶段3逐字稿与教案输出 -> 阶段4文件整理交付。
- `build-speaker-script`、`build-lesson-plan-context`、`build-lesson-plan` 和 `record-lesson-plan-qa` 改为阶段3能力，输出到 `阶段3_逐字稿与教案输出/` 和 `_state/阶段3/`。
- `/文件整理` / `organize-deliverables` 改为阶段4整理交付，只复制已存在的阶段1、阶段2、阶段3交付物，并继续将已存在的逐字稿 PDF、教案 PDF 用 `pdftoppm` 导出 `216 DPI / 3x_72dpi` PNG 图片副本。
- `pptctl --help` 不再暴露旧可编辑 PPT、坐标复刻、OfficeCLI 坐标构建、阶段3去字背景生成和阶段3视觉 QA 命令。
- 正式图片生成 runtime 只支持阶段2；旧 `stage3-background` / `stage3_background` 去字背景路线会被显式拒绝。
- `image_result.schema.json` 收窄为阶段2图片结果 schema，旧 stage3 background image result 不再是正式结果类型。
- 正式打包排除旧可编辑 runtime 模块和旧 schema，减少误调用和包体积。

兼容性：

- 稳定 Skill 调用名仍是 `ppt-skill-v3`，Python package 名仍是 `ppt_skill_v3`。
- 历史项目中的旧 stage4 逐字稿/教案字段、旧 `stage3_editable_deck` basis 和旧目录只作为 legacy 读取线索保留；新项目、新文档、新命令不再把它们作为正式路线。
- `/canva`、`/可画` 仍是阶段外辅助编辑，不替代阶段3输出，也不自动推进阶段。

## 0.3.1 - 2026-09-12

本次增强 `/文件整理` 交付目录：阶段4逐字稿 PDF 和 K12 教案设计 PDF 会在整理时额外导出高清 PNG 图片副本。

新增：

- 新增 `pdf_page_images.py`，使用 Poppler `pdftoppm` 将已存在 PDF 渲染为 `216 DPI / 3x_72dpi` PNG。
- `/文件整理` 主题目录新增 `逐字稿图片/page_*.png` 和 `教案设计图片/page_*.png`。
- `organize-deliverables` JSON 摘要新增 `rendered`，记录导出页数、DPI、scale、图片尺寸、sha256 和工具路径。

调整：

- `/文件整理` 仍是被动整理入口，不写 decision，不推进阶段，不修改确认状态；PDF 图片只是已存在 PDF 的确定性派生交付副本。
- 默认只使用 `pdftoppm`，不使用备用渲染器；找不到工具、PDF 损坏或渲染失败时，只跳过对应图片导出，其他交付物继续整理。
- 支持 `PPT_SKILL_PDFTOPPM` 指定可执行文件，或 `PPT_SKILL_POPPLER_PATH` 指定 Poppler bin 目录，兼容 macOS、Linux 和 Windows `pdftoppm.exe`。

## 0.3.0 - 2026-09-02

本次新增 K12 阶段4教案设计能力，并进一步收敛为 AI 主控写作、runtime 只做确定性渲染和底线检查。

新增：

- 新增 K12 教案设计规范：只服务小学、初中、高中课件项目，非 K12 项目仍只输出阶段4演讲逐字稿。
- 新增 `education_context` 轻量教育上下文，用于记录可确认的学段、年级、学科、课题、教材线索和课时策略。
- 新增 K12 学科 profile registry，覆盖语文、数学、英语、物理、化学、生物、科学、政治/道德与法治、历史、地理、美术/艺术、信息科技、劳动、体育与健康。
- 新增阶段4教案生成命令：`build-lesson-plan-context`、`build-lesson-plan`、`record-lesson-plan-qa`。
- 新增 `validate-k12-subject-profiles` 命令，用于校验 K12 学科 profile 配置。
- 新增教案设计 Markdown、Word、PDF 三件套和 `lesson_plan_manifest.json` 入账路线。

调整：

- 阶段4可在 K12 项目中同时输出演讲逐字稿和教案设计；`stage4_script_completed` 保持兼容命名，但对 K12 项目同时代表教案三件套已完成。
- 教案内容质量由主控模型判断，runtime/doctor 只检查 K12 条件、材料追溯、文件存在、hash、PDF 可读性、教师可见文本清洁、实验安全等硬问题。
- 教案不以页数定质量；PDF 页数只记录排版结果，不触发低页数提示、warning 或完成判断。内容偏薄时由主控自然扩写教学分析、教学过程、任务评价、作业、板书和反思。
- 教学过程收敛为教师可读五列表：环节、教师活动、学生活动、任务与评价、设计意图/二次备课；时间、PPT 页码和材料来源不作为固定可见列。
- 板书设计和教学方案规范增强，强调课堂任务链、关键提问、追问纠偏、学生产出、评价证据、知识结构、问题链和方法链。
- 阶段4讲稿生成说明去工程化，减少 runtime、manifest、内部决策名等教师或用户不需要看到的表达。

兼容性：

- 不改稳定 Skill 调用名 `ppt-skill-v3`。
- 不改 Python package 名 `ppt_skill_v3`。
- 旧项目没有 `education_context` 时仍可恢复；K12 判断只在有明确学段、年级、学科、课题、教材等信号时触发。
- 在当时的阶段4模型中，`stage4_lesson_plan_required` 保留为兼容读取别名，新写入优先使用 `stage4_outputs.lesson_plan.required`；0.4.0 起新写入已迁到 `stage3_outputs.lesson_plan.required`。
- `docs/`、`tests/`、`outputs/` 仍按 `.gitignore` 作为本地开发、验收和项目产物目录，不进入公开 Skill 包。

验收：

- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .`
- `python3 scripts/pptctl.py validate-style-templates`
- `python3 scripts/pptctl.py validate-k12-subject-profiles`
- `PYTHONPATH=scripts/runtime python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q scripts/runtime/ppt_skill_v3`
- `git diff --check`

## 0.2.0 - 2026-08-26

本次是轻量化路由与 Canva 辅助编辑更新。

新增：

- 新增 `/canva`、`/可画` 阶段外 Canva 辅助编辑入口：导入或手动上传 PPT/PDF，用户手动 Magic Layers，回传 Canva 链接后由 Codex 使用 Canva 插件批量修正文案和样式。
- 新增 `create-canva-task-brief` runtime 命令，用于在具体 PPT 项目中生成 Canva 辅助编辑任务 brief，不修改阶段状态。
- 新增 drift-check 大类动作：`stage1_plan`、`stage2_image`、`stage3_editable`、`stage4_script`、`canva_auxiliary`，降低 Agent 选择 action 名的负担。
- 新增 controller decision schema 与 runtime 决策枚举同步测试，防止决策类型漂移。

调整：

- `SKILL.md` 增加更短的路线判断：默认四阶段、Canva 辅助、明确跳过才直接改文件、继续/确认/返工先恢复项目状态。
- 明确阶段2用户确认过的封面和试样页默认复用，不为正式全套图片重复生成。
- 明确阶段3正式路线仍是 OfficeCLI；Canva/Magic Layers 结果只作为阶段外辅助或阶段4外部锁稿来源，不自动算阶段3完成。
- 旧 Canva 浏览器自动点击 `AI图层` 路线改为 Legacy，只在用户明确要求浏览器控制时使用。
- 阶段0资料入口增加轻量判断：普通参考资料先登记来源和用途，只有需要完整提取、复刻、仿写或改造成 PPT 时才进入完整公众号资料包链路。
- `docs/current/` 口径收敛为开发规划入口，正式执行规则仍以 `SKILL.md` 和 `references/` 为准。

修复：

- 修正主控决策协议中的旧动作名 `call_editable_ppt_provider`，统一为 `build_officecli_coordinate_deck`。
- 补齐 `controller_decision.schema.json` 中缺失的 `reopen_stage3_sample_after_stage4`。

兼容性：

- 不改稳定 Skill 调用名 `ppt-skill-v3`。
- 不改 Python package 名 `ppt_skill_v3`。
- 不改现有项目目录结构或已存在项目状态字段。
- 不新增 Canva 作为阶段3正式 provider。

验收：

- `python3 /Users/yinxinhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py .`
- `PYTHONPATH=scripts/runtime python3 -m unittest discover -s tests`
- `python3 scripts/pptctl.py validate-style-templates`

## 0.1.0 - 2026-08-20

初始 GitHub 发布版本，包含中文 PPT 四阶段主控流程、阶段2图片版 PPT、阶段3 OfficeCLI 可编辑 PPT、阶段4演讲稿输出、恢复摘要、drift-check、work packet 和基础打包能力。
