# AI 安全文章手绘配图

六张图用于[文章正文](../../ai-safety.zh-CN.md)，每章一张。用户确认手绘风格后，进一步要求减少图中文字；当前正文使用少字版，仅保留必要的短标签。第四章使用 `v3`，补全了在边界被阻止的底价外发路径，其余为 `v2`。章节标题、结论和解释放在正文或图注中。

这些图片是概念说明，不是产品界面、原始截图或测评证据。第五章画的是示例授权策略，不能据此判断具体产品的默认资源权限，也不能据此确认实测中的拦截机制。

## 图片与生成提示

| 章节 | 图片 | 生成提示 |
| --- | --- | --- |
| 一：能力与保护范围 | [图片](ch01-ai-capabilities-handdrawn-v2.png) | [English prompt](ch01-ai-capabilities-handdrawn-v2.prompt.txt) |
| 二：训练、检测与权限 | [图片](ch02-training-controls-handdrawn-v2.png) | [English prompt](ch02-training-controls-handdrawn-v2.prompt.txt) |
| 三：提示词注入 | [图片](ch03-prompt-injection-handdrawn-v2.png) | [English prompt](ch03-prompt-injection-handdrawn-v2.prompt.txt) |
| 四：内部使用与对外披露 | [图片](ch04-data-boundary-handdrawn-v3.png) | [English prompt](ch04-data-boundary-handdrawn-v3.prompt.txt) |
| 五：执行边界 | [图片](ch05-execution-boundary-handdrawn-v2.png) | [English prompt](ch05-execution-boundary-handdrawn-v2.prompt.txt) |
| 六：实际结果核对 | [图片](ch06-evidence-verification-handdrawn-v2.png) | [English prompt](ch06-evidence-verification-handdrawn-v2.prompt.txt) |

生成日期：2026-11-23。使用内置 ImageGen，以[第三章原始样图](ch03-prompt-injection-handdrawn-v1.png)作为风格及编辑参考，生成新的独立版本。原始样图与其[生成提示](ch03-prompt-injection-handdrawn-v1.prompt.txt)保留。

第四章 `v3` 以保留的 [v2 图片](ch04-data-boundary-handdrawn-v2.png)为编辑输入，仅补充底价外发被阻止的路径。

## 验证范围

逐张检查了画面中的短标签、箭头方向、示意范围和文字密度。保存的 PNG 与工具返回的图片文件内容一致。正文只插入图片及图注，既有文字段落保留。文件签名、尺寸、图片引用、本地链接和空白格式通过本地检查。

## 英文配图

[英文正文](../../ai-safety.en.md)使用独立的英文图片文件，中文版继续使用上表原图。2026-11-23 使用内置 ImageGen 编辑原图，仅替换短标签，保留手绘风格、构图、配色和箭头含义。每张图的完整英文提示保存在对应文件中。

| 章节 | 英文图片 | 图中短标签 | 生成提示 |
| --- | --- | --- | --- |
| 一 | [图片](ch01-ai-capabilities-handdrawn-en-v1.png) | Data / Tools / Actions | [Prompt](ch01-ai-capabilities-handdrawn-en-v1.prompt.txt) |
| 二 | [图片](ch02-training-controls-handdrawn-en-v1.png) | Train / Detect / Authorize | [Prompt](ch02-training-controls-handdrawn-en-v1.prompt.txt) |
| 三 | [图片](ch03-prompt-injection-handdrawn-en-v1.png) | User / Content / Tools | [Prompt](ch03-prompt-injection-handdrawn-en-v1.prompt.txt) |
| 四 | [图片](ch04-data-boundary-handdrawn-en-v1.png) | Internal / Supplier / Price limit | [Prompt](ch04-data-boundary-handdrawn-en-v1.prompt.txt) |
| 五 | [图片](ch05-execution-boundary-handdrawn-en-v1.png) | Agent / Python / Tools | [Prompt](ch05-execution-boundary-handdrawn-en-v1.prompt.txt) |
| 六 | [图片](ch06-evidence-verification-handdrawn-en-v1.png) | Reply / Log / Outcome | [Prompt](ch06-evidence-verification-handdrawn-en-v1.prompt.txt) |

六张英文图已逐张检查，未增加段落说明。中英文配图随完整网站导出到 `articles/media/ai-safety/`，本地预览使用站内图片地址。加入网站目录和生成本地页面不等于已部署到公网。
