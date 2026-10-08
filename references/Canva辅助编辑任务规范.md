# Canva辅助编辑任务规范 · 1.3.2

## 路由、范围与授权

/canva、/可画指国际版Canva。Codex使用实际可用Canva插件，WorkBuddy使用已连接的Canva MCP。先确认设计、页数、权限及可编辑对象；已有链接优先使用，不创建替代设计。页面图片由插件/MCP返回的预览读取，允许内存读取或下载后本地读取；禁止使用Computer Use读取、截图或浏览器控制。

用户请求修订并保存即为本次范围内直接提交授权，不再逐批询问。范围由本次原话确定：
- 默认仅授权字体/粗细时，维持仅字体/粗细。
- 用户明确要求错别字、乱码、标点、字号、颜色、元素等修复时，依据原版修复当前工具支持的属性，不以默认范围拒绝已授权工作。
- 页面内容以项目阶段1批准文字为目标。恢复转换误识别属于还原，不能改写、添加新教学结论或覆盖content.json。
- 元素位置/尺寸、文本格式可按同页参考最小修复。整套检查不意味着每页必须改动；有效页面与有效对象保留。
- 没有对应工具能力时不承诺精确字体族、复杂形状、背景、动画、批量Magic Layers或新增文本框。图片内字无独立文本层时保留原图，记录未文字核验，不新增覆盖层伪装修复。

Canva是阶段外任务，不重跑阶段0—4，不重写配套，不设置基础阶段完成位，不登记external_locked_deck。基础交付事实保持。最终导出变化使动画对象映射失效，动画另按阶段5范围执行。

## 权威与逐页记录

项目内读取：
1. _state/阶段1/content.json：每页final_visible_text唯一可见正文。
2. 每页干净逐字稿.md与页面规划.md：标题、段落及页面任务。
3. 阶段2同页PDF/页面图：层级、颜色、粗细、字号关系、图文位置和留白。
4. 当前Canva对象：待修复的文字、坐标与尺寸，不能作为批准正文。

每页建立slide_index与Canva page_id映射，记录expected_text、current_text、差异、操作及回读结果。拆成多个对象或合在一个对象的文字，按实际阅读关系映射；不要把API对象存储顺序当成视觉顺序，不要因换行、合并对象虚报错字。保留正文标点、数字、单位与有意义空格。

修改后再次读文本/对象：
- 文字修复目标必须逐项等于批准文案；current_text可保留修复前转换错误，post_edit_text必须反映实际回读，不能直接复制expected_text伪造结果。
- 非文字属性记录依据与前后值；没有源依据时保留，不凭统一模板重排全稿。
- 已发现文字缺失、溢出、对象错误等仍须解决或明确剩余项；不能使用“未视觉核验”掩盖已知失败。
- 整图页没有文本层时，copy_check.status=verification_skipped、mode=unmodified_image，保存实际保留的对象ID和原因；该页无修改操作，不冒称逐字核验通过。
- 原版箭头由图片对象承载时，保留该对象，mode=retained_artwork；仍须回读全部可编辑文字，editable_text_verified=true、artwork_text_tokens记录箭头字符。只免除箭头像素核验，不能掩盖正文错误。

## 插件预览与持续执行

读取Canva编辑链接时，先通过插件/MCP取得设计和对应页的预览。图片内容块可直接转发；只返回预览URL时，按当前工具能力选择下列任一方式取得实际图像，两种方式读取的是同一来源图片，均可用于视觉审阅：

- 内存读取：用普通HTTP请求获取预览URL的原始图片字节，通过可用工具转成图像块并展示，例如fetch → arrayBuffer → emitImage；不要求插件本身返回image内容块。
- 本地读取：用普通HTTP请求下载同一预览URL的原始图片，保存到项目内部_state/工具任务/canva/<task_id>/previews/，再用view_image等图片读取工具查看，并展示本地预览。

根据工具能力选择可用路径；其中一条不支持时可换另一条，不因只有URL或远程URL不能直接传入图像工具就判定无法看图。两种读取均属于本次Canva预览审阅，无需额外询问下载授权。禁止使用Computer Use、浏览器自动控制或浏览器截图读取页面。

每次get-design-thumbnail都向用户展示对应预览；取得图像后优先展示实际图像，仍只能展示URL时按工具规则使用临时Markdown图片。使用对应设计、页码和当前编辑状态的预览：修改前图不能冒充修改后或保存后结果，过期链接由插件重新获取。内存与本地路径均保留源图片内容，不重绘、压缩或拼接成替代页图；原图对照拼图只作为辅助，不能替代单页审阅。签名URL只在本次读取中临时使用，不写入项目日志；可记录页码、读取方式、实际审阅结果和图片指纹。

