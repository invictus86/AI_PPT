# Canva文字校对与精准修复 · 1.3.27

在原有Canva五页批次内使用，不新增用户入口、阶段或确认节点。保留字体、视觉、保存回读和失败恢复合同。`check-canva-text`只是读取本地输入并返回诊断/操作JSON，不调用Canva、不保存设计、不写阶段1。

## 两条校对线

1. **转换比对**：以阶段1批准文字为准，定位错字、乱码、漏字、多字、重复识别、标点及数字单位变化。正常分段、换行和明确中文排版空格沿用原容差；英文词间空格、数字、答案和含义标点仍保护。
2. **语言审阅**：主控实际逐句阅读全部批准文字，结合本课语境检查同音/形近字、词语搭配、重复词、明显病句及标点。人名、专业术语、名言和引文须核对来源，不能凭常见写法改名词。程序中的少量常见词形只提示候选，不是通用纠错器，未命中不能证明无错。错误例句、引文原貌等可保留，写明排除理由。

原稿疑误记为`source_issues`，含原文、位置、建议、分类与理由，始终`auto_repair=false`。即使Canva与原稿完全相同，也要单列语言疑误；不得自动更新content.json、逐字稿或提示词。含疑误的文字单位不生成自动替换，避免把Canva中已正确的字改回原稿错字。其他有依据的文字单位可以继续；汇报分开说明“已还原转换错误”和“原稿疑误待核实”，不把保存成功说成原稿语言全对。

## 实际对象与定位

先读取当前页面文本对象，用批准文字单位到实际对象片段的映射表达阅读关系，不按API存储顺序猜。一个批准单位可对应多对象，一个对象也可对应多个批准单位；片段不得重叠。未归属文字会报告，不能静默忽略整句遗漏、额外段落或重复文字。对象ID必须来自当前交易，下面示例ID不能用于真实设计。

`start/end`为纯文字中的Unicode字符位置，左闭右开，不是API的UTF-16索引。片段直接取实际回读文本，不重写成期望文字。缺失整框可用空segments报告，不能借此新建文本框。图形箭头与图片文字例外沿用原copy_check；存在时将已审阅的copy_check一并传入，继续绑定原版和当前预览证据，不补写覆盖文字。

输入示意：
```json
{
  "slide_index":1,
  "canva_page_id":"实际页面ID",
  "mapping_reviewed":true,
  "objects":[{"element_id":"实际对象ID","text":"认直学习"}],
  "mappings":[{"unit_index":0,"segments":[{"element_id":"实际对象ID","start":0,"end":4}]}],
  "language_review":{
    "controller_reviewed":true,
    "reviewed_unit_indices":[0],
    "review_evidence":"实际逐句审阅及必要来源核对的观察，不能照抄示例",
    "issues":[]
  }
}
```

`unit_index`是本页final_visible_text的0起始索引。语言疑误issues每项写unit_index/start/end/current_text/suggested_text/category/reason；category可为typo、wording、repeated_word、punctuation、number、unit、name、term、quote。current_text须精确对应批准原文。dismissed_hints每项写unit_index/start/end/reason，仅排除实际出现的候选。没有完成实际语言审阅时不填true；可先省略language_review取得差异和词形线索，审阅后再生成报告。

在现有项目/task内调用：
```bash
python .skill/scripts/pptctl.py check-canva-text --run-dir <项目> --task-id <任务> --input <实际回读与审阅JSON> --mode inspect
```

结果包含原稿疑误、逐字差异、对象ID、对象内位置、上下文和精准替换候选。报告保留在当前任务内即可；只传筛选后的纯文本和定位，不复制完整MCP richtext/fill载荷，不记录签名URL或交易ID。

## 精准修复与回读

执行前，将上一步真实报告作为`report`，当前再次回读的全部文字对象作为`live_objects`，并带slide_index，调用同一命令`--mode prepare`。只有已有文字修复授权且允许find_and_replace_text时返回可派发操作；这不是新增授权，主控按用户本次文字修复原话在原authorize-canva-repair范围中登记该操作，窄范围字体请求不扩大。

操作绑定实际对象ID，在对象内扩展最小必要上下文直到唯一匹配。同对象的多处修改合成一个一致的操作，保留中间正常文字。实际对象文字变化、零/多匹配、跨对象或不连续片段不能可靠定位时重新读取和判断，不盲替换、不全设计查找替换、不改正常对象。原稿疑误不会作为替换目标。

AI只把prepare返回的操作交给当前可用Canva工具，仍遵守工具能力与实际提交约束。随后再次读取全部文字对象，以同样的report/live_objects/slide_index调用`--mode verify`：核对修改对象达到原稿目标、未修改对象未被误伤、没有额外或缺少的文字对象。该核验基于实际工具回读，不得把计划结果当作live_objects。

新建任务的文字修复批次在原page_audit内保留`text_proofreading`报告；提交记录还保留`text_repair_readback={controller_readback_confirmed:true,objects:[实际回读]}`。原copy_check、视觉审阅及保存后回读仍完整执行。无文字层且未修改的原图页保持原例外。旧任务不自动迁移；旧字体等窄范围合同保持。

失败后核实远端已保存时，恢复证据增加`text_repair_readbacks`列表，每项含slide_index/controller_readback_confirmed/objects，用真正重新读取的对象核验。不能以“保存过”或旧草稿通过精准修复核验；原失败记录与设计保护规则不改。
