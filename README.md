# AI_PPT · PPT Skill v3

两台 Windows 电脑可修改、同步的精品班会与家长会 PPT Skill。

本仓库根目录是 Skill 主体。使用时将仓库放在工作区的 `.skill/` 中，输入资料和 PPT 输出放在工作区的对应目录。

- 制作流程：[SKILL.md](SKILL.md)
- 安装、便携使用、双向同步及版本管理：[唯一维护说明](docs/维护说明.md)
- 版本记录：[CHANGELOG.md](CHANGELOG.md)

私用便携包自带 Python、脚本依赖、Git、Poppler 和已有生图配置。解压后双击“开始使用”，在 Codex 中打开生成的 PPT 工作区。便携包包含凭据，仅在自己的电脑之间传输；本公开仓库只保存源码。

修改前后双击 `scripts/双向同步.cmd`。本机修改会先保存为提交，再合并远端并上传；同一处有冲突时停止并保留双方提交。使用 Word/PPT 后台验证需本机已有 Microsoft Word 和 PowerPoint，Canva 需各自账号连接器授权。