区分“插件返回预览”与“主控实际看到像素”：
- 实际可查看图像：逐页目视审阅文字、层级、断行、留白与遮挡，记录reviewed_by_controller。
- 当前可用的内存/本地读取方式均无法取得可查看图像时：展示返回预览，记录preview_status=readback_only和visual_verification.verified=false、实际失败或能力缺项原因，并继续依据批准文案、已查看的本地原版参考和服务端对象数据作确定性修复、回读和保存；不切换Computer Use。
- 只有实际查看对应图片像素并完成逐页审阅，才记录reviewed_by_controller。不把拿到URL、下载成功、输出图像块但未审阅、JSON或几何检查写成目视通过。没有可靠依据的视觉重设计不执行；保留有效元素。
- 权限失败、文本无法回读、预览提示真实错误、交易失效或保存失败是实际阻断，必须处理；这与仅缺少可查看图像不同。

readback_only要求preview_shown=true、readback_confirmed=true、非空reason；未目视检查项记verification_skipped。最终汇报实际保存页码与未目视核验范围，不把“全部处理并保存”写成“全页视觉验收通过”。

## 交易与保存

默认5页一批，最后不足5页按剩余页；相同设计先claim-canva-design，同一时间只有一个编辑交易。不同设计可以并行。每批：
1. 读取当前设计并写本批逐页修复计划。
2. start-editing-transaction，使用返回的实际交易和对象身份。
3. 执行授权范围内、当前工具支持的操作。
4. 逐页回读文字/对象并展示插件预览；按上述规则记录视觉是否实际验证。
5. 依据本次用户“修改并保存”的授权直接commit，不再等待逐批确认。
6. 重新读取保存结果，核对页数、文本和对象；保存成功才记录committed。

校验看本批最新回读审计，不能要求修复前草稿已无错误才能保存。未知交易结果不盲目重试；失效交易先核对远端终态，已取消后重新读取和启动。已保存页不重复修改。不记录transaction ID、token、完整richtext/fill原文或签名URL。

只有工具明确支持的操作才能请求：
- replace_text/find_and_replace_text：恢复有来源的批准文字。
- format_text：字号、颜色、粗细、行高、对齐等实际支持字段；不承诺工具没有的font_family。
- position_element/resize_element：参考驱动的最小位置/尺寸修复。
- 当前插件文本框不支持直接垂直缩放；用真实可用的字号、换行、行高自动撑高。标点修复后检查文字框自动高度，异常换行可按参考水平加宽并回读，不把操作失败冒称成功。
- 换图、增删元素或页面仅在用户明确授权且有独立证据时另行处理；本任务默认不授权这些破坏性重建。

## 记录与确定性命令

创建任务：
```bash
python .skill/scripts/pptctl.py create-canva-task-brief --run-dir <项目> --provider canva_international --host-profile codex --executor canva_plugin
```

明确授权保真修复后登记操作范围：
```bash
python .skill/scripts/pptctl.py authorize-canva-repair --run-dir <项目> --task-id <任务> --evidence <真实用户原话> --operation replace_text --operation format_text --operation position_element --operation resize_element
```

新任务默认仍为stage1_unchanged_fonts_only；上述显式登记改为authorized_reference_repair，不自动扩大旧授权。允许修复前文字与权威不同，修复后必须实际回读为权威文字，阶段1改变仍使旧参考失效。

记录在_state/工具任务/canva/<task_id>/，含task、design_link、reference_text_by_slide、page_audit、batch_edit_log、未处理项。preview_status、visual_verification与copy_check保持真实；runtime只检验合同，不自动判断审美或声称看过图像。draft后登记真实committed/cancelled/failed，正常终态释放同设计租约，failed保留租约待恢复。

failed恢复：
```bash
python .skill/scripts/pptctl.py resolve-canva-recovery --run-dir <项目> --task-id <任务> --evidence <实际证据JSON>
```
须实际核实原design_id及batch_id的commit/cancel，不按超时解锁，不虚构取消。commit恢复同时核验保存回读及允许范围。原failed历史不重写。

## 收口

全部26页等目标页数均已检查，必要修复保存并重新回读，才报告全部处理保存。说明设计链接、页数、实际修复、有效保留页、保存核对及未验证项；不要让少数不支持属性覆盖可完成工作，也不要把人工待办说成已修复。没有实际导出不写导出记录，Canva导出候选稿不自动覆盖基础课件与配套。
